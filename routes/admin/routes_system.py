from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, IPAttemptLog
from utils.cleanup import get_unconfirmed_cutoff
from utils.time import current_time
from datetime import timedelta

admin_system_bp = Blueprint('admin_system', __name__, url_prefix='/admin/api')

# Получить всех пользователей
@admin_system_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if current_user.role not in 'admin':
        return jsonify({'error': 'Доступ запрещён'}), 403

    users = User.query.all()
    result = []

    cutoff_naive = get_unconfirmed_cutoff()

    for u in users:
        # Сравниваем только если created_at не None
        is_old_unconfirmed = (
            not u.confirm_email and
            u.created_at is not None and
            u.created_at < cutoff_naive  # ← просто сравниваем с cutoff
        )

        result.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'confirm_email': u.confirm_email,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'is_old_unconfirmed': is_old_unconfirmed,
            'ip_logs_count': len(u.ip_logs)
        })
    return jsonify(result)

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