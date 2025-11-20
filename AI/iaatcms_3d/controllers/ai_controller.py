# controllers/ai_controller.py
"""
Manages AI algorithms (Fuzzy, CSP, A*, GA) with debugging/visualization hooks
"""

import heapq
import random
import math
from typing import List, Dict, Tuple, Optional, Callable
from collections import defaultdict


class AIController:
    """Controller for AI algorithms with visualization support"""
    
    def __init__(self):
        self.debug_mode = False
        self.astar_debug_data = {}
        self.csp_debug_data = {}
        self.ga_debug_data = {}
        
        # Callbacks for visualization
        self.on_astar_step = None
        self.on_csp_step = None
        self.on_ga_generation = None
    
    # ========== FUZZY LOGIC ==========
    
    def tri_membership(self, x, a, b, c):
        """Triangular membership function"""
        if x <= a or x >= c:
            return 0.0
        if x == b:
            return 1.0
        if x < b:
            return (x - a) / (b - a)
        return (c - x) / (c - b)
    
    def fuzzy_priority(self, fuel_pct: float, weather: float, emergency: bool) -> Dict:
        """
        Calculate fuzzy priority with intermediate values for visualization
        Returns dict with priority score and breakdown
        """
        if emergency:
            return {
                "priority": 1.0,
                "fuel_level": "critical",
                "weather_level": "n/a",
                "emergency": True,
                "breakdown": "Emergency override"
            }
        
        # Normalize inputs
        fuel = max(0.0, min(1.0, fuel_pct / 100.0))
        inv_fuel = 1.0 - fuel
        
        # Fuel membership
        fuel_low = self.tri_membership(inv_fuel, 0.6, 0.9, 1.0)
        fuel_med = self.tri_membership(inv_fuel, 0.3, 0.5, 0.7)
        fuel_high = self.tri_membership(inv_fuel, 0.0, 0.0, 0.4)
        
        # Weather membership
        w_poor = self.tri_membership(weather, 0.6, 0.8, 1.0)
        w_med = self.tri_membership(weather, 0.3, 0.5, 0.7)
        w_good = self.tri_membership(weather, 0.0, 0.1, 0.4)
        
        # Rule evaluation
        r_high = max(fuel_low, w_poor)
        r_med = max(min(fuel_med, w_med), min(fuel_low, w_med))
        r_low = max(fuel_high, w_good)
        
        # Defuzzification (centroid)
        numerator = r_low * 0.1 + r_med * 0.5 + r_high * 0.9
        denominator = max(1e-6, r_low + r_med + r_high)
        priority = numerator / denominator
        
        # Determine levels for display
        fuel_level = "low" if fuel_low > 0.5 else "medium" if fuel_med > 0.5 else "high"
        weather_level = "poor" if w_poor > 0.5 else "medium" if w_med > 0.5 else "good"
        
        return {
            "priority": priority,
            "fuel_level": fuel_level,
            "weather_level": weather_level,
            "emergency": False,
            "breakdown": f"Fuel={fuel_level}, Weather={weather_level}",
            "memberships": {
                "fuel": {"low": fuel_low, "med": fuel_med, "high": fuel_high},
                "weather": {"poor": w_poor, "med": w_med, "good": w_good}
            },
            "rules": {"high": r_high, "med": r_med, "low": r_low}
        }
    
    # ========== A* PATHFINDING ==========
    
    def astar_taxi(self, start: str, goal: str, nodes: Dict, adj: Dict, 
                   blocked: set = None) -> Optional[List[str]]:
        """
        A* pathfinding with debug visualization support
        """
        blocked = blocked or set()
        
        if start not in nodes or goal not in nodes:
            return None
        
        def dist(a, b):
            return math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1])
        
        def heuristic(n):
            return dist(n, goal)
        
        open_set = [(heuristic(start), 0.0, start, [start])]
        g_score = {start: 0.0}
        closed_set = set()
        
        # Debug tracking
        debug_steps = []
        
        step_count = 0
        while open_set:
            f, g, current, path = heapq.heappop(open_set)
            
            if self.debug_mode:
                debug_steps.append({
                    "step": step_count,
                    "current": current,
                    "open": [n for _, _, n, _ in open_set],
                    "closed": list(closed_set),
                    "path": path,
                    "g_score": g,
                    "f_score": f
                })
                if self.on_astar_step:
                    self.on_astar_step(debug_steps[-1])
            
            if current == goal:
                self.astar_debug_data[f"{start}->{goal}"] = debug_steps
                return path
            
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # Explore neighbors
            for neighbor in adj.get(current, []):
                if neighbor in blocked or neighbor in closed_set:
                    continue
                
                tentative_g = g + dist(current, neighbor)
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor)
                    heapq.heappush(open_set, (f_score, tentative_g, neighbor, path + [neighbor]))
            
            step_count += 1
        
        return None  # No path found
    
    # ========== CSP SCHEDULER ==========
    
    def csp_schedule(self, flights: List[Dict], runways: List[str], 
                     gates: List[str], separation: int = 1) -> Optional[Dict]:
        """
        CSP scheduler with backtracking and debug visualization
        """
        self.csp_debug_data = {
            "steps": [],
            "backtracks": 0,
            "assignments_tried": 0
        }
        
        # Build domains
        domains = {}
        for flight in flights:
            domain = []
            for runway in runways:
                for gate in gates:
                    for slot in range(flight['slot'], flight['slot'] + 6):
                        domain.append((runway, gate, slot))
            domains[flight['id']] = domain
        
        def is_consistent(var, val, assignment):
            runway, gate, slot = val
            
            for other_var, other_val in assignment.items():
                other_runway, other_gate, other_slot = other_val
                
                # Runway separation
                if other_runway == runway and abs(other_slot - slot) < separation:
                    return False
                
                # Gate occupancy
                if other_gate == gate and abs(other_slot - slot) < 2:
                    return False
            
            return True
        
        def select_unassigned(assignment):
            unassigned = [f for f in flights if f['id'] not in assignment]
            # MRV heuristic
            unassigned.sort(key=lambda x: len(domains[x['id']]))
            return unassigned[0]['id'] if unassigned else None
        
        def backtrack(assignment, depth=0):
            if len(assignment) == len(flights):
                return assignment
            
            var = select_unassigned(assignment)
            
            for val in domains[var]:
                self.csp_debug_data['assignments_tried'] += 1
                
                if self.debug_mode and self.on_csp_step:
                    self.on_csp_step({
                        "depth": depth,
                        "var": var,
                        "val": val,
                        "assignment": dict(assignment),
                        "checking": "consistency"
                    })
                
                if is_consistent(var, val, assignment):
                    assignment[var] = val
                    result = backtrack(assignment, depth + 1)
                    
                    if result:
                        return result
                    
                    del assignment[var]
                    self.csp_debug_data['backtracks'] += 1
                    
                    if self.debug_mode and self.on_csp_step:
                        self.on_csp_step({
                            "depth": depth,
                            "var": var,
                            "action": "backtrack"
                        })
            
            return None
        
        # Sort by priority descending
        flights_sorted = sorted(flights, key=lambda x: -x['priority'])
        result = backtrack({})
        
        return result
    
    # ========== GENETIC ALGORITHM ==========
    
    def ga_optimize_order(self, flight_ids: List[str], fitness_fn: Callable,
                          pop_size: int = 32, generations: int = 40,
                          mutation_rate: float = 0.12) -> List[str]:
        """
        Genetic algorithm for landing order optimization with visualization
        """
        self.ga_debug_data = {
            "generations": [],
            "best_fitness_history": [],
            "avg_fitness_history": []
        }
        
        # Initialize population
        population = [random.sample(flight_ids, len(flight_ids)) 
                      for _ in range(pop_size)]
        
        for gen in range(generations):
            # Evaluate fitness
            scored = [(fitness_fn(individual), individual) for individual in population]
            scored.sort(key=lambda x: x[0])
            
            # Track statistics
            best_fitness = scored[0][0]
            avg_fitness = sum(score for score, _ in scored) / len(scored)
            
            self.ga_debug_data['best_fitness_history'].append(best_fitness)
            self.ga_debug_data['avg_fitness_history'].append(avg_fitness)
            
            if self.debug_mode and self.on_ga_generation:
                self.on_ga_generation({
                    "generation": gen,
                    "best_fitness": best_fitness,
                    "avg_fitness": avg_fitness,
                    "best_individual": scored[0][1],
                    "population_size": len(population)
                })
            
            # Selection (top 50%)
            population = [individual for _, individual in scored[:pop_size // 2]]
            
            # Crossover and mutation
            children = []
            while len(population) + len(children) < pop_size:
                parent_a = random.choice(population)
                parent_b = random.choice(population)
                
                # Ordered crossover
                cut = random.randint(1, len(parent_a) - 1)
                child = parent_a[:cut] + [x for x in parent_b if x not in parent_a[:cut]]
                
                # Mutation
                if random.random() < mutation_rate:
                    i, j = random.sample(range(len(child)), 2)
                    child[i], child[j] = child[j], child[i]
                
                children.append(child)
            
            population += children
        
        # Return best individual
        final_scored = [(fitness_fn(ind), ind) for ind in population]
        return min(final_scored, key=lambda x: x[0])[1]
