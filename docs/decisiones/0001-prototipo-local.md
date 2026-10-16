# ADR 0001 — Prototipo local y verificable

Estado: implementado para fase 1.

## Decisiones

- Monolito modular, Python 3.12, FastAPI, Streamlit consumidor HTTP y SQLite local.
- Ingesta financiera estricta mediante CSV estándar/openpyxl. Pandas se limita a tablas de UI:
  evita inferencia automática de importes e identificadores en el dominio.
- Plantillas Jinja2 empaquetadas, junto al código; no carpeta raíz duplicada.
- Migraciones Alembic empaquetadas para poder ejecutarse con la aplicación instalada.
- Cabeceras de cliente inmutables por factura; maestro relacional editable diferido.
- Fixture de cinco clientes y perfil separado para el adjunto amplio de una factura, con nombre genérico.
- Sin IA generativa, HeyGen, trabajador ni distribución en la fase inicial.
- Dependencias compatibles declaradas y entorno probado fijado en requirements.lock.

## Consecuencias

Instalación sencilla y resultados reproducibles. Streamlit se reemplaza sin mover reglas.
Los documentos de auditoría conservan cadenas exactas además de centavos normalizados.
Una fuente nueva invalida guiones anteriores aun con idénticos importes, para mantener revisión
vinculada a la evidencia concreta. No se reactivan aprobaciones al borrar versiones posteriores.

SQLite y el cerrojo de proceso no ofrecen coordinación distribuida. Multiusuario/varios servidores
requieren PostgreSQL, autenticación y una evaluación de la cola. El uso con datos reales requiere
otras decisiones de seguridad y retención. La exactitud comprobada del texto no certifica un video futuro.
