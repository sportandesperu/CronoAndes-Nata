# main.py
# API REST para CronoAndes-Nata — modo offline-first
# Compatible con PostgreSQL en Render

from flask import Flask, request, jsonify
import os
import psycopg2
from datetime import datetime, timezone

app = Flask(__name__)

# === Base de datos ===
def get_db_conn():
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        raise Exception("DATABASE_URL no está definida")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url, sslmode='require')

def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tiempos (
            id SERIAL PRIMARY KEY,
            evento TEXT NOT NULL,
            dorsal TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp_iso TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT NOW()
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_tiempos_evento ON tiempos (evento)')
    conn.commit()
    cur.close()
    conn.close()

# === Ruta raíz ===
@app.route('/')
def home():
    return jsonify({
        "app": "CronoAndes-Nata",
        "version": "1.0",
        "endpoints": {
            "POST /api/tiempos/<event_code>": "Recibir tiempos",
            "GET /api/tiempos/<event_code>": "Obtener tiempos"
        }
    })

# === Recibir tiempos ===
@app.route('/api/tiempos/<event_code>', methods=['POST'])
def recibir_tiempos(event_code):
    try:
        init_db()
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "Se espera una lista de registros"}), 400

        conn = get_db_conn()
        cur = conn.cursor()
        # Eliminar datos anteriores del mismo evento (para evitar duplicados)
        cur.execute("DELETE FROM tiempos WHERE evento = %s", (event_code,))
        
        for item in 
            dorsal = str(item.get('Dorsal', '')).strip()
            action = str(item.get('action', 'llegada')).strip().lower()
            timestamp_iso = str(item.get('timestamp_iso', datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))).strip()
            if dorsal and event_code:
                cur.execute(
                    "INSERT INTO tiempos (evento, dorsal, action, timestamp_iso) VALUES (%s, %s, %s, %s)",
                    (event_code, dorsal, action, timestamp_iso)
                )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "guardados": len(data)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Obtener tiempos ===
@app.route('/api/tiempos/<event_code>', methods=['GET'])
def obtener_tiempos(event_code):
    try:
        init_db()
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT dorsal, action, timestamp_iso FROM tiempos WHERE evento = %s ORDER BY id",
            (event_code,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([
            {"dorsal": r[0], "action": r[1], "timestamp_iso": r[2]} for r in rows
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Health check ===
@app.route('/health')
def health():
    try:
        init_db()
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# === Iniciar ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
