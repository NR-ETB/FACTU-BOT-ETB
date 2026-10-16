# Datos sintéticos

`cinco_clientes.csv` y `cinco_clientes.xlsx` representan las mismas cinco facturas.
Totales esperados: 70000.00, 105000.00, 95000.00, 119000.00 y 115000.00 COP.
El caso de impuesto es un importe suministrado; no define una regla fiscal.

`etb_prueba_sintetica.csv` reproduce el esquema y los importes de la muestra adjunta,
con un nombre genérico. El original permanece fuera de Git.
Perfil `etb_prueba_v1`: subtotal 140000.00 − descuento 10000.00 = total 130000.00.
El subtotal es un control, no un concepto adicional.

Regenerar el XLSX: `python scripts/create-test-workbook.py`.
Las columnas monetarias e identificadores se almacenan como texto para preservar su representación.
