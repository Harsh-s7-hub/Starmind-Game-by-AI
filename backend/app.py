# backend/app.py
from flask import Flask, request, jsonify
from ai_engine import AIEngine

app = Flask(__name__)
ai = AIEngine()

@app.route("/api/player_move", methods=["POST"])
def player_move():
    data = request.json
    response = ai.process_player_action(data)
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
