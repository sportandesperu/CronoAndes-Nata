import streamlit as st
from supabase import create_client
from datetime import datetime
from collections import defaultdict

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY)

# Estilo profesional – legible en exteriores
st.markdown("""
<style>
    .main { background-color: white; }
    h1, h2, h3 { color: #002147 !important; font-weight: bold; }
    .stExpander {
        border: 2px solid #002147 !important;
        border-radius: 8px !important;
        background-color: #f8f9fa !important;
    }
    .stExpander > div[role="button"] {
        font-weight: bold !important;
        color: #002147 !important;
    }
    .tiempo-display {
        font-size: 1.1em;
        font-weight: bold;
        color: #d32f2f;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="🏊 Resultados en Vivo – Natación",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🏊 RESULTADOS EN VIVO")
st.caption("Actualización automática cada 8 segundos")

def formatear_tiempo_segundos(segundos) -> str:
    if segundos is None or segundos <= 0:
        return "—"
    try:
        total = float(segundos)
        mins = int(total // 60)
        secs = total % 60
        if mins > 0:
            return f"{mins}:{secs:05.2f}"
        return f"{secs:.2f}"
    except (ValueError, TypeError):
        return str(segundos)

try:
    # Obtener nombre del evento desde resultados (prioridad)
    response = supabase.table("resultados").select("event_code, nombre_evento").order("event_code", desc=True).limit(1).execute()
    
    if not response.data:
        # Fallback a nadadores
        response = supabase.table("nadadores").select("event_code").order("event_code", desc=True).limit(1).execute()
        if not response.data:
            st.error("❌ No hay eventos registrados aún.")
            st.stop()
        latest_event = response.data[0]["event_code"]
        nombre_evento = latest_event
    else:
        latest_event = response.data[0]["event_code"]
        nombre_evento = response.data[0].get("nombre_evento") or latest_event

    st.header(f"**{nombre_evento}**")
    st.caption(f"Código: `{latest_event}`")

    # Cargar tiempos en vivo
    tiempos_res = supabase.table("eventos_tiempo").select(
        "evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto"
    ).eq("event_code", latest_event).execute()

    if tiempos_res.data:
        pruebas = defaultdict(list)
        for t in tiempos_res.data:
            pruebas[t["evento_completo"]].append(t)

        for prueba in sorted(pruebas.keys()):
            with st.expander(f"▶️ {prueba}", expanded=True):
                tiempos = sorted(pruebas[prueba], key=lambda x: (x.get("serie_numero", 1), x.get("carril", 0)))
                for t in tiempos:
                    col1, col2, col3 = st.columns([1, 3, 2])
                    with col1:
                        st.markdown(f"**S{t['serie_numero']} - C{t['carril']}**")
                    with col2:
                        st.markdown(f"**{t['nombre_completo']}**<br>*{t['club']}*", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f'<div class="tiempo-display">{formatear_tiempo_segundos(t["tiempo_neto"])}</div>', unsafe_allow_html=True)
                    st.divider()
    else:
        st.info("⏳ Aún no hay tiempos en vivo. ¡Las carreras están por comenzar!")

except Exception as e:
    st.error(f"❌ Error al cargar los datos: {e}")

# --- Auto-refresh con JavaScript (sin dependencias externas) ---
st.markdown(
    """
    <script>
    setTimeout(() => window.location.reload(), 8000);
    </script>
    """,
    unsafe_allow_html=True
)

st.divider()
st.caption("sportandesperu@gmail.com • Actualización automática activa")
