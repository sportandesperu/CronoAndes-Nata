# app.py
# Backend para resultados en vivo — Compatible con tu esquema de Supabase (multthuaptff)
# Lee directamente de las tablas: nadadores, eventos_tiempo, resultados

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# === Configuración ===
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'natacion-backend-2025')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# === Conexión a Supabase ===
def get_db_conn():
    """Conecta a tu proyecto Supabase: multuhaptff"""
    # URL de conexión de Supabase
    db_url = os.environ.get('SUPABASE_DB_URL')
    if not db_url:
        raise RuntimeError("❌ SUPABASE_DB_URL no definida. Configúrala en GitHub Secrets.")
    return psycopg2.connect(db_url, sslmode='require')

# === Endpoints ===

@app.route('/')
def home():
    return jsonify({
        "app": "Natación Resultados en Vivo",
        "version": "1.0",
        "db": "Supabase (multhuaptff)",
        "endpoints": [
            "/api/eventos/<event_code>/resultados",
            "/api/eventos/<event_code>/tiempos",
            "/api/eventos/<event_code>/inscritos"
        ]
    })

@app.route('/health')
def health():
    try:
        conn = get_db_conn()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# --- 1. Obtener inscritos de un evento ---
@app.route('/api/eventos/<event_code>/inscritos')
def get_inscritos(event_code):
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT nombre, apellido, genero, club, prueba, categoria, edad
            FROM nadadores
            WHERE event_code = %s
            ORDER BY categoria, genero, prueba, apellido, nombre
        """, (event_code,))
        inscritos = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(row) for row in inscritos]), 200
    except Exception as e:
        logging.exception("Error al obtener inscritos")
        return jsonify({"error": str(e)}), 500

# --- 2. Obtener tiempos en vivo (preliminares y finales) ---
@app.route('/api/eventos/<event_code>/tiempos')
def get_tiempos(event_code):
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT evento_completo, serie_numero, carril, nombre_completo, club, tiempo_neto
            FROM eventos_tiempo
            WHERE event_code = %s AND tiempo_neto IS NOT NULL AND tiempo_neto > 0
            ORDER BY evento_completo, serie_numero, carril
        """, (event_code,))
        tiempos = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(row) for row in tiempos]), 200
    except Exception as e:
        logging.exception("Error al obtener tiempos")
        return jsonify({"error": str(e)}), 500

# --- 3. Obtener resultados finales (con posición) ---
@app.route('/api/eventos/<event_code>/resultados')
def get_resultados(event_code):
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT evento_completo, posicion, nombre_completo, club, tiempo_neto
            FROM resultados
            WHERE event_code = %s AND tiempo_neto IS NOT NULL AND tiempo_neto > 0
            ORDER BY evento_completo, posicion
        """, (event_code,))
        resultados = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(row) for row in resultados]), 200
    except Exception as e:
        logging.exception("Error al obtener resultados")
        return jsonify({"error": str(e)}), 500

# --- 4. Obtener medallero (solo competitivo) ---
@app.route('/api/eventos/<event_code>/medallero')
def get_medallero(event_code):
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Excluir pruebas de Exhibición
        cur.execute("""
            SELECT 
                club,
                COUNT(CASE WHEN posicion = 1 THEN 1 END) as oros,
                COUNT(CASE WHEN posicion = 2 THEN 1 END) as platas,
                COUNT(CASE WHEN posicion = 3 THEN 1 END) as bronces
            FROM resultados
            WHERE event_code = %s 
              AND tiempo_neto IS NOT NULL 
              AND tiempo_neto > 0
              AND posicion IN (1, 2, 3)
              AND evento_completo NOT ILIKE '%Exhibición%'
            GROUP BY club
            ORDER BY oros DESC, platas DESC, bronces DESC
        """, (event_code,))
        medallero = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(row) for row in medallero]), 200
    except Exception as e:
        logging.exception("Error al obtener medallero")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
