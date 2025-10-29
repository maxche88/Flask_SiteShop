# Регистрация. Аутентификация и управление сессией.

from flask import Blueprint, request, redirect, url_for, render_template, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, decode_token
from models import db, User,IPAttemptLog
from utils.tokens import generate_password_reset_token, generate_email_confirmation_token
from utils.mail import send_password_reset_email, send_confirm_email
from email_validator import validate_email, EmailNotValidError
import logging


auth_bp = Blueprint('session', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        if not all([username, email, password, confirm_password]):
            return jsonify({'success': False, 'errors': ['Все поля обязательны для заполнения.']})

        if password != confirm_password:
            return jsonify({'success': False, 'errors': ['Пароли не совпадают.']})

        existing_user = User.query.filter(
            (User.username.ilike(username)) | (User.email.ilike(email))
        ).first()

        if existing_user:
            return jsonify({
                'success': False,
                'errors': ['Пользователь с таким именем или электронной почтой уже существует.']
            }), 400

        try:
            valid_email = validate_email(email)
            email = valid_email.email
        except EmailNotValidError as e:
            logging.warning(f"Некорректный email при регистрации: {email}, Ошибка: {str(e)}")
            return jsonify({
                'success': False,
                'errors': ['Указанный email некорректен или сервер не отвечает.']
            }), 400

        # Генерация токена подтверждения
        token = generate_email_confirmation_token(email)
        confirm_url = url_for('session.confirm_email', token=token, _external=True)

        # Отправка письма
        is_email_sent = send_confirm_email(email, confirm_url)

        if not is_email_sent:
            return jsonify({
                'success': False,
                'errors': ['Не корректный email или ошибка SMPT сервера.']
            }), 400

        # Создаем пользователя
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        # Получаем IP пользователя
        ip_address = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr

        # Создаём запись в логе попыток
        ip_log = IPAttemptLog(
            ip_address=ip_address,
            user=new_user,
            recovery_attempts_count=3
        )

        try:
            db.session.add(new_user)
            db.session.add(ip_log)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Пользователь успешно зарегистрирован'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'errors': ['Ошибка при регистрации.']})

    return render_template('register.html')


# Роутер для подтверждения учётной записи.
@auth_bp.route('/confirm-email', methods=['GET'])
def confirm_email():
    token = request.args.get('token')

    if not token:
        if 'text/html' in request.accept_mimetypes:
            return render_template('confirm_email.html', error="Токен не предоставлен.")
        else:
            return jsonify({
                'success': False,
                'message': 'Токен не предоставлен.'
            }), 400

    try:
        decoded_token = decode_token(token)

        if decoded_token.get('type') != 'email_confirmation':
            if 'text/html' in request.accept_mimetypes:
                return render_template('confirm_email.html', error="Недопустимый тип токена.")
            else:
                return jsonify({
                    'success': False,
                    'message': 'Недопустимый тип токена.'
                }), 400

        email = decoded_token.get('sub')
        user = User.query.filter_by(email=email).first()

        if not user:
            if 'text/html' in request.accept_mimetypes:
                return render_template('confirm_email.html', error="Пользователь не найден.")
            else:
                return jsonify({
                    'success': False,
                    'message': 'Пользователь не найден.'
                }), 404

        if user.confirm_email:
            if 'text/html' in request.accept_mimetypes:
                return render_template('confirm_email.html', message="Email уже подтверждён.")
            else:
                return jsonify({
                    'success': True,
                    'message': 'Email уже подтверждён.'
                }), 200

        # Подтверждаем email
        user.confirm_email = True
        db.session.commit()

        if 'text/html' in request.accept_mimetypes:
            return render_template('confirm_email.html', message="Email успешно подтверждён!")
        else:
            return jsonify({
                'success': True,
                'message': 'Email успешно подтверждён!'
            }), 200

    except Exception as e:
        logging.info(f"Неверный или просроченный токен: {email}, Ошибка: {str(e)}")
        if 'text/html' in request.accept_mimetypes:
            return render_template('confirm_email.html', error="Неверный или просроченный токен.")
        else:
            return jsonify({
                'success': False,
                'message': 'Неверный или просроченный токен.'
            }), 400


# Роутер слушает GET - отображает форму входа
# POST запрос - проверяет логин и пароль, далее возвращает ответ клиенту
# с токеном. 
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Отображение формы
    if request.method == 'GET':
        return render_template('login.html')

    # Обработка входящих данных
    elif request.method == 'POST':
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

        username_or_email = data.get('username')
        password = data.get('password')

        user = User.query.filter(db.or_(
            User.username == username_or_email,
            User.email == username_or_email
        )).first()

        if not user or not user.check_password(password):
            return jsonify({
                'success': False,
                'errors': ['Неверное имя пользователя или пароль']
            }), 401

        if not user.confirm_email:
            return jsonify({
                'success': False,
                'errors': ['Подтвердите email. Письмо отправлено вам на email который вы указали при регистрации.']
            }), 401

        # Генерация токена
        access_token = create_access_token(identity=str(user.id))

        # Формирование JSON-ответа с токеном
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


# Востановление пароля по запросу отправки ссылки на email.
# GET: Показывает форму с полем ввода email.
# POST: Принимает запрос и отправляет письмо на email, если
# соответствует с email который указывал при регистрации.
# В случае не корректного email записывается ip адрес в бд
# Таблица имеет поле "recovery_attempts_count" это счётчик
# кол-ва попыток для восстановления пароля.
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_():
    if request.method == 'GET':
        return render_template('reset_password.html', mess='Введите корректный email который вы указывали при регистрации!')

    elif request.method == 'POST':
        # Получаем email из формы
        email = request.form.get('email')

        # Получаем IP клиента
        client_ip = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr

        if not client_ip:
            message = 'Ошибка получения IP-адреса.'
            return render_template('reset_password.html', err=message)

        # Получаем запись по IP
        user_ip = IPAttemptLog.query.filter_by(ip_address=client_ip).first()

        # Валидируем email и проверяем существование пользователя
        if not email or not validate_email(email):
            # Логика для невалидного email
            if not user_ip:
                new_user_ip = IPAttemptLog(ip_address=client_ip, recovery_attempts_count=2)
                db.session.add(new_user_ip)
                db.session.commit()
                message = "Введите корректный email. Осталось попыток: 2"
                return render_template('reset_password.html', err=message)

            elif user_ip.recovery_attempts_count <= 1:
                message = "Вы исчерпали все попытки восстановления пароля."
                return render_template('reset_password.html', err=message)

            else:
                user_ip.recovery_attempts_count -= 1
                db.session.commit()
                message = f"Введите корректный email. Осталось попыток: {user_ip.recovery_attempts_count}"
                return render_template('reset_password.html', err=message)

        # Проверяем, существует ли пользователь с таким email
        user = User.query.filter_by(email=email).first()
        if not user:
            if not user_ip:
                new_user_ip = IPAttemptLog(ip_address=client_ip)
                db.session.add(new_user_ip)
                db.session.commit()
                message = "Пользователь с таким email не найден. Осталось попыток: 2"
                return render_template('reset_password.html', err=message)

            elif user_ip.recovery_attempts_count <= 1:
                message = "Вы исчерпали все попытки восстановления пароля."
                return render_template('reset_password.html', err=message)

            else:
                user_ip.recovery_attempts_count -= 1
                db.session.commit()
                message = f"Пользователь с таким email не найден. Осталось попыток: {user_ip.recovery_attempts_count}"
                return render_template('reset_password.html', err=message)

        # Проверяем, остались ли попытки у пользователя
        if user_ip and user_ip.recovery_attempts_count <= 1:
            message = "Вы исчерпали все попытки восстановления пароля."
            return render_template('reset_password.html', err=message)

        # Генерируем токен и ссылку
        token = generate_password_reset_token(user.email)
        reset_url = url_for('session.reset_password_with_token', token=token, _external=True)

        # Отправляем письмо и проверяем результат
        if send_password_reset_email(user, reset_url):
            message = "Ссылка для восстановления пароля успешно отправлена на email."
            return render_template('reset_password.html', mess=message)
        else:
            message = "Не удалось отправить ссылку для восстановления пароля. Попробуйте позже."
            return render_template('reset_password.html', err=message)


# Роутер с формой по востановлению пароля.
# Форма рендерится когда пользователь переходит по ссылке
# которая отправляется на email.
@auth_bp.route('/reset-password/token', methods=['GET', 'POST'])
def reset_password_with_token():
    token = request.args.get('token')

    if not token:
        return render_template('reset_password.html'), 400

    # Расшифровываем токен
    decoded_token = decode_token(token)

    if decoded_token.get('type') != 'password_reset':
        return render_template('reset_password_form.html', err="Недопустимый тип токена.")

    email = decoded_token.get('sub')
    user = User.query.filter_by(email=email).first()

    if not user:
        return render_template('reset_password_form.html', err="Пользователь не найден.")

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password:
            return render_template('reset_password_form.html', token=token, err="Пароль не может быть пустым")

        if password != confirm_password:
            return render_template('reset_password_form.html', token=token, err="Пароли не совпадают")

        # Обновляем пароль
        user.set_password(password)
        db.session.commit()

        return redirect(url_for('session.login'))

    return render_template('reset_password_form.html', token=token)
