import re
from decimal import Decimal

MAX_AMOUNT = Decimal("999999999999.99")


def parse_money(value: str) -> Decimal:
    # No exponenciales, separadores locales, NaN/Infinity ni redondeo implícito.
    if not re.fullmatch(r"-?\d{1,12}(?:\.\d{1,2})?", value):
        raise ValueError("Importe inválido: use punto decimal, sin miles y hasta dos decimales.")
    amount = Decimal(value)
    if abs(amount) > MAX_AMOUNT:
        raise ValueError("Importe fuera del rango admitido.")
    return amount.quantize(Decimal("0.01"))


def cents(amount: Decimal) -> int:
    return int(amount * 100)


_SMALL = (
    "cero",
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    "once",
    "doce",
    "trece",
    "catorce",
    "quince",
    "dieciséis",
    "diecisiete",
    "dieciocho",
    "diecinueve",
    "veinte",
    "veintiuno",
    "veintidós",
    "veintitrés",
    "veinticuatro",
    "veinticinco",
    "veintiséis",
    "veintisiete",
    "veintiocho",
    "veintinueve",
)
_TENS = {
    30: "treinta",
    40: "cuarenta",
    50: "cincuenta",
    60: "sesenta",
    70: "setenta",
    80: "ochenta",
    90: "noventa",
}
_HUNDREDS = (
    "",
    "ciento",
    "doscientos",
    "trescientos",
    "cuatrocientos",
    "quinientos",
    "seiscientos",
    "setecientos",
    "ochocientos",
    "novecientos",
)


def apocope(text: str) -> str:
    if text.endswith("veintiuno"):
        return text[:-9] + "veintiún"
    if text.endswith("uno"):
        return text[:-3] + "un"
    return text


def number_words(number: int) -> str:
    if not 0 <= number <= 999999999999:
        raise ValueError("Número fuera del rango de verbalización.")
    if number < 30:
        return _SMALL[number]
    if number < 100:
        tens, unit = divmod(number, 10)
        return _TENS[tens * 10] + (" y " + _SMALL[unit] if unit else "")
    if number == 100:
        return "cien"
    if number < 1000:
        hundreds, remainder = divmod(number, 100)
        return _HUNDREDS[hundreds] + (" " + number_words(remainder) if remainder else "")
    if number < 1000000:
        thousands, remainder = divmod(number, 1000)
        prefix = "mil" if thousands == 1 else apocope(number_words(thousands)) + " mil"
        return prefix + (" " + number_words(remainder) if remainder else "")
    millions, remainder = divmod(number, 1000000)
    prefix = "un millón" if millions == 1 else apocope(number_words(millions)) + " millones"
    return prefix + (" " + number_words(remainder) if remainder else "")


def money_words(amount: Decimal) -> str:
    minor = cents(abs(amount))
    whole, fraction = divmod(minor, 100)
    unit = "peso" if whole == 1 else "pesos"
    connector = " de" if whole and whole % 1000000 == 0 else ""
    result = f"{apocope(number_words(whole))}{connector} {unit}"
    if fraction:
        result += f" con {apocope(number_words(fraction))} "
        result += "centavo" if fraction == 1 else "centavos"
    return ("menos " if amount < 0 else "") + result
