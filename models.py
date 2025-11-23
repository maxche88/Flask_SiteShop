from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func


class User(db.Model):
    """
    Хранит учётные данные зарегистрированных пользователей.
    Поддерживает роли: user, suser, admin.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hash_passwd = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(5), default="user")
    avatar_url = db.Column(db.String(255), default="/img/avatars/default_user.png")
    confirm_email = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)

    def set_password(self, password):
        """Хэширует пароль и сохраняет его в hash_passwd"""
        self.hash_passwd = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет пароль через хэш"""
        return check_password_hash(self.hash_passwd, password)

    def __repr__(self):
        return f'<User {self.username}>'


class IPAttemptLog(db.Model):
    """
    Фиксирует попытки входа/восстановления пароля с IP-адреса.
    Используется для ограничения количества попыток и блокировки злонамеренных адресов.
    При удалении пользователя связанные записи удаляются (CASCADE).
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
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User", backref=db.backref("ip_logs", lazy=True, passive_deletes=True))


class UserToken(db.Model):
    """
    Хранит информацию о выданных JWT-токенах: JTI, срок действия,
    статус отзыва и привязку к пользователю.
    Используется для точного отзыва сессий и отображения статуса в админке. 
    """
    __tablename__ = 'user_tokens'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    user_id = db.Column(db.Integer, nullable=False)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)


class Shop(db.Model):
    """
    Каталог товаров магазина.
    Поле 'quantity' отражает текущий остаток на складе.
    При покупке остаток уменьшается.
    """
    __tablename__ = 'shop'

    id = db.Column(db.Integer, primary_key=True)
    article_num = db.Column(db.String, nullable=False)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    link_img = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now())
    category = db.Column(db.String(80))
    sale = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('products', lazy=True, passive_deletes=True))

    def __repr__(self):
        return f"<Product {self.title}>"


class CartItem(db.Model):
    """
    Текущие товары в корзине пользователя.
    Существует только до оформления покупки.
    После покупки элементы удаляются и переносятся в OrderItem.
    """
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False)
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True, passive_deletes=True))
    product = db.relationship('Shop', backref=db.backref('cart_items', lazy=True))

    def __repr__(self):
        return f"<CartItem user_id={self.user_id}, product_id={self.product_id}, quantity={self.quantity}>"


class Order(db.Model):
    """
    Представляет завершённый заказ пользователя.
    Содержит общую информацию: сумму, статус, данные оплаты.
    Для каждой корзины создаётся ровно один Order.
    """
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=func.now())
    status = db.Column(db.String(20), default='paid')
    total_amount = db.Column(db.Integer, nullable=False)
    card_number = db.Column(db.String(20))
    cardholder_name = db.Column(db.String(100))
    expiry = db.Column(db.String(7))  # "MM/YYYY"

    user = db.relationship('User', backref=db.backref('orders', lazy=True, passive_deletes=True))


class OrderItem(db.Model):
    """
    Детализация заказа: какие товары, в каком количестве и по какой цене были куплены.
    Цена сохраняется на момент покупки, даже если в будущем изменится в Shop.
    """
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('orders.id', ondelete='CASCADE'),
        nullable=False
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('shop.id', ondelete='SET NULL'),
        nullable=False
    )
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Integer, nullable=False)  # цена на момент покупки

    order = db.relationship('Order', backref=db.backref('items', lazy=True, passive_deletes=True))
    product = db.relationship('Shop', backref=db.backref('order_items', lazy=True))


# ==============================================================================
# Таблицы сообщений.
# ==============================================================================

class MessageTopic(db.Model):
    """
    Справочник возможных тем обращений (например: 'Вопрос по товару', 'Техподдержка').
    Позволяет стандартизировать категории и упрощает фильтрацию.
    """
    __tablename__ = 'message_topics'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)


class Dialog(db.Model):
    """
    Логический контейнер для обмена сообщениями между участниками.
    
    Поддерживает два типа инициаторов:
      - Авторизованный пользователь (user_id ссылается на users.id)
      - Гость (guest_name + guest_email)
    
    Может быть привязан к заказу или товару для контекстной поддержки.
    Статус ('open', 'closed', 'archived') позволяет управлять жизненным циклом.
    При удалении диалога все связанные сообщения удаляются автоматически (каскад).
    """
    __tablename__ = 'dialogs'

    id = db.Column(db.Integer, primary_key=True)
    
    # Контекст обращения
    topic_id = db.Column(db.Integer, db.ForeignKey('message_topics.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=True)

    # Инициатор: либо авторизованный пользователь, либо гость
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    # Метаданные
    status = db.Column(db.String(20), default='open')  # open | closed | archived
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Отношения
    topic = db.relationship('MessageTopic', backref='dialogs')
    user = db.relationship('User', backref='dialogs')
    messages = db.relationship(
        'Message',
        backref='dialog',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Dialog {self.id} (status={self.status})>'


class Message(db.Model):
    """
    Отдельное сообщение в рамках диалога.
    
    Поддерживает отправку от:
      - Авторизованных пользователей (sender_user_id + sender_role)
      - Гостей (sender_user_id = NULL, sender_role = 'guest')
    
    Для гостей данные (имя, email) берутся из связанного Dialog.
    При удалении диалога сообщения удаляются автоматически (каскад).
    
    attachments: список прикреплённых файлов (из таблицы Attachment).
    """
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    dialog_id = db.Column(db.Integer, db.ForeignKey('dialogs.id', ondelete='CASCADE'), nullable=False)

    # Отправитель
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    sender_role = db.Column(db.String(20), nullable=False)  # user | suser | admin

    # Содержимое
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)

    # Дополнительно
    is_read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_role}>'

    # Отношения
    sender = db.relationship('User', foreign_keys=[sender_user_id])
    attachments = db.relationship(
        'Attachment',
        backref='message',
        cascade='all, delete-orphan'
    )


class Attachment(db.Model):
    """
    Файл, прикреплённый к сообщению (например: скриншот, фото, PDF).
    
    Файлы хранятся на диске или в объектном хранилище.
    В БД сохраняются только метаданные и относительный путь к файлу.
    
    При удалении сообщения вложения удаляются из БД автоматически.
    Физическое удаление файла должно обрабатываться в бизнес-логике.
    """
    __tablename__ = 'attachments'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)

    # Путь к файлу относительно корня хранилища (например: 'uploads/2025/11/uuid.jpg')
    file_path = db.Column(db.String(255), nullable=False)

    # Оригинальное имя файла (для отображения и скачивания)
    original_filename = db.Column(db.String(255), nullable=False)

    # Технические метаданные
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # в байтах
    uploaded_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)

    def __repr__(self):
        return f'<Attachment {self.id} for message {self.message_id}>'
    

# ==============================================================================
# Таблица TEST_UI.
# ==============================================================================
class BugReport(db.Model):
    """
    Хранит отчёты об ошибках (баг-репорты), созданные пользователями с ролью 'test' или 'admin'.
    Привязан к автору, поддерживает статус, критичность, шаги воспроизведения и вложения.
    """
    __tablename__ = 'bug_reports'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high, critical
    status = db.Column(db.String(20), nullable=False, default='new')  # new, open, in_progress, resolved, closed
    precondition = db.Column(db.Text, nullable=True)
    environment = db.Column(db.Text, nullable=True)  # например: "Chrome 124, Windows 11, staging"
    steps_to_reproduce = db.Column(db.Text, nullable=False)
    actual_result = db.Column(db.Text, nullable=False)
    expected_result = db.Column(db.Text, nullable=False)
    attachments = db.Column(db.Text, nullable=True)
    # Служебные поля
    category = db.Column(db.String(100), nullable=True)  # опционально: "UI", "API", "Mobile", "Checkout"
    created_at = db.Column(db.DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    # Автор
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('bug_reports', lazy=True))

    def __repr__(self):
        return f'<BugReport {self.id}: {self.title}>'