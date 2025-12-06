"""
Регистрация, аутентификация и управление сессиями пользователей.
  1. Регистрация и подтверждение email
  2. Аутентификация (вход/выход)
  3. Восстановление пароля
  4. Управление email (смена/отмена)
  5. Обновление профиля (имя пользователя)
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import (
    Blueprint, request, redirect, url_for,
    render_template, jsonify, make_response, g, current_app
)
from flask_jwt_extended import (
    get_jwt_identity, decode_token, verify_jwt_in_request,
    get_jwt, unset_jwt_cookies, create_access_token
)
from extensions import db
from models import User, UserToken, IPAttemptLog
from utils.tokens import generate_password_reset_token, generate_email_confirmation_token
from utils.mail import send_password_reset_email, send_confirm_email, normalize_email
from utils.ip_log import (
    get_client_ip, get_or_create_ip_log,
    decrement_recovery_attempts, bind_ip_to_user_and_reset_attempts,
    update_ip_log_with_user_agent
)
from utils.user_sessions import create_access_token_for_user
from utils.responses import render_or_json


# Инициализация Blueprint и логгера
auth_bp = Blueprint('session', __name__)
auth_logger = logging.getLogger('app.auth')



# 1. РЕГИСТРАЦИЯ И ПОДТВЕРЖДЕНИЕ EMAIL
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Регистрация нового пользователя.
    - Поддерживает HTML-форму и JSON-API.
    - Требует валидный email и совпадение паролей.
    - Создаёт пользователя и отправляет письмо подтверждения.
    """
    if request.method == 'POST':
        client_ip = get_client_ip()
        data = request.get_json()

        if not data:
            auth_logger.warning(f"Регистрация: неверный формат данных с IP {client_ip}")
            return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

        username = data.get('username', '').strip()
        raw_email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        if not all([username, raw_email, password, confirm_password]):
            return jsonify({'success': False, 'errors': ['Все поля обязательны']})

        if password != confirm_password:
            auth_logger.warning(f"Регистрация: пароли не совпадают (username: {username}, IP: {client_ip})")
            return jsonify({'success': False, 'errors': ['Пароли не совпадают.']})

        email = normalize_email(raw_email)
        if email is None:
            auth_logger.warning(f"Регистрация: некорректный email '{raw_email}' с IP {client_ip}")
            return jsonify({'success': False, 'errors': ['Указанный email некорректен.']}), 400

        # Проверка уникальности имени/email (регистронезависимо)
        existing_user = User.query.filter(
            (User.username.ilike(username)) | (User.email.ilike(email))
        ).first()
        if existing_user:
            auth_logger.warning(f"Регистрация: дубль (username: {username}, email: {email}, IP: {client_ip})")
            return jsonify({
                'success': False,
                'errors': ['Пользователь с таким именем или email уже существует.']
            }), 400

        # Отправка письма подтверждения
        token = generate_email_confirmation_token(email)
        confirm_url = url_for('session.confirm_email', token=token, _external=True)
        if not send_confirm_email(email, confirm_url):
            auth_logger.error(f"Регистрация: не удалось отправить письмо на {email} (IP: {client_ip})")
            return jsonify({
                'success': False,
                'errors': ['Не удалось отправить письмо. Проверьте корректность email.']
            }), 400

        # Создание пользователя
        new_user = User(username=username, email=email, created_at=datetime.now(timezone.utc))
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            bind_ip_to_user_and_reset_attempts(new_user)
            auth_logger.info(f"Успешная регистрация: user_id={new_user.id}, username={username}, email={email}, IP={client_ip}")
            return jsonify({
                'success': True,
                'message': 'Пользователь успешно зарегистрирован! Ссылка для подтверждения отправлена на email.'
            })
        except Exception as e:
            db.session.rollback()
            auth_logger.exception(f"Критическая ошибка при регистрации (username: {username}, email: {email}, IP: {client_ip})")
            return jsonify({'success': False, 'errors': ['Ошибка при регистрации.']}), 500

    return render_template('auth/register.html')


@auth_bp.route('/confirm-email', methods=['GET'])
def confirm_email():
    """
    Подтверждение email по токену из ссылки.
    - Проверяет тип и содержимое токена.
    - Подтверждает email, если ещё не подтверждён.
    """
    token = request.args.get('token')
    client_ip = get_client_ip()

    if not token:
        auth_logger.warning(f"Подтверждение email: токен отсутствует, IP: {client_ip}")
        return render_or_json(
            template_name='auth/confirm_email.html',
            json_data={'message': 'Токен не предоставлен.'},
            status_code=400,
            is_success=False
        )

    try:
        decoded_token = decode_token(token)
        if decoded_token.get('type') != 'email_confirmation':
            raise ValueError("Недопустимый тип токена")
        email = decoded_token.get('sub')
        if not email:
            raise ValueError("Email отсутствует в токене")

        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("Пользователь не найден")

        if user.confirm_email:
            auth_logger.info(f"Повторное подтверждение email: {email}, IP: {client_ip}")
            return render_or_json(
                template_name='auth/confirm_email.html',
                json_data={'message': 'Email уже подтверждён.'},
                status_code=200,
                is_success=True
            )

        user.confirm_email = True
        db.session.commit()
        auth_logger.info(f"Email подтверждён: user_id={user.id}, email={email}, IP: {client_ip}")

        return render_or_json(
            template_name='auth/confirm_email.html',
            json_data={'message': 'Email успешно подтверждён!'},
            status_code=200,
            is_success=True
        )

    except Exception as e:
        auth_logger.warning(f"Ошибка подтверждения email: {str(e)}, токен={token[:20]}..., IP: {client_ip}")
        return render_template('auth/confirm_email.html', error="Неверный или просроченный токен."), 400



# 2. АУТЕНТИФИКАЦИЯ (ВХОД / ВЫХОД)
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Аутентификация пользователя.
    - Требует подтверждённый email.
    - Блокирует вход с заблокированных IP.
    - При успехе — выдаёт JWT и сохраняет токен в БД.
    """
    if request.method == 'GET':
        return render_template('auth/login.html')

    client_ip = get_client_ip()
    data = request.get_json()

    if not data:
        auth_logger.warning(f"Вход: неверный формат данных, IP: {client_ip}")
        return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

    # Проверка блокировки IP
    ip_log = IPAttemptLog.query.filter_by(ip_address=client_ip).first()
    if ip_log and ip_log.is_blocked:
        auth_logger.warning(f"Вход заблокирован: IP {client_ip} в чёрном списке")
        return jsonify({
            'success': False,
            'errors': ['Ваш IP-адрес заблокирован. Обратитесь к администратору.']
        }), 403

    username_or_email = data.get('username')
    password = data.get('password')

    user = User.query.filter(db.or_(
        User.username == username_or_email,
        User.email == username_or_email
    )).first()

    if not user or not user.check_password(password):
        auth_logger.warning(f"Неудачная попытка входа: {username_or_email}, IP: {client_ip}")
        return jsonify({'success': False, 'errors': ['Неверное имя пользователя или пароль']}), 401

    if not user.confirm_email:
        auth_logger.info(f"Вход запрещён: email не подтверждён, user_id={user.id}, IP: {client_ip}")
        return jsonify({
            'success': False,
            'errors': ['Подтвердите email. Письмо отправлено при регистрации.']
        }), 401

    # Сброс лимитов и привязка IP
    bind_ip_to_user_and_reset_attempts(user)
    update_ip_log_with_user_agent(client_ip)

    access_token = create_access_token_for_user(user.id)
    db.session.commit()

    auth_logger.info(f"Успешный вход: user_id={user.id}, IP: {client_ip}")
    return jsonify({
        'success': True,
        'message': 'Авторизация прошла успешно.',
        'access_token': access_token
    })


@auth_bp.route('/logout', methods=['GET'])
def logout():
    """
    Выход из системы.
    - Аннулирует текущий JWT в БД.
    - Удаляет куки на клиенте.
    - Перенаправляет на главную.
    """
    try:
        verify_jwt_in_request()
        jti = get_jwt()["jti"]
        current_user_id = get_jwt_identity()
        token = UserToken.query.filter_by(jti=jti, user_id=current_user_id).first()
        if token:
            token.revoked = True
            db.session.commit()
    except Exception:
        # Игнорируем ошибки: пользователь может быть не авторизован
        pass

    response = make_response(redirect(url_for('main.index')))
    unset_jwt_cookies(response)
    return response



# 3. ВОССТАНОВЛЕНИЕ ПАРОЛЯ
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """
    Инициация сброса пароля.
    - Учитывает лимиты попыток восстановления по IP.
    - Отправляет письмо ТОЛЬКО подтверждённым пользователям.
    - Обрабатывает только HTML-форму (POST).
    """
    if request.method == 'GET':
        return render_template('auth/reset_password.html', mess='Введите email, указанный при регистрации.')

    client_ip = get_client_ip()
    if not client_ip:
        auth_logger.error("Восстановление: не удалось получить IP")
        return render_template('auth/reset_password.html', err='Ошибка получения IP-адреса.')

    user_ip = get_or_create_ip_log(client_ip)
    if user_ip.recovery_attempts_count <= 0:
        auth_logger.warning(f"Восстановление: попытки исчерпаны, IP: {client_ip}")
        return render_template('auth/reset_password.html', err="Вы исчерпали все попытки восстановления пароля.")

    raw_email = request.form.get('email', '').strip()
    email = normalize_email(raw_email)

    if email is None:
        new_count = decrement_recovery_attempts(user_ip)
        message = f"Введите корректный email. Осталось попыток: {new_count}"
        return render_template('auth/reset_password.html', err=message if new_count > 0 else "Вы исчерпали все попытки.")

    user = User.query.filter_by(email=email).first()
    if not user:
        new_count = decrement_recovery_attempts(user_ip)
        message = f"Пользователь не найден. Осталось попыток: {new_count}"
        return render_template('auth/reset_password.html', err=message if new_count > 0 else "Вы исчерпали все попытки.")

    if not user.confirm_email:
        auth_logger.info(f"Восстановление: email не подтверждён, user_id={user.id}, IP: {client_ip}")
        return render_template('auth/reset_password.html', err="Сначала подтвердите email.")

    # Отправка ссылки
    token = generate_password_reset_token(user.email)
    reset_url = url_for('session.reset_password_with_token', token=token, _external=True)
    if not send_password_reset_email(user, reset_url):
        auth_logger.error(f"Не удалось отправить ссылку на {email}, IP: {client_ip}")
        return render_template('auth/reset_password.html', err="Не удалось отправить письмо. Попробуйте позже.")

    auth_logger.info(f"Ссылка восстановления отправлена: user_id={user.id}, email={email}, IP: {client_ip}")
    return render_template('auth/reset_password.html', mess="Ссылка для восстановления пароля отправлена на email.")


@auth_bp.route('/reset-password/token', methods=['GET', 'POST'])
def reset_password_with_token():
    """
    Установка нового пароля по токену.
    - Поддерживает HTML-форму и JSON-API.
    - Требует валидный токен с типом 'password_reset'.
    """
    token = request.args.get('token')
    client_ip = get_client_ip()

    if not token:
        if request.is_json:
            auth_logger.warning(f"Сброс пароля: токен не указан, IP: {client_ip}")
            return jsonify({"error": "Токен не указан"}), 400
        return render_template('auth/reset_password.html'), 400

    try:
        decoded = decode_token(token)
        if decoded.get('type') != 'password_reset':
            raise ValueError("Недопустимый тип токена")
        email = decoded.get('sub')
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("Пользователь не найден")
    except Exception as e:
        auth_logger.warning(f"Неверный токен сброса: {str(e)}, IP: {client_ip}")
        if request.is_json:
            return jsonify({"error": "Неверный или просроченный токен"}), 400
        return render_template('auth/reset_password_form.html', err="Неверный или просроченный токен."), 400

    if request.method == 'POST':
        # Получение данных
        if request.is_json:
            data = request.get_json()
            password = data.get('password')
            confirm_password = data.get('confirm_password')
        else:
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password:
            if request.is_json:
                return jsonify({"error": "Пароль не может быть пустым"}), 400
            return render_template('auth/reset_password_form.html', token=token, err="Пароль не может быть пустым")

        if password != confirm_password:
            auth_logger.warning(f"Сброс пароля: пароли не совпадают, user_id={user.id}, IP: {client_ip}")
            if request.is_json:
                return jsonify({"error": "Пароли не совпадают"}), 400
            return render_template('auth/reset_password_form.html', token=token, err="Пароли не совпадают")

        user.set_password(password)
        db.session.commit()
        bind_ip_to_user_and_reset_attempts(user)
        auth_logger.info(f"Пароль изменён: user_id={user.id}, IP: {client_ip}")

        if request.is_json:
            return jsonify({"success": True, "message": "Пароль успешно изменён"}), 200
        return redirect(url_for('session.login'))

    return render_template('auth/reset_password_form.html', token=token)



# 4. УПРАВЛЕНИЕ EMAIL
@auth_bp.route('/confirm-email-change', methods=['GET'])
def confirm_email_change():
    """
    Подтверждение смены email по токену.
    - Проверяет соответствие временного email и уникальность нового.
    - Применяет изменения при успехе.
    """
    token = request.args.get('token')
    if not token:
        return render_template('auth/confirm_email.html', error="Токен не предоставлен."), 400

    try:
        decoded = decode_token(token)
        if decoded.get('type') != 'email_change':
            raise ValueError("Неверный тип токена")
        user_id = decoded.get('user_id')
        new_email = decoded.get('sub')
        if not user_id or not new_email:
            raise ValueError("Отсутствуют user_id или email")

        user = User.query.get(user_id)
        if not user or user.pending_email != new_email:
            raise ValueError("Несоответствие данных")
        if User.query.filter(User.id != user.id, User.email == new_email).first():
            raise ValueError("Email уже занят")

        old_email = user.email
        user.email = new_email
        user.pending_email = None
        db.session.commit()
        auth_logger.info(f"Email изменён: {old_email} → {new_email}")
        return render_template('auth/confirm_email.html', message="Email успешно изменён!")

    except Exception as e:
        auth_logger.warning(f"Ошибка подтверждения смены email: {str(e)}")
        return render_template('auth/confirm_email.html', error="Неверный или просроченный токен."), 400


@auth_bp.route('/change-email-request', methods=['POST'])
def change_email_request():
    """
    Запрос на смену email.
    - Доступен только авторизованным.
    - Проверяет уникальность и корректность нового email.
    - Отправляет письмо на НОВЫЙ email.
    """
    user = g.current_user
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

    new_raw_email = data['email'].strip()
    if not new_raw_email or '@' not in new_raw_email or '.' not in new_raw_email.split('@')[-1]:
        return jsonify({'success': False, 'errors': ['Некорректный email']}), 400

    new_email = new_raw_email.lower()
    if new_email == user.email:
        return jsonify({'success': False, 'errors': ['Это текущий email']}), 400
    if User.query.filter(User.email == new_email).first():
        return jsonify({'success': False, 'errors': ['Email уже используется']}), 409

    user.pending_email = new_email
    db.session.commit()

    ttl_minutes = current_app.config.get('UNCONFIRMED_USER_TTL_MINUTES', 1440)
    token = create_access_token(
        identity=new_email,
        expires_delta=timedelta(minutes=ttl_minutes),
        additional_claims={'type': 'email_change', 'user_id': user.id}
    )
    confirm_url = url_for('session.confirm_email_change', token=token, _external=True)

    if not send_confirm_email(new_email, confirm_url):
        user.pending_email = None
        db.session.commit()
        auth_logger.error(f"Не удалось отправить письмо смены email на {new_email}, user_id={user.id}")
        return jsonify({'success': False, 'errors': ['Не удалось отправить письмо. Проверьте email.']}), 500

    auth_logger.info(f"Запрос смены email: user_id={user.id}, новый={new_email}")
    return jsonify({
        'success': True,
        'message': 'На новый email отправлена ссылка для подтверждения.'
    })


@auth_bp.route('/cancel-email-change', methods=['POST'])
def cancel_email_change():
    """
    Отмена запроса на смену email.
    - Удаляет значение из pending_email.
    """
    user = g.current_user
    if not user.pending_email:
        return jsonify({'success': False, 'error': 'Нет активного запроса на смену email'}), 400

    old_pending = user.pending_email
    user.pending_email = None
    db.session.commit()
    auth_logger.info(f"Отменён запрос на смену email: user_id={user.id}, pending_email={old_pending}")
    return jsonify({'success': True, 'message': 'Запрос на смену email отменён'})



# 5. ОБНОВЛЕНИЕ ПРОФИЛЯ
@auth_bp.route('/api/user/update-username', methods=['POST'])
def update_username():
    """
    Обновление имени пользователя (username).
    - Доступен только авторизованным.
    - Проверяет длину, уникальность и отличие от текущего.
    """
    user = g.current_user
    data = request.get_json()
    if not data or 'username' not in data:
        return jsonify({'success': False, 'error': 'Отсутствует имя'}), 400

    new_username = data['username'].strip()
    if len(new_username) < 2:
        return jsonify({'success': False, 'error': 'Имя должно содержать минимум 2 символа'}), 400
    if new_username.lower() == user.username.lower():
        return jsonify({'success': False, 'error': 'Это текущее имя'}), 400

    existing = User.query.filter(
        User.username.ilike(new_username),
        User.id != user.id
    ).first()
    if existing:
        return jsonify({'success': False, 'error': 'Пользователь с таким именем уже существует.'}), 400

    old_username = user.username
    user.username = new_username
    db.session.commit()
    auth_logger.info(f"Имя изменено: user_id={user.id}, {old_username} → {new_username}")
    return jsonify({'success': True, 'username': user.username})