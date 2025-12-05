import streamlit as st
from supabase import create_client
from datetime import datetime
from collections import defaultdict
from streamlit_autorefresh import st_autorefresh

# --- Configuración de Supabase (SOLO LECTURA) ---
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY)

# --- Auto-refresh cada 8 segundos ---
count = st_autorefresh(interval=8000, key="resultados_vivo_refresh")

# --- Estilo profesional tipo campeonato internacional ---
st.markdown("""
<style>
    /* Fondo blanco puro para máxima legibilidad en exteriores */
    .main { background-color: white; }
    h1, h2, h3, h4, h5, h6 {
        color: #002147 !important; /* Azul oscuro (como FINA) */
        font-weight: bold;
    }
    .stExpander {
        border: 2px solid #002147 !important;
        border-radius: 8px !important;
        background-color: #f8f9fa !important;
    }
    .stExpander > div[role="button"] {
        font-weight: bold !important;
        color: #002147 !important;
    }
    /* Texto de tiempos en grande y en negrita */
    .tiempo-display {
        font-size: 1.1em;
        font-weight: bold;
        color: #d32f2f; /* Rojo oscuro para destacar tiempos */
    }
    /* Mensajes de info en azul suave */
    .stInfo {
        background-color: #e3f2fd !important;
        color: #0d47a1 !important;
    }
    /* Botones de expander con buen contraste */
    .stButton>button {
        background-color: #002147;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="🏊 Resultados en Vivo – Natación",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🏊 RESULTADOS EN VIVO")
st.caption("Actualización automática cada 8 segundos ⏱️")

# --- Función para formatear tiempo ---
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

# --- Cargar datos ---
try:
    # Obtener event_code y nombre_evento desde RESULTADOS (prioridad)
    response_resultados = supabase.table("resultados").select("event_code, nombre_evento").order("event_code", desc=True).limit(1).execute()
    
    latest_event = None
    nombre_evento = None

    if response_resultados.data:
        latest_event = response_resultados.data[0]["event_code"]
        nombre_evento = response_resultados.data[0].get("nombre_evento") or latest_event
    else:
        response_nadadores = supabase.table("nadadores").select("event_code").order("event_code", desc=True).limit(1).execute()
        if response_nadadores.data:
            latest_event = response_nadadores.data[0]["event_code"]
            nombre_evento = latest_event
        else:
            st.error("❌ No hay eventos registrados aún.")
            st.stop()

    st.header(f"**{nombre_evento}**")
    st.caption(f"Código: `{latest_event}`")

    # Cargar tiempos en vivo
    res_tiempos = supabase.table("eventos_tiempo").select("evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto").eq("event_code", latest_event).execute()

    if res_tiempos.data:
        pruebas = defaultdict(list)
        for r in res_tiempos.data:
            pruebas[r["evento_completo"]].append(r)

        for prueba, tiempos in pruebas.items():
            with st.expander(f"▶️ {prueba}", expanded=True):
                tiempos_ordenados = sorted(tiempos, key=lambda x: (x.get("serie_numero", 1), x.get("carril", 0)))
                for t in tiempos_ordenados:
                    nombre = t.get("nombre_completo", "—")
                    club = t.get("club", "—")
                    tiempo = t.get("tiempo_neto")
                    tiempo_str = formatear_tiempo_segundos(tiempo)
                    serie = t.get("serie_numero", 1)
                    carril = t.get("carril", "?")
                    
                    col1, col2, col3 = st.columns([1, 3, 2])
                    with col1:
                        st.markdown(f"**S{serie} - C{carril}**")
                    with col2:
                        st.markdown(f"**{nombre}**<br>*{club}*", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f'<div class="tiempo-display">{tiempo_str}</div>', unsafe_allow_html=True)
                    st.divider()
    else:
        st.info("⏳ Aún no hay tiempos en vivo. ¡Las carreras están por comenzar!")

except Exception as e:
    st.error(f"❌ Error al cargar los datos: {e}")

# --- Ver otro evento ---
with st.expander("🔍 Ver otro evento"):
    codigo_manual = st.text_input("Código del evento", placeholder="Ej: XK9B2")
    if codigo_manual.strip():
        try:
            nombre_evento_manual = codigo_manual
            nombre_check = supabase.table("resultados").select("nombre_evento").eq("event_code", codigo_manual.strip()).limit(1).execute()
            if nombre_check.data and nombre_check.data[0].get("nombre_evento"):
                nombre_evento_manual = nombre_check.data[0]["nombre_evento"]

            res_manual = supabase.table("eventos_tiempo").select("evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto").eq("event_code", codigo_manual.strip()).execute()
            if res_manual.data:
                st.subheader(f"Resultados – {nombre_evento_manual}")
                pruebas = defaultdict(list)
                for r in res_manual.data:
                    pruebas[r["evento_completo"]].append(r)
                for prueba, tiempos in pruebas.items():
                    st.markdown(f"### **{prueba}**")
                    tiempos_ordenados = sorted(tiempos, key=lambda x: (x.get("serie_numero", 1), x.get("carril", 0)))
                    for t in tiempos_ordenados:
                        nombre = t.get("nombre_completo", "—")
                        club = t.get("club", "—")
                        tiempo = t.get("tiempo_neto")
                        tiempo_str = formatear_tiempo_segundos(tiempo)
                        st.markdown(f"**Serie {t.get('serie_numero', 1)} - Carril {t.get('carril', '?')}**: {nombre} ({club}) → **{tiempo_str}**")
            else:
                st.warning("No se encontraron tiempos para ese código.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Pie de página discreto ---
st.divider()
st.caption("Actualización automática activa • sportandesperu@gmail.com")
