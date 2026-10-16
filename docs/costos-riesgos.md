# Costos, riesgos y evaluación audiovisual pendiente

Fase 1: cero llamadas y cero consumo de APIs de generación. Existen costos de desarrollo y equipo local.
No hay cuenta de proveedor conectada desde el código ni claves que habiliten generación.

## Referencia de costos, no cotización

Consulta de planificación del 16 de octubre de 2026: Studio Avatar III USD 0,99/min;
Studio Avatar IV USD 4,83/min. Cinco videos de un minuto: USD 4,95 o 24,15; cien diarios:
USD 99 o 483/día. Excluye impuestos, divisas, almacenamiento, regeneración y servicios adicionales.
No garantiza compatibilidad de motor, cuenta y plantilla. Revalidar tarifas antes de H8.

[Precios oficiales](https://help.heygen.com/en/articles/10060327-heygen-api-pricing-explained)
· [Guía de APIs](https://www.heygen.com/blog/heygen-api-guide).

## Evaluación antes de integrar

Comparar voz es-CO, pronunciación de cifras, fidelidad al texto, plantilla con variables,
legibilidad y capacidad máxima de conceptos, acceso de la cuenta, contrato REST vigente,
duración, cuotas, estados, idempotencia, descarga y tratamiento de datos.
Objetivo de prueba: avatar y resumen visual 16:9/1080p, sin música, 60–90 segundos orientativos.
Bloquear una factura que no quepa; nunca omitir conceptos por duración.
Esta evaluación documental inicial no sustituye la validación contractual ni la prueba técnica.

## Diseño operativo de fase 2

- Interfaz del proveedor: enviar solicitud con guion aprobado/configuración, consultar estado y descargar.
- Trabajo persistido antes de enviar; registrar identificador externo antes de continuar.
- Identidad por versión de guion, proveedor, plantilla, voz y configuración.
- Concurrencia inicial uno, presupuesto por lote/día y bloqueo cuando no alcance el saldo estimado.
- Consultas transitorias: hasta tres reintentos, respetar Retry-After.
- Seguimiento entre 15 y 60 segundos; a los 30 minutos dejar pendiente, sin reenviar automáticamente.
- Un envío incierto exige conciliación; no prometer exactamente una ejecución si el proveedor no lo garantiza.
- Separar GENERADO de APROBADO_AUDIOVISUAL; escuchar y revisar todo el piloto.

## Riesgos y responsables

| Riesgo | Control | Responsable propuesto |
|---|---|---|
| Fuente ambigua o doble impuesto | Contrato aditivo y mapeo revisado | Facturación |
| Descripción comercial incorrecta | Revisión de catálogo/fuente | Negocio |
| Voz o pantalla alteran datos | Revisión audiovisual completa | Operador y comunicaciones |
| Cobro duplicado | Identidad persistente y conciliación de incertidumbre | Tecnología |
| Dependencia/cambios de proveedor | Adaptador aislado, contrato y tarifas versionados | Tecnología |
| Datos personales | Minimización y revisión de condiciones antes de datos reales | Seguridad |
| Revisión manual limita capacidad | Medir minutos de revisión por video | Operaciones |
| Concurrencia SQLite | Un proceso local; PostgreSQL al ampliar operación | Tecnología |

Decisiones abiertas: catálogo corporativo, voz/avatar/activos autorizados, cuenta y presupuesto API,
retención y condiciones del proveedor, autenticación y futura infraestructura. No bloquean fase 1.
