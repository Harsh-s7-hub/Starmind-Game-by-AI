# backend/adversarial_ai.py
"""
Small adversarial decision helper.
Given a lightweight world model (powers, sizes), it simulates simple action effects
and returns a numeric evaluation for candidate actions. Intended for short lookahead.
"""

import random

class DiplomacyAI:
    def __init__(self, aggression=0.5, caution=0.5, plan_depth=2):
        self.aggression = aggression
        self.caution = caution
        self.plan_depth = plan_depth

    def evaluate_world(self, self_id, target_id, world_state, trust_map):
        # world_state: {"powers": {id: power}, "sizes": {id: size}, ...}
        our = world_state['powers'].get(self_id, 0.1)
        their = world_state['powers'].get(target_id, 0.1)
        territory = world_state['sizes'].get(self_id, 0) - world_state['sizes'].get(target_id, 0)
        trust = trust_map.get(target_id, 0.5)
        # weighted score
        return (our - their)*2.0 + territory*1.0 + (trust - 0.5) * 1.0

    def simulate_action(self, action, self_id, target_id, world_state):
        # shallow deterministic-ish effect models
        cloned = {'powers': dict(world_state['powers']), 'sizes': dict(world_state['sizes'])}
        if action == 'attack':
            ratio = cloned['powers'].get(self_id, 1.0) / max(0.001, cloned['powers'].get(target_id, 1.0))
            gain = min(2.0, ratio * 0.45)
            cloned['powers'][self_id] = cloned['powers'].get(self_id, 1.0) + gain
            cloned['powers'][target_id] = max(0.1, cloned['powers'].get(target_id, 1.0) - gain*0.6)
        elif action == 'ally':
            cloned['powers'][self_id] = cloned['powers'].get(self_id, 1.0) + 0.35
            cloned['powers'][target_id] = cloned['powers'].get(target_id, 1.0) + 0.35
        elif action == 'expand':
            cloned['powers'][self_id] = cloned['powers'].get(self_id, 1.0) + 0.45
        return cloned

    def choose_best_action(self, self_id, target_id, world_state, trust_map, depth=None):
        if depth is None:
            depth = self.plan_depth
        actions = ['attack', 'ally', 'expand']
        best = None
        best_score = -1e9
        for act in actions:
            cloned = self.simulate_action(act, self_id, target_id, world_state)
            # opponent simple policy: choose action that maximizes its own evaluate (adversarial)
            # opponent picks from same actions
            if depth > 0:
                # naive opponent best response
                opp_best = -1e9
                for opp_act in actions:
                    opp_cloned = self.simulate_action(opp_act, target_id, self_id, cloned)
                    score = self.evaluate_world(self_id, target_id, opp_cloned, trust_map)
                    if score > opp_best:
                        opp_best = score
                score_here = opp_best
            else:
                score_here = self.evaluate_world(self_id, target_id, cloned, trust_map)
            # bias by aggression/caution
            if act == 'attack':
                score_here *= (1.0 + self.aggression)
            if act == 'ally':
                score_here *= (1.0 + (1.0 - self.aggression) * 0.5)
            if score_here > best_score:
                best_score = score_here
                best = act
        return best, best_score
