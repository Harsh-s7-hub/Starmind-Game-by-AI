# main.py — IAATCMS (B+C merged) — Tabbed UI (Simulation | Radar | Dashboard | Logs)
"""
Powerful Intelligent Airport Management Simulation
- Tabbed Tkinter UI (Simulation, Radar, Dashboard, Logs)
- Embedded Pygame simulation with realistic approach funnels and runway selection
- Holding patterns, separation enforcement, A* taxi planner with smooth curves
- CSP scheduler, GA ordering optimizer, fuzzy priority + wind drift
- Radar with rotating sweep, Plotly dashboard (optional) with hue/gradient visuals
- Designed to be robust and run on typical mid-range laptop
"""

# ---------------------------
# PART 1/3: imports, config, utilities, fuzzy, A*, CSP, taxi smoothing helpers
# ---------------------------

import os
import sys
import math
import random
import time
import threading
import heapq
import tempfile
import webbrowser
from collections import deque, Counter
import json

import tkinter as tk
from tkinter import ttk, messagebox

# Optional Plotly for beautiful graphs
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False

# pygame for simulation rendering
try:
    import pygame
    from pygame.locals import *
except Exception:
    print("pygame is required. Install with: pip install pygame")
    raise

import numpy as np

# ---------------------------
# Configuration & Geometry
# ---------------------------
SIM_W, SIM_H = 1100, 700
FPS = 60

# Runways geometry (two parallel)
RUNWAY_LEN = 760
RUNWAY_W = 72
RUNWAY1_X = (SIM_W // 2) - (RUNWAY_LEN // 2)
RUNWAY1_Y = 110
RUNWAY2_X = RUNWAY1_X
RUNWAY2_Y = RUNWAY1_Y + 170

GATE_Y = RUNWAY2_Y + 190

# Taxi nodes (positions tuned)
TAXI_NODES = {
    "RWY1_EXIT": (RUNWAY1_X + RUNWAY_LEN - 56, RUNWAY1_Y + RUNWAY_W//2 + 6),
    "T_A": (RUNWAY1_X + 150, RUNWAY1_Y + 80),
    "T_B": (RUNWAY1_X + 340, RUNWAY1_Y + 80),
    "T_C": (RUNWAY1_X + 520, RUNWAY1_Y + 80),
    "T_D": (RUNWAY1_X + 660, RUNWAY1_Y + 80),
    "RWY2_EXIT": (RUNWAY2_X + RUNWAY_LEN - 56, RUNWAY2_Y + RUNWAY_W//2 + 6),
    "G1": (RUNWAY1_X + 140, GATE_Y),
    "G2": (RUNWAY1_X + 270, GATE_Y),
    "G3": (RUNWAY1_X + 400, GATE_Y),
    "G4": (RUNWAY1_X + 530, GATE_Y),
    "G5": (RUNWAY1_X + 660, GATE_Y),
}

TAXI_ADJ = {
    "RWY1_EXIT": ["T_A"],
    "T_A": ["RWY1_EXIT","T_B","G1"],
    "T_B": ["T_A","T_C","G2"],
    "T_C": ["T_B","T_D","G3"],
    "T_D": ["T_C","RWY2_EXIT","G4","G5"],
    "RWY2_EXIT": ["T_D"],
    "G1": ["T_A"], "G2": ["T_B"], "G3": ["T_C"], "G4": ["T_D"], "G5": ["T_D"]
}
GATES = ["G1","G2","G3","G4","G5"]
GATE_POS = {g: TAXI_NODES[g] for g in GATES}

# Knowledge base (simple)
KB = {
    "airport_name": "IAATCMS - Advanced Demo",
    "runways": {"RWY1": {"len_m":3500}, "RWY2":{"len_m":3200}},
    "gates": {g: {"size": "large" if i<2 else "medium" if i<4 else "small"} for i,g in enumerate(GATES)},
    "taxi_nodes": TAXI_NODES
}

# Simulation parameters
MIN_SEPARATION_PX = 80  # minimum horizontal separation (pixels)
HOLD_RADIUS = 42
APPROACH_STEPS = 160
TAXI_SPEED = 70  # px/sec approx
APPROACH_SPEED = 160  # px/sec
RUNWAY_SEP_SEC = 6.0

# Wind model (direction degrees, speed m/s)
WIND_DIR = 0.0  # degrees from north (0)
WIND_SPEED = 0.0  # m/s (will affect runway choice lightly)

# ---------------------------
# Utilities
# ---------------------------
def dist(a,b): return math.hypot(a[0]-b[0], a[1]-b[1])
def clamp(x,a,b): return max(a, min(b, x))

def lerp(a,b,t): return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t)

# Smooth quadratic bezier between p0->p1->p2
def quad_bezier(p0,p1,p2,steps=100):
    pts=[]
    for i in range(steps+1):
        t = i/steps
        x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
        y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
        pts.append((x,y))
    return pts

# path smoothing (simple Chaikin)
def smooth_path(pts, iterations=2):
    p = pts[:]
    for _ in range(iterations):
        q=[]
        for i in range(len(p)-1):
            a = p[i]; b = p[i+1]
            q.append((0.75*a[0]+0.25*b[0], 0.75*a[1]+0.25*b[1]))
            q.append((0.25*a[0]+0.75*b[0], 0.25*a[1]+0.75*b[1]))
        p = q
    return p

# ---------------------------
# Fuzzy priority & rules
# ---------------------------
def tri(x,a,b,c):
    if x <= a or x >= c: return 0.0
    if x == b: return 1.0
    if x < b: return (x-a)/(b-a)
    return (c-x)/(c-b)

def fuzzy_priority(fuel_pct, weather, emergency=False):
    # fuel_pct: 0-100, weather: 0-1 (1 worst)
    if emergency: return 1.0
    f = clamp(fuel_pct/100.0,0.0,1.0)
    inv_f = 1.0 - f
    fuel_low = tri(inv_f, 0.6, 0.9, 1.0)
    fuel_med = tri(inv_f, 0.3, 0.5, 0.7)
    fuel_high = tri(inv_f, 0.0, 0.0, 0.4)
    w_poor = tri(weather, 0.6, 0.8, 1.0)
    w_med = tri(weather, 0.3, 0.5, 0.7)
    w_good = tri(weather, 0.0, 0.1, 0.4)
    r_high = max(fuel_low, w_poor)
    r_med = max(min(fuel_med, w_med), min(fuel_low, w_med))
    r_low = max(fuel_high, w_good)
    numerator = r_low*0.1 + r_med*0.5 + r_high*0.9
    denom = max(1e-6, r_low + r_med + r_high)
    return clamp(numerator/denom, 0.0, 1.0)

# ---------------------------
# A* taxi planner
# ---------------------------
def a_star_taxi(start, goal, blocked=set()):
    nodes = TAXI_NODES
    if start not in nodes or goal not in nodes: return None
    def heuristic(n): return dist(nodes[n], nodes[goal])
    openq = []
    heapq.heappush(openq, (heuristic(start), 0.0, start, [start]))
    gbest = {start:0.0}
    visited = set()
    while openq:
        f,g,cur,path = heapq.heappop(openq)
        if cur == goal: return path
        if cur in visited: continue
        visited.add(cur)
        for nb in TAXI_ADJ.get(cur, []):
            if nb in blocked: continue
            ng = g + dist(nodes[cur], nodes[nb])
            if nb not in gbest or ng < gbest[nb]:
                gbest[nb] = ng
                heapq.heappush(openq, (ng + heuristic(nb), ng, nb, path + [nb]))
    return None

# ---------------------------
# CSP Scheduler (backtracking)
# ---------------------------
class CSP_Scheduler:
    def __init__(self, flights, runways, gates, separation_slots=1):
        self.flights = flights
        self.runways = runways
        self.gates = gates
        self.sep = separation_slots
        self.domains = {}

    def setup(self):
        for f in self.flights:
            dom=[]
            for r in self.runways:
                for g in self.gates:
                    for s in range(f['slot'], f['slot']+6):
                        dom.append((r,g,s))
            self.domains[f['id']] = dom

    def consistent(self, var, val, assignment):
        r,g,s = val
        for ov, ovv in assignment.items():
            orun, ogate, oslot = ovv
            if orun == r and abs(oslot - s) < self.sep: return False
            if ogate == g and abs(oslot - s) < 2: return False
        return True

    def select(self, assignment):
        un = [f for f in self.flights if f['id'] not in assignment]
        un.sort(key=lambda x: len(self.domains.get(x['id'], [])))
        return un[0]['id'] if un else None

    def backtrack(self, assignment):
        if len(assignment) == len(self.flights): return assignment
        var = self.select(assignment)
        for val in list(self.domains.get(var, [])):
            if self.consistent(var, val, assignment):
                assignment[var] = val
                res = self.backtrack(assignment)
                if res: return res
                del assignment[var]
        return None

    def solve(self):
        self.setup()
        self.flights.sort(key=lambda x: -x['priority'])
        return self.backtrack({})

# ---------------------------
# GA for order optimization
# ---------------------------
def ga_optimize_order(ids, fitness_fn, pop_size=32, gens=40, mut_rate=0.12):
    pop = [random.sample(ids, len(ids)) for _ in range(pop_size)]
    for _ in range(gens):
        scored = [(fitness_fn(ind), ind) for ind in pop]
        scored.sort(key=lambda x: x[0])
        pop = [ind for (_,ind) in scored[:pop_size//2]]
        children=[]
        while len(pop) + len(children) < pop_size:
            a = random.choice(pop); b=random.choice(pop)
            cut = random.randint(1, len(a)-1)
            child = a[:cut] + [x for x in b if x not in a[:cut]]
            if random.random() < mut_rate:
                i,j = random.sample(range(len(child)),2); child[i],child[j] = child[j],child[i]
            children.append(child)
        pop += children
    return min(pop, key=fitness_fn)

# ---------------------------
# PART 1/3 END
# ---------------------------
# ---------------------------
# PART 2/3: Flight class, ATC Dialog, PygameSim with improved behavior
# ---------------------------

# ---------- Flight model ----------
class Flight:
    counter = 2000
    def __init__(self, ftype="A320", fuel=None, weather=None, emergency=False, edge=None, req_slot=1):
        self.id = f"F{Flight.counter}"; Flight.counter += 1
        self.type = ftype
        self.fuel = fuel if fuel is not None else random.randint(8,95)
        self.weather = weather if weather is not None else round(random.random(),2)
        self.emergency = emergency
        self.priority = fuzzy_priority(self.fuel, self.weather, self.emergency)
        self.state = "spawning"  # spawning, approaching, requesting, holding, landing, rollout, taxiing, at_gate, diverted
        self.entry_edge = edge
        self.pos = (0,0)
        self.approach_path = []
        self.approach_index = 0
        self.assigned = None
        self.taxi_path = None
        self.taxi_index = 0.0
        self.landed_runway = None
        self.request_slot = req_slot
        self.hold_center = None
        self.hold_angle = 0.0
        self.altitude = 4000  # arbitrary units; will descend on approach
        self.gate_timer = None

    def to_dict(self):
        return {"id":self.id, "slot":self.request_slot, "priority":self.priority, "type":self.type}

# ---------- ATC dialog popup ----------
class ATCDialog:
    def __init__(self, master, flight, callback):
        self.top = tk.Toplevel(master)
        self.top.title(f"ATC — {flight.id}")
        self.top.grab_set()
        txt = f"Flight {flight.id} ({flight.type}) requesting landing\nFuel:{flight.fuel}% Weather:{flight.weather} Priority:{flight.priority:.2f}"
        if flight.emergency: txt = "!!! EMERGENCY !!!\n" + txt
        tk.Label(self.top, text=txt, wraplength=420, justify="left").pack(padx=10, pady=8)
        frm = tk.Frame(self.top); frm.pack(pady=6)
        tk.Button(frm, text="Grant", width=10, command=lambda: self.ret("grant", callback)).pack(side="left", padx=6)
        tk.Button(frm, text="Hold", width=10, command=lambda: self.ret("hold", callback)).pack(side="left", padx=6)
        tk.Button(frm, text="Divert", width=10, command=lambda: self.ret("divert", callback)).pack(side="left", padx=6)
        tk.Button(frm, text="Cancel", width=10, command=lambda: self.ret(None, callback)).pack(side="left", padx=6)

    def ret(self, choice, callback):
        try: callback(choice)
        finally: self.top.destroy()

# ---------- PygameSim: core simulation with improved funnels & separation ----------
class PygameSim:
    def __init__(self, parent_frame, width=SIM_W, height=SIM_H):
        self.parent = parent_frame
        self.width = width; self.height = height
        # SDL embedding
        os.environ['SDL_WINDOWID'] = str(self.parent.winfo_id())
        # init pygame properly
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("IAATCMS Simulation")
        self.clock = pygame.time.Clock()

        # state
        self.flights = []
        self.logs = deque(maxlen=800)
        self.auto_spawn = False
        self.auto_schedule = False
        self.auto_decision_flag = False
        self.auto_decision_threshold = 0.55
        self.last_spawn = time.time()
        self.last_schedule = time.time()
        self.runway_busy_until = {"RWY1":0.0, "RWY2":0.0}
        self.runway_sep = RUNWAY_SEP_SEC
        self.tk_root = None
        self.tk_callback = None
        self.running = True
        self.wind_dir = WIND_DIR; self.wind_speed = WIND_SPEED
        self.radar_angle = 0.0

        # Approach funnels: define funnel centers and arcs for smooth separation
        self.funnels = {
            "RWY1": {"start_center": (-160, RUNWAY1_Y + 10), "mid_offset": (RUNWAY1_X + RUNWAY_LEN/2, RUNWAY1_Y + 160), "threshold": (RUNWAY1_X + 40, RUNWAY1_Y + RUNWAY_W//2)},
            "RWY2": {"start_center": (self.width+160, RUNWAY2_Y + 10), "mid_offset": (RUNWAY2_X + RUNWAY_LEN/2, RUNWAY2_Y + 160), "threshold": (RUNWAY2_X + 40, RUNWAY2_Y + RUNWAY_W//2)}
        }

        # start thread
        self._start_thread()

    def log(self, s):
        self.logs.appendleft(f"[{time.strftime('%H:%M:%S')}] {s}")

    # spawn with approach funnel & arc distribution to avoid clusters
    def spawn_flight(self, ftype=None, emergency=False, prefer_runway=None):
        typ = ftype if ftype else random.choice(["A320","B737","A330","Turboprop"])
        edge = random.choice(["left","right","top","bottom"])
        # build approach path to chosen runway (use wind preference)
        # Choose runway by preference/wind: if prefer_runway provided use it, else pick based on wind
        r = prefer_runway if prefer_runway else self.choose_runway_by_wind()
        # start point on arc depending on edge (but add randomness to spread)
        if edge == "left":
            start = (-140 + random.uniform(-20,20), random.randint(80, self.height-80))
        elif edge == "right":
            start = (self.width+140 + random.uniform(-20,20), random.randint(80, self.height-80))
        elif edge == "top":
            start = (random.randint(80,self.width-80), -140 + random.uniform(-20,20))
        else:
            start = (random.randint(80,self.width-80), self.height+140 + random.uniform(-20,20))

        funnel = self.funnels[r]
        mid = funnel["mid_offset"]
        # randomize mid a little to avoid identical curves
        mid = (mid[0] + random.uniform(-80,80), mid[1] + random.uniform(-30,30))
        thresh = funnel["threshold"]

        path = quad_bezier(start, mid, thresh, steps=APPROACH_STEPS)
        path = smooth_path(path, iterations=2)
        f = Flight(typ, fuel=random.randint(8,95), weather=round(random.random(),2), emergency=emergency, edge=edge, req_slot=1+random.randint(0,4))
        f.approach_path = path; f.approach_index = 0; f.pos = path[0]; f.state = "approaching"; f.target_runway = r
        # push to list
        self.flights.append(f)
        self.log(f"Spawned {f.id} type {f.type} -> {r} (edge {edge})")
        return f

    def choose_runway_by_wind(self):
        # simplistic: prefer runway aligning with headwind (here mock: 50/50)
        return random.choice(["RWY1","RWY2"])

    def run_csp(self):
        to_sched = [fl.to_dict() for fl in self.flights if fl.state in ("approaching","holding","requesting","spawning")]
        if not to_sched:
            self.log("CSP: none")
            return {}
        cs = CSP_Scheduler(to_sched, ["RWY1","RWY2"], GATES, separation_slots=1)
        sol = cs.solve()
        if not sol:
            self.log("CSP no solution")
            return {}
        for fid, val in sol.items():
            fo = next((x for x in self.flights if x.id == fid), None)
            if fo: fo.assigned = val
        self.log("CSP assigned")
        return sol

    # separation check returns True if two flights are too close horizontally
    def violates_separation(self, f, others):
        for o in others:
            if o is f: continue
            if dist(f.pos, o.pos) < MIN_SEPARATION_PX:
                return True
        return False

    def step(self, dt):
        # auto spawn / schedule
        if self.auto_spawn and time.time() - self.last_spawn > 2.8:
            self.spawn_flight(); self.last_spawn = time.time()
        if self.auto_schedule and time.time() - self.last_schedule > 6.0:
            self.run_csp(); self.last_schedule = time.time()

        remove=[]
        for fl in list(self.flights):
            if fl.state == "approaching":
                # ensure horizontal spacing: if too close to previous on approach, slow down or enter holding
                others = [o for o in self.flights if o.state in ("approaching","requesting","holding","landing")]
                if self.violates_separation(fl, others):
                    # enter holding to avoid stacking
                    fl.state = "holding"
                    fl.hold_center = (fl.pos[0], fl.pos[1]-80)
                    fl.hold_angle = random.uniform(0,360)
                    self.log(f"{fl.id} auto-hold (spacing)")
                    continue
                # advance index by approach speed scaled to dt
                step_px = APPROACH_SPEED * dt
                # find index advancement by distance traveled along path
                idx = fl.approach_index
                while idx < len(fl.approach_path)-1 and dist(fl.approach_path[idx], fl.approach_path[min(idx+1, len(fl.approach_path)-1)]) < step_px:
                    idx += 1
                # if can't move many steps, increment fractionally
                fl.approach_index = min(len(fl.approach_path)-1, fl.approach_index + 1)
                fl.pos = fl.approach_path[fl.approach_index]
                fl.altitude = max(0, fl.altitude - 600*dt)  # descend rate approx
                # if near threshold request landing
                if fl.approach_index >= len(fl.approach_path)-12:
                    # check runway busy
                    runway = fl.target_runway
                    if time.time() < self.runway_busy_until.get(runway, 0.0):
                        # mark hold
                        fl.state = "holding"; fl.hold_center = (fl.pos[0], fl.pos[1]-68); fl.hold_angle = 0.0
                        self.log(f"{fl.id} hold due to busy {runway}")
                        continue
                    else:
                        fl.state = "requesting"
                        # decision callback
                        def decision_cb(dec, f=fl, runway=runway):
                            if dec == "grant":
                                f.state = "landing"; f.landed_runway = runway
                                self.runway_busy_until[runway] = time.time() + self.runway_sep
                                self.log(f"{f.id} cleared to land on {runway}")
                            elif dec == "hold":
                                f.state = "holding"; f.hold_center = (f.pos[0], f.pos[1]-80); f.hold_angle = 0.0
                                self.log(f"{f.id} instructed hold")
                            elif dec == "divert":
                                f.state = "diverted"; self.log(f"{f.id} diverted by ATC")
                            else:
                                f.state = "holding"; f.hold_center = (f.pos[0], f.pos[1]-80); f.hold_angle = 0.0
                        if self.auto_decision_flag:
                            th = self.auto_decision_threshold
                            if fl.priority >= th: decision_cb("grant")
                            else:
                                if fl.priority < 0.12: decision_cb("divert")
                                else: decision_cb("hold")
                        else:
                            if self.tk_callback and self.tk_root:
                                self.tk_callback(lambda: ATCDialog(self.tk_root, fl, decision_cb))
                            else:
                                decision_cb("grant")

            elif fl.state == "holding":
                fl.hold_angle = (fl.hold_angle + 80*dt) % 360
                ang = math.radians(fl.hold_angle)
                cx,cy = fl.hold_center if fl.hold_center else (fl.pos[0], fl.pos[1]-60)
                fl.pos = (cx + HOLD_RADIUS*math.cos(ang), cy + HOLD_RADIUS*math.sin(ang))
                # occasionally attempt re-request
                if random.random() < 0.02:
                    fl.state = "requesting"

            elif fl.state == "requesting":
                # if assigned runway busy, hold
                runway = getattr(fl, "target_runway", "RWY1")
                if time.time() < self.runway_busy_until.get(runway, 0.0):
                    fl.state = "holding"; fl.hold_center = (fl.pos[0], fl.pos[1]-80); fl.hold_angle = 0.0
                    self.log(f"{fl.id} hold (busy)")
                # otherwise waiting for ATC dialog (handled earlier)
                pass

            elif fl.state == "landing":
                # move along runway toward rollout zone
                if fl.landed_runway == "RWY1":
                    vx = 160*dt; fl.pos = (fl.pos[0]+vx, fl.pos[1])
                    if fl.pos[0] > RUNWAY1_X + RUNWAY_LEN*0.6:
                        fl.state = "rollout"
                else:
                    vx = 160*dt; fl.pos = (fl.pos[0]+vx, fl.pos[1])
                    if fl.pos[0] > RUNWAY2_X + RUNWAY_LEN*0.6:
                        fl.state = "rollout"

            elif fl.state == "rollout":
                if fl.assigned and not fl.taxi_path:
                    exit_node = "RWY1_EXIT" if fl.landed_runway == "RWY1" else "RWY2_EXIT"
                    gate_node = fl.assigned[1]
                    p = a_star_taxi(exit_node, gate_node, blocked=set())
                    if p:
                        fl.taxi_path = p; fl.taxi_index = 0.0; fl.state = "taxiing"
                        self.log(f"{fl.id} taxiing via {p}")
                    else:
                        fl.state = "at_gate"; self.log(f"{fl.id} parked (no taxi path)")
                else:
                    fl.state = "at_gate"; self.log(f"{fl.id} at gate")

            elif fl.state == "taxiing":
                if fl.taxi_path and int(fl.taxi_index) < len(fl.taxi_path):
                    node = fl.taxi_path[int(fl.taxi_index)]
                    tgt = TAXI_NODES.get(node)
                    if tgt:
                        dx = tgt[0] - fl.pos[0]; dy = tgt[1] - fl.pos[1]; d = math.hypot(dx,dy)
                        if d < 6:
                            fl.taxi_index += 1
                        else:
                            vx = dx/(d+1e-6) * TAXI_SPEED * dt
                            vy = dy/(d+1e-6) * TAXI_SPEED * dt
                            fl.pos = (fl.pos[0] + vx, fl.pos[1] + vy)
                    else:
                        fl.taxi_index += 1
                else:
                    fl.state = "at_gate"; fl.gate_timer = time.time(); self.log(f"{fl.id} reached gate")

            elif fl.state == "diverted":
                # fly off-screen
                if fl.entry_edge == "left": fl.pos = (fl.pos[0] - 160*dt, fl.pos[1])
                elif fl.entry_edge == "right": fl.pos = (fl.pos[0] + 160*dt, fl.pos[1])
                elif fl.entry_edge == "top": fl.pos = (fl.pos[0], fl.pos[1] - 160*dt)
                else: fl.pos = (fl.pos[0], fl.pos[1] + 160*dt)
                if (fl.pos[0] < -200 or fl.pos[0] > self.width+200 or fl.pos[1] < -200 or fl.pos[1] > self.height+200):
                    remove.append(fl)

            elif fl.state == "at_gate":
                if fl.gate_timer is None: fl.gate_timer = time.time()
                if time.time() - fl.gate_timer > 8.0: remove.append(fl)

        for r in remove:
            if r in self.flights: self.flights.remove(r)

    # draw with nicer visuals and taxi centerlines
    def draw(self):
        # background
        self.screen.fill((16,22,40))
        pygame.draw.rect(self.screen, (26,130,50), (0, RUNWAY1_Y - 140, self.width, RUNWAY2_Y + RUNWAY_W - (RUNWAY1_Y - 140) + 260))

        # runways
        r1 = (RUNWAY1_X, RUNWAY1_Y, RUNWAY_LEN, RUNWAY_W)
        r2 = (RUNWAY2_X, RUNWAY2_Y, RUNWAY_LEN, RUNWAY_W)
        pygame.draw.rect(self.screen, (50,50,50), r1, border_radius=12)
        pygame.draw.rect(self.screen, (50,50,50), r2, border_radius=12)
        for rx, ry in ((RUNWAY1_X, RUNWAY1_Y),(RUNWAY2_X, RUNWAY2_Y)):
            for s in range(20, RUNWAY_LEN-20, 64):
                pygame.draw.rect(self.screen, (230,230,230), (rx + s, ry + RUNWAY_W//2 -5, 30, 10), border_radius=3)

        # taxiways centerlines
        for a,b in [("RWY1_EXIT","T_A"),("T_A","T_B"),("T_B","T_C"),("T_C","T_D"),("T_D","RWY2_EXIT")]:
            if a in TAXI_NODES and b in TAXI_NODES:
                pygame.draw.line(self.screen, (120,120,120), TAXI_NODES[a], TAXI_NODES[b], 14)
                # thin centerline
                pygame.draw.line(self.screen, (80,80,80), TAXI_NODES[a], TAXI_NODES[b], 6)

        # gates
        font_sm = pygame.font.SysFont("Arial", 12)
        for g,p in GATE_POS.items():
            pygame.draw.rect(self.screen, (210,210,210), (p[0]-20, p[1]-12, 40, 26), border_radius=4)
            self.screen.blit(font_sm.render(g, True, (20,20,20)), (p[0]-10, p[1]-10))

        # taxi nodes
        for name,coord in TAXI_NODES.items():
            pygame.draw.circle(self.screen, (70,70,70), (int(coord[0]), int(coord[1])), 5)

        # draw flights
        for fl in self.flights:
            x,y = int(fl.pos[0]), int(fl.pos[1])
            col = (255,50,50) if fl.emergency else (20,20,20)
            size = 6 + int(6*fl.priority)
            pygame.draw.circle(self.screen, (0,0,0), (x,y), size+2)
            pygame.draw.circle(self.screen, col, (x,y), size)
            # label
            lbl = font_sm.render(fl.id, True, (255,255,255))
            self.screen.blit(lbl, (x + size + 6, y - size - 6))
            state_lbl = font_sm.render(fl.state, True, (230,230,230))
            self.screen.blit(state_lbl, (x + size + 6, y + 2))

        # small log text overlay
        font_mono = pygame.font.SysFont("Consolas", 12)
        ly = 6
        for i, line in enumerate(list(self.logs)[:6]):
            self.screen.blit(font_mono.render(line, True, (220,220,220)), (6, ly)); ly += 16

        pygame.display.flip()

    def integrate_tk(self, tk_root, tk_callback):
        self.tk_root = tk_root; self.tk_callback = tk_callback

    def _start_thread(self):
        def loop():
            prev = time.time()
            while self.running:
                now = time.time(); dt = now - prev; prev = now
                try:
                    self.step(dt)
                    self.draw()
                except Exception as e:
                    # append error but continue
                    self.logs.appendleft(f"ERR {e}")
                self.clock.tick(FPS)
            pygame.quit()
        t = threading.Thread(target=loop, daemon=True); t.start()

    def stop(self):
        self.running = False

# ---------------------------
# PART 2/3 END
# ---------------------------
# ---------------------------
# PART 3/3: Tkinter Tabbed UI (Simulation | Radar | Dashboard | Logs) and main()
# ---------------------------

class MainApp:
    def __init__(self, root):
        self.root = root
        root.title("IAATCMS — Intelligent Airport (B+C)")
        root.geometry("1400x820")

        # top-level Notebook tabs
        self.notebook = ttk.Notebook(root); self.notebook.pack(fill="both", expand=True)
        # Simulation tab frame
        self.tab_sim = ttk.Frame(self.notebook); self.notebook.add(self.tab_sim, text="Simulation")
        self.tab_radar = ttk.Frame(self.notebook); self.notebook.add(self.tab_radar, text="Radar")
        self.tab_dash = ttk.Frame(self.notebook); self.notebook.add(self.tab_dash, text="Dashboard")
        self.tab_logs = ttk.Frame(self.notebook); self.notebook.add(self.tab_logs, text="Logs")

        # Left control panel inside Simulation tab
        left = ttk.Frame(self.tab_sim, width=300); left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text="ATC Controls", font=("Arial", 14, "bold")).pack(pady=6)
        ttk.Button(left, text="Spawn Flight", command=self.spawn_click).pack(fill="x", pady=4)
        ttk.Button(left, text="Run CSP Scheduler", command=self.run_csp_click).pack(fill="x", pady=4)
        self.auto_spawn_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Auto Spawn", variable=self.auto_spawn_var, command=self.toggle_auto_spawn).pack(anchor="w", pady=2)
        self.auto_schedule_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Auto Schedule", variable=self.auto_schedule_var, command=self.toggle_auto_schedule).pack(anchor="w", pady=2)
        ttk.Separator(left).pack(fill="x", pady=6)
        ttk.Label(left, text="Auto Decision (AI)", font=("Arial", 11)).pack(pady=(4,0))
        self.auto_decision_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Enable Auto Decision", variable=self.auto_decision_var, command=self.toggle_auto_decision).pack(anchor="w")
        ttk.Label(left, text="Threshold (0.0 - 1.0)").pack(anchor="w", pady=(6,0))
        self.threshold_var = tk.DoubleVar(value=0.55)
        ttk.Scale(left, from_=0.0, to=1.0, variable=self.threshold_var, orient="horizontal").pack(fill="x", pady=2)
        ttk.Separator(left).pack(fill="x", pady=6)
        ttk.Button(left, text="Run GA (optimize order)", command=self.run_ga).pack(fill="x", pady=4)
        ttk.Button(left, text="Show Knowledge Base", command=self.show_kb).pack(fill="x", pady=4)
        ttk.Button(left, text="Export Schedule CSV", command=self.export_csv).pack(fill="x", pady=4)

        # center: simulation pygame canvas embed
        center = ttk.Frame(self.tab_sim); center.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sim_container = tk.Frame(center, width=SIM_W, height=SIM_H); sim_container.pack(); sim_container.pack_propagate(False)
        self.sim = PygameSim(sim_container, width=SIM_W, height=SIM_H)
        self.sim.integrate_tk(self.root, lambda fn: self.root.after(1, fn))

        # right: flights list
        right = ttk.Frame(self.tab_sim, width=280); right.pack(side="right", fill="y", padx=6, pady=6)
        ttk.Label(right, text="Flights", font=("Arial", 12, "bold")).pack(pady=6)
        self.flight_listbox = tk.Listbox(right, width=36, height=28)
        self.flight_listbox.pack()
        self.flight_listbox.bind("<<ListboxSelect>>", self.on_select_flight)

        # Radar tab canvas (large)
        self.radar_canvas = tk.Canvas(self.tab_radar, width=760, height=760, bg="black")
        self.radar_canvas.pack(padx=10, pady=10)
        # dashboard tab: button to open Plotly or text
        ttk.Button(self.tab_dash, text="Open Live Dashboard (Plotly)", command=self.open_dashboard).pack(pady=8)
        self.dashboard_info = tk.Text(self.tab_dash, width=100, height=30)
        self.dashboard_info.pack()
        # logs tab
        ttk.Label(self.tab_logs, text="System Logs", font=("Arial",12,"bold")).pack(pady=6)
        self.logs_text = tk.Text(self.tab_logs, width=160, height=40)
        self.logs_text.pack()

        # schedule UI updates
        self.root.after(600, self.ui_update)
        # radar update loop
        self.root.after(200, self.radar_update)

    # UI actions
    def spawn_click(self):
        f = self.sim.spawn_flight(); self.append_log(f"Spawn {f.id}"); self.refresh_flight_list()

    def run_csp_click(self):
        sol = self.sim.run_csp()
        if sol: self.append_log("CSP assigned"); self.refresh_flight_list()
        else: self.append_log("CSP no solution")

    def toggle_auto_spawn(self):
        self.sim.auto_spawn = self.auto_spawn_var.get(); self.append_log(f"Auto spawn {self.sim.auto_spawn}")

    def toggle_auto_schedule(self):
        self.sim.auto_schedule = self.auto_schedule_var.get(); self.append_log(f"Auto schedule {self.sim.auto_schedule}")

    def toggle_auto_decision(self):
        self.sim.auto_decision_flag = self.auto_decision_var.get()
        self.sim.auto_decision_threshold = float(self.threshold_var.get())
        self.append_log(f"Auto decision {self.sim.auto_decision_flag} thr {self.sim.auto_decision_threshold}")

    def run_ga(self):
        ids = [f.id for f in self.sim.flights]
        if not ids: self.append_log("GA: no flights"); return
        def fitness(order):
            pos = {fid:i for i,fid in enumerate(order)}
            cost = 0.0
            for f in self.sim.flights:
                cost += pos.get(f.id, len(order)) * (1.0 - f.priority)
            return cost
        best = ga_optimize_order(ids, fitness_fn=fitness, pop_size=36, gens=50)
        self.append_log(f"GA best order (first 10): {best[:10]}")
        messagebox.showinfo("GA Result", f"Best order (first 10):\n{best[:10]}")

    def show_kb(self):
        s = f"Airport: {KB['airport_name']}\n\nRunways:\n"
        for r,v in KB['runways'].items(): s += f"  {r}: {v}\n"
        s += "\nGates:\n"
        for g,v in KB['gates'].items(): s += f"  {g}: {v}\n"
        messagebox.showinfo("Knowledge Base", s)

    def export_csv(self):
        # export assigned schedule to CSV
        rows = []
        for f in self.sim.flights:
            if f.assigned:
                rows.append({"flight":f.id, "runway":f.assigned[0], "gate":f.assigned[1], "slot":f.assigned[2]})
        if not rows:
            messagebox.showinfo("Export", "No assignments to export")
            return
        fname = tempfile.gettempdir() + os.sep + "iaatcms_schedule.csv"
        import csv
        with open(fname, "w", newline="") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=["flight","runway","gate","slot"])
            writer.writeheader()
            for r in rows: writer.writerow(r)
        messagebox.showinfo("Export", f"Saved to {fname}")

    def refresh_flight_list(self):
        self.flight_listbox.delete(0, tk.END)
        for f in self.sim.flights:
            tag = " EMG" if f.emergency else ""
            ass = f.assigned[0] if f.assigned else "None"
            self.flight_listbox.insert(tk.END, f"{f.id} | {f.type} | pr:{f.priority:.2f} | {f.state} | {ass}{tag}")

    def on_select_flight(self, evt):
        sel = self.flight_listbox.curselection()
        if not sel: return
        idx = sel[0]; f = self.sim.flights[idx]
        info = f"ID:{f.id}\nType:{f.type}\nFuel:{f.fuel}\nWeather:{f.weather}\nPriority:{f.priority:.2f}\nState:{f.state}\nAssigned:{f.assigned}\nTaxi:{f.taxi_path}\n"
        messagebox.showinfo("Flight Info", info)

    def append_log(self, s):
        ts = time.strftime("%H:%M:%S"); self.logs_text.insert("1.0", f"[{ts}] {s}\n"); self.logs_text.see("1.0")

    def ui_update(self):
        # pull logs from sim
        while self.sim.logs:
            ln = self.sim.logs.pop(); self.append_log(ln)
        self.refresh_flight_list()
        # keep sim threshold updated
        self.sim.auto_decision_threshold = float(self.threshold_var.get())
        self.root.after(700, self.ui_update)

    # Radar UI
    def radar_update(self):
        c = self.radar_canvas; c.delete("all")
        w = int(c['width']); h = int(c['height']); cx,cy = w//2, h//2
        # rings
        for r in (60,120,180,240,300): c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#133f2b")
        # sweep arm
        if not hasattr(self.sim, "radar_angle"): self.sim.radar_angle = 0.0
        self.sim.radar_angle = (self.sim.radar_angle + 4) % 360
        ang = math.radians(self.sim.radar_angle)
        ex = cx + 300*math.cos(ang); ey = cy + 300*math.sin(ang)
        c.create_line(cx,cy, ex,ey, fill="#32ff4f", width=2)
        # blips (map coords scaled)
        map_cx, map_cy = SIM_W/2, SIM_H/2; scale = 0.35
        for f in self.sim.flights:
            mx = (f.pos[0] - map_cx)*scale + cx; my = (f.pos[1] - map_cy)*scale + cy
            color = "#ff4040" if f.emergency else "#00ffff"
            c.create_oval(mx-4,my-4,mx+4,my+4, fill=color, outline="")
            c.create_text(mx+8, my-6, text=f.id, fill="white", font=("Arial",8))
        self.root.after(80, self.radar_update)

    # Dashboard open (Plotly)
    def open_dashboard(self):
        if not PLOTLY_AVAILABLE:
            # simple text summary
            s = "Flights summary:\n"
            for f in self.sim.flights:
                s += f"{f.id} pr:{f.priority:.2f} fuel:{f.fuel} state:{f.state}\n"
            self.dashboard_info.delete("1.0", tk.END); self.dashboard_info.insert(tk.END, s)
            return
        flights = self.sim.flights
        if not flights:
            messagebox.showinfo("Dashboard", "No flights")
            return
        ids = [f.id for f in flights]; pr = [f.priority for f in flights]
        fuels = [f.fuel for f in flights]; we = [f.weather for f in flights]
        assigned = [f.assigned[0] if f.assigned else "None" for f in flights]
        cnt = Counter(assigned)
        # use HSV-like palette for hue colors
        def hsv_to_rgb(h,s=0.8,v=0.9):
            import colorsys
            r,g,b = colorsys.hsv_to_rgb(h,s,v)
            return f"rgb({int(r*255)},{int(g*255)},{int(b*255)})"
        colors = [hsv_to_rgb(i/len(ids)) for i in range(len(ids))]
        fig = make_subplots(rows=2, cols=2, subplot_titles=("Priority (hue scatter)","Fuel (line)","Weather (line)","Runway usage"))
        fig.add_trace(go.Scatter(x=ids, y=pr, mode='markers', marker=dict(color=colors, size=12), name="priority"), row=1, col=1)
        fig.add_trace(go.Scatter(x=ids, y=fuels, mode='lines+markers', name="fuel"), row=1, col=2)
        fig.add_trace(go.Scatter(x=ids, y=we, mode='lines+markers', name="weather"), row=2, col=1)
        fig.add_trace(go.Bar(x=list(cnt.keys()), y=list(cnt.values()), name="runway usage"), row=2, col=2)
        fig.update_layout(height=800, width=1100, showlegend=False, template="plotly_dark")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        fig.write_html(tmp.name, include_plotlyjs='cdn')
        webbrowser.open("file://" + tmp.name)

def main():
    root = tk.Tk()
    app = MainApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.sim.stop(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()

# ---------------------------
# END PART 3/3
# ---------------------------
