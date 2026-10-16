# Requisitos y trazabilidad

| ID | Comportamiento | Evidencia |
|---|---|---|
| RF01–RF03 | CSV/XLSX, errores localizados, identificadores y origen conservados | Unitarias de ingesta y equivalencia |
| RF04–RF05 | Catálogo/signos, suma exacta, bloqueo por factura | Unitarias y validación parcial API |
| RF06 | Guiones individuales y por lote explícito | Integración y aceptación |
| RF07 | Fuente, explicación y tabla de correspondencia | Pruebas de guiones alterados y UI |
| RF08 | Aprobación/rechazo versionados y motivo de rechazo | Ciclo API y UI |
| RF09 | Exportación con guiones e informe | Integración ZIP |
| RF10–RF12 | Generación, seguimiento y descarga audiovisual | Diferido a fase 2; sin endpoints habilitados |

## No funcionales

- Cero centavos de tolerancia; Decimal y almacenamiento normalizado entero.
- Repetición de datos, código de reglas y plantilla: mismo texto generado.
- Referencias de archivo/hash, hoja, fila y columna por importe, nombre y fechas.
- Un proceso API; interfaz sin acceso directo a SQLite.
- Límites iniciales: 10 MB, 100 facturas, 2.000 filas; XLSX descomprimido máximo 50 MB/1.000 componentes.
- Fechas ordenadas: inicio ≤ fin ≤ vencimiento. No se comparan con la fecha del equipo.
- Datos sintéticos confirmados explícitamente; sin credenciales audiovisuales ni tráfico de generación.
- Persistencia tras reinicio y migración inicial idempotente.
- Cinco facturas por formato en menos de diez segundos en el equipo medido.
- Telemetría Streamlit deshabilitada; registros de aplicación sin datos de cliente.

## Estados

- Importación: VALIDADO, CON_ERRORES, RECHAZADO. Una carga rechazada estructuralmente queda registrada.
- Factura: VALIDA/INVALIDA y marca de vigencia. Una fila inválida bloquea toda su factura.
- Guion: VALIDADO, APROBADO, RECHAZADO, OBSOLETO; BLOQUEADO cuando falla la comprobación al leerlo.
- La revisión es repetible, con historial. Una nueva decisión reemplaza el estado y conserva decisiones anteriores.
- El lote devuelve resultado o error por identificador; no afirma éxito global si alguna factura falló.
