# iaatcms_gui.py
# Intelligent Airport & ATC Management System with Tkinter GUI
# Includes:
#   - Fuzzy Logic Priority Engine
#   - A* Taxi Route Planning
#   - CSP Gate/Runway/Slot Assignment
#   - Knowledge Graph
#   - Tkinter GUI Visualization
#
# Python 3.8+ required, NO external libraries needed.

import math
import heapq
import random
from copy import deepcopy
from typing import List, Tuple, Optional
import tkinter as tk
from tkinter import ttk, messagebox

# ------------------------------------------------------------
# 1. KNOWLEDGE GRAPH (Airport layout, gates, runways, taxiways)
# ------------------------------------------------------------

AIRPORT = {
    "runways": {
        "R1": {"length": 4000, "type": "all"},
        "R2": {"length": 3000, "type": "medium"},
    },

    "gates": {
        "G1": {"size": "large"},
        "G2": {"size": "large"},
        "G3": {"size": "medium"},
        "G4": {"size": "medium"},
        "G5": {"size": "small"},
        "G6": {"size": "small"},
    },

    "taxi_nodes": {
        "T1": {"coord": (50, 150), "adj": ["T2", "R1_exit"]},
        "T2": {"coord": (150, 150), "adj": ["T1", "T3", "G1_entry"]},
        "T3": {"coord": (250, 150), "adj": ["T2", "T4", "G3_entry"]},
        "T4": {"coord": (350, 150), "adj": ["T3", "R2_exit", "G4_entry"]},

        "R1_exit": {"coord": (50, 50), "adj": ["T1"]},
        "R2_exit": {"coord": (350, 50), "adj": ["T4"]},

        "G1_entry": {"coord": (150, 250), "adj": ["T2"]},
        "G3_entry": {"coord": (250, 250), "adj": ["T3"]},
        "G4_entry": {"coord": (350, 250), "adj": ["T4"]},
    },

    "gate_node_map": {
        "G1": "G1_entry",
        "G2": "G1_entry",
        "G3": "G3_entry",
        "G4": "G4_entry",
        "G5": "G3_entry",
        "G6": "G4_entry",
    },

    "gate_capacity": {
        "large": ["A380", "B747", "B777", "A330"],
        "medium": ["A320", "B737", "E190"],
        "small": ["Turboprop", "Regional"],
    },
}

# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------
def euclid(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


# ------------------------------------------------------------
# 2. FUZZY LOGIC: Landing Priority
# ------------------------------------------------------------

def tri(x, a, b, c):
    if a == b:
        return 1.0 if x == a else 0.0
    if x <= a or x >= c: return 0.0
    if x == b: return 1.0
    if x < b: return (x-a)/(b-a)
    return (c-x)/(c-b)

def fuzzy_priority_score(fuel_percent, weather_severity, emergency):
    if emergency:
        return 1.0

    fuel = max(0, min(100, fuel_percent)) / 100
    inv_fuel = 1 - fuel

    fuel_low = tri(inv_fuel, 0.6, 0.9, 1.0)
    fuel_med = tri(inv_fuel, 0.3, 0.5, 0.7)
    fuel_high = tri(inv_fuel, 0.0, 0.0, 0.4)

    w_poor = tri(weather_severity, 0.6, 0.8, 1.0)
    w_med  = tri(weather_severity, 0.3, 0.5, 0.7)
    w_good = tri(weather_severity, 0.0, 0.1, 0.4)

    r_high = max(fuel_low, w_poor)
    r_med  = max(min(fuel_med, w_med), min(fuel_low, w_med))
    r_low  = max(fuel_high, w_good)

    num = r_low*0.1 + r_med*0.5 + r_high*0.9
    den = r_low + r_med + r_high + 1e-6
    return num / den


# ------------------------------------------------------------
# 3. A* TAXIWAY ROUTE PLANNER
# ------------------------------------------------------------

def a_star_taxi(start, goal, airport=AIRPORT, occupied=set()):
    nodes = airport["taxi_nodes"]
    if start not in nodes or goal not in nodes:
        return None

    def neighbors(n):
        for nb in nodes[n]["adj"]:
            if nb not in occupied:
                yield nb

    def h(n):
        return euclid(nodes[n]["coord"], nodes[goal]["coord"])

    pq = [(h(start), 0, start, [start])]
    g_best = {start:0}

    while pq:
        f, g, u, path = heapq.heappop(pq)
        if u == goal:
            return path

        for nb in neighbors(u):
            new_g = g + euclid(nodes[u]["coord"], nodes[nb]["coord"])
            if nb not in g_best or new_g < g_best[nb]:
                g_best[nb] = new_g
                heapq.heappush(pq, (new_g + h(nb), new_g, nb, path+[nb]))
    return None


# ------------------------------------------------------------
# 4. CSP SCHEDULER
# ------------------------------------------------------------

class CSP:
    def __init__(self, flights, runways, gates):
        self.flights = flights
        self.runways = runways
        self.gates = gates
        self.domains = {}

    def setup_domains(self):
        for f in self.flights:
            dom = []
            for r in self.runways:
                for g in self.gates:
                    for slot in range(f["arrival_slot"], f["arrival_slot"] + 6):
                        dom.append((r, g, slot))
            self.domains[f["id"]] = dom

    def valid(self, var, val, assign):
        r, g, s = val

        for other, (rr, gg, ss) in assign.items():
            if rr == r and abs(ss - s) < 1:
                return False
            if gg == g and abs(ss - s) < 2:
                return False

        return True

    def solve(self):
        self.setup_domains()
        assignment = {}

        def backtrack():
            if len(assignment) == len(self.flights):
                return True

            unassigned = [f for f in self.flights if f["id"] not in assignment]
            unassigned.sort(key=lambda x: -x["priority"])
            var = unassigned[0]["id"]

            for val in self.domains[var]:
                if self.valid(var, val, assignment):
                    assignment[var] = val
                    if backtrack(): return True
                    del assignment[var]
            return False

        success = backtrack()
        return assignment if success else None


# ------------------------------------------------------------
# 5. SIMULATION HELPERS
# ------------------------------------------------------------

def generate_random_flights(n=5):
    types = ["A320", "B737", "A330", "Turboprop"]
    flights = []
    for i in range(n):
        f = {
            "id": f"F{100+i}",
            "arrival_slot": random.randint(1, 8),
            "type": random.choice(types),
            "fuel": random.randint(10, 80),
            "weather": round(random.random(), 2),
            "emergency": random.random() < 0.10,
        }
        f["priority"] = fuzzy_priority_score(f["fuel"], f["weather"], f["emergency"])
        flights.append(f)
    return flights


def process_flights(flights):
    runways = list(AIRPORT["runways"])
    gates   = list(AIRPORT["gates"])

    csp = CSP(flights, runways, gates)
    assignments = csp.solve()
    if not assignments:
        return None, None

    routes = {}
    occupied = set()
    for fid, (r, g, slot) in assignments.items():
        start = r + "_exit"
        end = AIRPORT["gate_node_map"][g]
        path = a_star_taxi(start, end, AIRPORT, occupied)
        if path:
            routes[fid] = path
            occupied |= set(path)
        else:
            routes[fid] = None

    return assignments, routes


# ------------------------------------------------------------
# 6. GUI APPLICATION
# ------------------------------------------------------------

class IAATC_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IAATCMS - Airport & ATC Management (AI System)")
        self.root.geometry("1100x700")

        self.flights = []
        self.assignments = {}
        self.routes = {}

        # -------- LEFT PANEL
        left = ttk.Frame(root, padding=10)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Controls", font=("Arial", 16, "bold")).pack()

        ttk.Button(left, text="Load Sample Flights", command=self.load_sample).pack(fill="x", pady=5)
        ttk.Button(left, text="Generate Random Flights", command=self.make_random).pack(fill="x", pady=5)
        ttk.Button(left, text="Run AI System", command=self.run_ai).pack(fill="x", pady=5)
        ttk.Button(left, text="Clear", command=self.clear).pack(fill="x", pady=5)

        ttk.Label(left, text="\nFlights:").pack(anchor="w")
        self.lst = tk.Listbox(left, width=45, height=10)
        self.lst.pack()

        ttk.Label(left, text="\nLog:").pack(anchor="w")
        self.log = tk.Text(left, width=45, height=12)
        self.log.pack()

        # -------- RIGHT PANEL
        right = ttk.Frame(root, padding=10)
        right.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(right, bg="white")
        self.canvas.pack(fill="both", expand=True)

        ttk.Label(right, text="Assignments:", font=("Arial", 12, "bold")).pack(anchor="w")
        self.assign_box = tk.Text(right, height=8)
        self.assign_box.pack(fill="x")

        self.draw_airport()

    # ---------------- GUI Functions ----------------

    def load_sample(self):
        self.flights = [
            {"id":"F101","arrival_slot":3,"type":"A320","fuel":25,"weather":0.2,"emergency":False},
            {"id":"F202","arrival_slot":2,"type":"B737","fuel":10,"weather":0.3,"emergency":True},
            {"id":"F303","arrival_slot":4,"type":"A330","fuel":50,"weather":0.7,"emergency":False},
            {"id":"F404","arrival_slot":3,"type":"Turboprop","fuel":60,"weather":0.1,"emergency":False},
        ]
        for f in self.flights:
            f["priority"] = fuzzy_priority_score(f["fuel"], f["weather"], f["emergency"])
        self.update_flight_list()
        self.write_log("Loaded sample flights.")

    def make_random(self):
        self.flights = generate_random_flights()
        self.update_flight_list()
        self.write_log("Random flights generated.")

    def update_flight_list(self):
        self.lst.delete(0, tk.END)
        for f in self.flights:
            self.lst.insert(tk.END,
                f"{f['id']} | arr:{f['arrival_slot']} | type:{f['type']} | priority:{f['priority']:.2f}"
            )

    def run_ai(self):
        if not self.flights:
            messagebox.showwarning("No Flights", "Load or generate flights first.")
            return

        assign, routes = process_flights(self.flights)
        if not assign:
            messagebox.showerror("CSP Failed", "No valid assignment found.")
            return

        self.assignments = assign
        self.routes = routes
        self.show_assignments()
        self.draw_paths()
        self.write_log("AI system executed successfully.")

    def show_assignments(self):
        self.assign_box.delete("1.0", tk.END)
        for fid, (r, g, slot) in self.assignments.items():
            self.assign_box.insert(tk.END, f"{fid}: Runway={r}, Gate={g}, Slot={slot}\n")
        self.assign_box.insert(tk.END, "\nPriority Scores:\n")
        for f in self.flights:
            self.assign_box.insert(tk.END, f"{f['id']}: {f['priority']:.3f}, emergency={f['emergency']}\n")

    def clear(self):
        self.flights = []
        self.assignments = {}
        self.routes = {}
        self.lst.delete(0, tk.END)
        self.assign_box.delete("1.0", tk.END)
        self.log.delete("1.0", tk.END)
        self.draw_airport()
        self.write_log("Cleared all.")

    def write_log(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    # ---------------- Drawing Airport Layout ----------------

    def draw_airport(self):
        self.canvas.delete("all")

        # Draw taxiway edges
        for node, data in AIRPORT["taxi_nodes"].items():
            x1, y1 = data["coord"]
            for nb in data["adj"]:
                if nb in AIRPORT["taxi_nodes"]:
                    x2, y2 = AIRPORT["taxi_nodes"][nb]["coord"]
                    self.canvas.create_line(x1, y1, x2, y2, fill="#999", width=2)

        # Draw nodes
        for node, data in AIRPORT["taxi_nodes"].items():
            x, y = data["coord"]
            color = "lightgray"
            if node.endswith("_exit"): color = "orange"
            if node.endswith("_entry"): color = "lightblue"

            self.canvas.create_oval(x-8, y-8, x+8, y+8, fill=color)
            self.canvas.create_text(x, y-15, text=node, font=("Arial", 9))

    def draw_paths(self):
        self.draw_airport()
        colors = ["red","blue","green","purple","brown"]
        i = 0
        for fid, path in self.routes.items():
            if not path: continue
            col = colors[i % len(colors)]
            i += 1

            coords = [AIRPORT["taxi_nodes"][p]["coord"] for p in path if p in AIRPORT["taxi_nodes"]]

            for k in range(len(coords)-1):
                x1,y1 = coords[k]
                x2,y2 = coords[k+1]
                self.canvas.create_line(x1, y1, x2, y2, fill=col, width=3, arrow="last")

            sx, sy = coords[0]
            ex, ey = coords[-1]
            self.canvas.create_text((sx+ex)/2, (sy+ey)/2 - 10,
                                    text=fid, fill=col, font=("Arial", 12, "bold"))


# ------------------------------------------------------------
# 7. MAIN LAUNCH
# ------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = IAATC_GUI(root)
    root.mainloop()
