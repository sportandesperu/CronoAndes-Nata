import streamlit as st
from supabase import create_client
from collections import defaultdict

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY)

# --- Estilo: fondo oscuro + títulos SIEMPRE BLANCOS + legibilidad garantizada ---
st.markdown("""
<style>
    /* Fondo oscuro general */
    .main, .stApp {
        background-color: #0f172a !important;
        color: #f8fafc;
    }

    /* ✅ Títulos SIEMPRE BLANCOS, incluso al hacer scroll */
    h1, h2, h3, h4, h5, h6,
    .stApp > header *,
    .stApp > header a,
    .stApp > header .stMarkdown,
    .stTitle,
    .stSubheader {
        color: #ffffff !important;
        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif !important;
        font-weight: bold;
    }

    /* Header fijo con fondo oscuro al hacer scroll */
    .stApp > header {
        background-color: #0f172a !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
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
        color: #ffffff !important;
    }

    .stExpander {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: #f8fafc !important;
    }
    .stExpander > div[role="button"] {
        color: #ffffff !important;
        font-weight: bold;
        font-size: 1.25rem;
    }

    .col-carril, .col-posicion, .col-nombre, .col-club, .col-tiempo {
        padding: 8px 0;
        font-size: 1.05rem;
    }

    .col-carril {
        font-weight: bold;
        color: #94a3b8;
        text-align: center;
    }

    .col-posicion {
        font-weight: bold;
        text-align: center;
        min-width: 50px;
    }
    .col-posicion.puesto-1 { color: #fbbf24; } /* Oro */
    .col-posicion.puesto-2 { color: #cbd5e1; } /* Plata */
    .col-posicion.puesto-3 { color: #fda4af; } /* Bronce */

    .col-nombre {
        font-weight: bold;
        color: #f8fafc;
        text-align: left;
    }
    .col-club {
        color: #94a3b8;
        text-align: left;
    }
    .col-tiempo {
        font-weight: bold;
        text-align: right;
        font-family: 'Courier New', monospace;
    }
    .mejor-tiempo {
        color: #34d399 !important; /* Verde para mejor tiempo */
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
    # Obtener event_code y nombre_evento desde eventos_meta
    event_code = None
    nombre_evento = "Evento de Natación"

    meta_res = supabase.table("eventos_meta").select("event_code, nombre_evento").order("fecha_creacion", desc=True).limit(1).execute()
    if meta_res.data:
        event_code = meta_res.data[0]["event_code"]
        nombre_evento = meta_res.data[0].get("nombre_evento") or event_code
    else:
        nad_res = supabase.table("nadadores").select("event_code").order("event_code", desc=True).limit(1).execute()
        if nad_res.data:
            event_code = nad_res.data[0]["event_code"]
            nombre_evento = event_code
        else:
            st.error("❌ No hay eventos registrados aún.")
            st.stop()

    st.markdown(f'<div class="evento-header">{nombre_evento}</div>', unsafe_allow_html=True)

    # Cargar tiempos
    res = supabase.table("eventos_tiempo").select(
        "evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto"
    ).eq("event_code", event_code).execute()

    if res.data:
        pruebas = defaultdict(list)
        for r in res.data:
            pruebas[r["evento_completo"]].append(r)

        for prueba in sorted(pruebas.keys()):
            with st.expander(f"▶️ {prueba}", expanded=True):
                series = defaultdict(list)
                for t in pruebas[prueba]:
                    series[t["serie_numero"]].append(t)

                for serie_num in sorted(series.keys()):
                    st.markdown(f"**Serie {serie_num}**")
                    tiempos = series[serie_num]

                    # Filtrar y ordenar tiempos válidos para asignar posiciones
                    validos = [t for t in tiempos if t.get("tiempo_neto", 0) > 0]
                    if validos:
                        validos_sorted = sorted(validos, key=lambda x: x["tiempo_neto"])
                        mejor_tiempo_valor = validos_sorted[0]["tiempo_neto"]
                        # Mapa: (nombre, club) → posición
                        posicion_map = {
                            (t["nombre_completo"], t["club"]): i + 1
                            for i, t in enumerate(validos_sorted)
                        }
                    else:
                        mejor_tiempo_valor = None
                        posicion_map = {}

                    # Mostrar todos los nadadores en orden de carril
                    tiempos_ordenados_carril = sorted(tiempos, key=lambda x: x.get("carril", 999))
                    for t in tiempos_ordenados_carril:
                        carril = t["carril"]
                        nombre = t.get("nombre_completo", "—")
                        club = t.get("club", "—")
                        tiempo_val = t.get("tiempo_neto")
                        key = (nombre, club)

                        # Determinar posición
                        if tiempo_val and tiempo_val > 0:
                            posicion = posicion_map.get(key, "—")
                            tiempo_str = formatear_tiempo_segundos(tiempo_val)
                            es_mejor = (tiempo_val == mejor_tiempo_valor)
                        else:
                            posicion = "—"
                            tiempo_str = "—"
                            es_mejor = False

                        # Estilos para posición (podio)
                        clase_pos = ""
                        if posicion == 1:
                            clase_pos = "puesto-1"
                        elif posicion == 2:
                            clase_pos = "puesto-2"
                        elif posicion == 3:
                            clase_pos = "puesto-3"

                        col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 3, 2])
                        with col1:
                            st.markdown(f'<div class="col-carril">C{carril}</div>', unsafe_allow_html=True)
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
    else:
        st.info("⏳ Aún no hay tiempos en vivo. ¡Las carreras están por comenzar!")

except Exception as e:
    st.error(f"❌ Error al cargar los datos: {e}")

# --- Auto-refresh cada 6 segundos ---
st.markdown(
    """
    <script>
    setTimeout(() => window.location.reload(), 6000);
    </script>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="pie">sportandesperu@gmail.com • Actualización automática activa</div>', unsafe_allow_html=True)
