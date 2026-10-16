from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from videofacturacion.domain.models import Invoice

WIDTH, HEIGHT = 1280, 720
NAVY, TEAL, INK, MUTED = "#102C46", "#007E87", "#182E43", "#526579"


def display_money(value: str) -> str:
    amount = Decimal(value)
    sign = "−" if amount < 0 else ""
    major, minor = divmod(int(abs(amount) * 100), 100)
    return f"{sign}$ {major:,}".replace(",", ".") + (f",{minor:02d}" if minor else "") + " COP"


def scene_data(invoice: Invoice, segment: dict) -> dict:
    h = invoice.header
    kind = segment["kind"]
    if kind == "line":
        line = next(line for line in invoice.lines if line.line_id == segment["line_id"])
        if segment["amount"] != format(line.amount, ".2f"):
            raise ValueError("El importe visual no corresponde al concepto fuente.")
        return {
            "title": line.description,
            "label": line.service,
            "value": display_money(segment["amount"]),
            "note": "Descuento o abono aplicado"
            if line.amount < 0
            else "Importe informado en tu factura",
        }
    if kind == "total":
        if segment["amount"] != h["total_fuente"]:
            raise ValueError("El total visual no corresponde a la factura.")
        return {
            "title": "El total de tu factura",
            "label": "Total verificado con la fuente",
            "value": display_money(h["total_fuente"]),
            "note": "Cada concepto se ha conciliado sin redondeos",
        }
    if kind == "due":
        return {
            "title": "Tu fecha de vencimiento",
            "label": "Fecha registrada en la factura",
            "value": h["fecha_vencimiento"],
            "note": "Consulta el detalle en tu factura original",
        }
    if kind == "greeting":
        return {
            "title": "Tu factura, paso a paso",
            "label": h["nombre_cliente"],
            "value": "Resumen de facturación",
            "note": f"Período: {h['periodo_inicio']} al {h['periodo_fin']}",
        }
    raise ValueError("Tipo de escena desconocido.")


def font(size: int, bold=False):
    windows = Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf")
    if windows.is_file():
        return ImageFont.truetype(str(windows), size)
    return ImageFont.load_default(size=size)


def wrapped_lines(draw, text, face, max_width):
    lines, current = [], ""
    for word in text.split():
        if draw.textlength(word, font=face) > max_width:
            raise ValueError("Una palabra no cabe en la plantilla visual; revise la fuente.")
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=face) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + ([current] if current else [])


def paragraph(draw, text, x, y, *, size=24, max_width=1100, max_lines=2, fill=INK, bold=False):
    face = font(size, bold)
    lines = wrapped_lines(draw, text, face, max_width)
    if len(lines) > max_lines:
        raise ValueError("El texto no cabe en la plantilla; no se permite truncarlo.")
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += size + 9
    return y


def render_card(invoice: Invoice, segment: dict, index: int, count: int, target: Path) -> dict:
    data = scene_data(invoice, segment)
    image = Image.new("RGB", (WIDTH, HEIGHT), "#F2F6FA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 106), fill=NAVY)
    draw.text((60, 24), "ETB", font=font(39, True), fill="white")
    draw.text((166, 39), "VIDEOfacturación  /  Piloto local", font=font(22), fill="#DAEDF2")
    draw.rounded_rectangle((1012, 28, 1220, 74), radius=20, fill="#254760")
    draw.text((1038, 36), "DATOS FICTICIOS", font=font(18, True), fill="white")
    draw.rounded_rectangle((48, 134, 1232, 502), radius=24, fill="white")
    title_bottom = paragraph(draw, data["title"], 80, 154, size=31, max_lines=2, bold=True)
    paragraph(
        draw, data["label"], 80, max(239, title_bottom + 10), size=22, max_lines=1, fill=MUTED
    )
    paragraph(draw, data["value"], 80, 296, size=54, max_lines=1, fill=TEAL, bold=True)
    paragraph(draw, data["note"], 80, 406, size=21, max_lines=2, fill=MUTED)
    draw.text((65, 517), "NARRACIÓN", font=font(15, True), fill=TEAL)
    paragraph(draw, segment["text"], 65, 541, size=21, max_width=1140, max_lines=4, fill=INK)
    draw.rectangle((0, 684, WIDTH, HEIGHT), fill=NAVY)
    draw.rectangle((0, 680, int(WIDTH * (index + 1) / count), 684), fill=TEAL)
    draw.text(
        (48, 690),
        "BORRADOR  ·  VOZ es-ES  ·  SIN REVISIÓN AUDIOVISUAL",
        font=font(14),
        fill="white",
    )
    draw.text((1130, 690), f"{index + 1} / {count}", font=font(14), fill="white")
    image.save(target)
    return data
