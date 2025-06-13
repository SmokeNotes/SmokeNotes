import paho.mqtt.client as mqtt
import json
import os
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.sql import func

# ------------------------------
# Configuration
# ------------------------------
MQTT_BROKER = os.environ["MQTT_BROKER"]
MQTT_PORT = 1883
MQTT_USERNAME = os.environ["MQTT_USERNAME"]
MQTT_PASSWORD = os.environ["MQTT_PASSWORD"]
MQTT_TOPIC = os.environ["MQTT_TOPIC"]
DATABASE_URI = os.environ.get("DATABASE_PATH", "/app/data/bbq_sessions.db")

# ------------------------------
# Flask + SQLAlchemy Setup
# ------------------------------
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_URI}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
os.makedirs("data", exist_ok=True)


# ------------------------------
# Models
# ------------------------------
class BBQSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    meat_type = db.Column(db.String(100))
    start_time = db.Column(db.DateTime(timezone=True))
    end_time = db.Column(db.DateTime(timezone=True))
    target_temp = db.Column(db.Float)


class TemperatureLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cook_id = db.Column(db.Integer, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("b_b_q_session.id"), nullable=True)
    #timestamp = db.Column(db.DateTime, server_default=func.now())
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    set_temp = db.Column(db.Float)
    pit_temp = db.Column(db.Float)
    meat_temp1 = db.Column(db.Float)
    blower = db.Column(db.Float)


class Temperature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, index=True)
    #timestamp = db.Column(db.DateTime, default=func.now())
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    meat_temp = db.Column(db.Float)
    smoker_temp = db.Column(db.Float)
    note = db.Column(db.String(100))  # added for note "From Flameboss"


# ------------------------------
# Globals for Tracking State
# ------------------------------
disconnection_timers = {}  # cook_id: Timer
latest_temps = {}  # cook_id: {"meat": val, "smoker": val}
last_seen_cook_id = {}  # "latest": cook_id


# ------------------------------
# MQTT Handlers
# ------------------------------
def on_connect(client, userdata, flags, reason_code, properties):
    """Callback for when the client receives a CONNACK response from the server."""
    if reason_code == 0:
        print("Connected to MQTT broker successfully")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect to MQTT broker with reason code: {reason_code}")


def on_message(client, userdata, msg):
    global disconnection_timers, last_seen_cook_id, latest_temps

    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received payload: {payload}")

        # Handle disconnect message
        if payload.get("name") == "disconnected" and payload.get("from") == "mqttr-4":
            cook_id = payload.get("cook_id") or last_seen_cook_id.get("latest")
            if not cook_id:
                print("No cook_id available for disconnection.")
                return

            def set_end_time():
                with app.app_context():
                    now = datetime.now(ZoneInfo("UTC"))
                    db.session.execute(
                        text(
                            "UPDATE bbq_session SET end_time = :end_time WHERE id = :cook_id"
                        ),
                        {"end_time": now, "cook_id": cook_id},
                    )
                    db.session.commit()
                    print(f"Set end_time for session {cook_id} at {now}")

            if cook_id in disconnection_timers:
                disconnection_timers[cook_id].cancel()

            timer = threading.Timer(300, set_end_time)
            disconnection_timers[cook_id] = timer
            timer.start()
            print(f"Disconnection timer started for cook_id {cook_id}")
            return

        # Standard temp message
        cook_id = payload.get("cook_id")
        if not cook_id:
            print("No cook_id in message. Skipping.")
            return

        last_seen_cook_id["latest"] = cook_id

        if cook_id in disconnection_timers:
            disconnection_timers[cook_id].cancel()
            del disconnection_timers[cook_id]
            print(f"Disconnection timer cancelled for cook_id {cook_id}")

        timestamp = datetime.fromtimestamp(payload["sec"], tz=ZoneInfo("UTC"))

        temps = payload.get("temps", [])
        set_temp = payload.get("set_temp")
        blower = payload.get("blower")

        def convert(x):
            return round((9 / 50) * x + 32) if x is not None else None

        set_temp = convert(set_temp) if set_temp is not None else None
        blower = blower / 100 if blower is not None else None
        pit_temp = convert(temps[0]) if len(temps) > 0 and temps[0] != -32767 else None
        meat_temp1 = (
            convert(temps[1]) if len(temps) > 1 and temps[1] != -32767 else None
        )

        # Store latest temps
        if meat_temp1 is not None or pit_temp is not None:
            latest_temps[cook_id] = {"meat": meat_temp1, "smoker": pit_temp}

        with app.app_context():
            result = db.session.execute(
                text("SELECT id FROM bbq_session WHERE id = :cook_id"),
                {"cook_id": cook_id},
            ).fetchone()

            if not result:
                db.session.execute(
                    text(
                        """
                        INSERT INTO bbq_session (id, title, meat_type, start_time, target_temp) 
                        VALUES (:id, :title, :meat_type, :start_time, :target_temp)
                    """
                    ),
                    {
                        "id": cook_id,
                        "title": f"BBQ Session {cook_id} from flameboss",
                        "meat_type": "Unknown",
                        "start_time": timestamp,
                        "target_temp": set_temp if set_temp else 0,
                    },
                )
                db.session.commit()
                print(f"Created new BBQ session with ID {cook_id}")
            # Update target_temp in bbq_session if set_temp has changed
            elif set_temp is not None:
                db.session.execute(
                    text(
                        """
                        UPDATE bbq_session 
                        SET target_temp = :target_temp
                        WHERE id = :cook_id
                    """
                    ),
                    {
                        "target_temp": set_temp,
                        "cook_id": cook_id,
                    },
                )
                db.session.commit()
                print(f"Updated target temperature for session {cook_id} to {set_temp}°F")

            db.session.execute(
                text(
                    """
                    INSERT INTO temperature_log 
                    (cook_id, session_id, timestamp, set_temp, pit_temp, meat_temp1, blower) 
                    VALUES (:cook_id, :session_id, :timestamp, :set_temp, :pit_temp, :meat_temp1, :blower)
                """
                ),
                {
                    "cook_id": cook_id,
                    "session_id": cook_id,
                    "timestamp": timestamp,
                    "set_temp": set_temp,
                    "pit_temp": pit_temp,
                    "meat_temp1": meat_temp1,
                    "blower": blower,
                },
            )
            db.session.commit()
            print(f"Stored log at {timestamp}")

    except Exception as e:
        print("Error processing MQTT message:", e)


# ------------------------------
# Background Temp Storage
# ------------------------------
def persist_latest_temps():
    with app.app_context():
        now = datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
        count = 0
        for session_id, temps in latest_temps.items():
            # Check if session is still active (no end_time)
            result = db.session.execute(
                text("SELECT end_time FROM bbq_session WHERE id = :session_id"),
                {"session_id": session_id},
            ).fetchone()
            if result and result[0] is None:
                db.session.add(
                    Temperature(
                        session_id=session_id,
                        timestamp=now,
                        meat_temp=temps.get("meat"),
                        smoker_temp=temps.get("smoker"),
                        note="From Flameboss"  # Adds note telling us this is from Flameboss MQTT
                    )
                )
                count += 1
        db.session.commit()
        print(f"[{now}] Persisted temperatures for {count} active sessions.")

    threading.Timer(900, persist_latest_temps).start() # Update Temperature Log every 15 minutes


# ------------------------------
# Run Listener
# ------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    persist_latest_temps()

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
