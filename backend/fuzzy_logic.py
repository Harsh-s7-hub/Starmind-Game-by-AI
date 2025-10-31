# backend/fuzzy_logic.py
"""
Simple fuzzy diplomacy utilities.
Provides FuzzyDiplomacy class with eval(rel_power, distance, trust)
returns dict: {war_risk, cooperation}
All inputs are assumed normalized-ish:
 - rel_power: ratio (0.0 .. 2.0) where 1.0 ~ equal
 - distance: number (0..max_dist)
 - trust: 0.0 .. 1.0
"""
import math

def trapezoid(x, a, b, c, d):
    if x <= a or x >= d:
        return 0.0
    if a < x < b:
        return (x - a) / (b - a)
    if b <= x <= c:
        return 1.0
    if c < x < d:
        return (d - x) / (d - c)
    return 0.0

def triangle(x, a, b, c):
    if x <= a or x >= c:
        return 0.0
    if a < x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)

class FuzzyDiplomacy:
    def __init__(self, max_dist=30):
        self.max_dist = max_dist

    def eval(self, rel_power, distance, trust):
        # membership functions
        low_power = trapezoid(rel_power, 0.0, 0.0, 0.75, 0.95)
        equal_power = triangle(rel_power, 0.8, 1.0, 1.2)
        high_power = trapezoid(rel_power, 1.05, 1.25, 2.0, 2.0)

        near = trapezoid(distance, 0, 0, self.max_dist*0.2, self.max_dist*0.4)
        mid  = triangle(distance, self.max_dist*0.2, self.max_dist*0.5, self.max_dist*0.8)
        far  = trapezoid(distance, self.max_dist*0.6, self.max_dist*0.8, self.max_dist, self.max_dist)

        low_trust = trapezoid(trust, 0.0, 0.0, 0.2, 0.4)
        med_trust = triangle(trust, 0.2, 0.5, 0.8)
        high_trust = trapezoid(trust, 0.6, 0.8, 1.0, 1.0)

        # rules (handcrafted)
        war_1 = min(high_power, near, low_trust)
        war_2 = min(equal_power, near, low_trust)
        war_3 = min(high_power, mid, low_trust)
        war_score = max(war_1, war_2, war_3)

        coop_1 = min(high_trust, far)
        coop_2 = min(high_trust, mid, low_power)
        coop_3 = min(med_trust, far, equal_power)
        coop_score = max(coop_1, coop_2, coop_3)

        war_risk = min(1.0, war_score * 1.2 + (near * 0.12))
        cooperation = max(0.0, min(1.0, coop_score * 1.05 + (high_trust * 0.08) - (near * 0.08)))

        return {
            "war_risk": float(war_risk),
            "cooperation": float(cooperation),
            "members": {
                "low_power": low_power, "equal_power": equal_power, "high_power": high_power,
                "near": near, "mid": mid, "far": far,
                "low_trust": low_trust, "med_trust": med_trust, "high_trust": high_trust
            }
        }
