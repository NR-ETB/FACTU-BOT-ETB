# Seguridad y operación local

## Modelo operativo

Un operador, un equipo y un proceso API. Los scripts se enlazan a 127.0.0.1; Streamlit no accede
directamente a la base. No publicar puertos, usar carpetas de red ni iniciar varios trabajadores API.
No hay autenticación de usuarios ni control corporativo de roles en este prototipo.

Solo datos ficticios, con confirmación obligatoria al cargar. La confirmación no detecta datos reales.
El adjunto está identificado como prueba; se conserva fuera de Git y no se incluyen sus nombres en fixtures.

## Archivos y registros

Originales guardados con UUID técnico y extensión controlada, nunca con una ruta enviada por el usuario.
SQLite conserva centavos enteros y documentos de auditoría con cadenas decimales exactas.
Los registros de aplicación contienen eventos, identificadores técnicos y contadores, sin nombres,
guiones, valores de filas ni motivos de revisión. Ejecutar Uvicorn sin access log para evitar consultas
arbitrarias en registros. No utilizar depuración con contenido de solicitudes.

Datos locales sin cifrado propio de aplicación: requieren permisos y cifrado de disco del equipo
corporativo antes de cualquier uso con información real. No se afirma cumplimiento legal o autorización
para enviar información a proveedores. Los archivos permanecen hasta eliminación manual.

## Eliminación y respaldo

DELETE de importación elimina original, facturas, líneas, guiones y revisiones mediante cascada.
El archivo se renombra provisionalmente: un fallo de transacción restaura el original. Si se interrumpe
el borrado físico después de confirmar la base, la API informa 503 y completa esa eliminación manual
pendiente al reiniciar. Esta recuperación no es una política de borrado programado.
No reactiva versiones anteriores. No puede borrar ZIP que el operador ya descargó o exportó con la demo;
esas copias deben gestionarse manualmente. No hay recuperación de borrado en la aplicación.
Para copia coherente, detener API/UI y respaldar el directorio de datos completo. Restaurar con los servicios
detenidos; iniciar aplica las migraciones pendientes. No modificar manualmente filas de la base.

## Secretos y conectividad

`.env` excluido, `.env.example` sin secretos. Fase 1 no tiene credenciales de generación.
Telemetría de Streamlit deshabilitada; no hay llamadas audiovisuales. La interfaz sí realiza HTTP local
a la API. La instalación de dependencias requiere acceso al índice de paquetes.

## Incidentes

Si falla una carga o revisión, consultar el historial antes de repetirla. Importaciones idénticas son
idempotentes por hash/perfil. Ante error de disco, liberar espacio y comprobar integridad del directorio.
Los errores internos se devuelven sin detalles sensibles; los errores de validación tienen localización.
Un archivo con errores estructurales se conserva como intento rechazado, y puede eliminarse desde la UI.

## Antes de ampliar el uso

Decidir autenticación/SSO, permisos, auditoría corporativa, retención, cifrado, copias, restauración,
condiciones de proveedor y autorización para datos reales. Estas tareas son puertas de entrada a
una operación diferente; no autorizan distribución ni despliegue por sí solas.
