def calculate_conversion(amount: float, rate_from: float, rate_to: float) -> float:
    """
    Розраховує суму після конвертації через крос-курс НБУ.
    rate_from / rate_to — курс відповідної валюти до гривні (для UAH = 1.0).
    """
    return (amount * rate_from) / rate_to