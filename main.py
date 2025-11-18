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
            carril INTEGER NOT NULL CHECK (carril BETWEEN 1 AND 6),
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
            carril INTEGER NOT NULL CHECK (carril BETWEEN 1 AND 6),
            tipo TEXT NOT NULL CHECK (tipo IN ('salida', 'llegada')),
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
        "version": "1.1",
        "description": "API para cronometraje por series y carriles (sin dorsales)"
    })

# === Registrar un evento ===
@app.route('/api/eventos/<event_code>', methods=['PUT'])
def crear_evento(event_code):
    try:
        init_db()
        data = request.get_json()
        if not data:
            return jsonify({"error": "cuerpo JSON requerido"}), 400
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
            return jsonify({"error": "esperaba una lista de series"}), 400

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM series WHERE event_code = %s", (event_code,))
        
        for item in data:
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
            return jsonify({"error": "esperaba una lista de tiempos"}), 400

        conn = get_db_conn()
        cur = conn.cursor()
        for item in data:
            tipo = item.get('tipo', 'llegada').lower()
            if tipo not in ('salida', 'llegada'):
                return jsonify({"error": "tipo debe ser 'salida' o 'llegada'"}), 400
            timestamp_iso = item.get('timestamp_iso')
            if not timestamp_iso:
                # Generar timestamp en UTC si no se proporciona
                timestamp_iso = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            cur.execute('''
                INSERT INTO tiempos (event_code, serie_numero, carril, tipo, timestamp_iso)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                event_code,
                item.get('serie_numero'),
                item.get('carril'),
                tipo,
                timestamp_iso
            ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "ok", "tiempos": len(data)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Obtener tiempos para una serie o evento ===
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

# === Obtener estructura de series ===
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

# === Endpoint de resultados (solo datos crudos; el cálculo de tiempos netos se hace en frontend) ===
@app.route('/api/eventos/<event_code>/resultados')
def obtener_resultados_crudos(event_code):
    try:
        init_db()
        conn = get_db_conn()
        cur = conn.cursor()
        # Obtener todos los tiempos agrupados por serie/carril
        cur.execute('''
            SELECT s.serie_numero, s.carril, s.nombre, s.apellido, s.categoria,
                   t_salida.timestamp_iso AS salida,
                   t_llegada.timestamp_iso AS llegada
            FROM series s
            LEFT JOIN tiempos t_salida
                ON s.event_code = t_salida.event_code
                AND s.serie_numero = t_salida.serie_numero
                AND s.carril = t_salida.carril
                AND t_salida.tipo = 'salida'
            LEFT JOIN tiempos t_llegada
                ON s.event_code = t_llegada.event_code
                AND s.serie_numero = t_llegada.serie_numero
                AND s.carril = t_llegada.carril
                AND t_llegada.tipo = 'llegada'
            WHERE s.event_code = %s
            ORDER BY s.serie_numero, s.carril
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
                "categoria": r[4],
                "salida": r[5],
                "llegada": r[6]
            } for r in rows
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Borrar evento (para pruebas) ===
@app.route('/api/eventos/<event_code>/borrar', methods=['POST'])
def borrar_evento(event_code):
    try:
        init_db()
        data = request.get_json()
        if data.get('confirm') != 'borrar':
            return jsonify({"error": "confirmar con {'confirm': 'borrar'}"}), 400
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM tiempos WHERE event_code = %s", (event_code,))
        cur.execute("DELETE FROM series WHERE event_code = %s", (event_code,))
        cur.execute("DELETE FROM eventos WHERE event_code = %s", (event_code,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "evento eliminado"}), 200
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
    app.run(host='0.0.0.0', port=port, debug=False)
