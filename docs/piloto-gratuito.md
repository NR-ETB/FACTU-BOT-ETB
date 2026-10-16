# Evaluación del piloto gratuito local

Fecha: 16 de octubre de 2026. Evaluación autorizada por el usuario después de revisar el costo de HeyGen.

## Objetivo

Comprobar generación de MP4 personalizados con datos ficticios, guion determinista, importes visuales
y narración local, sin cuentas ni consumo de APIs audiovisuales externas.

## Implementación de la prueba

- Narración: Windows System.Speech, voz Microsoft Helena Desktop, es-ES, PCM mono a 22050 Hz.
- Escenas: tarjetas 1280×720 generadas con Pillow; conceptos, descuentos, total y vencimiento.
- Ensamblaje: FFmpeg suministrado por imageio-ffmpeg 0.6.0 dentro del entorno virtual.
- Video: MP4 H.264/AAC, 12 cuadros por segundo, marcas visibles de datos ficticios y borrador.
- Un segmento por línea, más presentación, total y vencimiento. Se conservan conceptos de importe cero.
- Temporización desde duración real de cada WAV, con pausa de 0,4 s por escena.
- Sin edición o cálculo libre: los datos visuales se vinculan a los segmentos verificados.
- Salida: manifiesto de origen, guion, importes, imágenes, duraciones y hashes.

La prueba se ejecuta mediante CLI. No incorpora generación audiovisual a los endpoints ni a Streamlit,
no modifica el historial de aprobación y no activa HeyGen. No hay cola, reintentos automáticos ni distribución.

## Resultados observados

La factura adjunta produjo un video de **57,917 segundos**, tamaño **1.162.508 bytes**, en
**15,027 segundos** de procesamiento audiovisual, con total de **130000.00 COP**.
Se comprobaron visualmente las tarjetas del descuento (-10000.00 COP) y del total.
Entorno: Windows AMD64, Python 3.12.14. Los tiempos son mediciones de este equipo, no una garantía.

Ubicación del informe de esta prueba:
`var/piloto-gratuito-adjunto/690f6d79-8268-489a-8802-278db1039783/piloto.json`.

Los resultados del lote de cinco clientes se conservan en `var/piloto-gratuito-cinco/ultimo-piloto.json`.

El lote terminó correctamente: **cinco MP4 en 43,728 segundos** de procesamiento secuencial.

| Factura ficticia | Total COP | Duración del video | Tiempo de render |
|---|---:|---:|---:|
| 001 | 70000.00 | 26,667 s | 7,781 s |
| 002 | 105000.00 | 40,833 s | 9,152 s |
| 003 | 95000.00 | 33,250 s | 8,299 s |
| 004 | 119000.00 | 35,667 s | 8,515 s |
| 005 | 115000.00 | 41,000 s | 9,755 s |

Los cinco MP4 y su informe se agruparon en
`var/piloto-gratuito-cinco/53aec3c5-5a54-4566-8cf8-02c307c7a84d/cinco-videos.zip`.
Total de esta evaluación: seis videos (cinco sintéticos y uno del adjunto), cero llamadas de generación externa.

## Verificación y límites

- 68 pruebas aprobadas: regresión de fase 1 y comprobaciones de formato monetario/escenas.
- El guion se verifica contra la fuente antes y después del render.
- La plantilla rechaza textos que no caben; no los trunca.
- Los WAV deben contener muestras no silenciosas y formato correcto.
- Cada MP4 se decodifica completo y exige pista de audio y video; la duración debe cubrir la narración.
- Esta verificación técnica no certifica pronunciación ni contenido escuchado: estado BORRADOR,
  revisión audiovisual PENDIENTE. No se registra aprobación humana automática.
- Voz de España, sin avatar. No se afirma cumplimiento del requisito de voz colombiana.
- Costo de APIs de generación: **USD 0,00**. Existen consumo de equipo y costos de desarrollo.
- Artefactos locales excluidos de Git, sin borrado programado ni envío externo.

## Conclusión y siguiente incremento

La generación básica local es viable para evaluar los cinco clientes. Para un piloto operado desde
la interfaz falta integrar un trabajo persistente y el botón de render desde guion aprobado, seguimiento,
previsualización, descarga y registro separado de la revisión audiovisual. Mantener el mismo contrato de
proveedor local para poder sustituir la voz es-ES por es-CO sin tocar facturación.

No extrapolar estas mediciones a 100 videos diarios sin probar lotes, almacenamiento, recuperación y
tiempo de revisión humana. Datos reales, distribución, despliegue y servicios de pago siguen fuera del piloto.

Referencias de los componentes: [Microsoft System.Speech](https://learn.microsoft.com/dotnet/api/system.speech.synthesis.speechsynthesizer),
[FFmpeg](https://ffmpeg.org/about.html). El motor local se encuentra en `audiovisual/local_pilot.py`.
