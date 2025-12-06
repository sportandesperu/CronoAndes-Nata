import streamlit as st
from supabase import create_client
from collections import defaultdict
import time

# --- Configuración de Supabase ---
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

st.set_page_config(
    page_title="🏆 CronoAndes — Resultados en Vivo",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🏆"
)

# --- ORDEN PERSONALIZADO ---
ORDEN_CATEGORIAS = [
    "Exhibición",
    "Pre-minima",
    "Minima",
    "Infantil A",
    "Infantil B",
    "Juvenil A",
    "Juvenil B",
    "Mayores",
]

def extraer_categoria_genero(evento: str) -> tuple[str, str]:
    """Extrae categoría base y género para ordenar."""
    if "Niñas" in evento or "Mujeres" in evento:
        genero = "Femenino"
    else:
        genero = "Masculino"
    
    for cat in ORDEN_CATEGORIAS:
        if cat in evento:
            return cat, genero
    return "ZZZ", genero

def clave_orden_prueba(evento: str) -> tuple[int, int, str]:
    cat, gen = extraer_categoria_genero(evento)
    if cat in ORDEN_CATEGORIAS:
        idx_cat = ORDEN_CATEGORIAS.index(cat)
    else:
        idx_cat = 999
    idx_gen = 0 if gen == "Femenino" else 1
    return (idx_cat, idx_gen, evento)

# --- Estilos profesionales ---
st.markdown("""
<style>
    .main, .stApp, [data-testid="stAppViewContainer"] {
        background-color: #f8f9fa !important;
        color: #1a1a1a !important;
    }
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    [data-testid="stHeadingWithActionElements"] h1,
    [data-testid="stHeadingWithActionElements"] div,
    .stTitle, .stHeader, .stSubheader {
        color: #111827 !important;
        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif !important;
        font-weight: bold !important;
    }
    [data-testid="stHeader"] {
        background-color: #ffffff !important;
    }
    .evento-header {
        text-align: center;
        padding: 0.8rem;
        background: #e0f2fe;
        border-radius: 8px;
        margin: 1rem 0;
        border: 2px solid #38bdf8;
        font-size: 1.4rem;
        font-weight: bold;
        color: #0c4a6e !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stExpander {
        background-color: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 10px !important;
        color: #1f2937 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        margin-bottom: 1.2rem;
    }
    .stExpander > div[role="button"] {
        color: #111827 !important;
        font-weight: bold;
        font-size: 1.25rem;
        padding: 0.8rem 1rem;
    }
    .stExpander > div[role="button"] *,
    .stExpander[open] > div[role="button"] * {
        color: #111827 !important;
    }
    .header-row {
        display: flex;
        background-color: #f3f4f6;
        padding: 10px 0;
        font-weight: bold;
        color: #374151;
        border-bottom: 2px solid #e5e7eb;
        margin-bottom: 12px;
        border-radius: 6px;
        font-size: 0.95rem;
    }
    .header-carril { width: 10%; text-align: center; }
    .header-pos { width: 10%; text-align: center; }
    .header-nombre { width: 30%; text-align: left; }
    .header-club { width: 30%; text-align: left; }
    .header-tiempo { width: 20%; text-align: right; }
    .col-carril, .col-posicion, .col-nombre, .col-club, .col-tiempo {
        padding: 8px 0;
        font-size: 1.05rem;
        color: #1f2937;
    }
    .col-carril {
        font-weight: bold;
        color: #4b5563;
        text-align: center;
    }
    .col-posicion {
        font-weight: bold;
        text-align: center;
        min-width: 50px;
    }
    .col-posicion.puesto-1 { color: #d97706; font-weight: bold; }
    .col-posicion.puesto-2 { color: #6b7280; font-weight: bold; }
    .col-posicion.puesto-3 { color: #be123c; font-weight: bold; }
    .col-nombre {
        font-weight: 600;
        color: #111827;
        text-align: left;
    }
    .col-club {
        color: #4b5563;
        text-align: left;
    }
    .col-tiempo {
        font-weight: 600;
        text-align: right;
        font-family: 'Courier New', monospace;
    }
    .mejor-tiempo {
        color: #059669 !important;
    }
    .footer {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        padding: 1.2rem 0;
        margin-top: 2rem;
        border-top: 1px solid #e5e7eb;
        color: #6b7280;
        font-size: 0.95rem;
    }
    .footer a {
        color: #3b82f6;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

def formatear_tiempo_segundos(segundos) -> str:
    if segundos is None or segundos <= 0:
        return "NT"
    try:
        total = float(segundos)
        mins = int(total // 60)
        secs = total % 60
        if mins > 0:
            return f"{mins}:{secs:05.2f}"
        return f"{secs:.2f}"
    except (ValueError, TypeError):
        return "NT"

def _mostrar_serie(tiempos):
    """Muestra una serie (preliminar o final) con formato consistente."""
    series = defaultdict(list)
    for t in tiempos:
        series[t["serie_numero"]].append(t)

    for serie_num in sorted(series.keys()):
        if max(series.keys()) > 1:
            st.markdown(f"**Serie {serie_num}**")

        st.markdown("""
        <div class="header-row">
            <div class="header-carril">Carril</div>
            <div class="header-pos">Pos</div>
            <div class="header-nombre">Nombre</div>
            <div class="header-club">Club</div>
            <div class="header-tiempo">Tiempo</div>
        </div>
        """, unsafe_allow_html=True)

        tiempos_serie = series[serie_num]
        con_tiempo = [t for t in tiempos_serie if t.get("tiempo_neto", 0) > 0]
        sin_tiempo = [t for t in tiempos_serie if t.get("tiempo_neto", 0) <= 0]

        con_tiempo_ordenados = sorted(con_tiempo, key=lambda x: x["tiempo_neto"])
        sin_tiempo_ordenados = sorted(sin_tiempo, key=lambda x: x.get("carril", 999))
        nadadores_ordenados = con_tiempo_ordenados + sin_tiempo_ordenados

        mejor_tiempo_valor = con_tiempo_ordenados[0]["tiempo_neto"] if con_tiempo_ordenados else None
        posicion_map = {
            (t["nombre_completo"], t["club"]): i + 1
            for i, t in enumerate(con_tiempo_ordenados)
        }

        for t in nadadores_ordenados:
            carril = t["carril"]
            nombre = t.get("nombre_completo", "")
            club = t.get("club", "")
            tiempo_val = t.get("tiempo_neto")
            key = (nombre, club)

            if tiempo_val and tiempo_val > 0:
                posicion = posicion_map.get(key, "")
                tiempo_str = formatear_tiempo_segundos(tiempo_val)
                es_mejor = (tiempo_val == mejor_tiempo_valor)
            else:
                posicion = ""
                tiempo_str = "NT"
                es_mejor = False

            clase_pos = ""
            if posicion == 1:
                clase_pos = "puesto-1"
            elif posicion == 2:
                clase_pos = "puesto-2"
            elif posicion == 3:
                clase_pos = "puesto-3"

            col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 3, 2])
            with col1:
                st.markdown(f'<div class="col-carril">{carril}</div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="col-posicion {clase_pos}">{posicion}</div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="col-nombre">{nombre}</div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="col-club">{club}</div>', unsafe_allow_html=True)
            with col5:
                clase_tiempo = "mejor-tiempo" if es_mejor else ""
                st.markdown(f'<div class="col-tiempo {clase_tiempo}">{tiempo_str}</div>', unsafe_allow_html=True)
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)

# --- UI ---
st.title("🏆 CronoAndes — Resultados en Vivo")

try:
    # Obtener event_code
    nad_res = supabase.table("nadadores").select("event_code").order("id", desc=True).limit(1).execute()
    if not nad_res.data:
        st.error("❌ No hay eventos registrados aún.")
        st.stop()
    event_code = nad_res.data[0]["event_code"]

    # Nombre del evento
    nombre_evento = "Evento en vivo"
    meta_res = supabase.table("eventos_meta").select("nombre_evento").eq("event_code", event_code).limit(1).execute()
    if meta_res.data and meta_res.data[0].get("nombre_evento"):
        nombre_evento = meta_res.data[0]["nombre_evento"]

    st.markdown(f'<div class="evento-header">{nombre_evento}</div>', unsafe_allow_html=True)

    # Cargar TIEMPOS
    tiempos_res = supabase.table("eventos_tiempo").select(
        "evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto"
    ).eq("event_code", event_code).execute()

    # Cargar RESULTADOS (para detectar finales)
    resultados_res = supabase.table("resultados").select("evento_completo").eq("event_code", event_code).execute()
    pruebas_con_final = {r["evento_completo"] for r in resultados_res.data} if resultados_res.data else set()

    if not tiempos_res.data:
        st.info("⏳ Aún no hay tiempos en vivo. ¡Las carreras están por comenzar!")
        st.stop()

    # Agrupar y ordenar
    pruebas = defaultdict(list)
    for r in tiempos_res.data:
        pruebas[r["evento_completo"]].append(r)

    pruebas_ordenadas = sorted(pruebas.keys(), key=clave_orden_prueba)
    preliminares = [p for p in pruebas_ordenadas if p not in pruebas_con_final]
    finales = [p for p in pruebas_ordenadas if p in pruebas_con_final]

    # Mostrar Preliminares
    if preliminares:
        st.markdown("### 🏊 Preliminares")
        for prueba in preliminares:
            with st.expander(f"▶️ {prueba}", expanded=False):
                _mostrar_serie(pruebas[prueba])

    # Mostrar Finales
    if finales:
        st.markdown("### 🏁 Finales")
        for prueba in finales:
            with st.expander(f"▶️ {prueba}", expanded=True):
                _mostrar_serie(pruebas[prueba])

except Exception as e:
    st.error(f"❌ Error al cargar los datos: {e}")

# --- Footer y actualización ---
st.markdown('<div class="footer"><a href="mailto:sportandesperu@gmail.com">sportandesperu@gmail.com</a> • Actualización automática</div>', unsafe_allow_html=True)

time.sleep(5)
st.rerun()
