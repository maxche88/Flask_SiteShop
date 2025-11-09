from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, IPAttemptLog
from utils.cleanup import get_unconfirmed_cutoff

admin_system_bp = Blueprint('admin_system', __name__, url_prefix='/admin/api')


# Поиск пользователей
@admin_system_bp.route('/users/search', methods=['GET'])
@jwt_required()
def search_users():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role not in 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    # Попробуем интерпретировать как ID (целое число)
    try:
        user_id = int(query)
        users_by_id = User.query.filter(User.id == user_id).all()
        if users_by_id:
            # Если найден по ID — возвращаем только его (точное совпадение)
            result = _serialize_users(users_by_id)
            return jsonify(result)
    except ValueError:
        pass  # Не число — ищем как текст

    # Поиск по тексту: username, email
    # Экранируем % и _ для LIKE
    safe_query = query.replace('%', '\\%').replace('_', '\\_')
    like_pattern = f"%{safe_query}%"

    text_matches = User.query.filter(
        db.or_(
            User.username.ilike(like_pattern),
            User.email.ilike(like_pattern)
        )
    ).all()

    # Поиск по дате: сравниваем строковое представление created_at
    # Поддерживаем форматы: "08.11.2025", "2025-11-08", "08.11.2025, 14:30"
    date_matches = []
    try:
        # Пробуем распарсить как дату в формате DD.MM.YYYY или ISO
        from datetime import datetime

        # Поддержка формата DD.MM.YYYY и DD.MM.YYYY, HH:MM
        if ',' in query:
            dt_part, _ = query.split(',', 1)
            dt_part = dt_part.strip()
        else:
            dt_part = query

        if '.' in dt_part:
            # Формат: DD.MM.YYYY
            parsed_date = datetime.strptime(dt_part, '%d.%m.%Y').date()
            date_matches = User.query.filter(
                db.cast(User.created_at, db.Date) == parsed_date
            ).all()
        else:
            # Пробуем ISO: YYYY-MM-DD
            parsed_date = datetime.fromisoformat(dt_part).date()
            date_matches = User.query.filter(
                db.cast(User.created_at, db.Date) == parsed_date
            ).all()
    except (ValueError, TypeError):
        pass  # Не дата — пропускаем

    # Объединяем результаты, убираем дубли
    all_matches = list({u.id: u for u in (text_matches + date_matches)}.values())

    result = _serialize_users(all_matches)
    return jsonify(result)


def _serialize_users(users):
    cutoff_naive = get_unconfirmed_cutoff()
    result = []
    for u in users:
        is_old_unconfirmed = (
            not u.confirm_email and
            u.created_at is not None and
            u.created_at < cutoff_naive
        )
        result.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'confirm_email': u.confirm_email,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'is_old_unconfirmed': is_old_unconfirmed,
            'ip_logs_count': len(u.ip_logs),
            'role': u.role
        })
    return result

# Получить всех пользователей
@admin_system_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role != 'admin':  # исправлено: было `not in 'admin'`
        return jsonify({'error': 'Доступ запрещён'}), 403

    users = User.query.all()
    result = []

    cutoff_naive = get_unconfirmed_cutoff()

    for u in users:
        is_old_unconfirmed = (
            not u.confirm_email and
            u.created_at is not None and
            u.created_at < cutoff_naive
        )

        # Получаем user_agent из первой (или последней) записи IP-лога
        user_agent = None
        if u.ip_logs:
            # Берём последнюю запись (самую свежую)
            latest_log = max(u.ip_logs, key=lambda log: log.id)
            user_agent = latest_log.user_agent

        result.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'confirm_email': u.confirm_email,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'is_old_unconfirmed': is_old_unconfirmed,
            'ip_logs_count': len(u.ip_logs),
            'role': u.role,
            'user_agent': user_agent  # ← новое поле
        })
        
    return jsonify(result)

# Изменить роль пользователя
@admin_system_bp.route('/users/<int:user_id>/role', methods=['PATCH'])
@jwt_required()
def update_user_role(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role != 'admin':
        return jsonify({'error': 'Только администратор может менять роли'}), 403

    data = request.get_json()
    new_role = data.get('role')

    if new_role not in ['admin', 'suser', 'user']:
        return jsonify({'error': 'Недопустимая роль'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    user.role = new_role
    db.session.commit()

    return jsonify({'success': True, 'role': user.role})

# Удалить выбранные по ID
@admin_system_bp.route('/users/delete-selected', methods=['DELETE'])
@jwt_required()
def delete_selected_users():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role not in 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    user_ids = data.get('user_ids', [])
    if not user_ids:
        return jsonify({'error': 'Не указаны ID'}), 400

    IPAttemptLog.query.filter(IPAttemptLog.user_id.in_(user_ids)).delete(synchronize_session=False)
    User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({'success': True, 'deleted_count': len(user_ids)})

# Удалить всех старых неподтверждённых
@admin_system_bp.route('/users/delete-old-unconfirmed', methods=['DELETE'])
@jwt_required()
def delete_old_unconfirmed():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role not in 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    # ТЕСТ: 1 минута вместо 24 часов
    cutoff_naive = get_unconfirmed_cutoff()

    old_users = User.query.filter(
        User.confirm_email.is_(False),
        User.created_at.isnot(None),
        User.created_at < cutoff_naive  # оба значения — naive
    ).all()

    user_ids = [u.id for u in old_users]

    if user_ids:
        IPAttemptLog.query.filter(IPAttemptLog.user_id.in_(user_ids)).delete(synchronize_session=False)
        User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        db.session.commit()

    return jsonify({'success': True, 'deleted_count': len(user_ids)})