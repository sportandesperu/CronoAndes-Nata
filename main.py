# main.py
# Backend para CronoAndes-Nata — MODO MANUAL (tiempos netos)
# Compatible con Streamlit (ingreso manual de tiempos como "28.45" o "NT")

from flask import Flask, request, jsonify
import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def get_db_conn():
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        raise RuntimeError("❌ DATABASE_URL no está definida.")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url, sslmode='require')

def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            event_code TEXT PRIMARY KEY,
            nombre_evento TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS nadadores (
            id SERIAL PRIMARY KEY,
            event_code TEXT NOT NULL,
            serie_numero INTEGER NOT NULL,
            carril INTEGER NOT NULL CHECK (carril BETWEEN 1 AND 10),
            nombre TEXT NOT NULL,
            apellido TEXT,
            club TEXT,
            categoria TEXT,
            UNIQUE(event_code, serie_numero, carril)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tiempos (
            id SERIAL PRIMARY KEY,
            event_code TEXT NOT NULL,
            serie_numero INTEGER NOT NULL,
            carril INTEGER NOT NULL CHECK (carril BETWEEN 1 AND 10),
            tiempo TEXT,  -- "28.45", "NT", etc.
            registrado_en TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    cur.execute('CREATE INDEX IF NOT EXISTS idx_tiempos_event_serie ON tiempos (event_code, serie_numero);')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_nadadores_event ON nadadores (event_code);')
    
    conn.commit()
    cur.close()
    conn.close()
    logging.info("✅ DB inicializada (modo manual).")

def validar_event_code(code):
    if not isinstance(code, str) or not code.strip() or len(code) > 50:
        raise ValueError("event_code inválido.")
    return code.strip()

def validar_serie_numero(num):
    if not isinstance(num, int) or num < 1 or num > 1000:
        raise ValueError("serie_numero debe ser entero entre 1 y 1000.")
    return num

def validar_carril(lane):
    if not isinstance(lane, int) or lane < 1 or lane > 10:
        raise ValueError("carril debe ser entero entre 1 y 10.")
    return lane

# --- Endpoints ---

@app.route('/')
def home():
    return jsonify({"app": "CronoAndes-Nata", "modo": "manual", "version": "2.1"})

@app.route('/health')
def health():
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/api/eventos/<event_code>', methods=['PUT'])
def crear_evento(event_code):
    try:
        event_code = validar_event_code(event_code)
        data = request.get_json()
        if not data or not data.get('nombre_evento'):
            return jsonify({"error": "nombre_evento requerido"}), 400
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO eventos (event_code, nombre_evento)
            VALUES (%s, %s)
            ON CONFLICT (event_code) DO NOTHING
        ''', (event_code, data['nombre_evento']))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error crear_evento")
        return jsonify({"error": "error interno"}), 500

@app.route('/api/eventos/<event_code>/nadadores', methods=['POST'])
def subir_nadadores(event_code):
    try:
        event_code = validar_event_code(event_code)
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "esperaba lista"}), 400
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM nadadores WHERE event_code = %s", (event_code,))
        for item in data:
            serie = validar_serie_numero(item['serie_numero'])
            carril = validar_carril(item['carril'])
            nombre = str(item.get('nombre', '')).strip()
            if not nombre:
                return jsonify({"error": "nombre requerido"}), 400
            cur.execute('''
                INSERT INTO nadadores (event_code, serie_numero, carril, nombre, apellido, club, categoria)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                event_code,
                serie,
                carril,
                nombre,
                str(item.get('apellido', '')) or None,
                str(item.get('club', '')) or None,
                str(item.get('categoria', '')) or None
            ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "nadadores": len(data)}), 200
    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error subir_nadadores")
        return jsonify({"error": "error interno"}), 500

@app.route('/api/eventos/<event_code>/tiempos', methods=['POST'])
def registrar_tiempos(event_code):
    try:
        event_code = validar_event_code(event_code)
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "esperaba lista"}), 400
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM tiempos WHERE event_code = %s", (event_code,))
        for item in data:
            serie = validar_serie_numero(item['serie_numero'])
            carril = validar_carril(item['carril'])
            tiempo = item.get('Tiempo')  # ¡Ojo! Streamlit usa "Tiempo" con mayúscula
            # Permitir: número, string "28.45", "NT", o None
            if tiempo == "":
                tiempo = None
            cur.execute('''
                INSERT INTO tiempos (event_code, serie_numero, carril, tiempo)
                VALUES (%s, %s, %s, %s)
            ''', (event_code, serie, carril, str(tiempo) if tiempo is not None else None))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "tiempos": len(data)}), 200
    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error registrar_tiempos")
        return jsonify({"error": "error interno"}), 500

@app.route('/api/eventos/<event_code>/nadadores')
def obtener_nadadores(event_code):
    try:
        event_code = validar_event_code(event_code)
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT serie_numero, carril, nombre, apellido, club, categoria
            FROM nadadores WHERE event_code = %s
            ORDER BY serie_numero, carril
        ''', (event_code,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error obtener_nadadores")
        return jsonify({"error": "error interno"}), 500

@app.route('/api/eventos/<event_code>/tiempos')
def obtener_tiempos(event_code):
    try:
        event_code = validar_event_code(event_code)
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT serie_numero, carril, tiempo AS Tiempo
            FROM tiempos WHERE event_code = %s
            ORDER BY serie_numero, carril
        ''', (event_code,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Devolver con clave "Tiempo" (mayúscula) para compatibilidad con Streamlit
        return jsonify([{"serie_numero": r["serie_numero"], "carril": r["carril"], "Tiempo": r["tiempo"]} for r in rows]), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error obtener_tiempos")
        return jsonify({"error": "error interno"}), 500

# Inicializar DB
with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
