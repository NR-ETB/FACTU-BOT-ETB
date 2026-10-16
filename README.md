# Videofacturación Inteligente ETB

Prototipo local de **fase 1**: convierte facturas ficticias CSV/XLSX en guiones explicativos
deterministas, concilia sus importes y registra su revisión. Incluye una evaluación de **video local
gratuito por CLI**, separada de la interfaz. No invoca proveedores audiovisuales ni envía mensajes.

## Inicio rápido en Windows

Requiere Python 3.12 y dos terminales PowerShell abiertas en la raíz del repositorio.
El entorno `.venv` ya puede existir en este equipo; en una instalación nueva:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
```

En la primera terminal:

```powershell
.\scripts\start-api.ps1
```

En la segunda:

```powershell
.\scripts\start-ui.ps1
```

Interfaz: [http://127.0.0.1:8501](http://127.0.0.1:8501).
Contrato OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
Ambos servicios se enlazan a la interfaz local. Detener cada uno con Ctrl+C.
Si PowerShell restringe scripts, ejecutar directamente los comandos Python contenidos en ellos.
No iniciar varios procesos API sobre la misma base de datos.

## Recorrido del prototipo

1. Elegir `conceptos_v1`, cargar `tests/fixtures/cinco_clientes.csv` o `.xlsx` y confirmar datos ficticios.
2. Revisar estado de importación y errores por factura.
3. Generar el lote o una factura. Las facturas inválidas u obsoletas quedan bloqueadas.
4. Comparar guion, fuente y tabla de correspondencia.
5. Aprobar o rechazar; el rechazo exige motivo. No hay edición libre.
6. Descargar el ZIP con guiones por estado e informe JSON, o eliminar la importación.

Resultados esperados: cinco facturas y cinco guiones, con totales de **70.000, 105.000,
95.000, 119.000 y 115.000 COP**. Importar otro archivo con las mismas cuentas/facturas crea
una nueva versión y vuelve obsoletos los guiones anteriores; CSV y XLSX son fuentes distintas.
Reimportar exactamente el mismo archivo/perfil reutiliza su registro, sin reactivar versiones antiguas.

### CSV adjunto: `factura_prueba_ETB.csv`

Seleccionar **`etb_prueba_v1`**: utiliza coma y una fila por factura, con columnas por servicio.
La muestra adjunta contiene **una** factura: servicios 140.000 − descuento 10.000 = **130.000 COP**.
Se valida además el subtotal de internet, televisión y telefonía. El subtotal no se suma otra vez.
`tests/fixtures/etb_prueba_sintetica.csv` reproduce ese esquema con nombre genérico.
El archivo original de Downloads no forma parte del repositorio.

## Demostración sin servidores ni llamadas de generación

```powershell
.\.venv\Scripts\python.exe -m videofacturacion.demo
```

Procesa los cinco clientes en CSV y XLSX mediante la API en proceso, genera ZIP e informe de tiempo
en `var/demo/`. No aprueba automáticamente los guiones. Cada ZIP conserva el estado al exportarlo;
la base refleja que la fuente XLSX posterior sustituye a la CSV.

Para comprobar el archivo adjunto de prueba:

```powershell
.\.venv\Scripts\python.exe -m videofacturacion.demo --file "C:/Users/nicolas.rodriguez.u/Downloads/factura_prueba_ETB.csv" --profile etb_prueba_v1 --confirm-synthetic --data-dir var/prueba-adjunta
```

Las bases de demostración son independientes de la interfaz, que usa `var/etb.sqlite3` por defecto.

## Piloto gratuito de video local (Windows)

Evaluación solicitada: MP4 de borrador con voz instalada de Windows y tarjetas de facturación,
sin avatar ni APIs externas. Usa el guion verificado y no registra una aprobación humana.
La voz disponible utilizada es `Microsoft Helena Desktop`, español de España (`es-ES`).
Este resultado todavía necesita revisión audiovisual; no cumple la voz colombiana del objetivo final.

Si se instaló solo el paquete base, añadir las dependencias opcionales:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[local-video]"
```

Cinco clientes ficticios:

```powershell
.\.venv\Scripts\python.exe -m videofacturacion.audiovisual.local_pilot --confirm-synthetic
```

Archivo adjunto de prueba:

```powershell
.\.venv\Scripts\python.exe -m videofacturacion.audiovisual.local_pilot --file "C:/Users/nicolas.rodriguez.u/Downloads/factura_prueba_ETB.csv" --profile etb_prueba_v1 --confirm-synthetic --output var/piloto-gratuito-adjunto
```

La salida contiene MP4, guion, escenas, WAV y manifiesto de importes/tipos/duraciones/hashes.
`ultimo-piloto.json` referencia la última ejecución. Cada ejecución utiliza un directorio nuevo;
no modifica facturas, guiones ni aprobaciones de la aplicación. Los archivos del piloto se gestionan
separadamente y no se borran al eliminar una importación desde Streamlit.

Resultados y límites: [Evaluación del piloto gratuito](docs/piloto-gratuito.md).
El botón de generación de video en la interfaz y los trabajos persistentes aún no están integrados.

## Contrato de datos

`conceptos_v1`: CSV UTF-8, separador `;`, una fila por concepto; XLSX con hoja `facturacion`.
Columnas exactas:

```text
cliente_id;nombre_cliente;factura_id;cuenta_id;periodo_inicio;periodo_fin;fecha_vencimiento;moneda;total_fuente;linea_id;servicio;concepto_codigo;concepto_descripcion;importe
```

Identificadores textuales, fechas `AAAA-MM-DD`, moneda `COP` e importes con punto decimal,
sin miles y máximo dos decimales. Cabeceras repetidas deben coincidir.
Se rechazan fórmulas, conceptos desconocidos, signos incompatibles y diferencias de un centavo.
Catálogo: `INTERNET`, `TELEVISION`, `TELEFONIA`, `CARGO`, `IMPUESTO`, `SALDO_ANTERIOR`,
`OTROS_CARGOS` positivos o cero; `DESCUENTO`, `PAGO`, `ABONO` negativos o cero.
No incluir un mismo impuesto dentro de un cargo y como línea adicional.

No se recalculan tarifas ni impuestos. Las descripciones se tratan como datos literales,
nunca como instrucciones. Su corrección comercial corresponde al responsable de la fuente.

## Configuración y datos locales

Copiar `.env.example` a `.env` si se necesitan cambios. `ETB_DATA_DIR`, `ETB_MAX_FILE_MB`,
`ETB_MAX_INVOICES`, `ETB_MAX_LINES`, `ETB_API_URL`. Valores iniciales: 10 MB, 100 facturas,
2.000 filas; los lotes de guiones admiten hasta 100 identificadores.
La UI limita cargas a 10 MB mediante `.streamlit/config.toml`; si se cambia el límite API,
ajustar también ese archivo.

La primera ejecución aplica migraciones Alembic automáticamente. `var/` contiene SQLite y
copias de los originales con nombre técnico. `.env`, `.venv`, cachés y resultados no se versionan.
No se requieren claves API. La confirmación de datos ficticios es una declaración del operador,
no un detector automático de información personal.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe scripts/smoke-local.py
```

Incluyen importación, precisión, guiones alterados, persistencia tras reinicio, revisión,
exportación/eliminación, equivalencia CSV/XLSX y recorrido de interfaz con Streamlit AppTest.
La aceptación bloquea el transporte HTTP externo y verifica el objetivo de diez segundos.
La prueba HTTP arranca y detiene sus propios servidores locales y no deja servicios en ejecución.
`requirements.lock` fija el entorno probado; `pyproject.toml` declara intervalos compatibles.

## Documentación y siguientes fases

- [Alcance](docs/alcance.md), [requisitos](docs/requisitos.md), [arquitectura](docs/arquitectura.md).
- [Datos y perfiles](docs/modelo-datos.md), [roadmap](docs/plan-desarrollo.md), [aceptación](docs/pruebas-aceptacion.md).
- [Seguridad y operación](docs/seguridad-operacion.md), [costos y riesgos](docs/costos-riesgos.md).
- [Decisiones técnicas](docs/decisiones/0001-prototipo-local.md), [instrucciones para agentes](AGENTS.md).

HeyGen, trabajadores audiovisuales, presupuestos, autenticación multiusuario y despliegue
pertenecen a fases posteriores. Cualquier generación real requiere aprobación específica de uso
de API y gasto. No hay integración de distribución ni endpoints de video habilitados.
