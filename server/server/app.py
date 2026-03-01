import sqlite3
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
DB_NAME = "topuPdb.db"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Stores card info and last known balance
    cursor.execute('''CREATE TABLE IF NOT EXISTS cards 
                      (uid TEXT PRIMARY KEY, balance INTEGER, last_seen DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    # Stores every transaction
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, amount INTEGER, type TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db() 

# --- MQTT SETUP ---
MQTT_BROKER = "157.173.101.159"
TEAM_ID = "kaliza07"
TOPIC_STATUS = f"rfid/{TEAM_ID}/card/status"
TOPIC_TOPUP = f"rfid/{TEAM_ID}/card/topup"
TOPIC_BALANCE = f"rfid/{TEAM_ID}/card/balance"

print(f"\n[INIT] MQTT Topics:")
print(f"  STATUS:  {TOPIC_STATUS}")
print(f"  TOPUP:   {TOPIC_TOPUP}")
print(f"  BALANCE: {TOPIC_BALANCE}\n")

# Global state to track if we are waiting for a checkout tap
checkout_queue = {"active": False, "amount": 0}

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] ✅ Connected with result code {rc}")
    client.subscribe(TOPIC_STATUS)
    client.subscribe(TOPIC_BALANCE)
    print(f"[MQTT] ✅ Subscribed to {TOPIC_STATUS}")
    print(f"[MQTT] ✅ Subscribed to {TOPIC_BALANCE}")

def on_disconnect(client, userdata, rc):
    print(f"[MQTT] ❌ Disconnected with result code {rc}")

def on_message(client, userdata, msg):
    global checkout_queue
    try:
        data = json.loads(msg.payload)
        uid = data.get('uid')
        bal = data.get('balance') or data.get('new balance')

        print(f"[MQTT] Received message on {msg.topic}: UID={uid}, Balance={bal}")

        # Update Database
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO cards (uid, balance) VALUES (?, ?)", (uid, bal))
        conn.commit()
        conn.close()

        # If in "Checkout Mode", calculate payment
        if checkout_queue["active"]:
            if bal >= checkout_queue["amount"]:
                deduction = -checkout_queue["amount"]
                client.publish(TOPIC_TOPUP, json.dumps({"uid": uid, "amount": deduction}))
                socketio.emit('checkout_result', {'status': 'success', 'uid': uid, 'new_balance': bal + deduction})
            else:
                socketio.emit('checkout_result', {'status': 'insufficient', 'uid': uid, 'needed': checkout_queue["amount"]})
            
            checkout_queue["active"] = False  # Reset queue

        # Forward to Frontend
        socketio.emit('card_tapped', data)

    except Exception as e:
        print(f"[ERROR] Failed to process MQTT message: {e}")

# --- START MQTT CLIENT ---
print(f"\n[INIT] Connecting to MQTT broker: {MQTT_BROKER}:1883...")
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
    print("[INIT] ✅ MQTT loop started")
except Exception as e:
    print(f"[INIT] ❌ MQTT Connection Failed: {e}")

# --- FLASK ROUTES ---
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/checkout', methods=['POST'])
def start_checkout():
    global checkout_queue
    data = request.json
    checkout_queue["active"] = True
    checkout_queue["amount"] = data['amount']
    print(f"[CHECKOUT] Waiting for card tap for amount: {checkout_queue['amount']}")
    return jsonify({"status": "waiting_for_tap"})

@app.route('/api/topup', methods=['POST'])
def topup():
    data = request.json
    print(f"[TOPUP] Sending topup command: {data}")
    mqtt_client.publish(TOPIC_TOPUP, json.dumps(data))
    return jsonify({"status": "command_sent"})

@app.route('/api/cards', methods=['GET'])
def get_all_cards():
    """Optional: Endpoint to read all card data from DB"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards")
    cards = cursor.fetchall()
    conn.close()
    return jsonify(cards)

# --- RUN SERVER ---
if __name__ == '__main__':
    print("[SERVER] Starting Flask + SocketIO server...")
    socketio.run(app, host='0.0.0.0', port=9243, debug=True)