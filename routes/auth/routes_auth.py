# Регистрация. Аутентификация и управление сессией.

from flask import Blueprint, request, redirect, url_for, render_template, jsonify, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, decode_token
from models import db, User,IPAttemptLog
from utils.tokens import generate_password_reset_token, generate_email_confirmation_token
from utils.mail import send_password_reset_email, send_confirm_email, normalize_email
import logging


auth_bp = Blueprint('session', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'errors': ['Неверный формат данных']}), 400

        username = data.get('username', '').strip()
        raw_email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        if not all([username, raw_email, password, confirm_password]):
            return jsonify({'success': False, 'errors': ['Все поля обязательны для заполнения.']})

        if password != confirm_password:
            return jsonify({'success': False, 'errors': ['Пароли не совпадают.']})

        # Нормализация и валидация за один вызов
        email = normalize_email(raw_email)
        if email is None:
            return jsonify({
                'success': False,
                'errors': ['Указанный email некорректен.']
            }), 400

        # Проверка на существование нормализованного email
        existing_user = User.query.filter(
            (User.username.ilike(username)) | (User.email.ilike(email))
        ).first()

        if existing_user:
            return jsonify({
                'success': False,
                'errors': ['Пользователь с таким именем или электронной почтой уже существует.']
            }), 400

        # Дальнейший email уже нормализованный и валидный
        token = generate_email_confirmation_token(email)
        confirm_url = url_for('session.confirm_email', token=token, _external=True)
        is_email_sent = send_confirm_email(email, confirm_url)

        if not is_email_sent:
            return jsonify({
                'success': False,
                'errors': ['Не удалось отправить письмо. Проверьте корректность email.']
            }), 400

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        ip_address = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
        ip_log = IPAttemptLog(ip_address=ip_address, user=new_user, recovery_attempts_count=3)

        try:
            db.session.add(new_user)
            db.session.add(ip_log)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Пользователь успешно зарегистрирован! Для подтверждения учётной записи вам отправлена на эл. почту'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'errors': ['Ошибка при регистрации.']})

    return render_template('auth/register.html')


# Роутер для подтверждения учётной записи.
@auth_bp.route('/confirm-email', methods=['GET'])
def confirm_email():
    token = request.args.get('token')

    if not token:
        if 'text/html' in request.accept_mimetypes:
            return render_template('auth/confirm_email.html', error="Токен не предоставлен.")
        else:
            return jsonify({
                'success': False,
                'message': 'Токен не предоставлен.'
            }), 400

    try:
        decoded_token = decode_token(token)

        if decoded_token.get('type') != 'email_confirmation':
            if 'text/html' in request.accept_mimetypes:
                return render_template('auth/confirm_email.html', error="Недопустимый тип токена.")
            else:
                return jsonify({
                    'success': False,
                    'message': 'Недопустимый тип токена.'
                }), 400

        email = decoded_token.get('sub')
        user = User.query.filter_by(email=email).first()

        if not user:
            if 'text/html' in request.accept_mimetypes:
                return render_template('auth/confirm_email.html', error="Пользователь не найден.")
            else:
                return jsonify({
                    'success': False,
                    'message': 'Пользователь не найден.'
                }), 404

        if user.confirm_email:
            if 'text/html' in request.accept_mimetypes:
                return render_template('auth/confirm_email.html', message="Email уже подтверждён.")
            else:
                return jsonify({
                    'success': True,
                    'message': 'Email уже подтверждён.'
                }), 200

        # Подтверждаем email
        user.confirm_email = True
        db.session.commit()

        if 'text/html' in request.accept_mimetypes:
            return render_template('auth/confirm_email.html', message="Email успешно подтверждён!")
        else:
            return jsonify({
                'success': True,
                'message': 'Email успешно подтверждён!'
            }), 200

    except Exception as e:
        logging.info(f"Неверный или просроченный токен: {email}, Ошибка: {str(e)}")
        if 'text/html' in request.accept_mimetypes:
            return render_template('auth/confirm_email.html', error="Неверный или просроченный токен.")
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
        return render_template('auth/login.html')

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


# Восстановление пароля по email.
# 
# GET: Отображает форму для ввода email, использованного при регистрации.
# 
# POST: Принимает email, нормализует и проверяет его валидность.
#       Если email корректен и принадлежит зарегистрированному пользователю —
#       отправляется письмо со ссылкой для сброса пароля.
# 
#       При невалидном email или отсутствии пользователя с таким email:
#       - IP-адрес клиента записывается в таблицу IPAttemptLog,
#       - уменьшается счётчик оставшихся попыток восстановления (начальное значение: 2,
#         что даёт пользователю в общей сложности 3 попытки: текущая + 2 дополнительные).
#       - При исчерпании попыток (счётчик <= 0) дальнейшие запросы блокируются.
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_():
    if request.method == 'GET':
        return render_template('auth/reset_password.html', mess='Введите корректный email, который вы указывали при регистрации!')

    elif request.method == 'POST':
        raw_email = request.form.get('email', '').strip()
        client_ip = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr

        if not client_ip:
            return render_template('auth/reset_password.html', err='Ошибка получения IP-адреса.')

        # Получаем или создаём запись об IP
        user_ip = IPAttemptLog.query.filter_by(ip_address=client_ip).first()
        if not user_ip:
            # Даём 3 попытки всего
            user_ip = IPAttemptLog(ip_address=client_ip, recovery_attempts_count=3)
            db.session.add(user_ip)
            db.session.commit()

        # Если попытки уже исчерпаны — блокируем сразу
        if user_ip.recovery_attempts_count <= 0:
            return render_template('auth/reset_password.html', err="Вы исчерпали все попытки восстановления пароля.")

        # Валидация и нормализация email
        email = normalize_email(raw_email)
        
        # === Обработка ошибок с учётом "последней попытки" ===
        if email is None:
            # Это невалидный email
            if user_ip.recovery_attempts_count <= 1:
                # Это 3-я (последняя) попытка
                user_ip.recovery_attempts_count = 0
                db.session.commit()
                return render_template('auth/reset_password.html', err="Вы исчерпали все попытки восстановления пароля.")
            else:
                # Уменьшаем счётчик и показываем оставшиеся попытки
                user_ip.recovery_attempts_count -= 1
                db.session.commit()
                remaining = user_ip.recovery_attempts_count
                message = f"Введите корректный email. Осталось попыток: {remaining}"
                return render_template('auth/reset_password.html', err=message)

        # Проверяем существование пользователя
        user = User.query.filter_by(email=email).first()
        if not user:
            user_ip.recovery_attempts_count -= 1
            db.session.commit()
            remaining = max(0, user_ip.recovery_attempts_count)
            message = f"Пользователь с таким email не найден. Осталось попыток: {remaining}"
            return render_template('auth/reset_password.html', err=message)

        # Отправляем письмо
        token = generate_password_reset_token(user.email)
        reset_url = url_for('session.reset_password_with_token', token=token, _external=True)

        if send_password_reset_email(user, reset_url):
            message = "Ссылка для восстановления пароля успешно отправлена на email."
            return render_template('auth/reset_password.html', mess=message)
        else:
            message = "Не удалось отправить ссылку для восстановления пароля. Попробуйте позже."
            return render_template('auth/reset_password.html', err=message)


# Роутер с формой по востановлению пароля.
# Форма рендерится когда пользователь переходит по ссылке
# которая отправляется на email.
@auth_bp.route('/reset-password/token', methods=['GET', 'POST'])
def reset_password_with_token():
    token = request.args.get('token')
    if not token:
        if request.is_json or request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json':
            return jsonify({"error": "Токен не указан"}), 400
        return render_template('auth/reset_password.html'), 400

    decoded_token = decode_token(token)
    if decoded_token.get('type') != 'password_reset':
        if request.is_json:
            return jsonify({"error": "Недопустимый тип токена"}), 400
        return render_template('auth/reset_password_form.html', err="Недопустимый тип токена.")

    email = decoded_token.get('sub')
    user = User.query.filter_by(email=email).first()
    if not user:
        if request.is_json:
            return jsonify({"error": "Пользователь не найден"}), 404
        return render_template('auth/reset_password_form.html', err="Пользователь не найден.")

    if request.method == 'POST':
        # Определяем, откуда пришёл запрос
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
            if request.is_json:
                return jsonify({"error": "Пароли не совпадают"}), 400
            return render_template('auth/reset_password_form.html', token=token, err="Пароли не совпадают")

        # Обновляем пароль
        user.set_password(password)
        db.session.commit()

        # Универсальный ответ
        if request.is_json:
            return jsonify({"success": True, "message": "Пароль успешно изменён"}), 200
        else:
            return redirect(url_for('session.login'))

    # GET-запрос: только рендер HTML (JSON-клиенты не должны делать GET сюда)
    return render_template('auth/reset_password_form.html', token=token)
