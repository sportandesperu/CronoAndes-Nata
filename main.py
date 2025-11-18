# main.py
# Backend para CronoAndes-Nata — Natación por series y carriles
# Sin dorsales. Identificación: evento + serie + carril + nombre

from flask import Flask, request, jsonify
import os
import psycopg2
from datetime import datetime, timezone

app = Flask(__name__)

# === Conexión a la base de datos ===
def get_db_conn():
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        raise Exception("DATABASE_URL no está definida")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url, sslmode='require')

# === Inicializar tablas ===
def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Tabla de eventos
    cur.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            event_code TEXT PRIMARY KEY,
            nombre_evento TEXT NOT NULL,
            distancia INTEGER,
            estilo TEXT,
            genero TEXT,
            creado_en TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Tabla de series (quién nada en qué carril)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS series (
            id SERIAL PRIMARY KEY,
            event_code TEXT NOT NULL,
            serie_numero INTEGER NOT NULL,
            carril INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            club TEXT,
            categoria TEXT,
            UNIQUE(event_code, serie_numero, carril)
        )
    ''')
    
    # Tabla de tiempos (salida/llegada por carril)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tiempos (
            id SERIAL PRIMARY KEY,
            event_code TEXT NOT NULL,
            serie_numero INTEGER NOT NULL,
            carril INTEGER NOT NULL,
            tipo TEXT NOT NULL,  -- 'salida' o 'llegada'
            timestamp_iso TEXT NOT NULL,
            registrado_en TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

# === Ruta raíz ===
@app.route('/')
def home():
    return jsonify({
        "app": "CronoAndes-Nata",
        "version": "1.0",
        "description": "API para cronometraje por series y carriles (sin dorsales)"
    })

# === Registrar un evento (opcional) ===
@app.route('/api/eventos/<event_code>', methods=['PUT'])
def crear_evento(event_code):
    try:
        init_db()
        data = request.get_json()
        nombre = data.get('nombre_evento', '').strip()
        if not nombre:
            return jsonify({"error": "nombre_evento requerido"}), 400
        
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO eventos (event_code, nombre_evento, distancia, estilo, genero)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (event_code) DO NOTHING
        ''', (
            event_code,
            nombre,
            data.get('distancia'),
            data.get('estilo'),
            data.get('genero')
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Subir lista de series (por evento) ===
@app.route('/api/eventos/<event_code>/series', methods=['POST'])
def subir_series(event_code):
    try:
        init_db()
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "esperaba una lista"}), 400

        conn = get_db_conn()
        cur = conn.cursor()
        # Limpiar series anteriores del evento
        cur.execute("DELETE FROM series WHERE event_code = %s", (event_code,))
        
        for item in 
            cur.execute('''
                INSERT INTO series (event_code, serie_numero, carril, nombre, apellido, club, categoria)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                event_code,
                item.get('serie_numero'),
                item.get('carril'),
                item.get('nombre', '').strip(),
                item.get('apellido', '').strip(),
                item.get('club', ''),
                item.get('categoria', '')
            ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "series": len(data)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Registrar tiempos (salida/llegada) ===
@app.route('/api/eventos/<event_code>/tiempos', methods=['POST'])
def registrar_tiempos(event_code):
    try:
        init_db()
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "esperaba una lista"}), 400

        conn = get_db_conn()
        cur = conn.cursor()
        for item in 
            cur.execute('''
                INSERT INTO tiempos (event_code, serie_numero, carril, tipo, timestamp_iso)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                event_code,
                item.get('serie_numero'),
                item.get('carril'),
                item.get('tipo', 'llegada').lower(),
                item.get('timestamp_iso', datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
            ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "tiempos": len(data)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Obtener tiempos para una serie ===
@app.route('/api/eventos/<event_code>/tiempos')
def obtener_tiempos(event_code):
    try:
        init_db()
        serie = request.args.get('serie')
        conn = get_db_conn()
        cur = conn.cursor()
        if serie:
            cur.execute('''
                SELECT serie_numero, carril, tipo, timestamp_iso
                FROM tiempos
                WHERE event_code = %s AND serie_numero = %s
                ORDER BY id
            ''', (event_code, int(serie)))
        else:
            cur.execute('''
                SELECT serie_numero, carril, tipo, timestamp_iso
                FROM tiempos
                WHERE event_code = %s
                ORDER BY id
            ''', (event_code,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([
            {
                "serie_numero": r[0],
                "carril": r[1],
                "tipo": r[2],
                "timestamp_iso": r[3]
            } for r in rows
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Obtener estructura de series (para mostrar en vivo) ===
@app.route('/api/eventos/<event_code>/series')
def obtener_series(event_code):
    try:
        init_db()
        serie = request.args.get('serie')
        conn = get_db_conn()
        cur = conn.cursor()
        if serie:
            cur.execute('''
                SELECT serie_numero, carril, nombre, apellido, club, categoria
                FROM series
                WHERE event_code = %s AND serie_numero = %s
                ORDER BY carril
            ''', (event_code, int(serie)))
        else:
            cur.execute('''
                SELECT serie_numero, carril, nombre, apellido, club, categoria
                FROM series
                WHERE event_code = %s
                ORDER BY serie_numero, carril
            ''', (event_code,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([
            {
                "serie_numero": r[0],
                "carril": r[1],
                "nombre": r[2],
                "apellido": r[3],
                "club": r[4],
                "categoria": r[5]
            } for r in rows
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Health check ===
@app.route('/health')
def health():
    try:
        init_db()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# === Iniciar ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
