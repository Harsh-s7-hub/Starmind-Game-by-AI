# iaatcms_simulation_atc.py
# Intelligent Airport & ATC Management (Advanced Simulation - Option B)
# Single-file program. Requires Python 3.8+. Optional: matplotlib for dashboard.
#
# Features:
#  - Animated approach, holding patterns, landing approval dialog
#  - CSP runway/gate assignment (auto, with override)
#  - Fuzzy priority
#  - A* taxi planner and taxi animation
#  - Runway occupancy and separation
#  - Knowledge Graph view
#  - Live analytics dashboard (matplotlib)
#
# Author: ChatGPT (customized for your rubric)
# ------------------------------------------------------------------------------------

import math, heapq, random, time
from copy import deepcopy
from typing import List, Tuple, Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

# Optional matplotlib (only needed for dashboard). If missing, dashboard button disabled.
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# ----------------------------
# Airport Knowledge Graph (semantic)
# ----------------------------
AIRPORT = {
    "name": "SimCity Intl",
    "runways": {
        "RWY09L": {"length": 4000, "type": "all"},
        "RWY09R": {"length": 3000, "type": "medium"},
    },
    "gates": {
        "G1": {"size": "large"}, "G2": {"size": "large"},
        "G3": {"size": "medium"}, "G4": {"size": "medium"},
        "G5": {"size": "small"}, "G6": {"size": "small"},
    },
    # Simple taxiway node graph coordinates for A* + visualization
    "taxi_nodes": {
        "T_A": {"coord": (120, 300), "adj": ["T_B", "RWY09L_exit"]},
        "T_B": {"coord": (250, 300), "adj": ["T_A", "T_C", "G1_entry"]},
        "T_C": {"coord": (380, 300), "adj": ["T_B", "T_D", "G3_entry"]},
        "T_D": {"coord": (510, 300), "adj": ["T_C", "RWY09R_exit", "G4_entry"]},
        "RWY09L_exit": {"coord": (120, 220), "adj": ["T_A"]},
        "RWY09R_exit": {"coord": (510, 220), "adj": ["T_D"]},
        "G1_entry": {"coord": (250, 360), "adj": ["T_B"]},
        "G3_entry": {"coord": (380, 360), "adj": ["T_C"]},
        "G4_entry": {"coord": (510, 360), "adj": ["T_D"]},
    },
    "gate_node_map": {
        "G1": "G1_entry", "G2": "G1_entry",
        "G3": "G3_entry", "G4": "G4_entry",
        "G5": "G3_entry", "G6": "G4_entry"
    },
    "gate_capacity": {
        "large": ["A380", "B747", "B777", "A330"],
        "medium": ["A320", "B737", "E190"],
        "small": ["Turboprop", "Regional"],
    },
    "semantic_relations": [
        ("RWY09L", "connected_to", "T_A"),
        ("G1", "entry_node", "G1_entry"),
        ("large_gate", "supports", "A380,B747,..."),
    ]
}

# ----------------------------
# Simulation constants
# ----------------------------
CANVAS_W = 900
CANVAS_H = 600
PLANE_SIZE = 10
APPROACH_ALTITUDE = 1000  # arbitrary units
HOLD_RADIUS = 40
RUNWAY_SEPARATION_SLOTS = 1  # discrete separation for CSP
TAXI_SPEED = 1  # nodes per tick
APPROACH_SPEED = 4  # pixels per tick
ANIMATION_INTERVAL_MS = 120  # GUI tick

# ----------------------------
# Utility functions
# ----------------------------
def euclid(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    return math.hypot(a[0]-b[0], a[1]-b[1])

def clamp(x, a, b): return max(a, min(b, x))

# ----------------------------
# Fuzzy priority module (fuel, weather, emergency)
# ----------------------------
def tri(x, a, b, c):
    if a == b:
        if x <= a: return 1.0 if x == a else 0.0
    if x <= a or x >= c: return 0.0
    if x == b: return 1.0
    if x < b: return (x-a)/(b-a)
    return (c-x)/(c-b)

def fuzzy_priority_score(fuel_percent: float, weather_severity: float, emergency: bool) -> float:
    if emergency: return 1.0
    fuel = clamp(fuel_percent/100.0, 0.0, 1.0)
    inv_fuel = 1.0 - fuel
    fuel_low = tri(inv_fuel, 0.6, 0.9, 1.0)
    fuel_med = tri(inv_fuel, 0.3, 0.5, 0.7)
    fuel_high = tri(inv_fuel, 0.0, 0.0, 0.4)
    w_poor = tri(weather_severity, 0.6, 0.8, 1.0)
    w_med = tri(weather_severity, 0.3, 0.5, 0.7)
    w_good = tri(weather_severity, 0.0, 0.1, 0.4)
    r_high = max(fuel_low, w_poor)
    r_med = max(min(fuel_med, w_med), min(fuel_low, w_med))
    r_low = max(fuel_high, w_good)
    numerator = r_low*0.1 + r_med*0.5 + r_high*0.9
    denom = max(1e-6, r_low + r_med + r_high)
    return clamp(numerator/denom, 0.0, 1.0)

# ----------------------------
# A* taxi planner (on taxi_nodes)
# ----------------------------
def a_star_taxi(start_node: str, goal_node: str, airport=AIRPORT, occupied=set()) -> Optional[List[str]]:
    nodes = airport["taxi_nodes"]
    if start_node not in nodes or goal_node not in nodes: return None
    def neighbors(n):
        for nb in nodes[n]["adj"]:
            if nb in occupied: continue
            yield nb
    def heuristic(n): return euclid(nodes[n]["coord"], nodes[goal_node]["coord"])
    openq = []
    heapq.heappush(openq, (heuristic(start_node), 0, start_node, [start_node]))
    gbest = {start_node: 0}
    visited = set()
    while openq:
        f, g, cur, path = heapq.heappop(openq)
        if cur == goal_node: return path
        if cur in visited: continue
        visited.add(cur)
        for nb in neighbors(cur):
            ng = g + euclid(nodes[cur]["coord"], nodes[nb]["coord"])
            if nb not in gbest or ng < gbest[nb]:
                gbest[nb] = ng
                heapq.heappush(openq, (ng + heuristic(nb), ng, nb, path + [nb]))
    return None

# ----------------------------
# CSP scheduler (runway/gate/slot) - backtracking
# ----------------------------
class CSP:
    def __init__(self, flights: List[Dict], runways: List[str], gates: List[str], separation_slots=RUNWAY_SEPARATION_SLOTS):
        self.flights = flights  # each flight has id, arrival_slot, type, priority
        self.runways = runways
        self.gates = gates
        self.sep = separation_slots
        self.domains = {}

    def setup_domains(self):
        for f in self.flights:
            dom = []
            # allow a small window for assignment after arrival slot
            for r in self.runways:
                for g in self.gates:
                    for slot in range(f["arrival_slot"], f["arrival_slot"] + 6):
                        dom.append((r, g, slot))
            dom.sort(key=lambda x: (abs(x[2] - f["arrival_slot"]), 0 if f["type"] in AIRPORT["gate_capacity"].get(AIRPORT["gates"][x[1]]["size"], []) else 1))
            self.domains[f["id"]] = dom

    def check_constraints(self, var, val, assignment):
        r, g, s = val
        f = next(filter(lambda x: x["id"]==var, self.flights))
        # gate compatibility
        gate_size = AIRPORT["gates"][g]["size"]
        allowed_types = AIRPORT["gate_capacity"].get(gate_size, [])
        if allowed_types and f["type"] not in allowed_types:
            return False
        for ov, ovval in assignment.items():
            orun, ogate, oslot = ovval
            # runway separation
            if orun == r and abs(oslot - s) < self.sep:
                return False
            # gate occupancy: need 2 slots
            if ogate == g and abs(oslot - s) < 2:
                return False
        return True

    def select_unassigned_var(self, assignment):
        unassigned = [f for f in self.flights if f["id"] not in assignment]
        # MRV heuristic: smallest domain
        unassigned.sort(key=lambda x: len(self.domains.get(x["id"], [])))
        return unassigned[0]["id"] if unassigned else None

    def backtrack(self, assignment):
        if len(assignment) == len(self.flights):
            return assignment
        var = self.select_unassigned_var(assignment)
        for val in self.domains.get(var, []):
            if self.check_constraints(var, val, assignment):
                assignment[var] = val
                res = self.backtrack(assignment)
                if res: return res
                del assignment[var]
        return None

    def solve(self):
        self.setup_domains()
        # order flights by priority descending to favor urgent flights
        self.flights.sort(key=lambda x: -x["priority"])
        sol = self.backtrack({})
        return sol

# ----------------------------
# Flight data structure & helpers
# ----------------------------
class Flight:
    def __init__(self, fid: str, arrival_slot: int, ftype: str, fuel: int, weather: float, emergency: bool):
        self.id = fid
        self.arrival_slot = arrival_slot
        self.type = ftype
        self.fuel = fuel
        self.weather = weather
        self.emergency = emergency
        self.priority = fuzzy_priority_score(fuel, weather, emergency)
        # position/visual
        # spawn point off-screen on approach vector (left or right)
        self.state = "enroute"  # enroute, approaching, holding, landing, landed, taxiing, at_gate, diverted
        self.alt = APPROACH_ALTITUDE
        self.approach_path = []  # list of (x,y) coords to follow
        self.pos = (0,0)
        self.canvas_id = None
        self.assigned = None  # (runway, gate, slot)
        self.taxi_path = None  # list of taxi node names
        self.taxi_index = 0

    def to_dict(self):
        return {"id":self.id,"arrival_slot":self.arrival_slot,"type":self.type,"fuel":self.fuel,"weather":self.weather,"emergency":self.emergency,"priority":self.priority}

# ----------------------------
# GUI & Simulation class
# ----------------------------
class IAATCSim:
    def __init__(self, root):
        self.root = root
        self.root.title("IAATCMS - Advanced Airport Simulation (Option B)")
        self.root.geometry("1200x760")
        self.canvas_w = CANVAS_W
        self.canvas_h = CANVAS_H

        # Simulation state
        self.flights: List[Flight] = []
        self.assignments: Dict[str, Tuple[str,str,int]] = {}
        self.routes: Dict[str, Optional[List[str]]] = {}
        self.occupied_runway_until: Dict[str, int] = {}  # runway -> slot until which occupied
        self.current_tick = 0  # discrete time slot counter
        self.auto_mode = False
        self.auto_job = None
        self.next_id = 1000

        # Build UI
        self.build_ui()
        # Draw static airport map
        self.draw_static_airport()
        # animation loop
        self.root.after(ANIMATION_INTERVAL_MS, self.animation_step)

    # ---------------- UI BUILD ----------------
    def build_ui(self):
        # Left controls
        left = ttk.Frame(self.root, padding=6)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="ATC Controls", font=("Arial", 14, "bold")).pack()
        ttk.Button(left, text="Load Sample Flights", command=self.load_sample).pack(fill="x", pady=3)
        ttk.Button(left, text="Generate Incoming Flight", command=self.generate_incoming).pack(fill="x", pady=3)
        self.auto_btn = ttk.Button(left, text="Start Auto Incoming", command=self.toggle_auto); self.auto_btn.pack(fill="x", pady=3)
        ttk.Button(left, text="Run Auto Scheduler (CSP)", command=self.run_csp_scheduler).pack(fill="x", pady=3)
        ttk.Button(left, text="Clear All Flights", command=self.clear_all).pack(fill="x", pady=3)
        if MATPLOTLIB_AVAILABLE:
            ttk.Button(left, text="Open Live Dashboard", command=self.open_dashboard).pack(fill="x", pady=6)
        else:
            ttk.Label(left, text="(Install matplotlib for dashboard)").pack(pady=6)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=6)
        ttk.Label(left, text="Managed Flights").pack(anchor="w")
        self.flight_listbox = tk.Listbox(left, width=36, height=18)
        self.flight_listbox.pack(pady=3)
        self.flight_listbox.bind("<<ListboxSelect>>", self.on_select_flight)

        ttk.Label(left, text="Log").pack(anchor="w")
        self.log_text = tk.Text(left, width=36, height=12)
        self.log_text.pack()

        # Center Canvas
        center = ttk.Frame(self.root)
        center.pack(side="left", fill="both", expand=True)
        ttk.Label(center, text="Airport Scene (Top-down)", font=("Arial", 14, "bold")).pack()
        self.canvas = tk.Canvas(center, width=self.canvas_w, height=self.canvas_h, bg="#e6f2ff")
        self.canvas.pack(fill="both", expand=True)

        # Right panels: dashboard & KG & controls
        right = ttk.Frame(self.root, padding=6)
        right.pack(side="right", fill="y")
        ttk.Label(right, text="Flight Dashboard", font=("Arial", 14, "bold")).pack()
        self.dashboard = tk.Text(right, width=40, height=12)
        self.dashboard.pack(pady=4)
        ttk.Label(right, text="Knowledge Graph", font=("Arial", 14, "bold")).pack(pady=(8,0))
        self.kg_text = tk.Text(right, width=40, height=14)
        self.kg_text.pack()
        self.populate_kg()

    # ---------------- static airport drawing ----------------
    def draw_static_airport(self):
        c = self.canvas
        c.delete("all")
        # draw runways as rectangles
        # RWY09L left, RWY09R right
        c.create_rectangle(80, 50, 320, 100, fill="#888", outline="black", tags="rwy")
        c.create_text(200, 75, text="RWY09L", fill="white", font=("Arial",10,"bold"))
        c.create_rectangle(480, 50, 720, 100, fill="#777", outline="black", tags="rwy")
        c.create_text(600, 75, text="RWY09R", fill="white", font=("Arial",10,"bold"))
        # taxi nodes and links
        for node, data in AIRPORT["taxi_nodes"].items():
            x,y = data["coord"]
            for nb in data["adj"]:
                if nb in AIRPORT["taxi_nodes"]:
                    x2,y2 = AIRPORT["taxi_nodes"][nb]["coord"]
                    c.create_line(x,y,x2,y2, fill="#333", width=2)
        # nodes
        for node, data in AIRPORT["taxi_nodes"].items():
            x,y = data["coord"]
            color = "lightgray"
            if node.endswith("_exit"): color="orange"
            if node.endswith("_entry"): color="lightblue"
            c.create_oval(x-8,y-8,x+8,y+8, fill=color, outline="black", tags=("node",node))
            c.create_text(x, y-14, text=node, font=("Arial",8))
        # gates and legend
        c.create_text(60, 140, text="Gates:", anchor="w", font=("Arial",10,"bold"))
        idx = 0
        for g, v in AIRPORT["gates"].items():
            c.create_text(60, 160 + idx*14, text=f"{g} ({v['size']})", anchor="w")
            idx += 1

    # ---------------- flight control methods ----------------
    def load_sample(self):
        # create a few incoming flights with approach paths
        sample = [
            Flight("AAL101", arrival_slot=2, ftype="A320", fuel=30, weather=0.2, emergency=False),
            Flight("DAL202", arrival_slot=1, ftype="B737", fuel=12, weather=0.3, emergency=True),
            Flight("UAL303", arrival_slot=3, ftype="A330", fuel=55, weather=0.6, emergency=False),
            Flight("SWA404", arrival_slot=2, ftype="Turboprop", fuel=70, weather=0.1, emergency=False),
        ]
        for f in sample:
            self.prepare_approach_for(f)
            self.flights.append(f)
        self.log("Loaded sample flights.")
        self.refresh_flight_list()

    def generate_incoming(self):
        fid = f"FL{self.next_id}"
        self.next_id += 1
        typ = random.choice(["A320","B737","A330","Turboprop"])
        fuel = random.randint(8,90)
        weather = round(random.random(), 2)
        emergency = random.random() < 0.12
        slot = max(0, self.current_tick + random.randint(1,4))
        f = Flight(fid, slot, typ, fuel, weather, emergency)
        self.prepare_approach_for(f)
        self.flights.append(f)
        self.log(f"Generated incoming {fid}")
        self.refresh_flight_list()

    def prepare_approach_for(self, f: Flight):
        # choose approach side based on runway selected randomly (simulate different approach vectors)
        # We'll create a smooth path of coords from offscreen to runway threshold
        side = random.choice(["left","right"])
        if side == "left":
            # start left off-canvas
            start = (-80, 60 + random.randint(0,40))
            runway_threshold = (200, 50 + 25)  # middle of RWY09L top
        else:
            start = (CANVAS_W + 80, 60 + random.randint(0,40))
            runway_threshold = (600, 50 + 25)
        # simple quadratic approach path: from start -> mid_point -> threshold
        midx = (start[0] + runway_threshold[0]) / 2
        midy = (start[1] + runway_threshold[1]) / 2 + 80  # curve
        path = []
        steps = 80
        for t in range(steps+1):
            s = t/steps
            # quadratic Bezier
            x = (1-s)**2 * start[0] + 2*(1-s)*s * midx + s**2 * runway_threshold[0]
            y = (1-s)**2 * start[1] + 2*(1-s)*s * midy + s**2 * runway_threshold[1]
            path.append((x,y))
        f.approach_path = path
        f.pos = path[0]
        f.state = "approaching"
        # precompute canvas id placeholder (will be created)
        f.canvas_id = None

    def refresh_flight_list(self):
        self.flight_listbox.delete(0, tk.END)
        for f in self.flights:
            tag = ""
            if f.emergency: tag = " | EMERGENCY"
            self.flight_listbox.insert(tk.END, f"{f.id} | {f.type} | fuel:{f.fuel}% | pr:{f.priority:.2f}{tag}")

    def clear_all(self):
        self.flights.clear(); self.assignments.clear(); self.routes.clear()
        self.occupied_runway_until.clear(); self.canvas.delete("flight")
        self.refresh_flight_list(); self.log("Cleared all flights.")

    # ---------------- CSP scheduler & assignment ----------------
    def run_csp_scheduler(self):
        # Build flight objects list for CSP (convert to dicts)
        flights_data = [f.to_dict() for f in self.flights if f.state in ("approaching","holding","enroute")]
        if not flights_data:
            self.log("No pending flights to schedule.")
            return
        csp = CSP(flights_data, list(AIRPORT["runways"].keys()), list(AIRPORT["gates"].keys()))
        sol = csp.solve()
        if not sol:
            self.log("CSP: no feasible assignment found.")
            return
        # apply assignments to flight objects
        self.assignments.clear(); self.routes.clear()
        for fid, val in sol.items():
            r,g,s = val
            self.assignments[fid] = val
            # find flight object
            fo = next((x for x in self.flights if x.id == fid), None)
            if fo:
                fo.assigned = (r,g,s)
                # compute taxi route once landed
                # determine runway exit node name (we use RWY09L_exit etc.)
                exit_node = r + "_exit"
                gate_node = AIRPORT["gate_node_map"][g]
                path = a_star_taxi(exit_node, gate_node, AIRPORT, occupied=set())
                fo.taxi_path = path
        self.log("CSP: assignments created.")
        self.refresh_flight_list()
        self.update_dashboard_text()

    # ---------------- Approvals UI ----------------
    def ask_for_landing_clearance(self, f: Flight, runway_name: str):
        # Popup with Grant / Delay / Divert options. This is run in main thread (Tkinter).
        # Build message
        msg = f"Flight {f.id} ({f.type}) requesting landing on {runway_name}.\nFuel: {f.fuel}%  Weather: {f.weather}  Priority: {f.priority:.2f}\n\nChoose action:"
        # If emergency, preselect Grant
        if f.emergency:
            response = messagebox.askyesno("Landing Request - EMERGENCY", msg + "\n\nGrant landing? (Yes = Grant, No = Divert)")
            return "grant" if response else "divert"
        # Otherwise custom dialog
        dlg = LandingDecisionDialog(self.root, title=f"Landing request: {f.id}", message=msg)
        self.root.wait_window(dlg.top)
        return dlg.result  # 'grant'/'delay'/'divert' or None

    # ---------------- animation step (main loop) ----------------
    def animation_step(self):
        # advance simulation tick
        self.current_tick += 1
        # animate flights
        self.canvas.delete("flight")
        for f in list(self.flights):
            if f.state == "approaching":
                # move along approach path
                if len(f.approach_path) > 1:
                    # pop next position by speed
                    # find current index in path (closest)
                    # simpler: advance by fixed increment (APPROACH_SPEED)
                    # compute index based on distance traveled approx.
                    if not hasattr(f, "_app_index"):
                        f._app_index = 0
                    f._app_index = min(len(f.approach_path)-1, f._app_index + 1)
                    f.pos = f.approach_path[f._app_index]
                    # if near runway threshold (last 12 steps), request landing clearance
                    if f._app_index >= len(f.approach_path) - 12:
                        # select intended runway (closest)
                        # compute nearest runway center
                        rcoords = {"RWY09L": (200,75), "RWY09R": (600,75)}
                        # choose runway by nearest threshold
                        dists = {r: euclid(f.pos, rc) for r,rc in rcoords.items()}
                        chosen = min(dists, key=dists.get)
                        # Check runway availability (occupied_until)
                        until = self.occupied_runway_until.get(chosen, 0)
                        if self.current_tick <= until:
                            # runway busy => hold
                            # move to holding pattern state (circle near holding point)
                            f.state = "holding"
                            f.hold_center = (f.pos[0], f.pos[1] - 60)
                            f.hold_angle = 0
                            self.log(f"{f.id} entering hold due to busy {chosen}")
                        else:
                            # request clearance:
                            decision = self.ask_for_landing_clearance(f, chosen)
                            if decision == "grant":
                                self.log(f"{f.id} cleared to land on {chosen}")
                                f.state = "landing"
                                f.landing_runway = chosen
                                # occupy runway for separation time slots
                                self.occupied_runway_until[chosen] = self.current_tick + 3  # simple occupancy
                            elif decision == "delay":
                                f.state = "holding"
                                f.hold_center = (f.pos[0], f.pos[1] - 80)
                                f.hold_angle = 0
                                self.log(f"{f.id} instructed to hold")
                            elif decision == "divert":
                                f.state = "diverted"
                                self.log(f"{f.id} diverted by ATC")
                            else:
                                # if closed dialog, treat as hold
                                f.state = "holding"; f.hold_center = (f.pos[0], f.pos[1]-80); f.hold_angle = 0
                else:
                    # no approach path, go holding
                    f.state = "holding"
            elif f.state == "holding":
                # circle around hold_center
                if not hasattr(f, "hold_angle"):
                    f.hold_angle = 0
                f.hold_angle = (f.hold_angle + 25) % 360
                cx, cy = f.hold_center
                rad = HOLD_RADIUS
                ang = math.radians(f.hold_angle)
                f.pos = (cx + rad * math.cos(ang), cy + rad * math.sin(ang))
                # randomly re-request landing occasionally
                if random.random() < 0.02:
                    # pick nearest runway
                    rcoords = {"RWY09L": (200,75), "RWY09R": (600,75)}
                    chosen = min(rcoords.keys(), key=lambda r: euclid(f.pos, rcoords[r]))
                    if self.current_tick > self.occupied_runway_until.get(chosen,0):
                        decision = self.ask_for_landing_clearance(f, chosen)
                        if decision == "grant":
                            f.state = "landing"; f.landing_runway = chosen; self.occupied_runway_until[chosen] = self.current_tick + 3
                        elif decision == "divert":
                            f.state = "diverted"
            elif f.state == "landing":
                # animate down along final approach (move to runway center)
                # simple: move towards runway center point
                rcoords = {"RWY09L": (200,75), "RWY09R": (600,75)}
                target = rcoords.get(f.landing_runway, (200,75))
                # step towards
                dx = target[0] - f.pos[0]; dy = target[1] - f.pos[1]
                dist = math.hypot(dx,dy)
                if dist < 6:
                    # landed
                    f.state = "landed"
                    f.pos = target
                    f.alt = 0
                    self.log(f"{f.id} has landed on {f.landing_runway}")
                    # assign gate if assigned earlier; otherwise schedule later
                    if f.assigned:
                        pass
                    # compute taxi path now
                    if f.assigned:
                        r,g,s = f.assigned
                        exit_node = r + "_exit"
                        gate_node = AIRPORT["gate_node_map"][g]
                        f.taxi_path = a_star_taxi(exit_node, gate_node, AIRPORT, occupied=set())
                        if f.taxi_path:
                            f.taxi_index = 0
                            f.state = "taxiing"
                            self.log(f"{f.id} taxiing to {g}")
                    else:
                        # if no assignment, run CSP again to assign waiting flights
                        self.run_csp_scheduler()
                        # if now assigned, set taxi
                        fo = next((x for x in self.flights if x.id == f.id), None)
                        if fo and fo.assigned:
                            r,g,s = fo.assigned
                            exit_node = r + "_exit"; gate_node = AIRPORT["gate_node_map"][g]
                            fo.taxi_path = a_star_taxi(exit_node, gate_node, AIRPORT, occupied=set())
                            if fo.taxi_path: fo.taxi_index = 0; fo.state = "taxiing"
                else:
                    step = min(APPROACH_SPEED, dist)
                    f.pos = (f.pos[0] + dx/dist*step, f.pos[1] + dy/dist*step)
            elif f.state == "taxiing":
                if not f.taxi_path:
                    # no route, finished
                    f.state = "at_gate"
                else:
                    idx = getattr(f, "taxi_index", 0)
                    if idx >= len(f.taxi_path):
                        f.state = "at_gate"
                        self.log(f"{f.id} reached gate.")
                    else:
                        node = f.taxi_path[idx]
                        if node in AIRPORT["taxi_nodes"]:
                            f.pos = AIRPORT["taxi_nodes"][node]["coord"]
                        f.taxi_index = idx + TAXI_SPEED
            elif f.state == "diverted":
                # animate leaving to off-screen
                f.pos = (f.pos[0] + (random.choice([-1,1]) * 20), f.pos[1] - 10)
                if f.pos[0] < -200 or f.pos[0] > CANVAS_W + 200:
                    # remove
                    self.log(f"{f.id} has diverted and left the airspace.")
                    try: self.flights.remove(f)
                    except: pass
                    continue
            elif f.state == "landed":
                # shortly transition to taxiing automatically if taxi path exists
                if f.taxi_path:
                    f.state = "taxiing"
                    f.taxi_index = 0
            # draw plane
            x,y = f.pos
            plane_col = "red" if f.emergency else "black"
            # size scaled by priority
            sz = PLANE_SIZE + int(6 * f.priority)
            f.canvas_id = self.canvas.create_oval(x-sz, y-sz, x+sz, y+sz, fill=plane_col, tags=("flight", f.id))
            self.canvas.create_text(x, y - sz - 8, text=f.id, font=("Arial", 8), tags="flight")
            # small label with state
            self.canvas.create_text(x, y + sz + 8, text=f.state, font=("Arial", 7), tags="flight")
        # increment world time
        self.current_tick += 1
        # schedule next tick
        self.root.after(ANIMATION_INTERVAL_MS, self.animation_step)

    # ---------------- user select flight ----------------
    def on_select_flight(self, evt):
        sel = self.flight_listbox.curselection()
        if not sel: return
        idx = sel[0]; f = self.flights[idx]
        # show dashboard info
        self.update_dashboard_for(f)

    def update_dashboard_for(self, f: Flight):
        self.dashboard.delete("1.0", tk.END)
        self.dashboard.insert(tk.END, f"Flight: {f.id}\nType: {f.type}\nFuel: {f.fuel}%\nWeather: {f.weather}\nPriority: {f.priority:.2f}\nState: {f.state}\n")
        if f.assigned:
            r,g,s = f.assigned
            self.dashboard.insert(tk.END, f"\nAssigned: {r} / {g} @ slot {s}\n")
        if f.taxi_path:
            self.dashboard.insert(tk.END, f"\nTaxi path: {' -> '.join(f.taxi_path)}\n")

    # ---------------- small UI helpers ----------------
    def log(self, text: str):
        ts = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {text}\n")
        self.log_text.see(tk.END)

    def update_dashboard_text(self):
        self.dashboard.delete("1.0", tk.END)
        self.dashboard.insert(tk.END, f"Time tick: {self.current_tick}\nFlights: {len(self.flights)}\nAssigned: {len(self.assignments)}\n")
        # list scheduled runways
        for fid, (r,g,s) in self.assignments.items():
            self.dashboard.insert(tk.END, f"{fid}: {r}/{g}@{s}\n")

    # ---------------- auto incoming ----------------
    def toggle_auto(self):
        if not self.auto_mode:
            self.auto_mode = True; self.auto_btn.config(text="Stop Auto Incoming")
            self.schedule_auto()
            self.log("Auto incoming started.")
        else:
            self.auto_mode = False; self.auto_btn.config(text="Start Auto Incoming")
            if self.auto_job: self.root.after_cancel(self.auto_job); self.auto_job = None
            self.log("Auto incoming stopped.")

    def schedule_auto(self):
        if not self.auto_mode: return
        self.auto_job = self.root.after(4000, self.auto_incoming)

    def auto_incoming(self):
        # generate a new flight periodically
        self.generate_incoming()
        # occasionally auto-run scheduler
        if random.random() < 0.6:
            self.run_csp_scheduler()
        self.schedule_auto()

    # ---------------- knowledge graph viewer ----------------
    def populate_kg(self):
        self.kg_text.delete("1.0", tk.END)
        self.kg_text.insert(tk.END, f"Airport: {AIRPORT['name']}\n\nRunways:\n")
        for r,v in AIRPORT["runways"].items():
            self.kg_text.insert(tk.END, f"  - {r} : length={v['length']} type={v['type']}\n")
        self.kg_text.insert(tk.END, "\nGates:\n")
        for g,v in AIRPORT["gates"].items():
            self.kg_text.insert(tk.END, f"  - {g} : size={v['size']}\n")
        self.kg_text.insert(tk.END, "\nTaxi Nodes:\n")
        for n,v in AIRPORT["taxi_nodes"].items():
            self.kg_text.insert(tk.END, f"  - {n} -> {', '.join(v['adj'])}\n")
        self.kg_text.insert(tk.END, "\nSemantic relations:\n")
        for a,b,c in AIRPORT["semantic_relations"]:
            self.kg_text.insert(tk.END, f"  - {a} --{b}--> {c}\n")

    # ---------------- Live Dashboard (matplotlib) ----------------
    def open_dashboard(self):
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showerror("Missing", "matplotlib not installed. Install via pip to use dashboard.")
            return
        LiveDashboard(self.root, self)

# ----------------------------
# Landing decision popup (custom dialog)
# ----------------------------
class LandingDecisionDialog:
    def __init__(self, parent, title="Landing Decision", message="Decision?"):
        top = self.top = tk.Toplevel(parent)
        top.title(title)
        top.grab_set()
        tk.Label(top, text=message, justify="left", wraplength=400).pack(padx=10, pady=8)
        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=6)
        ttk.Button(btn_frame, text="Grant", command=self.grant).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Delay (Hold)", command=self.delay).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Divert", command=self.divert).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side="left", padx=6)
        self.result = None

    def grant(self): self.result = "grant"; self.top.destroy()
    def delay(self): self.result = "delay"; self.top.destroy()
    def divert(self): self.result = "divert"; self.top.destroy()
    def cancel(self): self.result = None; self.top.destroy()

# ----------------------------
# Live Dashboard class (matplotlib)
# ----------------------------
if MATPLOTLIB_AVAILABLE:
    class LiveDashboard:
        def __init__(self, parent, sim: IAATCSim):
            self.sim = sim
            self.root = tk.Toplevel(parent)
            self.root.title("IAATCMS - Live Analytics Dashboard")
            self.root.geometry("1100x700")
            self.fig = Figure(figsize=(11,7), dpi=100)
            self.ax1 = self.fig.add_subplot(231)
            self.ax2 = self.fig.add_subplot(232)
            self.ax3 = self.fig.add_subplot(233)
            self.ax4 = self.fig.add_subplot(234)
            self.ax5 = self.fig.add_subplot(235)
            self.ax6 = self.fig.add_subplot(236)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self.update_interval = 1500
            self.update_loop()

        def update_loop(self):
            flights = self.sim.flights
            self.ax1.clear(); self.ax2.clear(); self.ax3.clear(); self.ax4.clear(); self.ax5.clear(); self.ax6.clear()
            if flights:
                ids = [f.id for f in flights]
                priorities = [f.priority for f in flights]
                self.ax1.bar(ids, priorities); self.ax1.set_title("Priority Scores")
                last = flights[-10:]
                lx = [f.id for f in last]; fuels=[f.fuel for f in last]; we=[f.weather for f in last]
                self.ax2.plot(lx, fuels, marker="o"); self.ax2.set_title("Fuel (last 10)")
                self.ax3.plot(lx, we, marker="o", color="orange"); self.ax3.set_ylim(0,1); self.ax3.set_title("Weather severity")
                # runway usage
                if self.sim.assignments:
                    runs = [v[0] for v in self.sim.assignments.values()]
                    from collections import Counter
                    cnt = Counter(runs)
                    self.ax4.bar(cnt.keys(), cnt.values()); self.ax4.set_title("Runway usage")
                    gates = [v[1] for v in self.sim.assignments.values()]
                    gcnt = Counter(gates)
                    self.ax5.bar(gcnt.keys(), gcnt.values()); self.ax5.set_title("Gate occupancy")
                else:
                    self.ax4.text(0.2,0.5,"No assignment")
                    self.ax5.text(0.2,0.5,"No assignment")
                ecount = sum(1 for f in flights if f.emergency); ne = len(flights)-ecount
                self.ax6.pie([ecount, ne], labels=["Emergency","Normal"], autopct='%1.1f%%'); self.ax6.set_title("Emergency ratio")
            else:
                for ax in (self.ax1,self.ax2,self.ax3,self.ax4,self.ax5,self.ax6):
                    ax.text(0.5,0.5,"No data", ha='center')
            self.canvas.draw()
            self.root.after(self.update_interval, self.update_loop)

# ----------------------------
# Run the app
# ----------------------------
def main():
    root = tk.Tk()
    sim = IAATCSim(root)
    root.mainloop()

if __name__ == "__main__":
    main()
