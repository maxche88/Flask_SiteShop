# Корзина покупателя.
# Функции для добавления товаров в корзину, просмотр содержимого корзины и оформление покупки (перевод товаров из корзины в статус «куплено»).

from models import  CartItem, Shop
from extensions import db
from utils.database_utils import current_time

def add_to_cart(user_id, product_id, quantity=1):
    """
    Добавляет товар в корзину пользователя или увеличивает количество уже существующего товара в корзине.
    """
    existing_item = CartItem.query.filter_by(
        user_id=user_id, product_id=product_id, is_purchased=False
    ).first()  # Ищет в базе данных существующий элемент корзины (CartItem) с заданными user_id и product_id, который ещё не куплен (is_purchased=False).

    if existing_item:  # Если такой элемент найден — увеличивает его количество на указанное quantity
        existing_item.quantity += quantity
    else:  # Если элемента нет — создаёт новый объект CartItem с указанными параметрами и добавляет его в сессию SQLAlchemy.
        new_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            is_purchased=False
        )
        db.session.add(new_item)
    
    db.session.commit()

def get_user_cart(user_id):
    """
    Возвращает все товары из корзины конкретного пользователя, которые ещё не были куплены.
    """
    return CartItem.query.filter_by(user_id=user_id, is_purchased=False).all()  # Выполняет запрос к базе данных, выбирая все записи CartItem.
                                                                                # user_id совпадает с переданным,
                                                                                # is_purchased=False (т.е. товары ещё в корзине, а не в истории покупок).

def purchase_cart_items(user_id):
    """
    Помечает товары в корзине как купленные и уменьшает остаток на складе (Shop.quantity).
    """
    cart_items = CartItem.query.filter_by(user_id=user_id, is_purchased=False).all()
    
    for item in cart_items:
        # Уменьшаем остаток на складе
        item.product.quantity -= item.quantity
        
        # Защита от отрицательного остатка
        if item.product.quantity < 0:
            item.product.quantity = 0

        # Помечаем как купленное
        item.is_purchased = True
        item.purchased_at = current_time()

    db.session.commit()

def validate_cart_for_checkout(user_id):
    """
    Проверяет, можно ли оформить заказ:
    - все товары существуют,
    - количество в корзине не превышает остаток на складе (Shop.quantity),
    - количество >= 1.
    
    Возвращает:
        (errors: list[str], cart_items: list[CartItem])
    """
    cart_items = CartItem.query.filter_by(user_id=user_id, is_purchased=False).all()
    errors = []

    for item in cart_items:
        product = Shop.query.get(item.product_id)
        if not product:
            errors.append(f"Товар с ID {item.product_id} удалён из каталога.")
            continue

        if item.quantity < 1:
            errors.append(f"Некорректное количество для товара «{product.title}».")
        elif item.quantity > product.quantity:  # product.quantity = остаток на складе
            errors.append(
                f"Товара «{product.title}» осталось только {product.quantity} шт., "
                f"а у вас в корзине {item.quantity}."
            )

    return errors, cart_items