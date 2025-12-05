import streamlit as st
from supabase import create_client
from datetime import datetime

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"  # ← TU anon_key real

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

st.set_page_config(page_title="🏊 Resultados en Vivo", layout="wide")
st.title("🏊 Resultados en Vivo – Natación")

try:
    # Obtener el event_code más reciente (de la tabla nadadores)
    response = supabase.table("nadadores").select("event_code, nombre").order("event_code", desc=True).limit(1).execute()
    
    if not response.
        st.error("❌ No hay eventos registrados aún.")
        st.stop()
    
    latest_event = response.data[0]["event_code"]
    st.caption(f"Evento actual: **{latest_event}**")

    # Cargar resultados del evento más reciente
    res = supabase.table("resultados").select("*").eq("event_code", latest_event).execute()
    
    if res.
        st.subheader("🏅 Resultados Finales")
        resultados = sorted(
            [r for r in res.data if r.get("posicion") is not None],
            key=lambda x: x["posicion"]
        )
        for r in resultados:
            st.write(f"{r['posicion']}. **{r['nombre_completo']}** ({r['club']}) – **{r['tiempo_neto']}s**")
    else:
        st.info("⏳ Aún no hay resultados. ¡Las carreras están por comenzar!")

except Exception as e:
    st.error("❌ Error al cargar los datos. Verifica la conexión a Supabase.")

# Opción para ver otros eventos (opcional)
with st.expander("🔍 Ver otro evento"):
    codigo_manual = st.text_input("Código del evento", placeholder="Ej: XK9B2")
    if codigo_manual:
        try:
            res_manual = supabase.table("resultados").select("*").eq("event_code", codigo_manual).execute()
            if res_manual.
                st.subheader(f"Resultados – {codigo_manual}")
                for r in sorted([r for r in res_manual.data if r.get("posicion")], key=lambda x: x["posicion"]):
                    st.write(f"{r['posicion']}. {r['nombre_completo']} – {r['tiempo_neto']}s")
        except:
            st.error("Código no válido.")
