# backend/ai_engine.py
from fuzzy_logic import FuzzySystem
from a_star import AStarSearch
from csp_solver import CSPPlanner
from adversarial_ai import DiplomacyAI

class AIEngine:
    def __init__(self):
        self.fuzzy = FuzzySystem()
        self.a_star = AStarSearch()
        self.csp = CSPPlanner()
        self.diplomacy = DiplomacyAI()

    def process_player_action(self, action):
        # Example structure of data:
        # {"type": "attack", "from": "A1", "to": "B3"}
        if action["type"] == "attack":
            path = self.a_star.find_path(action["from"], action["to"])
            ai_response = self.diplomacy.react_to_attack(action)
            return {"path": path, "ai_response": ai_response}
        elif action["type"] == "negotiate":
            trust = self.fuzzy.evaluate_trust(action["offer"])
            return {"ai_decision": "accept" if trust > 0.6 else "reject"}
        else:
            return {"message": "unknown action"}
