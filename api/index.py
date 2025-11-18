from flask import Flask, request, jsonify, render_template
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
CONNECTION_STRING = os.getenv("CONNECTION_STRING")
app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'

@app.route('/sensor')
def sensor():
        
    # Connect to the database
    try:
        connection = psycopg2.connect(CONNECTION_STRING)
        print("Connection successful!")
        
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        cursor.execute("select * from sensores")
        result = cursor.fetchone()
        print("Current Time:", result)
    
        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")
        return f"Current Time:{result}"
    except Exception as e:
        return(f"Failed to connect: {e}")

@app.route('/pagina')
def pagina():
    return render_template("pagina.html", user="Carlos")

# app.py (o index.py)

# ... (otras importaciones y rutas)

@app.route('/dashboard')
def dashboard():
    sensor_ids = []
    conn = None
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        cur = conn.cursor()
        
        # Obtener IDs de sensores
        cur.execute("SELECT DISTINCT sensor_id FROM sensores ORDER BY sensor_id ASC;")
        sensor_ids = [row[0] for row in cur.fetchall()]
        
        cur.close()
    except Exception as e:
        print(f"Error al cargar datos del dashboard: {e}")
        
    finally:
        if conn:
            conn.close()

    # Usar render_template para cargar dashboard.html
    # La variable 'sensor_ids' es accesible en el HTML.
    return render_template("dashboard.html", sensor_ids=sensor_ids)

# ... (otras rutas y tu ruta /sensor/<int:sensor_id> que debe devolver JSON)

@app.route("/sensor/<int:sensor_id>", methods=["POST"])
def insert_sensor_value(sensor_id):
    value = request.args.get("value", type=float)
    if value is None:
        return jsonify({"error": "Missing 'value' query parameter"}), 400

    try:
        connection = psycopg2.connect(CONNECTION_STRING)
        print("Connection successful!")
        cursor = connection.cursor()

        # Insert into sensors table
        cursor.execute(
            "INSERT INTO sensores (sensor_id, value) VALUES (%s, %s)",
            (sensor_id, value)
        )
        connection.commit()

        return jsonify({
            "message": "Sensor value inserted successfully",
            "sensor_id": sensor_id,
            "value": value
        }), 201

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'connection' in locals():
            connection.close()

@app.route("/sensor/<int:sensor_id>")
def get_sensor(sensor_id):
    try:
        conn = psycopg2.connect(CONNECTION_STRING)
        cur = conn.cursor()

        # Get the latest 10 values
        cur.execute("""
            SELECT value, created_at
            FROM sensores
            WHERE sensor_id = %s
            ORDER BY created_at DESC
            LIMIT 10;
        """, (sensor_id,))
        rows = cur.fetchall()

        # Convert to lists for graph
        values = [r[0] for r in rows][::-1]        # reverse for chronological order
        timestamps = [r[1].strftime('%Y-%m-%d %H:%M:%S') for r in rows][::-1]
        
        return jsonify(sensor_id=sensor_id, values=values, timestamps=timestamps)
        
    except Exception as e:
        return f"<h3>Error: {e}</h3>"

    finally:
        if 'conn' in locals():
            conn.close()
