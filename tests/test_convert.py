from services.converter import calculate_conversion


def test_convert_same_currency():
    assert calculate_conversion(100, 1.0, 1.0) == 100


def test_convert_usd_to_eur():
    result = calculate_conversion(100, 41.0, 45.0)
    assert round(result, 2) == round(100 * 41.0 / 45.0, 2)


def test_convert_uah_to_pln():
    result = calculate_conversion(250, 1.0, 10.0)
    assert result == 25.0