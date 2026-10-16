# Estrategia de pruebas y aceptación

## Comandos

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m videofacturacion.demo
```

Las pruebas utilizan datos ficticios y directorios temporales; no requieren un servidor externo.
El directorio de datos se inyecta en la aplicación y las migraciones se ejercitan desde cero y al reiniciar.

## Cobertura de comportamiento

- Importes ambiguos, NaN, exponenciales, precisión adicional, signos, centavos y verbalización.
- Identificadores con ceros, fechas imposibles, cabeceras contradictorias, líneas duplicadas.
- Conceptos desconocidos, suma distinta por un centavo, monedas distintas de COP.
- Estructura, delimitadores y codificación, límites, fórmulas XLSX.
- Guion alterado: importe, omisión, duplicación, sentido financiero, nombre, fecha, origen y evidencia.
- API: recorrido completo, deduplicación, errores seguros, revisiones, ZIP y borrado en cascada.
- Obsolescencia tras nueva fuente o plantilla; persistencia de aprobación tras reinicio.
- Perfil adjunto: subtotal 140000.00, descuento 10000.00 y total 130000.00.
- AppTest: generación del lote, revisión, exportación y aviso de API no disponible.
- Aceptación CSV/XLSX: cinco guiones, cifras esperadas, sin transporte HTTP externo y menos de diez segundos.

## Resultados del 16 de octubre de 2026

Entorno: Windows AMD64, Python 3.12.14, procesador Intel64 Family 6 Model 186 Stepping 3.
Dependencias exactas en requirements.lock. Comprobación final:

| Comprobación | Resultado |
|---|---|
| pytest | 62 pruebas aprobadas en 8,60 s |
| Ruff | Sin errores en src, tests y scripts |
| pip check | Sin dependencias incompatibles |
| HTTP real | FastAPI y Streamlit disponibles en 127.0.0.1; carga de cinco facturas y cinco guiones correcta |
| Demo CSV + XLSX | Cinco facturas y cinco guiones por formato; 36 enlaces verificados por formato; 0,601 s total |
| Adjunto de prueba | Una factura, un guion, 11 enlaces verificados; 0,323 s; total 130000.00 COP |
| Generación externa | Cero llamadas |
| Procesos de prueba | Detenidos automáticamente al terminar la prueba HTTP |

Evidencia local no versionada: `var/aceptacion-final/ultima-demostracion.json`, sus dos ZIP y
`var/adjunto-final/ultima-demostracion.json` con el ZIP del adjunto. Los tiempos excluyen la instalación
y el inicio del intérprete; incluyen migraciones, importación, guiones y exportación en proceso.

Existe un aviso de deprecación del TestClient de Starlette por su compatibilidad actual con HTTPX.
No afecta la ejecución comprobada; revisar la migración a su transporte recomendado al actualizar
dependencias. No se suprime el aviso ni se presenta como un fallo funcional.

Se comprobaron además fallos de disco/transacción al escribir y borrar, con restauración o recuperación
de originales pendientes. Los resultados audiovisuales y las pruebas de proveedor corresponden a
fases posteriores.

## Evaluación audiovisual local posterior

La evaluación gratuita solicitada posteriormente añadió seis pruebas de cifras y escenas: **68 pruebas
aprobadas en 11,64 s** con la misma advertencia de deprecación. Ruff sin errores y pip check correcto.
Se renderizaron y decodificaron seis MP4 (adjunto y cinco clientes sintéticos), comprobando pistas de
audio/video, duraciones y audio no silencioso. Se inspeccionaron las tarjetas de descuento y total del
adjunto y una captura del MP4 codificado. No se certifica la pronunciación: revisión humana pendiente.
Mediciones y limitaciones en [piloto-gratuito.md](piloto-gratuito.md).
