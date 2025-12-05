def validate_price(price_str: str, max_price: int = 2_000_000_000) -> int:
    """
    Валидация цены как целого числа.
    """
    if not price_str:
        raise ValueError("Цена не указана")

    try:
        price = int(float(price_str))  # сначала float, чтобы обработать "100.0"
    except (ValueError, TypeError):
        raise ValueError("Цена должна быть целым числом")

    if price < 0:
        raise ValueError("Цена не может быть отрицательной")

    if price > max_price:
        raise ValueError(f"Цена не может превышать {max_price:,}")

    return price