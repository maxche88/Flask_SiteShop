import logging
import os
from flask import Blueprint, jsonify, request, current_app, abort, g
from werkzeug.exceptions import NotFound
from models import User, IPAttemptLog, UserToken
from extensions import db
from utils.cleanup import get_unconfirmed_cutoff
from datetime import datetime, timezone


admin_system_bp = Blueprint('admin_system', __name__, url_prefix='/admin/api')
sys_logger = logging.getLogger('app.system')



def _serialize_users(users):
    """
    Преобразует список объектов User в список словарей (JSON),
    чтобы можно было отправить данные пользователей через API (в admin_panel).
    """
    cutoff_naive = get_unconfirmed_cutoff()
    result = []
    for u in users:
        is_old_unconfirmed = (
            not u.confirm_email and
            u.created_at is not None and
            u.created_at < cutoff_naive
        )

        user_agent = None
        if u.ip_logs:
            latest_log = max(u.ip_logs, key=lambda log: log.id)
            user_agent = latest_log.user_agent

        # Проверяем активную сессию и оставшееся время
        session_minutes_left = None
        now = datetime.now(timezone.utc)

        token = UserToken.query.filter(
            UserToken.user_id == u.id,
            UserToken.revoked.is_(False),
            UserToken.expires_at > now
        ).order_by(UserToken.expires_at.asc()).first()

        if token:
            delta = token.expires_at - datetime.now(timezone.utc)
            minutes_left = int(delta.total_seconds() // 60)
            if minutes_left > 0:
                session_minutes_left = minutes_left

        result.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'confirm_email': u.confirm_email,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'is_old_unconfirmed': is_old_unconfirmed,
            'ip_logs_count': len(u.ip_logs),
            'role': u.role,
            'user_agent': user_agent,
            'session_minutes_left': session_minutes_left
        })

    return result

# === Роуты ===

@admin_system_bp.route('/users/search', methods=['GET'])
def search_users():
    """
    Поиск пользователей в админке по ID, имени, email или дате регистрации.
    Поддерживает форматы даты: DD.MM.YYYY и YYYY-MM-DD. 
    """
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    # Поиск по ID
    try:
        user_id = int(query)
        users_by_id = User.query.filter(User.id == user_id).all()
        if users_by_id:
            return jsonify(_serialize_users(users_by_id))
    except ValueError:
        pass

    # Поиск по тексту
    safe_query = query.replace('%', '\\%').replace('_', '\\_')
    like_pattern = f"%{safe_query}%"
    
    text_matches = User.query.filter(
        db.or_(
            User.username.ilike(like_pattern),
            User.email.ilike(like_pattern)
        )
    ).all()

    # Поиск по дате
    date_matches = []

    try:
        dt_part = query.split(',', 1)[0].strip() if ',' in query else query
        if '.' in dt_part:
            parsed_date = datetime.strptime(dt_part, '%d.%m.%Y').date()
        else:
            parsed_date = datetime.fromisoformat(dt_part).date()
        date_matches = User.query.filter(db.cast(User.created_at, db.Date) == parsed_date).all()
    except (ValueError, TypeError):
        pass

    # Объединяем и убираем дубли
    all_matches = list({u.id: u for u in (text_matches + date_matches)}.values())
    return jsonify(_serialize_users(all_matches))


@admin_system_bp.route('/users', methods=['GET'])
def get_all_users():
    try:
        user = g.current_user
        if user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        users = User.query.all()
        return jsonify(_serialize_users(users))
    except Exception as e:
        sys_logger.error(f"Ошибка в get_all_users: {e}")
        return jsonify({'error': 'Ошибка при загрузке пользователей'}), 500


@admin_system_bp.route('/users/<int:user_id>/role', methods=['PATCH'])
def update_user_role(user_id):
    """
    Изменяет роль пользователя (admin/suser/user/tester). Доступен только администраторам. 
    """
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Только администратор может менять роли'}), 403

    data = request.get_json()
    new_role = data.get('role')

    if new_role not in ['admin', 'suser', 'user', 'tester']:
        return jsonify({'error': 'Недопустимая роль'}), 400

    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    target_user.role = new_role
    db.session.commit()

    return jsonify({'success': True, 'role': target_user.role})


@admin_system_bp.route('/users/delete-selected', methods=['DELETE'])
def delete_selected_users():
    """
    Удаляет выбранных пользователей.
    Связанные данные обрабатываются каскадно на уровне БД:
      - CartItem → удаляются полностью
      - IPAttemptLog → удаляются полностью
      - Shop.user_id → обнуляется (SET NULL), товары остаются
    Токены отзываются (revoked=True).
    """
    user = g.current_user

    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    user_ids = data.get('user_ids', [])
    if not user_ids:
        return jsonify({'error': 'Не указаны ID'}), 400

    try:
        user_ids = list(set(int(uid) for uid in user_ids))
    except (ValueError, TypeError):
        return jsonify({'error': 'Некорректный формат ID'}), 400

    if user.id in user_ids:
        return jsonify({'error': 'Нельзя удалить самого себя'}), 400

    # Отзываем токены (логическая операция — не удаляем физически)
    UserToken.query.filter(UserToken.user_id.in_(user_ids)).update(
        {'revoked': True}, synchronize_session=False
    )

    # Удаляем пользователей — КАСКАД СДЕЛАЕТ ОСТАЛЬНОЕ!
    deleted_count = User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        sys_logger.error("Ошибка при удалении пользователей: %s", str(e), exc_info=True)
        return jsonify({'error': 'Ошибка при удалении'}), 500

    return jsonify({'success': True, 'deleted_count': deleted_count})


@admin_system_bp.route('/users/delete-old-unconfirmed', methods=['DELETE'])
def delete_old_unconfirmed():
    """
    Массово удаляет неподтверждённые аккаунты, созданные более 24 часов назад (или другого срока из настроек).
    """
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    cutoff_naive = get_unconfirmed_cutoff()

    old_users = User.query.filter(
        User.confirm_email.is_(False),
        User.created_at.isnot(None),
        User.created_at < cutoff_naive
    ).all()

    user_ids = [u.id for u in old_users]

    if user_ids:
        IPAttemptLog.query.filter(IPAttemptLog.user_id.in_(user_ids)).delete(synchronize_session=False)
        User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.session.commit()

    return jsonify({'success': True, 'deleted_count': len(user_ids)})


@admin_system_bp.route('/users/revoke-sessions', methods=['POST'])
def revoke_user_sessions():
    """Отзыв всех сессий выбранных пользователей через UserToken."""
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    user_ids = request.get_json().get('user_ids', [])
    if not user_ids:
        return jsonify({'error': 'Не указаны user_ids'}), 400

    revoked_count = 0
    for uid in user_ids:
        try:
            user_id = int(uid)
            if db.session.get(User, user_id):
                UserToken.query.filter_by(user_id=user_id).update({'revoked': True})
                revoked_count += 1
        except (ValueError, TypeError):
            continue

    db.session.commit()
    return jsonify({'success': True, 'revoked_count': revoked_count})


@admin_system_bp.route('/users/delete-tokens', methods=['DELETE'])
def delete_user_tokens():
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    now = datetime.now(timezone.utc)
    data = request.get_json() or {}

    if data.get('user_ids'):
        user_ids = data['user_ids']
        if not isinstance(user_ids, list) or not user_ids:
            return jsonify({'error': 'Некорректный список user_ids'}), 400

        # Удаляем ТОЛЬКО просроченные токены (даже если не отозваны)
        deleted_count = UserToken.query.filter(
            UserToken.user_id.in_(user_ids),
            UserToken.expires_at < now
        ).delete(synchronize_session=False)

    else:
        # Удаляем ВСЕ просроченные токены (игнорируем revoked!)
        deleted_count = UserToken.query.filter(
            UserToken.expires_at < now
        ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({'success': True, 'deleted_count': deleted_count})


# Получить все логи
@admin_system_bp.route('/logs')
def get_logs():
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403
        
    logs = IPAttemptLog.query.order_by(IPAttemptLog.id.desc()).all()
    return jsonify([{
        'user_id': log.user_id,
        'ip_address': log.ip_address,
        'recovery_attempts_count': log.recovery_attempts_count,
        'is_blocked': log.is_blocked
    } for log in logs])


# Поиск
@admin_system_bp.route('/logs/search')
def search_logs():
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403
        
    q = request.args.get('q', '').strip()
    is_blocked = request.args.get('is_blocked')

    query = IPAttemptLog.query

    if is_blocked is not None:
        blocked_val = is_blocked.lower() == 'true'
        query = query.filter(IPAttemptLog.is_blocked == blocked_val)
    elif q:
        if q.isdigit():
            query = query.filter(IPAttemptLog.user_id == int(q))
        else:
            query = query.filter(IPAttemptLog.ip_address.ilike(f'%{q}%'))

    logs = query.order_by(IPAttemptLog.id.desc()).all()
    return jsonify([{
        'user_id': log.user_id,
        'ip_address': log.ip_address,
        'recovery_attempts_count': log.recovery_attempts_count,
        'is_blocked': log.is_blocked
    } for log in logs])


# Блокировка записей
@admin_system_bp.route('/logs/block', methods=['PATCH'])
def block_logs():
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    ip_addresses = data.get('ip_addresses', [])

    if not ip_addresses:
        return jsonify({'error': 'Не указаны IP-адреса'}), 400

    if not isinstance(ip_addresses, list):
        return jsonify({'error': 'Некорректный формат IP-адресов'}), 400

    try:
        # Находим все записи с такими IP и блокируем их
        updated = IPAttemptLog.query.filter(
            IPAttemptLog.ip_address.in_(ip_addresses)
        ).update({'is_blocked': True}, synchronize_session=False)

        db.session.commit()
        return jsonify({'blocked_count': updated}), 200

    except Exception as e:
        db.session.rollback()
        sys_logger.error(f"Ошибка при блокировке IP: {e}", exc_info=True)
        return jsonify({'error': 'Ошибка при обновлении базы данных'}), 500


@admin_system_bp.route('/logs/unblock', methods=['PATCH'])
def unblock_logs():
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403
        
    ip_addresses = request.get_json().get('ip_addresses', [])
    IPAttemptLog.query.filter(IPAttemptLog.ip_address.in_(ip_addresses)) \
                      .update({'is_blocked': False})
    db.session.commit()
    return jsonify({'success': True})


# ФАЙЛОВЫЕ ЛОГИ

@admin_system_bp.route('/logs/files')
def list_log_files():
    """Возвращает список .log файлов из папки LOG_DIR"""
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    log_dir = current_app.config.get('LOG_DIR')
    if not log_dir or not os.path.isdir(log_dir):
        return jsonify([])

    try:
        files = [f for f in os.listdir(log_dir) if f.endswith('.log') and os.path.isfile(os.path.join(log_dir, f))]
        return jsonify(sorted(files))
    except Exception as e:
        sys_logger.error("Ошибка при чтении списка лог-файлов: %s", e)
        return jsonify([]), 500


@admin_system_bp.route('/logs/files/<filename>')
def get_log_file_content(filename):
    """Возвращает содержимое указанного .log файла как plain text"""
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Защита от path traversal
    if not filename.endswith('.log') or '..' in filename or filename.startswith('/'):
        abort(400)

    # Дополнительная защита: оставляем только basename
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        abort(400)

    log_dir = current_app.config.get('LOG_DIR')
    if not log_dir:
        abort(500)

    filepath = os.path.join(log_dir, safe_filename)

    if not os.path.isfile(filepath):
        raise NotFound("Файл лога не найден")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Возвращаем как plain text, НЕ как JSON!
        return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except UnicodeDecodeError:
        sys_logger.warning("Файл %s не в кодировке UTF-8", safe_filename)
        abort(400, description="Файл не является текстовым (ожидается UTF-8)")
    except Exception as e:
        sys_logger.error("Ошибка чтения лог-файла %s: %s", safe_filename, e)
        abort(500)


@admin_system_bp.route('/logs/files/<filename>/clear', methods=['POST'])
def clear_log_file(filename):
    user = g.current_user
    if user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    # Защита от path traversal
    if not filename.endswith('.log') or '..' in filename or filename.startswith('/'):
        abort(400)

    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        abort(400)

    log_dir = current_app.config.get('LOG_DIR')
    if not log_dir:
        abort(500)

    filepath = os.path.join(log_dir, safe_filename)
    if not os.path.isfile(filepath):
        abort(404)

    try:
        # Очищаем файл (делаем пустым)
        open(filepath, 'w').close()
        return jsonify({'success': True, 'message': f'Файл {filename} очищен'})
    except Exception as e:
        sys_logger.error("Ошибка очистки лог-файла %s: %s", safe_filename, e)
        abort(500)