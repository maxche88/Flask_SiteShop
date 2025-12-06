from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import json


# ПОЛЬЗОВАТЕЛЬ
class User(db.Model):
    """
    Основная таблица пользователей.
    Все зависимости настраиваются через `ondelete` в связанных таблицах.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hash_passwd = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(6), default="user")
    avatar_url = db.Column(db.String(255), default="static/uploads/avatars/default_user.png")
    confirm_email = db.Column(db.Boolean, default=False)
    pending_email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)

    def set_password(self, password):
        self.hash_passwd = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hash_passwd, password)

    def __repr__(self):
        return f'<User {self.username}>'


# ЛОГИ ПОПЫТОК (IP)
class IPAttemptLog(db.Model):
    """
    Логи IP-адресов, привязанных к пользователю.
    При удалении пользователя — удаляются автоматически (CASCADE).
    """
    __tablename__ = 'ip_attempt_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True
    )
    ip_address = db.Column(db.String(45), nullable=False, unique=True)
    recovery_attempts_count = db.Column(db.Integer, nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    is_blocked = db.Column(db.Boolean, default=False)

    # Обратная связь с User
    user = db.relationship(
        "User",
        backref=db.backref("ip_logs", lazy=True, passive_deletes=True)
    )


# ТОКЕНЫ
class UserToken(db.Model):
    """
    Токены сессий. `user_id` — целое число, но **не внешний ключ**.
    Это сделано для возможности отзыва токенов даже после удаления пользователя.
    """
    __tablename__ = 'user_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)


# ТОВАРЫ
class Shop(db.Model):
    """
    Товары в каталоге.
    При удалении автора — `user_id = NULL` (товар остаётся в системе).
    """
    __tablename__ = 'shop'

    id = db.Column(db.Integer, primary_key=True)
    article_num = db.Column(db.String, nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),  # Автор удаляется, товар остаётся
        nullable=True
    )
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)  # Используем целочисленный тип (Integer) с валидацией, чтобы избежать ошибок округления и упростить хранение.
    quantity = db.Column(db.Integer, nullable=False)
    link_img = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    category = db.Column(db.String(80))
    sale = db.Column(db.Boolean, default=False)

    user = db.relationship(
        'User',
        backref=db.backref('products', lazy=True, passive_deletes=True)
    )


# КОРЗИНА
class CartItem(db.Model):
    """
    Товары в корзине пользователя.
    При удалении пользователя — корзина удаляется полностью.
    """
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),  # удалять корзину
        nullable=False
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('shop.id', ondelete='CASCADE'),
        nullable=False
    )
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False)

    user = db.relationship(
        'User',
        backref=db.backref('cart_items', lazy=True, passive_deletes=True)
    )
    product = db.relationship(
        'Shop',
        backref=db.backref('cart_items', lazy=True, passive_deletes=True)
    )


# ЗАКАЗЫ
class Order(db.Model):
    """
    Завершённые заказы.
    При удалении пользователя — `user_id = NULL`, заказ остаётся (для отчётов, аналитики).
    """
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    status = db.Column(db.String(20), default='paid')
    total_amount = db.Column(db.Integer, nullable=False)
    card_number = db.Column(db.String(20))
    cardholder_name = db.Column(db.String(100))
    expiry = db.Column(db.String(7))

    user = db.relationship(
        'User',
        backref=db.backref('orders', lazy=True, passive_deletes=True)
    )


# ПОЗИЦИИ ЗАКАЗА
class OrderItem(db.Model):
    """
    Детализация заказа.
    `product_id` может стать NULL, если товар удалён из каталога.
    `order_id` — всегда остаётся.
    """
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('orders.id', ondelete='CASCADE'),  # удаляется только при удалении заказа
        nullable=False
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('shop.id', ondelete='SET NULL'),
        nullable=True
    )
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Integer, nullable=False)

    order = db.relationship(
        'Order',
        backref=db.backref('items', lazy=True, passive_deletes=True)
    )
    product = db.relationship('Shop', backref=db.backref('order_items', lazy=True))



# ТЕМЫ СООБЩЕНИЙ
class MessageTopic(db.Model):
    """Справочник тем обращений. Не зависит от пользователей."""
    __tablename__ = 'message_topics'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)



# ДИАЛОГИ И СООБЩЕНИЯ
class Dialog(db.Model):
    """
    Диалог, инициированный пользователем.
    При удалении пользователя — весь диалог удаляется (включая сообщения и вложения).
    """
    __tablename__ = 'dialogs'
    
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('message_topics.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('shop.id', ondelete='SET NULL'), nullable=True)

    # Инициатор: авторизованный пользователь
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True
    )
    # Или гость (name + email)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))

    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Связи
    topic = db.relationship('MessageTopic', backref='dialogs')
    user = db.relationship('User', backref='dialogs')
    messages = db.relationship(
        'Message',
        backref='dialog',
        cascade='all, delete-orphan',  # автоматически удаляет вложения и сообщения
        lazy='dynamic'
    )

class Message(db.Model):
    """
    Сообщение в диалоге.
    Отправитель может быть NULL (гость), но если это пользователь — ссылка на `users.id`.
    Удаляется вместе с диалогом (`cascade='all, delete-orphan'` в Dialog).
    """
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    dialog_id = db.Column(
        db.Integer,
        db.ForeignKey('dialogs.id', ondelete='CASCADE'),
        nullable=False
    )
    sender_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    sender_role = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    is_read = db.Column(db.Boolean, default=False)
    attachment = db.Column(db.String(255), nullable=True)
    sender = db.relationship('User', foreign_keys=[sender_user_id])
    


class BugReport(db.Model):
    """
    Баг-репорт, созданный пользователем.
    При удалении автора — удаляется полностью.
    """
    __tablename__ = 'bug_reports'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='new')
    precondition = db.Column(db.Text)
    environment = db.Column(db.Text)
    steps_to_reproduce = db.Column(db.Text, nullable=False)
    actual_result = db.Column(db.Text, nullable=False)
    expected_result = db.Column(db.Text, nullable=False)
    attachments = db.Column(db.Text)
    category = db.Column(db.String(100))
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),  # удалять при удалении автора
        nullable=False
    )
    author = db.relationship(
        'User',
        backref=db.backref('bug_reports', lazy=True)
    )


class Checklist(db.Model):
    """
    Чек-лист, созданный пользователем.
    При удалении автора — удаляется полностью.
    """
    __tablename__ = 'checklists'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    items_json = db.Column(db.Text, default='[]')
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),  # удалять при удалении автора
        nullable=False
    )
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    author = db.relationship(
        'User',
        backref=db.backref('checklists', lazy=True)
    )

    @property
    def items(self):
        try:
            return json.loads(self.items_json)
        except (ValueError, TypeError):
            return []

    @items.setter
    def items(self, value):
        if not isinstance(value, list):
            raise ValueError("Items must be a list")
        self.items_json = json.dumps(value, ensure_ascii=False)

    def __repr__(self):
        return f'<Checklist {self.id}: {self.title}>'