import streamlit as st
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import tempfile
from dotenv import load_dotenv
from pipeline.processor import process_pdf

load_dotenv()

st.set_page_config(
    page_title="AcademiCheck",
    page_icon="📄",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Mono', monospace;
    }
    
    h1, h2, h3 {
        font-family: 'DM Serif Display', serif;
    }
    
    .main {
        background-color: #0f0f0f;
        color: #e8e4d9;
    }
    
    .stApp {
        background-color: #0f0f0f;
    }
    
    .error-card {
        background: #1a1a1a;
        border-left: 3px solid #c8a96e;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 4px 4px 0;
    }
    
    .error-type {
        color: #c8a96e;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .error-description {
        color: #e8e4d9;
        font-size: 14px;
        margin: 4px 0;
    }
    
    .error-context {
        color: #666;
        font-size: 12px;
        font-style: italic;
    }
    
    .page-badge {
        background: #c8a96e;
        color: #0f0f0f;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 11px;
        font-weight: 500;
    }
    
    .stButton > button {
        background: #c8a96e;
        color: #0f0f0f;
        border: none;
        border-radius: 2px;
        font-family: 'DM Mono', monospace;
        font-weight: 500;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    
    .stButton > button:hover {
        background: #e8c97e;
        color: #0f0f0f;
    }
</style>
""", unsafe_allow_html=True)

st.title("Revisor virtual")
st.markdown("##### Sistema de revisión automática")
st.divider()

# Estado de sesión
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "confirmed_errors" not in st.session_state:
    st.session_state.confirmed_errors = {}

# Upload
col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader("Subir archivo de la memoria (PDF)", type=["pdf"])

if uploaded_file is not None:
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get("last_file_id") != file_id:
        st.session_state.pipeline_result = None
        st.session_state.confirmed_errors = {}
        st.session_state.pop("report", None)
        st.session_state.last_file_id = file_id
        st.rerun()

if uploaded_file:
    if st.button("Analizar documento"):
        st.session_state.pipeline_result = None
        st.session_state.confirmed_errors = {}
        st.session_state.pop("report", None)
        
        with st.spinner("Analizando documento..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            result = process_pdf(tmp_path)
            st.session_state.pipeline_result = result
            os.unlink(tmp_path)

if st.session_state.pipeline_result:
    result = st.session_state.pipeline_result

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Páginas analizadas", result.total_pages)
    with col2:
        st.metric("Errores detectados", result.total_errors)
    with col3:
        st.metric("Tiempo de análisis", f"{result.total_processing_time}s")

    st.divider()
    st.markdown("### Revisión de errores")
    st.markdown("*Confirmá o descartá cada error antes de generar el reporte.*")

    all_errors = []
    for page in result.pages:
        for error in page.confirmed_errors:
            if error.confirmed:
                all_errors.append(error)

    if not all_errors:
        st.info("No se detectaron errores en el documento.")
    else:
        for i, error in enumerate(all_errors):
            with st.container():
                st.markdown(f"""
                <div class="error-card">
                    <span class="page-badge">Página {error.page_number}</span>
                    <span class="error-type" style="margin-left:12px">{error.error_type}</span>
                    <div class="error-description">{error.description}</div>
                    <div class="error-context">"{error.context}"</div>
                </div>
                """, unsafe_allow_html=True)

                key = f"error_{i}"
                if key not in st.session_state.confirmed_errors:
                    st.session_state.confirmed_errors[key] = True

                st.session_state.confirmed_errors[key] = st.checkbox(
                    "Confirmar error",
                    value=st.session_state.confirmed_errors[key],
                    key=f"check_{i}"
                )

    st.divider()
    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("Generar reporte"):
            final_errors = [
                {
                    "page_number": error.page_number,
                    "error_type": error.error_type,
                    "description": error.description,
                    "context": error.context
                }
                for i, error in enumerate(all_errors)
                if st.session_state.confirmed_errors.get(f"error_{i}", True)
            ]

            report = {
                "pdf": uploaded_file.name if uploaded_file else "documento.pdf",
                "total_errors": len(final_errors),
                "errors": final_errors
            }

            st.session_state.report = report
            st.success(f"Reporte generado con {len(final_errors)} errores confirmados.")
            st.download_button(
                "Descargar reporte JSON",
                data=json.dumps(report, ensure_ascii=False, indent=2),
                file_name="reporte_errores.json",
                mime="application/json"
            )

    with col2:
        if "report" in st.session_state:
            st.markdown("**Enviar reporte por email**")
            email_to = st.text_input("Email del destinatario")
            if st.button("Enviar por email"):
                if email_to:
                    try:
                        msg = MIMEMultipart()
                        msg["From"] = os.getenv("SMTP_USER")
                        msg["To"] = email_to
                        msg["Subject"] = "Reporte de revisión académica — AcademiCheck"

                        body = f"Se adjunta el reporte de revisión del documento.\n\nErrores encontrados: {st.session_state.report['total_errors']}"
                        msg.attach(MIMEText(body, "plain"))

                        attachment = MIMEText(
                            json.dumps(st.session_state.report, ensure_ascii=False, indent=2),
                            "plain"
                        )
                        attachment.add_header("Content-Disposition", "attachment", filename="reporte_errores.json")
                        msg.attach(attachment)

                        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", 587))) as server:
                            server.starttls()
                            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
                            server.sendmail(os.getenv("SMTP_USER"), email_to, msg.as_string())

                        st.success(f"Reporte enviado a {email_to}")
                    except Exception as e:
                        st.error(f"Error al enviar: {e}")
                else:
                    st.warning("Ingresá un email válido.")