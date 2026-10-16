import httpx
import pandas as pd
import streamlit as st

from videofacturacion.config import Settings

st.set_page_config(page_title="Videofacturación ETB", page_icon="🧾", layout="wide")
settings = Settings()


def api(method, path, **kwargs):
    try:
        with httpx.Client(
            base_url=settings.api_url + "/api/v1", timeout=30, trust_env=False
        ) as client:
            response = client.request(method, path, **kwargs)
        if response.is_error:
            try:
                message = response.json()["error"]["message"]
            except (ValueError, KeyError):
                message = "La operación no pudo completarse."
            st.error(message)
            return None
        if response.status_code == 204:
            return True
        return (
            response.content
            if "application/zip" in response.headers.get("content-type", "")
            else response.json()
        )
    except httpx.HTTPError:
        st.error("No hay conexión con la API local. Iníciala y vuelve a cargar esta página.")
        return None


st.title("Videofacturación Inteligente ETB")
st.caption("Fase 1 · Guiones verificables · Datos ficticios · Operación local")

with st.sidebar:
    st.header("Cargar archivo de prueba")
    profile = st.selectbox(
        "Formato",
        ["conceptos_v1", "etb_prueba_v1"],
        help="Conceptos: CSV con punto y coma. ETB prueba: CSV con coma y columnas por servicio.",
    )
    uploaded = st.file_uploader("Archivo CSV o XLSX", type=["csv", "xlsx"])
    confirmed = st.checkbox("Confirmo que todos los datos son ficticios")
    if st.button("Importar archivo", disabled=uploaded is None or not confirmed, type="primary"):
        result = api(
            "POST",
            "/imports",
            files={"file": (uploaded.name, uploaded.getvalue())},
            data={"profile": profile, "synthetic_confirmed": "true"},
        )
        if result:
            st.session_state["last_import"] = result["id"]
            st.session_state["notice"] = (
                "Archivo reutilizado." if result["reused"] else "Importación registrada."
            )
            st.rerun()

if notice := st.session_state.pop("notice", None):
    st.success(notice)
imports = api("GET", "/imports")
if imports is None:
    st.stop()
if not imports:
    st.info(
        "Carga un archivo de prueba para comenzar. Hay ejemplos de cinco clientes en tests/fixtures."
    )
    st.stop()
by_id = {item["id"]: item for item in imports}
selected_default = st.session_state.get("last_import")
options = list(by_id)
selected = st.selectbox(
    "Importación",
    options,
    index=options.index(selected_default) if selected_default in by_id else 0,
    format_func=lambda identifier: (
        f"{by_id[identifier]['created_at'][:19]} · {by_id[identifier]['profile']} · {identifier[:8]}"
    ),
)
imported = by_id[selected]
st.caption(f"Archivo fuente: {imported['filename']} · SHA-256: {imported['file_hash']}")
left, middle, right = st.columns(3)
left.metric("Estado", imported["status"])
middle.metric("Facturas válidas", imported["valid"])
right.metric("Facturas con errores", imported["invalid"])
if imported["issues"]:
    st.error("El archivo tiene errores de estructura. No se generarán guiones.")
    st.dataframe(imported["issues"], hide_index=True)

invoices = api("GET", "/invoices", params={"import_id": selected}) or []
if invoices:
    st.subheader("Facturas")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Factura": invoice["source"]["header"]["factura_id"],
                    "Cliente": invoice["source"]["header"]["nombre_cliente"],
                    "Total COP": invoice["total"],
                    "Suma de conceptos": invoice["calculated"],
                    "Estado": invoice["status"],
                    "Vigente": invoice["current"],
                }
                for invoice in invoices
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    valid_ids = [i["id"] for i in invoices if i["status"] == "VALIDA" and i["current"]]
    if st.button("Generar guiones del lote", disabled=not valid_ids):
        batch = api("POST", "/scripts/batch", json={"invoice_ids": valid_ids})
        if batch:
            st.session_state["notice"] = f"Procesadas {len(batch['results'])} facturas."
            st.rerun()
    invoice_id = st.selectbox(
        "Factura para revisar",
        [i["id"] for i in invoices],
        format_func=lambda value: next(
            i["source"]["header"]["factura_id"] for i in invoices if i["id"] == value
        ),
    )
    invoice = next(i for i in invoices if i["id"] == invoice_id)
    if invoice["issues"]:
        st.error("Factura bloqueada: corrige el archivo fuente y realiza una nueva importación.")
        st.dataframe(invoice["issues"], hide_index=True)
    if not invoice["current"]:
        st.warning("Esta factura pertenece a una versión anterior de la fuente.")
    with st.expander("Datos y referencias originales"):
        st.json(invoice["source"])
    if st.button("Generar guion de esta factura", disabled=invoice_id not in valid_ids):
        if api("POST", "/scripts/batch", json={"invoice_ids": [invoice_id]}):
            st.rerun()
    scripts = api("GET", "/scripts", params={"invoice_id": invoice_id}) or []
    for script in scripts:
        st.subheader(f"Guion · {script['status']}")
        st.caption(f"Versión: {script['payload']['template_version']} · {script['id']}")
        st.text(script["payload"]["text"])
        st.markdown("**Correspondencia con la fuente**")
        evidence = [
            {
                "Campo / línea": e.get("line_id", e.get("field")),
                "Hoja": e["source"]["sheet"],
                "Fila": e["source"]["row"],
                "Columna": e["source"]["field"],
                "Original": e["source"]["raw"],
                "Normalizado": e["normalized"],
                "Narrado": e["spoken"],
                "Sentido": e.get("financial_sense", ""),
                "Verificado": e["verified"],
            }
            for e in script["payload"]["evidence"]
        ]
        st.dataframe(pd.DataFrame(evidence), hide_index=True, width="stretch")
        if script["status"] not in ("OBSOLETO", "BLOQUEADO"):
            with st.form("review-" + script["id"]):
                decision = st.radio("Decisión", ["APROBADO", "RECHAZADO"], horizontal=True)
                reason = st.text_area("Motivo (obligatorio al rechazar)", max_chars=1000)
                if st.form_submit_button("Registrar revisión"):
                    if api(
                        "POST",
                        f"/scripts/{script['id']}/reviews",
                        json={"decision": decision, "reason": reason, "operator": "operador-local"},
                    ):
                        st.session_state["notice"] = "Revisión guardada."
                        st.rerun()
        if script["reviews"]:
            with st.expander("Historial de revisión"):
                st.dataframe(script["reviews"], hide_index=True)

with st.expander("Exportación y eliminación"):
    if st.button("Preparar ZIP de guiones e informe"):
        exported = api("GET", f"/imports/{selected}/export")
        if exported:
            st.download_button(
                "Descargar resultados",
                exported,
                file_name=f"informe-{selected}.zip",
                mime="application/zip",
                on_click="ignore",
            )
    delete_confirmed = st.checkbox(
        "Eliminar esta importación, sus guiones y revisiones", key="delete-" + selected
    )
    if st.button("Eliminar importación", disabled=not delete_confirmed):
        if api("DELETE", f"/imports/{selected}"):
            st.session_state.pop("last_import", None)
            st.rerun()
