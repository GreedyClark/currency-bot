def calculate_conversion(amount: float, rate_from: float, rate_to: float) -> float:
    """rate_from і rate_to задані до гривні, для UAH це 1.0."""
    return (amount * rate_from) / rate_to