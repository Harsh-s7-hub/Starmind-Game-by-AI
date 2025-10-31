# backend/ai_engine.py
"""
Main AIEngine: wraps A*, fuzzy diplomacy, CSP planner, and adversarial AI.
This file expects a minimal "galaxy model" that contains:
 - systems: dict system_id -> {"pos": (x,y), "owner": id or None, "resources": int}
 - adjacency: dict node -> list(nodes)
You can adapt it to your game's galaxy representation.
"""

from fuzzy_logic import FuzzyDiplomacy
from a_star import AStar
from csp_solver import CSPPlanner
from adversarial_ai import DiplomacyAI

class AIEngine:
    def __init__(self, galaxy=None):
        """
        galaxy: optional initial model. If None, engine expects caller to pass systems/adj when calling methods.
        """
        self.galaxy = galaxy
        self.fuzzy = None
        self.csp = CSPPlanner()
        self.diplomacy = DiplomacyAI()
        # ASTAR is created on demand when galaxy info is present

    def attach_galaxy(self, systems, adjacency, max_dist=50):
        # systems: dict id->{"pos":(x,y), ...}
        positions = {sid: systems[sid]['pos'] for sid in systems}
        self.astar = AStar(adjacency, positions)
        self.fuzzy = FuzzyDiplomacy(max_dist=max_dist)
        self.galaxy = {"systems": systems, "adj": adjacency}

    def process_player_action(self, action):
        """
        action example:
          {"type":"attack", "from": start_id, "to": goal_id, "player_id": pid}
          {"type":"negotiate", "with": target_id, "player_id": pid, "offer": {...}}
          {"type":"expand", "slots": 1, "player_id": pid}
        Returns a JSON-serializable dict with "result" and optional fields:
         - path: list of nodes (if path computed)
         - ai_responses: list of ai decisions (if a turn triggered)
        """
        if not hasattr(self, 'galaxy') or self.galaxy is None:
            return {"error": "Galaxy not attached to AIEngine."}

        if action["type"] == "attack":
            start = action["from"]
            goal = action["to"]
            path, cost = self.astar.find_path(start, goal)
            # also evaluate fuzzy risk toward nearest enemy (simple)
            systems = self.galaxy['systems']
            # choose a target empire id if present on goal
            target_owner = systems.get(goal, {}).get('owner', None)
            # produce AI reaction: have all other empires evaluate and optionally respond
            # For prototype, just return path and found cost
            return {"result": "attack_path", "path": path, "cost": cost, "target_owner": target_owner}
        elif action["type"] == "negotiate":
            # message to target -> evaluate fuzzy trust (expect offer contains trust estimate)
            pid = action["player_id"]
            target = action["with"]
            offer = action.get("offer", {})
            # simple trust numeric guess sent in offer (or compute heuristics)
            offered_trust = float(offer.get("trust", 0.5))
            # distance between nearest systems of player and target
            # For prototype we don't compute exact; just call fuzzy with sample values
            rel_power = offer.get("rel_power", 1.0)
            distance = offer.get("distance", 10)
            res = self.fuzzy.eval(rel_power, distance, offered_trust)
            decision = "accept" if res["cooperation"] > 0.5 else "reject"
            return {"result": "negotiation", "fuzzy": res, "decision": decision}
        elif action["type"] == "expand":
            # choose candidate systems near player's owned systems (caller may provide)
            player_id = action["player_id"]
            return {"result": "expand_requested", "message": "CSP planner can pick colonies (use attach_galaxy then call planner)"}
        else:
            return {"result": "unknown_action"}
