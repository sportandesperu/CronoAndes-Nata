# main.py
# Backend para CronoAndes-Nata — Sistema mundial de natación
# Soporta cronometraje distribuido: partidor + jueces de llegada
# Guarda salida y llegada por carril. Calcula tiempos netos en frontend o en resultados.

from flask import Flask, request, jsonify
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
import logging

# --- Configuración básica ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Conexión a la base de datos (usar connection pooling en producción si escala) ---
def get_db_conn():
    db_url = os.environ.get('DATABASE_URL', '').strip()
    if not db_url:
        raise RuntimeError("❌ DATABASE_URL no está definida en variables de entorno.")
    # Render usa postgres://, pero psycopg2 requiere postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url, sslmode='require')

# --- Inicialización segura de tablas (solo una vez al iniciar la app) ---
def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    
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
    
    # Guarda eventos de tiempo: salida (1 por serie) o llegada (1 por carril)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tiempos (
            id SERIAL PRIMARY KEY,
            event_code TEXT NOT NULL,
            serie_numero INTEGER NOT NULL,
            carril INTEGER NOT NULL CHECK (carril BETWEEN 1 AND 10),
            tipo TEXT NOT NULL CHECK (tipo IN ('salida', 'llegada')),
            timestamp_iso TEXT NOT NULL,  -- ISO 8601 en UTC: "2025-11-19T12:34:56.789Z"
            registrado_en TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    # Índices para rendimiento
    cur.execute('CREATE INDEX IF NOT EXISTS idx_tiempos_event_serie_tipo ON tiempos (event_code, serie_numero, tipo);')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_nadadores_event_serie ON nadadores (event_code, serie_numero);')
    
    conn.commit()
    cur.close()
    conn.close()
    logging.info("✅ Base de datos inicializada correctamente.")

# --- Validación de inputs ---
def validar_event_code(code):
    if not isinstance(code, str) or not code.strip() or len(code) > 50:
        raise ValueError("event_code debe ser una cadena no vacía (máx. 50 caracteres).")
    return code.strip()

def validar_serie_numero(num):
    if not isinstance(num, int) or num < 1 or num > 1000:
        raise ValueError("serie_numero debe ser un entero entre 1 y 1000.")
    return num

def validar_carril(lane):
    if not isinstance(lane, int) or lane < 1 or lane > 10:
        raise ValueError("carril debe ser un entero entre 1 y 10.")
    return lane

# --- Endpoints ---

@app.route('/')
def home():
    return jsonify({
        "app": "CronoAndes-Nata",
        "version": "2.0",
        "status": "online",
        "description": "API para cronometraje distribuido en competencias de natación"
    })

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
        logging.error(f"Health check falló: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

# --- Crear evento ---
@app.route('/api/eventos/<event_code>', methods=['PUT'])
def crear_evento(event_code):
    try:
        event_code = validar_event_code(event_code)
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Cuerpo JSON requerido."}), 400
        
        nombre = data.get('nombre_evento', '').strip()
        if not nombre:
            return jsonify({"error": "nombre_evento es obligatorio."}), 400
        
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
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error en crear_evento")
        return jsonify({"error": "Error interno."}), 500

# --- Subir nadadores por serie ---
@app.route('/api/eventos/<event_code>/nadadores', methods=['POST'])
def subir_nadadores(event_code):
    try:
        event_code = validar_event_code(event_code)
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "Esperaba una lista de nadadores."}), 400

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM nadadores WHERE event_code = %s", (event_code,))
        
        for item in data:
            serie = validar_serie_numero(item.get('serie_numero'))
            carril = validar_carril(item.get('carril'))
            nombre = str(item.get('nombre', '')).strip()
            if not nombre:
                return jsonify({"error": "nombre es obligatorio."}), 400
            
            cur.execute('''
                INSERT INTO nadadores (
                    event_code, serie_numero, carril, nombre, apellido, club, categoria
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                event_code,
                serie,
                carril,
                nombre,
                str(item.get('apellido', '')).strip() or None,
                str(item.get('club', '')).strip() or None,
                str(item.get('categoria', '')).strip() or None
            ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "nadadores": len(data)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error en subir_nadadores")
        return jsonify({"error": "Error interno."}), 500

# --- Registrar tiempos (salida o llegada) ---
@app.route('/api/eventos/<event_code>/tiempos', methods=['POST'])
def registrar_tiempos(event_code):
    try:
        event_code = validar_event_code(event_code)
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"error": "Esperaba una lista de eventos de tiempo."}), 400

        conn = get_db_conn()
        cur = conn.cursor()
        for item in data:
            serie = validar_serie_numero(item.get('serie_numero'))
            carril = validar_carril(item.get('carril'))
            tipo = str(item.get('tipo', '')).lower()
            if tipo not in ('salida', 'llegada'):
                return jsonify({"error": "tipo debe ser 'salida' o 'llegada'."}), 400
            
            # Usar el timestamp proporcionado o generar uno en UTC
            timestamp_iso = item.get('timestamp_iso')
            if not timestamp_iso:
                timestamp_iso = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            else:
                # Validar formato básico (no estricto)
                if not isinstance(timestamp_iso, str) or len(timestamp_iso) < 10:
                    return jsonify({"error": "timestamp_iso inválido."}), 400

            cur.execute('''
                INSERT INTO tiempos (event_code, serie_numero, carril, tipo, timestamp_iso)
                VALUES (%s, %s, %s, %s, %s)
            ''', (event_code, serie, carril, tipo, timestamp_iso))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "registros": len(data)}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error en registrar_tiempos")
        return jsonify({"error": "Error interno."}), 500

# --- Obtener nadadores de una serie ---
@app.route('/api/eventos/<event_code>/nadadores')
def obtener_nadadores(event_code):
    try:
        event_code = validar_event_code(event_code)
        serie = request.args.get('serie')
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if serie:
            serie = validar_serie_numero(int(serie))
            cur.execute('''
                SELECT serie_numero, carril, nombre, apellido, club, categoria
                FROM nadadores
                WHERE event_code = %s AND serie_numero = %s
                ORDER BY carril
            ''', (event_code, serie))
        else:
            cur.execute('''
                SELECT serie_numero, carril, nombre, apellido, club, categoria
                FROM nadadores
                WHERE event_code = %s
                ORDER BY serie_numero, carril
            ''', (event_code,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(row) for row in rows]), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error en obtener_nadadores")
        return jsonify({"error": "Error interno."}), 500

# --- Obtener tiempos de una serie o evento ---
@app.route('/api/eventos/<event_code>/tiempos')
def obtener_tiempos(event_code):
    try:
        event_code = validar_event_code(event_code)
        serie = request.args.get('serie')
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if serie:
            serie = validar_serie_numero(int(serie))
            cur.execute('''
                SELECT serie_numero, carril, tipo, timestamp_iso
                FROM tiempos
                WHERE event_code = %s AND serie_numero = %s
                ORDER BY id
            ''', (event_code, serie))
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
        return jsonify([dict(row) for row in rows]), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.exception("Error en obtener_tiempos")
        return jsonify({"error": "Error interno."}), 500

# --- Resultados crudos (para cálculo de tiempos netos en cliente) ---
@app.route('/api/eventos/<event_code>/resultados')
def obtener_resultados_crudos(event_code):
    try:
        event_code = validar_event_code(event_code)
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('''
            SELECT 
                n.serie_numero,
                n.carril,
                n.nombre,
                n.apellido,
                n.categoria,
                t_sal.timestamp_iso AS salida,
                t_lleg.timestamp_iso AS llegada
            FROM nadadores n
            LEFT JOIN tiempos t_sal
                ON n.event_code = t_sal.event_code
                AND n.serie_numero = t_sal.serie_numero
                AND n.carril = t_sal.carril
                AND t_sal.tipo = 'salida'
            LEFT JOIN tiempos t_lleg
                ON n.event_code = t_lleg.event_code
                AND n.serie_numero = t_lleg.serie_numero
                AND n.carril = t_lleg.carril
                AND t_lleg.tipo = 'llegada'
            WHERE n.event_code = %s
            ORDER BY n.serie_numero, n.carril
        ''', (event_code,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        logging.exception("Error en resultados_crudos")
        return jsonify({"error": "Error interno."}), 500

# --- Inicializar tablas al iniciar (solo en modo no Gunicorn/Render warmup) ---
with app.app_context():
    init_db()

# --- Iniciar app ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
