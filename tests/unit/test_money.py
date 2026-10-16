from decimal import Decimal

import pytest

from videofacturacion.domain.money import money_words, number_words, parse_money


@pytest.mark.parametrize(
    "raw", ["NaN", "Infinity", "1e3", "1,50", "1.000,00", "0.001", "", " 1", "1_000"]
)
def test_rejects_ambiguous_money(raw):
    with pytest.raises(ValueError):
        parse_money(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", "cero pesos"),
        ("1", "un peso"),
        ("21", "veintiún pesos"),
        ("31", "treinta y un pesos"),
        ("100", "cien pesos"),
        ("5000", "cinco mil pesos"),
        ("130000", "ciento treinta mil pesos"),
        ("1000000", "un millón de pesos"),
        ("21000000", "veintiún millones de pesos"),
        ("1000001.01", "un millón un pesos con un centavo"),
        ("0.21", "cero pesos con veintiún centavos"),
        ("-5000.50", "menos cinco mil pesos con cincuenta centavos"),
    ],
)
def test_money_words_golden(raw, expected):
    assert money_words(parse_money(raw)) == expected


def test_decimal_exactness():
    assert sum([parse_money("0.10")] * 3) == Decimal("0.30")
    assert parse_money("999999999999.99") == Decimal("999999999999.99")


def test_number_limits():
    assert number_words(21000) == "veintiún mil"
    with pytest.raises(ValueError):
        number_words(-1)
