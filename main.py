from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ─────────────────────────────────────────────
TEAM_ID = "kaliza07"
BASE_TOPIC = f"rfid/{TEAM_ID}/"
STATUS_TOPIC  = BASE_TOPIC + "card/status"
TOPUP_TOPIC   = BASE_TOPIC + "card/topup"
BALANCE_TOPIC = BASE_TOPIC + "card/balance"
# ─────────────────────────────────────────────

# MQTT Client
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected (rc={rc})")
    client.subscribe(STATUS_TOPIC)
    client.subscribe(BALANCE_TOPIC)
    print(f"[MQTT] Subscribed to: {STATUS_TOPIC}, {BALANCE_TOPIC}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        print(f"[MQTT → WS] {msg.topic}: {data}")
        # Emit to frontend **matching the dashboard listener**
        socketio.emit('update_dashboard', data)
    except Exception as e:
        print(f"[MQTT error] {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# MQTT background thread
def mqtt_thread():
    mqtt_client.connect("157.173.101.159", 1883, 60)
    mqtt_client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# HTTP endpoint: receive top-up request
@app.route('/topup', methods=['POST'])
def topup():
    data = request.get_json()
    uid = data.get('uid')
    amount = data.get('amount')

    if not uid or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"error": "Invalid uid or amount"}), 400

    payload = json.dumps({"uid": uid, "amount": int(amount)})
    mqtt_client.publish(TOPUP_TOPIC, payload)
    print(f"[HTTP → MQTT] Published top-up: {payload}")

    return jsonify({"success": True})

# Serve dashboard
@app.route('/')
def serve_dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    print(f"[INFO] Backend starting for team: {TEAM_ID}")
    socketio.run(app, host='127.0.0.1', port=5000, allow_unsafe_werkzeug=True)
