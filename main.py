# main.py
# Backend para CronoAndes-Natación — MODO TIMESTAMP (partida + llegada)
# Compatible con app móvil (partidor/llegada) y con Streamlit (fallback manual)

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
from datetime import datetime, timezone
import logging
import re

# === Configuración ===
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cronoandes-natacion-2025')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# === Funciones auxiliares ===
def parse_iso_ts(ts_str):
    """Convierte ISO 8601 a datetime UTC."""
    if ts_str.endswith('Z'):
        ts_str = ts_str[:-1]
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def truncate_to_ms(ts_str):
    """Trunca microsegundos a milisegundos y termina en 'Z'."""
    if not ts_str:
        return ts_str
    clean = ts_str.rstrip('Z').rstrip('+00:00')
    if '.' in clean:
        base, frac = clean.split('.', 1)
        frac = re.sub(r'[^0-9]', '', frac)[:6].ljust(6, '0')
        return f"{base}.{frac[:3]}Z"
    return clean + "Z"

def get_db_conn():
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        raise RuntimeError("❌ DATABASE_URL no definida")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url, sslmode='require')

def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    # Tabla de nadadores (solo metadatos para app móvil)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS nadadores (
            id SERIAL PRIMARY KEY,
            event_code TEXT NOT NULL,
            serie_numero INTEGER NOT NULL,
            carril INTEGER NOT NULL CHECK (carril BETWEEN 1 AND 10),
            nombre TEXT NOT NULL,
            apellido TEXT,
            club TEXT,
            UNIQUE(event_code, serie_numero, carril)
        )
    ''')
    # Tabla de eventos de tiempo (salida/llegada)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS eventos_tiempo (
            id SERIAL PRIMARY KEY,
            event_code TEXT NOT NULL,
            serie_numero INTEGER NOT NULL,
            carril INTEGER CHECK (carril BETWEEN 1 AND 10),
            action TEXT NOT NULL CHECK (action IN ('salida', 'llegada')),
            timestamp_iso TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT NOW(),
            reemplazado_por INTEGER REFERENCES eventos_tiempo(id)
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_nadadores_event ON nadadores (event_code, serie_numero);')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_eventos_activos ON eventos_tiempo (event_code, serie_numero) WHERE reemplazado_por IS NULL;')
    conn.commit()
    cur.close()
    conn.close()
    logging.info("✅ Base de datos inicializada para natación (carriles + timestamps).")

# === Endpoints ===

@app.route('/')
def home():
    return jsonify({
        "app": "CronoAndes-Natación",
        "modo": "timestamp",
        "version": "1.0",
        "compatible_con": "Streamlit (fallback) + App Móvil (partida/llegada)"
    })

@app.route('/health')
def health():
    try:
        init_db()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# --- Inscripciones (metadatos de series) ---
@app.route('/api/eventos/<event_code>/nadadores', methods=['POST', 'GET'])
def manejar_nadadores(event_code):
    try:
        init_db()
        event_code = event_code.strip()
        if request.method == 'POST':
            data = request.get_json()
            if not isinstance(data, list):
                return jsonify({"error": "esperaba lista"}), 400
            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM nadadores WHERE event_code = %s", (event_code,))
            for item in data:
                cur.execute('''
                    INSERT INTO nadadores (event_code, serie_numero, carril, nombre, apellido, club)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    event_code,
                    item['serie_numero'],
                    item['carril'],
                    item['nombre'],
                    item.get('apellido') or '',
                    item.get('club') or ''
                ))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"status": "ok", "nadadores": len(data)}), 200
        else:
            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute('''
                SELECT serie_numero, carril, nombre, apellido, club
                FROM nadadores
                WHERE event_code = %s
                ORDER BY serie_numero, carril
            ''', (event_code,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify([{
                "serie_numero": r[0],
                "carril": r[1],
                "nombre": r[2],
                "apellido": r[3],
                "club": r[4]
            } for r in rows]), 200
    except Exception as e:
        logging.exception("Error en /nadadores")
        return jsonify({"error": str(e)}), 500

# --- Registro de tiempos (partida o llegada) ---
@app.route('/api/eventos/<event_code>/tiempos', methods=['POST'])
def registrar_tiempo(event_code):
    try:
        init_db()
        event_code = event_code.strip()
        data = request.get_json()
        action = data.get('action', '').lower()
        serie_numero = data.get('serie_numero')
        carril = data.get('carril')  # opcional si es "salida"
        timestamp = data.get('timestamp')
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        if action not in ('salida', 'llegada'):
            return jsonify({"error": "action debe ser 'salida' o 'llegada'"}), 400
        if action == 'llegada' and (carril is None or not (1 <= carril <= 10)):
            return jsonify({"error": "carril requerido para llegada (1-10)"}), 400
        if not serie_numero or not (1 <= serie_numero <= 1000):
            return jsonify({"error": "serie_numero requerido (1-1000)"}), 400

        timestamp_clean = truncate_to_ms(timestamp)

        conn = get_db_conn()
        cur = conn.cursor()

        # Reemplazar entradas anteriores
        if action == 'salida':
            cur.execute("""
                UPDATE eventos_tiempo
                SET reemplazado_por = nextval('eventos_tiempo_id_seq')
                WHERE event_code = %s AND serie_numero = %s AND action = 'salida' AND reemplazado_por IS NULL
            """, (event_code, serie_numero))
        else:
            cur.execute("""
                UPDATE eventos_tiempo
                SET reemplazado_por = nextval('eventos_tiempo_id_seq')
                WHERE event_code = %s AND serie_numero = %s AND carril = %s AND action = 'llegada' AND reemplazado_por IS NULL
            """, (event_code, serie_numero, carril))

        # Insertar nuevo
        if action == 'salida':
            cur.execute('''
                INSERT INTO eventos_tiempo (event_code, serie_numero, action, timestamp_iso)
                VALUES (%s, %s, %s, %s)
            ''', (event_code, serie_numero, 'salida', timestamp_clean))
        else:
            cur.execute('''
                INSERT INTO eventos_tiempo (event_code, serie_numero, carril, action, timestamp_iso)
                VALUES (%s, %s, %s, %s, %s)
            ''', (event_code, serie_numero, carril, 'llegada', timestamp_clean))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok"}), 201
    except Exception as e:
        logging.exception("Error al registrar tiempo")
        return jsonify({"error": str(e)}), 500

# --- Obtener tiempos por evento y serie ---
@app.route('/api/eventos/<event_code>/tiempos/<int:serie_numero>')
def obtener_tiempos_serie(event_code, serie_numero):
    try:
        init_db()
        conn = get_db_conn()
        cur = conn.cursor()
        # Salidas
        cur.execute('''
            SELECT action, timestamp_iso FROM eventos_tiempo
            WHERE event_code = %s AND serie_numero = %s AND action = 'salida' AND reemplazado_por IS NULL
            ORDER BY id DESC LIMIT 1
        ''', (event_code, serie_numero))
        salida = cur.fetchone()

        # Llegadas
        cur.execute('''
            SELECT carril, timestamp_iso FROM eventos_tiempo
            WHERE event_code = %s AND serie_numero = %s AND action = 'llegada' AND reemplazado_por IS NULL
            ORDER BY id
        ''', (event_code, serie_numero))
        llegadas = cur.fetchall()
        cur.close()
        conn.close()

        salida_ts = salida[1] if salida else None
        llegadas_dict = {r[0]: r[1] for r in llegadas}

        return jsonify({
            "serie_numero": serie_numero,
            "salida": salida_ts,
            "llegadas": llegadas_dict  # {4: "2025-...Z", 5: "..."}
        }), 200
    except Exception as e:
        logging.exception("Error al obtener tiempos")
        return jsonify({"error": str(e)}), 500

# --- Calcular tiempos netos (para Streamlit o exportación) ---
@app.route('/api/eventos/<event_code>/resultados')
def obtener_resultados_netos(event_code):
    try:
        init_db()
        conn = get_db_conn()
        cur = conn.cursor()
        # Obtener todas las salidas y llegadas activas
        cur.execute('''
            SELECT serie_numero, action, carril, timestamp_iso
            FROM eventos_tiempo
            WHERE event_code = %s AND reemplazado_por IS NULL
            ORDER BY serie_numero, id
        ''', (event_code,))
        eventos = cur.fetchall()
        cur.close()
        conn.close()

        # Agrupar por serie
        series = {}
        for serie_num, action, carril, ts in eventos:
            if serie_num not in series:
                series[serie_num] = {"salida": None, "llegadas": {}}
            if action == "salida":
                series[serie_num]["salida"] = ts
            elif action == "llegada" and carril is not None:
                series[serie_num]["llegadas"][carril] = ts

        # Calcular tiempos netos
        resultados = []
        for serie_num, data in series.items():
            if not data["salida"]:
                continue
            salida_dt = parse_iso_ts(data["salida"])
            for carril, llegada_ts in data["llegadas"].items():
                try:
                    llegada_dt = parse_iso_ts(llegada_ts)
                    neto_ms = (llegada_dt - salida_dt).total_seconds() * 1000
                    if neto_ms >= 0:
                        resultados.append({
                            "serie_numero": serie_num,
                            "carril": carril,
                            "tiempo_neto": round(neto_ms / 1000, 2),  # en segundos
                            "estado": "válido"
                        })
                except:
                    continue

        return jsonify(resultados), 200
    except Exception as e:
        logging.exception("Error al calcular resultados")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
