# backend/app.py
from flask import Flask, request, jsonify
from ai_engine import AIEngine
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow cross-origin for dev
engine = AIEngine()

@app.route("/api/attach_galaxy", methods=["POST"])
def attach_galaxy():
    data = request.json
    # data should contain 'systems' and 'adj'
    try:
        systems = data['systems']
        adj = data['adj']
    except KeyError:
        return jsonify({"error": "attach payload must contain systems and adj"}), 400
    # systems: {id: {"pos":[x,y], "owner":..., "resources":...}, ...}
    engine.attach_galaxy(systems, adj, max_dist=data.get("max_dist", 50))
    return jsonify({"result": "galaxy_attached"})

@app.route("/api/player_move", methods=["POST"])
def player_move():
    data = request.json
    res = engine.process_player_action(data)
    return jsonify(res)

if __name__ == "__main__":
    app.run(debug=True)
