import streamlit as st
from supabase import create_client

# Configuración de Supabase (SOLO LECTURA)
SUPABASE_URL = "https://tvbmajrcylbzgalxivoy.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2Ym1hanJjeWxiemdhbHhpdm95Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyNDMyMzIsImV4cCI6MjA3OTgxOTIzMn0.4FbEulTNGbAxFV0fp99TnHc3Yke4jYNgoMd3JNqpCv4"  # ← TU anon_key real

# Conectar
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Título
st.set_page_config(page_title="🏊 Resultados en Vivo", layout="wide")
st.title("🏊 Resultados en Vivo – Natación")

# Pedir código del evento
event_code = st.text_input("🔹 Ingresa el código del evento", placeholder="Ej: XK9B2")

if event_code:
    try:
        # Leer resultados
        res = supabase.table("resultados").select("*").eq("event_code", event_code).execute()
        if res.data:
            st.subheader(f"🏅 Resultados – Evento: {event_code}")
            # Ordenar por posición
            resultados = sorted(
                [r for r in res.data if r.get("posicion") is not None],
                key=lambda x: x["posicion"]
            )
            for r in resultados:
                st.write(f"{r['posicion']}. **{r['nombre_completo']}** ({r['club']}) – **{r['tiempo_neto']}s**")
        else:
            st.info("⏳ No hay resultados aún. ¡Pronto empezarán las carreras!")
    except Exception as e:
        st.error("❌ No se pudieron cargar los datos. Verifica el código.")
else:
    st.info("➡️ Ingresa el código del evento para ver resultados en vivo.")
