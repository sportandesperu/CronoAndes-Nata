import streamlit as st
from supabase import create_client
from collections import defaultdict

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY)

# --- Estilo: Formato Copa del Mundo (oscuro, profesional, legible) ---
st.markdown("""
<style>
    /* Fondo oscuro principal */
    .main, .stApp {
        background-color: #0f172a !important;
        color: #f8fafc;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif !important;
        font-weight: bold;
        text-shadow: 0 0 6px rgba(56, 189, 248, 0.5);
    }
    .stTitle {
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .stSubheader {
        color: #94a3b8 !important;
        font-size: 1.1rem;
    }
    .evento-header {
        text-align: center;
        padding: 0.8rem;
        background: #1e293b;
        border-radius: 8px;
        margin: 1rem 0;
        border: 2px solid #38bdf8;
        font-size: 1.4rem;
        font-weight: bold;
        color: white;
    }
    .stExpander {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #f8fafc !important;
    }
    .stExpander > div[role="button"] {
        color: #f8fafc !important;
        font-weight: bold;
        font-size: 1.25rem;
    }
    .fila-tiempo {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 6px;
        margin: 8px 0;
        border-left: 3px solid #38bdf8;
    }
    .col-pos {
        font-weight: bold;
        color: #60a5fa;
        font-size: 1.1rem;
        text-align: center;
        min-width: 40px;
    }
    .col-nombre {
        font-weight: bold;
        color: #f8fafc;
        font-size: 1.1rem;
        text-align: left;
    }
    .col-club {
        color: #94a3b8;
        font-size: 1rem;
        text-align: left;
    }
    .col-tiempo {
        font-weight: bold;
        color: #60a5fa;
        font-size: 1.2rem;
        text-align: right;
        font-family: 'Courier New', monospace;
    }
    .stInfo, .stSuccess, .stWarning, .stError {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border-left: 4px solid #38bdf8;
    }
    .pie {
        text-align: center;
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="🏆 CronoAndes — Resultados en Vivo",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🏆 CronoAndes — Resultados en Vivo")

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
        return "—"

try:
    # Paso 1: Obtener el event_code más reciente (de nadadores o eventos_meta)
    event_code = None
    nombre_evento = "Evento de Natación"

    # Intentar desde eventos_meta (mejor opción)
    meta_res = supabase.table("eventos_meta").select("event_code, nombre_evento").order("fecha_creacion", desc=True).limit(1).execute()
    if meta_res.data:
        event_code = meta_res.data[0]["event_code"]
        nombre_evento = meta_res.data[0].get("nombre_evento") or event_code
    else:
        # Fallback: usar el event_code más reciente de nadadores
        nad_res = supabase.table("nadadores").select("event_code").order("event_code", desc=True).limit(1).execute()
        if nad_res.data:
            event_code = nad_res.data[0]["event_code"]
            nombre_evento = event_code  # solo código como fallback
        else:
            st.error("❌ No hay eventos registrados aún.")
            st.stop()

    st.markdown(f'<div class="evento-header">{nombre_evento}</div>', unsafe_allow_html=True)

    # Paso 2: Cargar tiempos usando el event_code obtenido
    res = supabase.table("eventos_tiempo").select(
        "evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto"
    ).eq("event_code", event_code).execute()

    if res.data:
        pruebas = defaultdict(list)
        for r in res.data:
            pruebas[r["evento_completo"]].append(r)

        for prueba in sorted(pruebas.keys()):
            with st.expander(f"▶️ {prueba}", expanded=True):
                tiempos = sorted(pruebas[prueba], key=lambda x: (x.get("serie_numero", 1), x.get("carril", 0)))
                series = defaultdict(list)
                for t in tiempos:
                    series[t["serie_numero"]].append(t)
                
                for serie_num in sorted(series.keys()):
                    st.markdown(f"**Serie {serie_num}**")
                    for t in series[serie_num]:
                        col1, col2, col3, col4 = st.columns([1, 3, 3, 2])
                        with col1:
                            st.markdown(f'<div class="col-pos">C{t["carril"]}</div>', unsafe_allow_html=True)
                        with col2:
                            st.markdown(f'<div class="col-nombre">{t.get("nombre_completo", "—")}</div>', unsafe_allow_html=True)
                        with col3:
                            st.markdown(f'<div class="col-club">{t.get("club", "—")}</div>', unsafe_allow_html=True)
                        with col4:
                            st.markdown(f'<div class="col-tiempo">{formatear_tiempo_segundos(t.get("tiempo_neto"))}</div>', unsafe_allow_html=True)
                        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
    else:
        st.info("⏳ Aún no hay tiempos en vivo. ¡Las carreras están por comenzar!")

except Exception as e:
    st.error(f"❌ Error al cargar los datos: {e}")

# --- Auto-refresh con JavaScript (cada 6 segundos) ---
st.markdown(
    """
    <script>
    setTimeout(() => window.location.reload(), 6000);
    </script>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="pie">sportandesperu@gmail.com • Actualización automática activa</div>', unsafe_allow_html=True)
