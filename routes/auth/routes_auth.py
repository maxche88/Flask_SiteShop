# Регистрация. Аутентификация и управление сессией.
import logging
from flask import Blueprint, request, redirect, url_for, render_template, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, decode_token
from models import db, User
from utils.tokens import generate_password_reset_token, generate_email_confirmation_token
from utils.mail import send_password_reset_email, send_confirm_email, normalize_email
from utils.ip_log import get_client_ip, get_or_create_ip_log, decrement_recovery_attempts, bind_ip_to_user_and_reset_attempts, update_ip_log_with_user_agent

from utils.responses import render_or_json


auth_bp = Blueprint('session', __name__)
auth_logger = logging.getLogger('app.auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        client_ip = get_client_ip()

        if not data:
            auth_logger.warning(f"Регистрация: неверный формат данных с IP {client_ip}")
            return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

        username = data.get('username', '').strip()
        raw_email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        if not all([username, raw_email, password, confirm_password]):
            return jsonify({'success': False, 'errors': ['Все поля обязательны для заполнения.']})

        if password != confirm_password:
            auth_logger.warning(f"Регистрация: пароли не совпадают (username: {username}, IP: {client_ip})")
            return jsonify({'success': False, 'errors': ['Пароли не совпадают.']})
        
        email = normalize_email(raw_email)
        if email is None:
            auth_logger.warning(f"Регистрация: некорректный email '{raw_email}' с IP {client_ip}")
            return jsonify({
                'success': False,
                'errors': ['Указанный email некорректен.']
            }), 400
        
        existing_user = User.query.filter(
            (User.username.ilike(username)) | (User.email.ilike(email))
        ).first()

        if existing_user:
            auth_logger.warning(
                f"Регистрация: попытка создать дубль (username: {username}, email: {email}, IP: {client_ip})"
            )

            return jsonify({
                'success': False,
                'errors': ['Пользователь с таким именем или электронной почтой уже существует.']
            }), 400
        
        token = generate_email_confirmation_token(email)
        confirm_url = url_for('session.confirm_email', token=token, _external=True)
        is_email_sent = send_confirm_email(email, confirm_url)

        if not is_email_sent:

            auth_logger.error(
                f"Регистрация: не удалось отправить письмо на {email} (IP: {client_ip})"
            )

            return jsonify({
                'success': False,
                'errors': ['Не удалось отправить письмо. Проверьте корректность email.']
            }), 400

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()

            # Привязываем IP к пользователю и даём полный лимит попыток
            bind_ip_to_user_and_reset_attempts(new_user)

            auth_logger.info(
                f"Успешная регистрация: user_id={new_user.id}, username={username}, email={email}, IP={client_ip}"
            )

            return jsonify({
                'success': True,
                'message': 'Пользователь успешно зарегистрирован! Для подтверждения учётной записи вам отправлена ссылка на эл. почту.'
            }), 200

        except Exception as e:
            db.session.rollback()

            auth_logger.exception(
                f"Критическая ошибка при регистрации (username: {username}, email: {email}, IP: {client_ip})"
            )
            
            return jsonify({'success': False, 'errors': ['Ошибка при регистрации.']})

    return render_template('auth/register.html')


# Роутер для подтверждения учётной записи.
@auth_bp.route('/confirm-email', methods=['GET'])
def confirm_email():
    token = request.args.get('token')
    
    if not token:
        auth_logger.warning(f"Подтверждение email: токен не предоставлен, IP: {get_client_ip()}")
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
            auth_logger.info(f"Попытка повторного подтверждения email: {email}, IP: {get_client_ip()}")
            return render_or_json(
                template_name='auth/confirm_email.html',
                json_data={'message': 'Email уже подтверждён.'},
                status_code=200,
                is_success=True
            )
        
        user.confirm_email = True
        db.session.commit()
        auth_logger.info(f"Email подтверждён: user_id={user.id}, email={email}, IP: {get_client_ip()}")
        
        return render_or_json(
            template_name='auth/confirm_email.html',
            json_data={'message': 'Email успешно подтверждён!'},
            status_code=200,
            is_success=True
        )

    except Exception as e:
        auth_logger.warning(f"Ошибка подтверждения email: {str(e)}, токен={token[:20]}..., IP: {get_client_ip()}")
        return render_template('auth/confirm_email.html', 
                               error="Неверный или просроченный токен."), 400



# Роутер слушает GET - отображает форму входа
# POST запрос - проверяет логин и пароль, далее возвращает ответ клиенту
# с токеном. 
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'GET':
        return render_template('auth/login.html')
    
    elif request.method == 'POST':
        data = request.get_json()
        client_ip = get_client_ip()

        if not data:
            auth_logger.warning(f"Вход: неверный формат данных, IP: {client_ip}")
            return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

        username_or_email = data.get('username')
        password = data.get('password')

        user = User.query.filter(db.or_(
            User.username == username_or_email,
            User.email == username_or_email
        )).first()

        if not user or not user.check_password(password):
            auth_logger.warning(f"Неудачная попытка входа: {username_or_email}, IP: {client_ip}")
            return jsonify({
                'success': False,
                'errors': ['Неверное имя пользователя или пароль']
            }), 401

        if not user.confirm_email:
            auth_logger.info(f"Вход заблокирован: email не подтверждён, user_id={user.id}, IP: {client_ip}")
            return jsonify({
                'success': False,
                'errors': ['Подтвердите email. Письмо отправлено вам на email который вы указывали при регистрации.']
            }), 401

        # Сбрасываем счётчик попыток восстановления для текущего IP и привязываем его к пользователю
        bind_ip_to_user_and_reset_attempts(user)

        # Сохраняем User-Agent устройства
        update_ip_log_with_user_agent(client_ip)

        access_token = create_access_token(identity=str(user.id))
        
        response_data = {
            'success': True,
            'message': 'Авторизация прошла успешно.',
            'access_token': access_token
        }

        return jsonify(response_data)


# Проверка пользователя на аутентификацию
@auth_bp.route('/auth', methods=['GET'])
@jwt_required()  # Декоратор проверки JWT-токена
def auth():
    try:
        current_user_id = get_jwt_identity()  # Извлекаем идентификатор текущего пользователя
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"msg": "Пользователь не найден"}), 404
            
        # Формируем ответ с информацией о пользователе
        response_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
        
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({"msg": str(e)}), 500


# Очищает cookie.
@auth_bp.route('/logout', methods=['GET'])
def logout():
    # Перенаправляем обратно на главную страницу
    response = make_response(redirect(url_for('main.index')))  
    # Удаляем cookie с токеном
    response.delete_cookie('access_token')

    return response


# Восстановление пароля по email.
# 
# GET: Отображает форму для ввода email, использованного при регистрации.
# 
# POST: Принимает email, нормализует и проверяет его валидность.
#       Если email корректен, принадлежит **подтверждённому** пользователю —
#       отправляется письмо со ссылкой для сброса пароля.
# 
#       Если пользователь не подтвердил email → ошибка.
#       При невалидном email или отсутствии пользователя:
#       - IP-адрес клиента записывается в таблицу IPAttemptLog,
#       - уменьшается счётчик попыток восстановления,
#       - при исчерпании попыток — блокировка.
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_():
    if request.method == 'GET':
        return render_template('auth/reset_password.html', mess='Введите корректный email, который вы указывали при регистрации!')

    elif request.method == 'POST':
        raw_email = request.form.get('email', '').strip()
        client_ip = get_client_ip()

        if not client_ip:
            auth_logger.error("Восстановление пароля: не удалось получить IP-адрес")
            return render_template('auth/reset_password.html', err='Ошибка получения IP-адреса.')

        # Получаем или создаём запись об IP
        user_ip = get_or_create_ip_log(client_ip)

        # Если попытки исчерпаны — блокируем
        if user_ip.recovery_attempts_count <= 0:
            auth_logger.warning(f"Восстановление пароля: попытки исчерпаны, IP: {client_ip}")
            return render_template('auth/reset_password.html', err="Вы исчерпали все попытки восстановления пароля.")

        # Валидация email
        email = normalize_email(raw_email)

        if email is None:
            # Невалидный email — уменьшаем счётчик
            new_count = decrement_recovery_attempts(user_ip)
            auth_logger.warning(f"Восстановление пароля: невалидный email '{raw_email}', IP: {client_ip}, осталось попыток: {new_count}")
            if new_count == 0:
                return render_template('auth/reset_password.html', err="Вы исчерпали все попытки восстановления пароля.")
    
            else:
                message = f"Введите корректный email. Осталось попыток: {new_count}"
                return render_template('auth/reset_password.html', err=message)

        # Проверяем, существует ли пользователь с таким email
        user = User.query.filter_by(email=email).first()
        if not user:
            new_count = decrement_recovery_attempts(user_ip)
            message = f"Пользователь с таким email не найден. Осталось попыток: {new_count}"
            return render_template('auth/reset_password.html', err=message)

        # пользователь должен быть подтверждён!
        if not user.confirm_email:
            auth_logger.info(f"Восстановление пароля: email не подтверждён, user_id={user.id}, IP: {client_ip}")
            return render_template('auth/reset_password.html', err="Для восстановления пароля необходимо сначала подтвердить ваш email.")

        # Отправляем письмо
        token = generate_password_reset_token(user.email)
        reset_url = url_for('session.reset_password_with_token', token=token, _external=True)

        if send_password_reset_email(user, reset_url):
            auth_logger.info(f"Ссылка восстановления отправлена: user_id={user.id}, email={email}, IP: {client_ip}")
            message = "Ссылка для восстановления пароля успешно отправлена на email."
            return render_template('auth/reset_password.html', mess=message)
        else:
            auth_logger.error(f"Не удалось отправить ссылку восстановления на {email}, IP: {client_ip}")
            message = "Не удалось отправить ссылку для восстановления пароля. Попробуйте позже."
            return render_template('auth/reset_password.html', err=message)


# Роутер с формой по востановлению пароля.
# Форма рендерится когда пользователь переходит по ссылке
# которая отправляется на email.
@auth_bp.route('/reset-password/token', methods=['GET', 'POST'])
def reset_password_with_token():
    token = request.args.get('token')
    client_ip = get_client_ip()
    if not token:
        if request.is_json or request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json':
            auth_logger.warning(f"Сброс пароля: токен не указан, IP: {client_ip}")
            return jsonify({"error": "Токен не указан"}), 400
        return render_template('auth/reset_password.html'), 400

    decoded_token = decode_token(token)
    if decoded_token.get('type') != 'password_reset':
        auth_logger.warning(f"Сброс пароля: недопустимый тип токена, IP: {client_ip}")
        if request.is_json:
            return jsonify({"error": "Недопустимый тип токена"}), 400
        return render_template('auth/reset_password_form.html', err="Недопустимый тип токена.")

    email = decoded_token.get('sub')
    user = User.query.filter_by(email=email).first()
    if not user:
        auth_logger.warning(f"Сброс пароля: пользователь не найден по email из токена {email}, IP: {client_ip}")
        if request.is_json:
            return jsonify({"error": "Пользователь не найден"}), 404
        return render_template('auth/reset_password_form.html', err="Пользователь не найден.")

    if request.method == 'POST':

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

        # Сбрасываем счётчик и привязываем IP к пользователю после успешного сброса
        bind_ip_to_user_and_reset_attempts(user)
        auth_logger.info(f"Пароль успешно изменён: user_id={user.id}, IP: {client_ip}")

        if request.is_json:
            return jsonify({"success": True, "message": "Пароль успешно изменён"}), 200
        else:
            return redirect(url_for('session.login'))
        
    return render_template('auth/reset_password_form.html', token=token)
