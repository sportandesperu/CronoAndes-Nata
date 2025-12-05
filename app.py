import streamlit as st
from supabase import create_client
from datetime import datetime

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY)

st.set_page_config(page_title="🏊 Resultados en Vivo", layout="wide")
st.title("🏊 Resultados en Vivo – Natación")

# Auto-refresco cada 10 segundos para resultados en vivo
st_autorefresh = st.empty()
if st_autorefresh.button("🔄 Actualizar ahora", key="manual_refresh"):
    st.rerun()

# Función para formatear tiempo
def formatear_tiempo_segundos(segundos: float) -> str:
    if segundos is None or segundos <= 0:
        return "—"
    mins = int(segundos // 60)
    secs = segundos % 60
    if mins > 0:
        return f"{mins}:{secs:05.2f}"
    return f"{secs:.2f}"

try:
    # Obtener el event_code más reciente desde eventos_tiempo (donde se suben los tiempos en vivo)
    response = supabase.table("eventos_tiempo").select("event_code, nombre_evento").order("created_at", desc=True).limit(1).execute()
    
    if not response.data:
        st.error("❌ No hay eventos con tiempos registrados aún.")
        st.stop()
    
    latest_event = response.data[0]["event_code"]
    nombre_evento = response.data[0].get("nombre_evento") or latest_event
    st.caption(f"Evento actual: **{nombre_evento}** (Código: `{latest_event}`)")

    # Cargar TIEMPOS en vivo del evento más reciente (ordenados por serie y carril)
    res = supabase.table("eventos_tiempo").select("*").eq("event_code", latest_event).order("serie_numero", desc=False).order("carril", desc=False).execute()
    
    if res.data:
        st.subheader("⏱️ Tiempos en Vivo")
        # Agrupar por evento_completo (prueba)
        from collections import defaultdict
        pruebas = defaultdict(list)
        for r in res.data:
            pruebas[r["evento_completo"]].append(r)
        
        for prueba, tiempos in pruebas.items():
            with st.expander(f"▶️ {prueba}", expanded=True):
                for t in tiempos:
                    nombre = t.get("nombre_completo", "—")
                    club = t.get("club", "—")
                    tiempo = t.get("tiempo_neto")
                    tiempo_str = formatear_tiempo_segundos(tiempo)
                    serie = t.get("serie_numero", 1)
                    carril = t.get("carril", "?")
                    st.write(f"**Serie {serie} - Carril {carril}**: {nombre} ({club}) – **{tiempo_str}**")
    else:
        st.info("⏳ Aún no hay tiempos en vivo. ¡Las carreras están por comenzar!")

except Exception as e:
    st.error(f"❌ Error al cargar los datos: {e}")

# Opción para ver otro evento
with st.expander("🔍 Ver otro evento"):
    codigo_manual = st.text_input("Código del evento", placeholder="Ej: XK9B2")
    if codigo_manual.strip():
        try:
            res_manual = supabase.table("eventos_tiempo").select("*").eq("event_code", codigo_manual.strip()).execute()
            if res_manual.data:
                st.subheader(f"Tiempos en Vivo – {codigo_manual}")
                pruebas = {}
                for r in res_manual.data:
                    prueba = r["evento_completo"]
                    if prueba not in pruebas:
                        pruebas[prueba] = []
                    pruebas[prueba].append(r)
                
                for prueba, tiempos in pruebas.items():
                    st.markdown(f"**{prueba}**")
                    for t in sorted(tiempos, key=lambda x: (x.get("serie_numero", 1), x.get("carril", 0))):
                        nombre = t.get("nombre_completo", "—")
                        club = t.get("club", "—")
                        tiempo = t.get("tiempo_neto")
                        tiempo_str = formatear_tiempo_segundos(tiempo)
                        serie = t.get("serie_numero", 1)
                        carril = t.get("carril", "?")
                        st.write(f"Serie {serie} - Carril {carril}: {nombre} ({club}) – {tiempo_str}")
            else:
                st.warning("No se encontraron tiempos para ese código.")
        except Exception as e:
            st.error(f"Error: {e}")

# Auto-refresh cada 15 segundos (opcional, para experiencia en vivo)
import time
time.sleep(15)
st.rerun()
