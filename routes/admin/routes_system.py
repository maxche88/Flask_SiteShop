import logging
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, IPAttemptLog, UserToken
from utils.cleanup import get_unconfirmed_cutoff
from datetime import datetime

admin_system_bp = Blueprint('admin_system', __name__, url_prefix='/admin/api')
system_logger = logging.getLogger('app.auth')

def _serialize_users(users):
    """
    Преобразует список объектов User в список словарей (JSON),
    чтобы можно было отправить данные пользователей через API (например, в админку).
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
        token = UserToken.query.filter(
            UserToken.user_id == u.id,
            UserToken.revoked.is_(False),
            UserToken.expires_at > datetime.utcnow()
        ).order_by(UserToken.expires_at.asc()).first()

        if token:
            delta = token.expires_at - datetime.utcnow()
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
            'session_minutes_left': session_minutes_left  # None или число
        })
    return result

# === Роуты ===

@admin_system_bp.route('/users/search', methods=['GET'])
@jwt_required()
def search_users():
    """
    Поиск пользователей в админке по ID, имени, email или дате регистрации.
    Поддерживает форматы даты: DD.MM.YYYY и YYYY-MM-DD. 
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role != 'admin':  # ✅ Исправлено: строгое сравнение
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

        from datetime import datetime
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
@jwt_required()
def get_all_users():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        if current_user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        users = User.query.all()
        return jsonify(_serialize_users(users))
    except Exception as e:

        system_logger.error(f"Ошибка в get_all_users: {e}")
        return jsonify({'error': 'Ошибка при загрузке пользователей'}), 500


@admin_system_bp.route('/users/<int:user_id>/role', methods=['PATCH'])
@jwt_required()
def update_user_role(user_id):
    """
    Изменяет роль пользователя (admin/suser/user). Доступен только администраторам. 
    """
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


@admin_system_bp.route('/users/delete-selected', methods=['DELETE'])
@jwt_required()
def delete_selected_users():
    """
    Удаляет выбранных пользователей и всю связанную с ними информацию.
    Токены не удаляются, а помечаются как отозванные (revoked=True).
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    user_ids = data.get('user_ids', [])
    if not user_ids:
        return jsonify({'error': 'Не указаны ID'}), 400

    # Отзываем токены выбранных пользователей
    from models import UserToken
    UserToken.query.filter(
        UserToken.user_id.in_(user_ids)
    ).update({'revoked': True}, synchronize_session=False)

    # Удаляем IP-логи
    IPAttemptLog.query.filter(
        IPAttemptLog.user_id.in_(user_ids)
    ).delete(synchronize_session=False)

    # Удаляем пользователей
    User.query.filter(
        User.id.in_(user_ids)
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({'success': True, 'deleted_count': len(user_ids)})


@admin_system_bp.route('/users/delete-old-unconfirmed', methods=['DELETE'])
@jwt_required()
def delete_old_unconfirmed():
    """
    Массово удаляет неподтверждённые аккаунты, созданные более 24 часов назад (или другого срока из настроек).
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role != 'admin':
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
@jwt_required()
def revoke_user_sessions():
    """Отзыв всех сессий выбранных пользователей через UserToken."""
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    user_ids = request.get_json().get('user_ids', [])
    if not user_ids:
        return jsonify({'error': 'Не указаны user_ids'}), 400

    revoked_count = 0
    for uid in user_ids:
        try:
            user_id = int(uid)
            if User.query.get(user_id):
                UserToken.query.filter_by(user_id=user_id).update({'revoked': True})
                revoked_count += 1
        except (ValueError, TypeError):
            continue

    db.session.commit()
    return jsonify({'success': True, 'revoked_count': revoked_count})


@admin_system_bp.route('/users/delete-tokens', methods=['DELETE'])
@jwt_required()
def delete_user_tokens():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    data = request.get_json()
    now = datetime.utcnow()

    if data.get('user_ids'):
        user_ids = data['user_ids']
        if not isinstance(user_ids, list) or not user_ids:
            return jsonify({'error': 'Некорректный список user_ids'}), 400

        deleted_count = UserToken.query.filter(
            UserToken.user_id.in_(user_ids),
            (UserToken.revoked == True) | (UserToken.expires_at < now)
        ).delete()

    else:
        deleted_count = UserToken.query.filter(
            (UserToken.revoked == True) | (UserToken.expires_at < now)
        ).delete()

    db.session.commit()
    return jsonify({'success': True, 'deleted_count': deleted_count})