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

@app.route('/dashboard')
def dashboard():
    conn = None
    sensor_ids = []
    initial_data = {'values': [], 'timestamps': [], 'sensor_id': 'N/A'}

    try:
        # Conexión para obtener IDs de sensores y datos iniciales
        conn = psycopg2.connect(CONNECTION_STRING)
        cur = conn.cursor()
        
        # 1. Obtener todos los IDs de sensores distintos
        cur.execute("SELECT DISTINCT sensor_id FROM sensores ORDER BY sensor_id ASC;")
        sensor_ids = [row[0] for row in cur.fetchall()]
        
        # 2. Obtener datos iniciales para el primer sensor (si existe)
        if sensor_ids:
            first_sensor_id = sensor_ids[0]
            # Usaremos los datos que ya obtienes en /sensor/<int:sensor_id>
            # (aunque esa ruta debería devolver JSON para ser útil aquí).
            cur.execute("""
                SELECT value, created_at
                FROM sensores
                WHERE sensor_id = %s
                ORDER BY created_at DESC
                LIMIT 10;
            """, (first_sensor_id,))
            rows = cur.fetchall()
            initial_data = {
                'values': [r[0] for r in rows][::-1],
                'timestamps': [r[1].strftime('%H:%M:%S') for r in rows][::-1],
                'sensor_id': first_sensor_id
            }
        
        cur.close()
    except Exception as e:
        # En caso de error, inicializa con datos vacíos
        print(f"Error al cargar datos del dashboard: {e}")
        sensor_ids = []
    finally:
        if conn:
            conn.close()

    # 3. Generar las opciones del selector HTML
    select_options = "\n".join(
        f'<option value="{id}" {"selected" if id == initial_data["sensor_id"] else ""}>Sensor ID: {id}</option>' for id in sensor_ids
    )

    # 4. Construir el HTML completo
    # NOTA: El JS usará la ruta /sensor/<id> para obtener nuevos datos.
    # Esta ruta debe devolver JSON, no HTML.
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard Dinámico</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            #chartContainer {{ margin-top: 20px; border: 1px solid #ccc; padding: 15px; border-radius: 8px; }}
            select {{ padding: 8px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Gráfica por Sensor</h1>

            <label for="sensor-select">Selecciona un Sensor:</label>
            <select id="sensor-select" onchange="loadSensorData()">
                <option value="">-- Elige un Sensor --</option>
                {select_options}
            </select>
            
            <p id="loading-status" style="color: blue;">{"Gráfica cargada." if sensor_ids else "No se encontraron sensores en la base de datos."}</p>

            <div id="chartContainer">
                <canvas id="sensorChart"></canvas>
            </div>
        </div>

        <script>
            let sensorChart;
            const initialData = {{
                values: {initial_data['values']},
                timestamps: {initial_data['timestamps']},
                sensor_id: {initial_data['sensor_id']}
            }};

            function updateChart(sensorId, values, timestamps) {{
                const ctx = document.getElementById('sensorChart').getContext('2d');
                if (sensorChart) {{ sensorChart.destroy(); }}

                sensorChart = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: timestamps, 
                        datasets: [{{
                            label: `Valor del Sensor ID ${{sensorId}}`,
                            data: values, 
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1,
                            fill: false
                        }}]
                    }},
                    options: {{ responsive: true }}
                }});
            }}

            function loadSensorData() {{
                const selectElement = document.getElementById('sensor-select');
                const sensorId = selectElement.value;
                const statusElement = document.getElementById('loading-status');

                if (!sensorId) {{
                    if (sensorChart) {{ sensorChart.destroy(); sensorChart = null; }}
                    statusElement.textContent = "Selecciona un sensor para ver su gráfica.";
                    return;
                }}

                statusElement.textContent = `Cargando datos para el Sensor ID ${{sensorId}}...`;

                // LLAMADA A TU RUTA EXISTENTE: /sensor/<int:sensor_id>
                fetch(`/sensor/${{sensorId}}`) 
                    .then(response => {{
                        if (!response.ok) {{
                            throw new Error(`Error en la petición: ${{response.status}}`);
                        }}
                        return response.json();
                    }})
                    .then(data => {{
                        // Tu ruta /sensor/<id> devuelve: values, timestamps.
                        updateChart(sensorId, data.values, data.timestamps);
                        statusElement.textContent = `Gráfica actualizada para el Sensor ID ${{sensorId}}.`;
                    }})
                    .catch(error => {{
                        console.error('Error al obtener los datos:', error);
                        statusElement.textContent = `Fallo al cargar la gráfica: ${{error.message}}`;
                    }});
            }}
            
            // Cargar gráfica inicial al iniciar
            document.addEventListener('DOMContentLoaded', () => {{
                if (initialData.sensor_id !== 'N/A') {{
                    updateChart(initialData.sensor_id, initialData.values, initialData.timestamps);
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html_content

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
