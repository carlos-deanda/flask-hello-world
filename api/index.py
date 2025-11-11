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
    return render_template("pagina.html")



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
