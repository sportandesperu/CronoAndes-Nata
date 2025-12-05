import streamlit as st
from supabase import create_client
from datetime import datetime

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"

supabase = create_client(SUPABASE_URL.strip(), SUPABASE_ANON_KEY)

st.set_page_config(page_title="🏊 Resultados en Vivo", layout="wide")
st.title("🏊 Resultados en Vivo – Natación")

try:
    # Obtener el event_code más reciente (de la tabla resultados, no nadadores)
    response = supabase.table("resultados").select("event_code, nombre_evento").order("event_code", desc=True).limit(1).execute()
    
    if not response.data:
        st.error("❌ No hay eventos registrados aún.")
        st.stop()
    
    latest_event = response.data[0]["event_code"]
    nombre_evento = response.data[0].get("nombre_evento") or latest_event  # Usa nombre_evento si existe
    st.caption(f"Evento actual: **{nombre_evento}** (Código: `{latest_event}`)")

    # Cargar resultados del evento más reciente
    res = supabase.table("resultados").select("*").eq("event_code", latest_event).execute()
    
    if res.data:
        st.subheader("🏅 Resultados Finales")
        # Filtrar y ordenar por posición
        resultados_validos = [r for r in res.data if r.get("posicion") is not None]
        resultados_ordenados = sorted(resultados_validos, key=lambda x: x["posicion"])
        
        for r in resultados_ordenados:
            nombre = r.get("nombre_completo", "—")
            club = r.get("club", "—")
            tiempo = r.get("tiempo_neto", 0)
            # Formato bonito del tiempo (opcional)
            tiempo_str = f"{tiempo:.2f}s" if isinstance(tiempo, (int, float)) else str(tiempo)
            st.write(f"{r['posicion']}. **{nombre}** ({club}) – **{tiempo_str}**")
    else:
        st.info("⏳ Aún no hay resultados. ¡Las carreras están por comenzar!")

except Exception as e:
    st.error(f"❌ Error al cargar los datos: {e}")

# Opción para ver otros eventos
with st.expander("🔍 Ver otro evento"):
    codigo_manual = st.text_input("Código del evento", placeholder="Ej: XK9B2")
    if codigo_manual.strip():
        try:
            # Intentar obtener el nombre del evento desde un resultado
            nombre_evento_manual = codigo_manual
            nombre_check = supabase.table("resultados").select("nombre_evento").eq("event_code", codigo_manual.strip()).limit(1).execute()
            if nombre_check.data and nombre_check.data[0].get("nombre_evento"):
                nombre_evento_manual = nombre_check.data[0]["nombre_evento"]
            
            res_manual = supabase.table("resultados").select("*").eq("event_code", codigo_manual.strip()).execute()
            if res_manual.data:
                st.subheader(f"Resultados – {nombre_evento_manual}")
                resultados_manual = [r for r in res_manual.data if r.get("posicion") is not None]
                for r in sorted(resultados_manual, key=lambda x: x["posicion"]):
                    nombre = r.get("nombre_completo", "—")
                    club = r.get("club", "—")
                    tiempo = r.get("tiempo_neto", 0)
                    tiempo_str = f"{tiempo:.2f}s" if isinstance(tiempo, (int, float)) else str(tiempo)
                    st.write(f"{r['posicion']}. {nombre} ({club}) – {tiempo_str}")
            else:
                st.warning("No se encontraron resultados para ese código.")
        except Exception as e:
            st.error(f"Código no válido o error: {e}")
