from flask import Flask, jsonify, request
from flask_cors import CORS
import heapq
import math
from typing import List, Dict, Tuple, Optional
import random

app = Flask(__name__)
CORS(app)

# ============================================================================
# GAME STATE & DATA STRUCTURES
# ============================================================================

class GameState:
    def __init__(self):
        self.commander_name = "Commander"
        self.current_turn = 0
        self.player_resources = {"credits": 1000, "fuel": 500, "alloy": 300}
        self.player_fleet_position = "Terra Prime"
        self.trust_levels = {
            "Nexus Collective": 0.5,
            "Quantum Dominion": 0.3,
            "Ethereal Syndicate": 0.7,
            "Void Sentinels": 0.2
        }
        self.controlled_systems = ["Terra Prime"]
        self.ai_empires = self._initialize_empires()
        self.star_systems = self._initialize_star_systems()
        
    def _initialize_empires(self):
        return {
            "Nexus Collective": {
                "ideology": "collaborative",
                "power": 0.6,
                "systems": ["Nexus-7", "Alpha Centauri"],
                "hostility": 0.4
            },
            "Quantum Dominion": {
                "ideology": "expansionist",
                "power": 0.8,
                "systems": ["Quantum Gate", "Orion's Edge"],
                "hostility": 0.7
            },
            "Ethereal Syndicate": {
                "ideology": "peaceful",
                "power": 0.5,
                "systems": ["Ethereal Haven"],
                "hostility": 0.2
            },
            "Void Sentinels": {
                "ideology": "isolationist",
                "power": 0.9,
                "systems": ["Void Bastion", "Dark Nebula"],
                "hostility": 0.6
            }
        }
    
    def _initialize_star_systems(self):
        return {
            "Terra Prime": {"x": 0, "y": 0, "resources": {"credits": 100, "fuel": 50, "alloy": 30}},
            "Nexus-7": {"x": 5, "y": 3, "resources": {"credits": 80, "fuel": 60, "alloy": 40}},
            "Alpha Centauri": {"x": 3, "y": 5, "resources": {"credits": 90, "fuel": 70, "alloy": 35}},
            "Quantum Gate": {"x": 8, "y": 2, "resources": {"credits": 120, "fuel": 80, "alloy": 50}},
            "Orion's Edge": {"x": 10, "y": 8, "resources": {"credits": 110, "fuel": 90, "alloy": 45}},
            "Ethereal Haven": {"x": 2, "y": 8, "resources": {"credits": 70, "fuel": 40, "alloy": 25}},
            "Void Bastion": {"x": 12, "y": 12, "resources": {"credits": 150, "fuel": 100, "alloy": 60}},
            "Dark Nebula": {"x": 15, "y": 10, "resources": {"credits": 130, "fuel": 110, "alloy": 55}},
            "New Horizon": {"x": 6, "y": 6, "resources": {"credits": 95, "fuel": 65, "alloy": 38}}
        }

game_state = GameState()

# ============================================================================
# A* PATHFINDING ALGORITHM
# ============================================================================

def euclidean_distance(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """Heuristic function for A* - Euclidean distance"""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def a_star_pathfinding(start: str, goal: str, systems: Dict) -> Optional[List[str]]:
    """
    A* algorithm for optimal fleet navigation between star systems
    Returns the optimal path or None if no path exists
    """
    if start not in systems or goal not in systems:
        return None
    
    start_pos = (systems[start]["x"], systems[start]["y"])
    goal_pos = (systems[goal]["x"], systems[goal]["y"])
    
    # Priority queue: (f_score, g_score, current_node, path)
    open_set = [(euclidean_distance(start_pos, goal_pos), 0, start, [start])]
    closed_set = set()
    g_scores = {start: 0}
    
    while open_set:
        f_score, g_score, current, path = heapq.heappop(open_set)
        
        if current == goal:
            return path
        
        if current in closed_set:
            continue
        
        closed_set.add(current)
        current_pos = (systems[current]["x"], systems[current]["y"])
        
        # Generate neighbors (all systems within reasonable range)
        for neighbor, data in systems.items():
            if neighbor in closed_set:
                continue
            
            neighbor_pos = (data["x"], data["y"])
            distance = euclidean_distance(current_pos, neighbor_pos)
            
            # Only consider neighbors within jump range (simplified)
            if distance > 8:
                continue
            
            tentative_g = g_score + distance
            
            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g
                h_score = euclidean_distance(neighbor_pos, goal_pos)
                f = tentative_g + h_score
                heapq.heappush(open_set, (f, tentative_g, neighbor, path + [neighbor]))
    
    return None

# ============================================================================
# CONSTRAINT SATISFACTION PROBLEM (CSP)
# ============================================================================

class ResourceCSP:
    """
    CSP for resource allocation across colonies and fleets
    Variables: allocation amounts for each colony
    Domains: possible resource amounts
    Constraints: total resources available, minimum requirements
    """
    
    def __init__(self, total_resources: Dict[str, int], colonies: List[str], 
                 min_requirements: Dict[str, Dict[str, int]]):
        self.total_resources = total_resources
        self.colonies = colonies
        self.min_requirements = min_requirements
        self.allocation = {}
    
    def is_consistent(self, allocation: Dict) -> bool:
        """Check if allocation satisfies all constraints"""
        # Check minimum requirements
        for colony, resources in allocation.items():
            if colony in self.min_requirements:
                for resource_type, amount in self.min_requirements[colony].items():
                    if resources.get(resource_type, 0) < amount:
                        return False
        
        # Check total resource constraints
        total_used = {"credits": 0, "fuel": 0, "alloy": 0}
        for resources in allocation.values():
            for resource_type, amount in resources.items():
                total_used[resource_type] += amount
        
        for resource_type, amount in total_used.items():
            if amount > self.total_resources.get(resource_type, 0):
                return False
        
        return True
    
    def backtracking_search(self) -> Optional[Dict]:
        """Backtracking algorithm to find valid allocation"""
        return self._backtrack({})
    
    def _backtrack(self, allocation: Dict) -> Optional[Dict]:
        if len(allocation) == len(self.colonies):
            return allocation if self.is_consistent(allocation) else None
        
        # Select unassigned colony
        unassigned = [c for c in self.colonies if c not in allocation]
        if not unassigned:
            return None
        
        colony = unassigned[0]
        
        # Try different allocations (simplified domain)
        for credits in range(0, self.total_resources["credits"] + 1, 50):
            for fuel in range(0, self.total_resources["fuel"] + 1, 25):
                for alloy in range(0, self.total_resources["alloy"] + 1, 15):
                    allocation[colony] = {"credits": credits, "fuel": fuel, "alloy": alloy}
                    
                    if self.is_consistent(allocation):
                        result = self._backtrack(allocation.copy())
                        if result:
                            return result
        
        return None

# ============================================================================
# FUZZY LOGIC SYSTEM
# ============================================================================

class FuzzyLogicSystem:
    """
    Fuzzy logic for decision-making under uncertainty
    Handles trust assessment, threat evaluation, and diplomatic decisions
    """
    
    @staticmethod
    def fuzzify_trust(trust_value: float) -> Dict[str, float]:
        """Convert crisp trust value to fuzzy sets"""
        fuzzy_trust = {
            "very_low": max(0, min(1, (0.3 - trust_value) / 0.3)),
            "low": max(0, min(1 - abs(trust_value - 0.3) / 0.2, 0)),
            "medium": max(0, 1 - abs(trust_value - 0.5) / 0.2),
            "high": max(0, 1 - abs(trust_value - 0.7) / 0.2),
            "very_high": max(0, min(1, (trust_value - 0.7) / 0.3))
        }
        return fuzzy_trust
    
    @staticmethod
    def fuzzify_distance(distance: float) -> Dict[str, float]:
        """Convert distance to fuzzy sets (normalized 0-20)"""
        return {
            "very_close": max(0, min(1, (5 - distance) / 5)),
            "close": max(0, 1 - abs(distance - 7) / 3),
            "medium": max(0, 1 - abs(distance - 12) / 4),
            "far": max(0, min(1, (distance - 15) / 5))
        }
    
    @staticmethod
    def fuzzify_power(power: float) -> Dict[str, float]:
        """Convert power level to fuzzy sets"""
        return {
            "weak": max(0, min(1, (0.4 - power) / 0.4)),
            "moderate": max(0, 1 - abs(power - 0.5) / 0.2),
            "strong": max(0, min(1, (power - 0.6) / 0.4))
        }
    
    @staticmethod
    def evaluate_threat(trust: float, distance: float, power: float) -> float:
        """
        Fuzzy inference system to evaluate threat level
        Rules-based reasoning combining trust, distance, and power
        """
        trust_fuzzy = FuzzyLogicSystem.fuzzify_trust(trust)
        distance_fuzzy = FuzzyLogicSystem.fuzzify_distance(distance)
        power_fuzzy = FuzzyLogicSystem.fuzzify_power(power)
        
        # Rule base (simplified)
        threat_score = 0.0
        
        # High power + low trust + close distance = high threat
        threat_score += min(power_fuzzy["strong"], trust_fuzzy["very_low"], 
                           distance_fuzzy["very_close"]) * 0.9
        
        # High power + medium trust + close = medium threat
        threat_score += min(power_fuzzy["strong"], trust_fuzzy["medium"], 
                           distance_fuzzy["close"]) * 0.6
        
        # Low power + any trust = low threat
        threat_score += power_fuzzy["weak"] * 0.2
        
        # High trust + far distance = low threat
        threat_score += min(trust_fuzzy["very_high"], distance_fuzzy["far"]) * 0.1
        
        return min(1.0, threat_score)
    
    @staticmethod
    def suggest_diplomatic_action(trust: float, threat: float) -> str:
        """Suggest diplomatic action based on fuzzy reasoning"""
        if threat > 0.7:
            return "fortify_defenses"
        elif threat > 0.5:
            return "cautious_diplomacy"
        elif trust > 0.6:
            return "alliance_proposal"
        else:
            return "trade_agreement"

# ============================================================================
# ADVERSARIAL SEARCH (MINIMAX WITH ALPHA-BETA PRUNING)
# ============================================================================

class AdversarialSearch:
    """
    Minimax with alpha-beta pruning for AI empire strategic planning
    Evaluates multiple moves and counter-moves
    """
    
    @staticmethod
    def evaluate_state(state: Dict, player: str) -> float:
        """
        Evaluation function for game state
        Higher is better for the player
        """
        score = 0.0
        
        # Territory control
        score += len(state["controlled_systems"]) * 100
        
        # Resource strength
        score += sum(state["player_resources"].values()) * 0.5
        
        # Trust with empires
        score += sum(state["trust_levels"].values()) * 50
        
        # Threat penalty
        for empire, data in state["ai_empires"].items():
            threat = FuzzyLogicSystem.evaluate_threat(
                state["trust_levels"][empire],
                5.0,  # Simplified distance
                data["power"]
            )
            score -= threat * 30
        
        return score
    
    @staticmethod
    def get_possible_actions(state: Dict) -> List[str]:
        """Generate possible actions from current state"""
        actions = []
        
        # Expansion actions
        for system in state["star_systems"]:
            if system not in state["controlled_systems"]:
                actions.append(f"expand_{system}")
        
        # Diplomatic actions
        for empire in state["ai_empires"]:
            actions.append(f"negotiate_{empire}")
            actions.append(f"threaten_{empire}")
        
        # Resource actions
        actions.append("gather_resources")
        actions.append("fortify_defenses")
        
        return actions[:10]  # Limit for performance
    
    @staticmethod
    def minimax(state: Dict, depth: int, alpha: float, beta: float, 
                maximizing_player: bool) -> Tuple[float, Optional[str]]:
        """
        Minimax algorithm with alpha-beta pruning
        Returns (best_score, best_action)
        """
        if depth == 0:
            return AdversarialSearch.evaluate_state(state, "player"), None
        
        possible_actions = AdversarialSearch.get_possible_actions(state)
        
        if maximizing_player:
            max_eval = float('-inf')
            best_action = None
            
            for action in possible_actions:
                new_state = AdversarialSearch.apply_action(state.copy(), action)
                eval_score, _ = AdversarialSearch.minimax(
                    new_state, depth - 1, alpha, beta, False
                )
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_action = action
                
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Beta cutoff
            
            return max_eval, best_action
        else:
            min_eval = float('inf')
            best_action = None
            
            for action in possible_actions:
                new_state = AdversarialSearch.apply_action(state.copy(), action)
                eval_score, _ = AdversarialSearch.minimax(
                    new_state, depth - 1, alpha, beta, True
                )
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_action = action
                
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha cutoff
            
            return min_eval, best_action
    
    @staticmethod
    def apply_action(state: Dict, action: str) -> Dict:
        """Apply an action to state (simplified simulation)"""
        new_state = state.copy()
        
        if action.startswith("expand_"):
            system = action.replace("expand_", "")
            if system not in new_state["controlled_systems"]:
                new_state["controlled_systems"].append(system)
        
        elif action.startswith("negotiate_"):
            empire = action.replace("negotiate_", "")
            if empire in new_state["trust_levels"]:
                new_state["trust_levels"][empire] = min(1.0, 
                    new_state["trust_levels"][empire] + 0.1)
        
        return new_state

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/game/init', methods=['POST'])
def initialize_game():
    """Initialize a new game session"""
    global game_state
    data = request.json
    game_state.commander_name = data.get('commander_name', 'Commander')
    
    return jsonify({
        "success": True,
        "message": f"Welcome, {game_state.commander_name}. StarMind systems online.",
        "game_state": {
            "turn": game_state.current_turn,
            "resources": game_state.player_resources,
            "position": game_state.player_fleet_position,
            "controlled_systems": game_state.controlled_systems,
            "trust_levels": game_state.trust_levels
        }
    })

@app.route('/api/navigation/path', methods=['POST'])
def calculate_path():
    """Calculate optimal path using A* algorithm"""
    data = request.json
    start = data.get('start')
    goal = data.get('goal')
    
    path = a_star_pathfinding(start, goal, game_state.star_systems)
    
    if path:
        # Calculate fuel cost
        total_distance = 0
        for i in range(len(path) - 1):
            pos1 = (game_state.star_systems[path[i]]["x"], 
                   game_state.star_systems[path[i]]["y"])
            pos2 = (game_state.star_systems[path[i+1]]["x"], 
                   game_state.star_systems[path[i+1]]["y"])
            total_distance += euclidean_distance(pos1, pos2)
        
        fuel_cost = int(total_distance * 10)
        
        return jsonify({
            "success": True,
            "path": path,
            "distance": round(total_distance, 2),
            "fuel_cost": fuel_cost,
            "can_afford": game_state.player_resources["fuel"] >= fuel_cost
        })
    else:
        return jsonify({
            "success": False,
            "message": "No viable path found"
        })

@app.route('/api/resources/allocate', methods=['POST'])
def allocate_resources():
    """Solve CSP for resource allocation"""
    data = request.json
    colonies = data.get('colonies', game_state.controlled_systems)
    
    # Define minimum requirements for each colony
    min_requirements = {colony: {"credits": 20, "fuel": 10, "alloy": 5} 
                       for colony in colonies}
    
    csp = ResourceCSP(game_state.player_resources, colonies, min_requirements)
    allocation = csp.backtracking_search()
    
    if allocation:
        return jsonify({
            "success": True,
            "allocation": allocation,
            "message": "Optimal resource allocation computed"
        })
    else:
        return jsonify({
            "success": False,
            "message": "Cannot satisfy resource constraints"
        })

@app.route('/api/diplomacy/analyze', methods=['POST'])
def analyze_diplomacy():
    """Use fuzzy logic to analyze diplomatic situation"""
    data = request.json
    empire_name = data.get('empire')
    
    if empire_name not in game_state.ai_empires:
        return jsonify({"success": False, "message": "Empire not found"})
    
    empire = game_state.ai_empires[empire_name]
    trust = game_state.trust_levels[empire_name]
    
    # Calculate distance from player position to empire's primary system
    player_pos = (game_state.star_systems[game_state.player_fleet_position]["x"],
                  game_state.star_systems[game_state.player_fleet_position]["y"])
    empire_system = empire["systems"][0]
    empire_pos = (game_state.star_systems[empire_system]["x"],
                  game_state.star_systems[empire_system]["y"])
    distance = euclidean_distance(player_pos, empire_pos)
    
    # Evaluate threat
    threat = FuzzyLogicSystem.evaluate_threat(trust, distance, empire["power"])
    
    # Get recommendation
    action = FuzzyLogicSystem.suggest_diplomatic_action(trust, threat)
    
    # Generate trust fuzzy sets for detailed analysis
    trust_fuzzy = FuzzyLogicSystem.fuzzify_trust(trust)
    
    return jsonify({
        "success": True,
        "empire": empire_name,
        "analysis": {
            "trust_level": trust,
            "trust_category": max(trust_fuzzy, key=trust_fuzzy.get),
            "distance": round(distance, 2),
            "power_level": empire["power"],
            "threat_level": round(threat, 2),
            "recommended_action": action,
            "hostility": empire["hostility"]
        }
    })

@app.route('/api/strategy/ai_move', methods=['POST'])
def compute_ai_move():
    """Use adversarial search to compute AI empire's move"""
    data = request.json
    empire_name = data.get('empire')
    
    # Prepare state dictionary for minimax
    state_dict = {
        "controlled_systems": game_state.controlled_systems.copy(),
        "player_resources": game_state.player_resources.copy(),
        "trust_levels": game_state.trust_levels.copy(),
        "ai_empires": game_state.ai_empires.copy(),
        "star_systems": game_state.star_systems
    }
    
    # Compute best move using minimax (depth 2 for performance)
    score, action = AdversarialSearch.minimax(
        state_dict, depth=2, alpha=float('-inf'), 
        beta=float('inf'), maximizing_player=False
    )
    
    return jsonify({
        "success": True,
        "empire": empire_name,
        "action": action,
        "confidence": min(1.0, abs(score) / 100)
    })

@app.route('/api/game/status', methods=['GET'])
def game_status():
    """Get current game state"""
    # Calculate overall threat level
    total_threat = 0
    for empire, data in game_state.ai_empires.items():
        trust = game_state.trust_levels[empire]
        threat = FuzzyLogicSystem.evaluate_threat(trust, 5.0, data["power"])
        total_threat += threat
    
    avg_threat = total_threat / len(game_state.ai_empires)
    
    return jsonify({
        "success": True,
        "turn": game_state.current_turn,
        "commander": game_state.commander_name,
        "resources": game_state.player_resources,
        "position": game_state.player_fleet_position,
        "controlled_systems": game_state.controlled_systems,
        "trust_levels": game_state.trust_levels,
        "ai_empires": game_state.ai_empires,
        "star_systems": game_state.star_systems,
        "overall_threat": round(avg_threat, 2)
    })

@app.route('/api/game/action', methods=['POST'])
def perform_action():
    """Execute player action and advance game state"""
    data = request.json
    action_type = data.get('type')
    
    response = {"success": False, "message": "Unknown action"}
    
    if action_type == "move_fleet":
        target = data.get('target')
        path = a_star_pathfinding(game_state.player_fleet_position, target, 
                                  game_state.star_systems)
        if path and len(path) > 1:
            game_state.player_fleet_position = path[1]  # Move one step
            response = {
                "success": True,
                "message": f"Fleet moved to {path[1]}",
                "new_position": path[1]
            }
    
    elif action_type == "colonize":
        system = data.get('system')
        cost = {"credits": 200, "fuel": 100, "alloy": 50}
        
        if all(game_state.player_resources[r] >= cost[r] for r in cost):
            game_state.controlled_systems.append(system)
            for r in cost:
                game_state.player_resources[r] -= cost[r]
            response = {
                "success": True,
                "message": f"Successfully colonized {system}",
                "new_resources": game_state.player_resources
            }
        else:
            response = {"success": False, "message": "Insufficient resources"}
    
    elif action_type == "negotiate":
        empire = data.get('empire')
        if empire in game_state.trust_levels:
            # Negotiation increases trust
            game_state.trust_levels[empire] = min(1.0, 
                game_state.trust_levels[empire] + 0.15)
            response = {
                "success": True,
                "message": f"Diplomatic relations with {empire} improved",
                "new_trust": game_state.trust_levels[empire]
            }
    
    game_state.current_turn += 1
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)



   

