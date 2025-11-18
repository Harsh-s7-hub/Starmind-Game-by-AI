# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import time
import threading

from backend.game_engine import GameEngine, coord_to_sector, sector_to_coord

app = Flask(__name__)
CORS(app)

engine = GameEngine(num_civs=60, tick_rate=1.0)
engine.start()

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(engine.get_state())

@app.route("/api/set_name", methods=["POST"])
def set_name():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if name:
        engine.set_player_name(name)
        return jsonify({"ok": True, "message": f"Name set to {name}"})
    return jsonify({"ok": False, "message": "No name provided"}), 400

@app.route("/api/action/<action>", methods=["POST"])
def do_action(action):
    data = request.get_json() or {}
    civ_id = data.get("civ_id")
    if action == "negotiate":
        ok, msg = engine.action_negotiate(int(civ_id))
        return jsonify({"ok": ok, "message": msg})
    elif action == "trade":
        ok, msg = engine.action_trade(int(civ_id))
        return jsonify({"ok": ok, "message": msg})
    elif action == "attack":
        ok, msg = engine.action_attack(int(civ_id))
        return jsonify({"ok": ok, "message": msg})
    else:
        return jsonify({"ok": False, "message": "Unknown action"}), 400

@app.route("/api/send_fleet", methods=["POST"])
def api_send_fleet():
    data = request.get_json() or {}
    owner = data.get("owner", "HUMANITY")
    from_p = data.get("from_percent")
    to_p = data.get("to_percent")
    strength = int(data.get("strength", 50))
    speed = float(data.get("speed", 1.0))
    if not from_p or not to_p:
        return jsonify({"ok": False, "message": "from_percent and to_percent required"}), 400
    ok, msg = engine.send_fleet(owner, tuple(from_p), tuple(to_p), strength=strength, speed=speed)
    return jsonify({"ok": ok, "message": msg})

@app.route("/api/stop", methods=["POST"])
def stop_server():
    engine.stop()
    # do not attempt to shutdown Flask from here; this endpoint is for engine stop only
    return jsonify({"ok": True})

if __name__ == "__main__":
    # Run dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
