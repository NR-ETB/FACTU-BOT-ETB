# Trabajo en Videofacturación ETB

- Mantener fase 1 y evaluar el piloto audiovisual local gratuito solicitado por el usuario.
- El piloto local usa datos ficticios y produce borradores revisables; no implica aprobación humana.
- Sin APIs generativas de pago, envíos, campañas ni despliegues. HeyGen permanece deshabilitado.
- Datos sintéticos solamente. No copiar datos personales reales a fixtures, registros ni Git.
- Dominio sin dependencias de FastAPI, Streamlit, Pandas, SQLAlchemy o proveedores.
- Dinero: Decimal desde texto; SQLite en centavos enteros; JSON en cadenas decimales.
- No redondear para conciliar ni recalcular tarifas, impuestos o prorrateos.
- Toda cifra narrada conserva referencia al archivo, hoja, fila y campo originales.
- La interfaz solo consume la API. El navegador no es fuente persistente del proceso.
- No permitir edición libre de guiones ni aprobar versiones obsoletas.
- Mantener versiones de reglas/plantilla y pruebas independientes al cambiar redacción.
- Nunca registrar contenido de archivos, guiones, nombres, credenciales o errores externos crudos.
- Comprobaciones: `.venv/Scripts/python -m pytest` y `.venv/Scripts/python -m ruff check src tests scripts`.
- Demo: `.venv/Scripts/python -m videofacturacion.demo`.
- Antes de terminar, actualizar documentación y ejecutar aceptación CSV/XLSX.
- Fase 2 exige autorización específica de gasto y uso de API. No implementar distribución.
