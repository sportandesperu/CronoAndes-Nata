# main.py
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="CronoAndes API",
    description="API pública para sincronización de tiempos en competencias deportivas (natación, ciclismo, etc.)",
    version="1.0",
    docs_url="/docs",  # Documentación interactiva en /docs
    redoc_url=None
)

# --- Conexión a la base de datos ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ La variable DATABASE_URL no está definida. "
                       "Asegúrate de vincular la base de datos en Render.")

# --- Modelo de datos (flexible para tiempos, mangas, resultados) ---
class Registro(BaseModel):
    Dorsal: Optional[str] = None
    Nombre: Optional[str] = None
    Apellido: Optional[str] = None
    Club: Optional[str] = None
    Categoria: Optional[str] = None
    Evento: Optional[str] = None
    Manga: Optional[str] = None
    Tiempo: Optional[str] = None
    Tiempo_Num: Optional[float] = None
    Carril: Optional[int] = None
    Posición: Optional[int] = None
    Diferencia: Optional[str] = None
    Final: Optional[bool] = None

# --- Función para obtener conexión a la DB ---
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# --- Inicializar tablas al iniciar ---
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tiempos (
        id SERIAL PRIMARY KEY,
        event_code TEXT NOT NULL,
        Dorsal TEXT,
        Nombre TEXT,
        Apellido TEXT,
        Club TEXT,
        Categoria TEXT,
        Evento TEXT,
        Manga TEXT,
        Tiempo TEXT,
        Tiempo_Num REAL,
        Carril INTEGER
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Ejecutar al arrancar
init_db()

# --- Endpoints ---
@app.post("/api/tiempos/{event_code}")
async def recibir_tiempos(event_code: str, datos: List[Registro]):
    """Recibe una lista de tiempos y los almacena en la DB bajo un event_code."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Eliminar datos anteriores del mismo evento (para evitar duplicados)
        cur.execute("DELETE FROM tiempos WHERE event_code = %s", (event_code,))
        # Insertar nuevos registros
        for reg in datos:
            d = reg.dict(exclude_none=True)
            if not d:
                continue
            cols = ["event_code"] + list(d.keys())
            vals = [event_code] + list(d.values())
            placeholders = ", ".join(["%s"] * len(cols))
            cols_str = ", ".join(f'"{c}"' for c in cols)
            cur.execute(f'INSERT INTO tiempos ({cols_str}) VALUES ({placeholders})', vals)
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "ok", "guardados": len(datos)}
    except Exception as e:
        logging.error(f"Error al guardar tiempos para {event_code}: {e}")
        raise HTTPException(status_code=500, detail="Error interno al guardar")

@app.get("/api/tiempos/{event_code}")
async def obtener_tiempos(event_code: str):
    """Devuelve todos los tiempos asociados a un event_code."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tiempos WHERE event_code = %s", (event_code,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error al leer tiempos para {event_code}: {e}")
        return []

# --- Ruta raíz (opcional, para verificación) ---
@app.get("/")
async def home():
    return {
        "mensaje": "CronoAndes API activa",
        "documentación": "/docs",
        "ejemplo": "/api/tiempos/DHVALLE-1"
    }
