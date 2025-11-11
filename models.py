from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    """
    Таблица предназначена для хранения информации о зарегистрированных пользователях веб-приложения.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hash_passwd = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(5), default="user")
    avatar_url = db.Column(db.String(255), default="/img/avatars/default_user.png")
    confirm_email = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)

    def set_password(self, password):
        """Хэширует пароль и сохраняет его в hash_passwd"""
        self.hash_passwd = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет пароль через хэш"""
        return check_password_hash(self.hash_passwd, password)

    def __repr__(self):
        return f'<User {self.username}>'


class IPAttemptLog(db.Model):
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
    __tablename__ = 'shop'

    id = db.Column(db.Integer, primary_key=True)
    article_num = db.Column(db.Integer, nullable=False)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    link_img = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    category = db.Column(db.String(80))
    sale = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('products', lazy=True, passive_deletes=True))

    def __repr__(self):
        return f"<Product {self.title}>"


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    is_purchased = db.Column(db.Boolean, default=False)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False)
    purchased_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('cart_items', lazy=True, passive_deletes=True))
    product = db.relationship('Shop', backref=db.backref('cart_items', lazy=True))

    def __repr__(self):
        return f"<CartItem user_id={self.user_id}, product_id={self.product_id}, quantity={self.quantity}>"
