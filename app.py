import streamlit as st
from supabase import create_client
from datetime import datetime
from collections import defaultdict

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY)

st.set_page_config(page_title="🏊 Resultados en Vivo", layout="wide")
st.title("🏊 Resultados en Vivo – Natación")

# Función para formatear tiempo
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
    # Paso 1: Obtener event_code y nombre_evento desde RESULTADOS (prioridad)
    response_resultados = supabase.table("resultados").select("event_code, nombre_evento").order("event_code", desc=True).limit(1).execute()
    
    latest_event = None
    nombre_evento = None

    if response_resultados.data:
        latest_event = response_resultados.data[0]["event_code"]
        nombre_evento = response_resultados.data[0].get("nombre_evento") or latest_event
    else:
        # Fallback: buscar en nadadores (inscripciones)
        response_nadadores = supabase.table("nadadores").select("event_code").order("event_code", desc=True).limit(1).execute()
        if response_nadadores.data:
            latest_event = response_nadadores.data[0]["event_code"]
            nombre_evento = latest_event  # No hay nombre_evento en nadadores, usar event_code
        else:
            st.error("❌ No hay eventos registrados aún.")
            st.stop()

    st.caption(f"Evento actual: **{nombre_evento}** (Código: `{latest_event}`)")

    # Paso 2: Cargar TIEMPOS en vivo desde eventos_tiempo (solo con campos existentes)
    res_tiempos = supabase.table("eventos_tiempo").select("evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto").eq("event_code", latest_event).execute()

    if res_tiempos.data:
        st.subheader("⏱️ Tiempos en Vivo")
        pruebas = defaultdict(list)
        for r in res_tiempos.data:
            pruebas[r["evento_completo"]].append(r)

        for prueba, tiempos in pruebas.items():
            with st.expander(f"▶️ {prueba}", expanded=True):
                # Ordenar por serie y carril
                tiempos_ordenados = sorted(tiempos, key=lambda x: (x.get("serie_numero", 1), x.get("carril", 0)))
                for t in tiempos_ordenados:
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
            # Intentar obtener nombre_evento desde resultados
            nombre_evento_manual = codigo_manual
            nombre_check = supabase.table("resultados").select("nombre_evento").eq("event_code", codigo_manual.strip()).limit(1).execute()
            if nombre_check.data and nombre_check.data[0].get("nombre_evento"):
                nombre_evento_manual = nombre_check.data[0]["nombre_evento"]

            res_manual = supabase.table("eventos_tiempo").select("evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto").eq("event_code", codigo_manual.strip()).execute()
            if res_manual.data:
                st.subheader(f"Tiempos en Vivo – {nombre_evento_manual}")
                pruebas = defaultdict(list)
                for r in res_manual.data:
                    pruebas[r["evento_completo"]].append(r)
                for prueba, tiempos in pruebas.items():
                    st.markdown(f"**{prueba}**")
                    tiempos_ordenados = sorted(tiempos, key=lambda x: (x.get("serie_numero", 1), x.get("carril", 0)))
                    for t in tiempos_ordenados:
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
