# Modelo y perfiles

## Entidades de fase 1

Importación → facturas versionadas → líneas, guiones → revisiones.
Importación: UUID técnico, hash SHA-256, perfil, extensión, creación UTC y errores estructurales.
Factura: clave lógica cuenta/factura, instantánea de cliente/cabecera/líneas, vigencia, estado,
hash, total y suma en centavos. Línea: identificador, centavos y referencia original.
Guion: firma, segmentos, texto, evidencia y estado. Revisión: decisión, motivo, operador y fecha.

Los campos cliente_id/nombre_cliente se guardan en cada instantánea, evitando que un cambio de
nombre modifique documentos anteriores. No se captura documento de identidad, teléfono, dirección o correo.
En fase 2 se añadirán trabajos y artefactos, sin modificar el significado de una aprobación de guion.

## conceptos_v1

Columnas exactas en README; todas obligatorias. Orden libre, sin duplicados ni columnas extra.
CSV UTF-8 con BOM opcional y punto y coma. XLSX hoja `facturacion`, sin fórmulas.
Dinero textual sin separador de miles, punto decimal, hasta 12 enteros y dos decimales.
XLSX admite celdas numéricas si su representación es válida; identificadores deben almacenarse
como texto para conservar ceros que Excel ya no puede recuperar después de convertirlos a números.
No se redondean artefactos de precisión: se rechazan.

Cabecera: cliente_id, nombre_cliente, factura_id, cuenta_id, periodo_inicio, periodo_fin,
fecha_vencimiento, moneda, total_fuente. Detalle: linea_id, servicio, concepto_codigo,
concepto_descripcion, importe. Cabecera idéntica por cuenta/factura; línea única en cada factura.
Identificadores de cliente, factura y cuenta: letras ASCII, números, guion y guion bajo, hasta 80 caracteres.
Textos: máximo 300 caracteres y sin controles. Se recortan espacios exteriores conservando el valor
original en las referencias auditables y el archivo cargado.

Total = suma de todas las líneas firmadas. Impuestos independientes suministrados por la fuente.
No se puede detectar automáticamente que un impuesto ya venía incluido en otro cargo: el responsable
del archivo debe cumplir el contrato. La conciliación numérica no demuestra corrección tributaria.

## etb_prueba_v1

CSV con coma y encabezados exactos de `tests/fixtures/etb_prueba_sintetica.csv`; XLSX con la misma
estructura en hoja `facturacion`. Una fila por factura. Mapeo explícito:

| Origen | Destino |
|---|---|
| id_cliente | cliente_id |
| numero_cuenta | cuenta_id |
| numero_factura | factura_id |
| total_pagar | total_fuente |
| valor_internet / television / telefonia | líneas INTERNET / TELEVISION / TELEFONIA |
| descuento | línea DESCUENTO con signo invertido |
| saldo_anterior / otros_cargos | líneas positivas correspondientes |
| subtotal_servicios | control de suma de los tres servicios; no se narra como cargo adicional |

Todos esos importes de origen deben ser no negativos. Las líneas de cero se conservan y explican.
fecha_emision, estado_factura y tipo_servicio permanecen en el original; no se utilizan para afirmar
estado de pago ni condiciones comerciales. No se deducen impuestos ausentes.
Este perfil solo es un adaptador para el archivo de prueba, no una especificación oficial de ETB.

## Evidencia

Cada enlace conserva hash de archivo, hoja, fila, columna y valor original, junto con el valor
normalizado, expresión narrada, sentido financiero y resultado. La factura conserva las descripciones
y servicios que originan los segmentos. La verificación comprueba cobertura, totales, fechas, nombre,
texto completo y manifiesto; una edición manual de la base no equivale a una revisión autorizada.
