# main.py — IAATCMS (Updated: taxi labels, inline matplotlib dashboard, radar-click highlight, emergency landings)
"""
Updated Intelligent Airport & ATC Management Simulation
Features added in this update:
 - Taxi node labels explicitly shown (T_A, T_B, etc.)
 - Click-to-highlight aircraft: click radar blip or select flight to highlight in sim
 - Inline live graphs (matplotlib) in Dashboard tab
 - Improved UI layout + small polish
 - Periodic emergency landings (configurable)
 - 'Intelligent System Design' text added to UI for report
 - Safety spacing and taxi smoothing improvements
"""

# ---------------------------
# PART 1/3: imports, config, utilities, fuzzy, A*, CSP, smoothing helpers
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

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# matplotlib for inline dashboard
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# pygame
try:
    import pygame
    from pygame.locals import *
except Exception:
    print("pygame required. Install with: pip install pygame")
    raise

import numpy as np

# ---------------------------
# Configuration & geometry
# ---------------------------
SIM_W, SIM_H = 1100, 700
FPS = 60

RUNWAY_LEN = 760
RUNWAY_W = 72
RUNWAY1_X = (SIM_W // 2) - (RUNWAY_LEN // 2)
RUNWAY1_Y = 110
RUNWAY2_X = RUNWAY1_X
RUNWAY2_Y = RUNWAY1_Y + 170

GATE_Y = RUNWAY2_Y + 190

# Taxi nodes (explicit labels show where T_A, T_B... are)
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

KB = {
    "airport_name": "IAATCMS - Advanced Demo",
    "runways": {"RWY1": {"len_m":3500}, "RWY2": {"len_m":3200}},
    "gates": {g: {"size": "large" if i<2 else "medium" if i<4 else "small"} for i,g in enumerate(GATES)},
    "taxi_nodes": TAXI_NODES
}

# simulation params
MIN_SEPARATION_PX = 80
HOLD_RADIUS = 42
APPROACH_STEPS = 160
TAXI_SPEED = 70
APPROACH_SPEED = 160
RUNWAY_SEP_SEC = 6.0

# Emergency spawn probability per spawn (0.0-1.0)
EMERGENCY_PROB = 0.08

# ---------------------------
# Utilities
# ---------------------------
def dist(a,b): return math.hypot(a[0]-b[0], a[1]-b[1])
def clamp(x,a,b): return max(a, min(b,x))
def lerp(a,b,t): return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t)

def quad_bezier(p0,p1,p2,steps=100):
    pts=[]
    for i in range(steps+1):
        t = i/steps
        x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
        y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
        pts.append((x,y))
    return pts

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
# Fuzzy priority (same as before)
# ---------------------------
def tri(x,a,b,c):
    if x <= a or x >= c: return 0.0
    if x == b: return 1.0
    if x < b: return (x-a)/(b-a)
    return (c-x)/(c-b)

def fuzzy_priority(fuel_pct, weather, emergency=False):
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
    def h(n): return dist(nodes[n], nodes[goal])
    openq = [(h(start), 0.0, start, [start])]
    best = {start:0.0}
    visited = set()
    while openq:
        f,g,cur,path = heapq.heappop(openq)
        if cur == goal: return path
        if cur in visited: continue
        visited.add(cur)
        for nb in TAXI_ADJ.get(cur, []):
            if nb in blocked: continue
            ng = g + dist(nodes[cur], nodes[nb])
            if nb not in best or ng < best[nb]:
                best[nb] = ng
                heapq.heappush(openq, (ng + h(nb), ng, nb, path + [nb]))
    return None

# ---------------------------
# CSP Scheduler
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
# GA optimizer (same as earlier)
# ---------------------------
def ga_optimize_order(ids, fitness_fn, pop_size=32, gens=40, mut_rate=0.12):
    pop = [random.sample(ids, len(ids)) for _ in range(pop_size)]
    for _ in range(gens):
        scored = [(fitness_fn(ind), ind) for ind in pop]
        scored.sort(key=lambda x: x[0])
        pop = [ind for (_,ind) in scored[:pop_size//2]]
        children=[]
        while len(pop) + len(children) < pop_size:
            a = random.choice(pop); b = random.choice(pop)
            cut = random.randint(1, len(a)-1)
            child = a[:cut] + [x for x in b if x not in a[:cut]]
            if random.random() < mut_rate:
                i,j = random.sample(range(len(child)),2); child[i],child[j] = child[j],child[i]
            children.append(child)
        pop += children
    return min(pop, key=fitness_fn)

# ---------------------------
# END PART 1/3
# ---------------------------
# ---------------------------
# PART 2/3: Flight class, ATC dialog, PygameSim (improved funnels, highlight), separation & emergency
# ---------------------------

class Flight:
    counter = 3000
    def __init__(self, ftype="A320", fuel=None, weather=None, emergency=False, edge=None, req_slot=1):
        self.id = f"F{Flight.counter}"; Flight.counter += 1
        self.type = ftype
        self.fuel = fuel if fuel is not None else random.randint(8,95)
        self.weather = weather if weather is not None else round(random.random(),2)
        self.emergency = emergency
        self.priority = fuzzy_priority(self.fuel, self.weather, self.emergency)
        self.state = "spawning"
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
        self.altitude = 4000
        self.gate_timer = None
        self.target_runway = None
        self.highlight_until = 0.0  # highlight flashing end time

    def to_dict(self):
        return {"id":self.id, "slot":self.request_slot, "priority":self.priority, "type":self.type}

# ATC Dialog (non-blocking)
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

# PygameSim core
class PygameSim:
    def __init__(self, parent_frame, width=SIM_W, height=SIM_H):
        self.parent = parent_frame
        self.width = width; self.height = height
        os.environ['SDL_WINDOWID'] = str(self.parent.winfo_id())
        pygame.display.init(); pygame.font.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("IAATCMS Simulation")
        self.clock = pygame.time.Clock()

        self.flights = []
        self.logs = deque(maxlen=1000)
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
        self.radar_angle = 0.0

        # funnels
        self.funnels = {
            "RWY1": {"start": (-140, RUNWAY1_Y+40), "mid": (RUNWAY1_X + RUNWAY_LEN/2, RUNWAY1_Y + 190), "threshold": (RUNWAY1_X + 40, RUNWAY1_Y + RUNWAY_W//2)},
            "RWY2": {"start": (self.width+140, RUNWAY2_Y+40), "mid": (RUNWAY2_X + RUNWAY_LEN/2, RUNWAY2_Y + 190), "threshold": (RUNWAY2_X + 40, RUNWAY2_Y + RUNWAY_W//2)}
        }

        self._start_thread()

    def log(self, s):
        self.logs.appendleft(f"[{time.strftime('%H:%M:%S')}] {s}")

    def choose_runway_by_wind(self):
        return random.choice(["RWY1","RWY2"])

    def spawn_flight(self, ftype=None, emergency=None, prefer_runway=None):
        typ = ftype if ftype else random.choice(["A320","B737","A330","Turboprop"])
        if emergency is None: emergency = (random.random() < EMERGENCY_PROB)
        edge = random.choice(["left","right","top","bottom"])
        r = prefer_runway if prefer_runway else self.choose_runway_by_wind()
        if edge == "left":
            start = (-140 + random.uniform(-10,10), random.randint(80, self.height-80))
        elif edge == "right":
            start = (self.width+140 + random.uniform(-10,10), random.randint(80, self.height-80))
        elif edge == "top":
            start = (random.randint(80,self.width-80), -140 + random.uniform(-10,10))
        else:
            start = (random.randint(80,self.width-80), self.height+140 + random.uniform(-10,10))

        funnel = self.funnels[r]
        mid = (funnel["mid"][0] + random.uniform(-80,80), funnel["mid"][1] + random.uniform(-30,30))
        thresh = funnel["threshold"]
        path = quad_bezier(start, mid, thresh, steps=APPROACH_STEPS)
        path = smooth_path(path, iterations=2)
        f = Flight(typ, fuel=random.randint(8,95), weather=round(random.random(),2), emergency=emergency, edge=edge, req_slot=1+random.randint(0,4))
        f.approach_path = path; f.approach_index = 0; f.pos = path[0]; f.state = "approaching"; f.target_runway = r
        if emergency: f.priority = fuzzy_priority(f.fuel, f.weather, True)
        self.flights.append(f); self.log(f"Spawned {f.id} -> {r} (EMG={f.emergency})")
        return f

    def run_csp(self):
        to_sched = [fl.to_dict() for fl in self.flights if fl.state in ("approaching","holding","requesting","spawning")]
        if not to_sched:
            self.log("CSP: none")
            return {}
        cs = CSP_Scheduler(to_sched, ["RWY1","RWY2"], GATES, separation_slots=1)
        sol = cs.solve()
        if not sol:
            self.log("CSP: no solution")
            return {}
        for fid,val in sol.items():
            fo = next((x for x in self.flights if x.id == fid), None)
            if fo: fo.assigned = val
        self.log("CSP: assignments applied")
        return sol

    def violates_separation(self, f):
        for o in self.flights:
            if o is f: continue
            if o.state in ("landing","approaching","requesting","holding") and dist(f.pos, o.pos) < MIN_SEPARATION_PX:
                return True
        return False

    def step(self, dt):
        if self.auto_spawn and time.time() - self.last_spawn > 2.8:
            self.spawn_flight(); self.last_spawn = time.time()
        if self.auto_schedule and time.time() - self.last_schedule > 6.0:
            self.run_csp(); self.last_schedule = time.time()

        remove=[]
        for fl in list(self.flights):
            if fl.state == "approaching":
                if self.violates_separation(fl):
                    fl.state = "holding"; fl.hold_center = (fl.pos[0], fl.pos[1]-80); fl.hold_angle = random.uniform(0,360)
                    self.log(f"{fl.id} forced hold (spacing)")
                    continue
                fl.approach_index = min(len(fl.approach_path)-1, fl.approach_index + 1)
                fl.pos = fl.approach_path[fl.approach_index]
                fl.altitude = max(0, fl.altitude - 600*dt)
                if fl.approach_index >= len(fl.approach_path)-12:
                    runway = fl.target_runway
                    if time.time() < self.runway_busy_until.get(runway,0.0):
                        fl.state = "holding"; fl.hold_center = (fl.pos[0], fl.pos[1]-68); fl.hold_angle = 0.0
                        self.log(f"{fl.id} holding (runway busy)")
                        continue
                    else:
                        fl.state = "requesting"
                        def decision_cb(dec, f=fl, runway=runway):
                            if dec == "grant":
                                f.state = "landing"; f.landed_runway = runway
                                self.runway_busy_until[runway] = time.time() + self.runway_sep
                                f.highlight_until = time.time() + 6.0
                                self.log(f"{f.id} granted on {runway}")
                            elif dec == "hold":
                                f.state = "holding"; f.hold_center = (f.pos[0], f.pos[1]-80); f.hold_angle = 0.0
                                self.log(f"{f.id} told to hold")
                            elif dec == "divert":
                                f.state = "diverted"; self.log(f"{f.id} diverted")
                            else:
                                f.state = "holding"; f.hold_center = (f.pos[0], f.pos[1]-80)
                        if self.auto_decision_flag:
                            if fl.priority >= self.auto_decision_threshold: decision_cb("grant")
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
                if random.random() < 0.02: fl.state = "requesting"

            elif fl.state == "requesting":
                runway = getattr(fl, "target_runway", "RWY1")
                if time.time() < self.runway_busy_until.get(runway,0.0):
                    fl.state = "holding"; fl.hold_center = (fl.pos[0], fl.pos[1]-80); fl.hold_angle = 0.0
                    self.log(f"{fl.id} to hold (busy)")
                pass

            elif fl.state == "landing":
                if fl.landed_runway == "RWY1":
                    fl.pos = (fl.pos[0] + 160*dt, fl.pos[1])
                    if fl.pos[0] > RUNWAY1_X + RUNWAY_LEN*0.6: fl.state = "rollout"
                else:
                    fl.pos = (fl.pos[0] + 160*dt, fl.pos[1])
                    if fl.pos[0] > RUNWAY2_X + RUNWAY_LEN*0.6: fl.state = "rollout"

            elif fl.state == "rollout":
                if fl.assigned and not fl.taxi_path:
                    exit_node = "RWY1_EXIT" if fl.landed_runway == "RWY1" else "RWY2_EXIT"
                    gate_node = fl.assigned[1]
                    p = a_star_taxi(exit_node, gate_node, blocked=set())
                    if p:
                        fl.taxi_path = p; fl.taxi_index = 0.0; fl.state = "taxiing"; self.log(f"{fl.id} taxi {p}")
                    else:
                        fl.state = "at_gate"; self.log(f"{fl.id} parked (no taxi)")

            elif fl.state == "taxiing":
                if fl.taxi_path and int(fl.taxi_index) < len(fl.taxi_path):
                    node = fl.taxi_path[int(fl.taxi_index)]
                    tgt = TAXI_NODES.get(node)
                    if tgt:
                        dx = tgt[0]-fl.pos[0]; dy = tgt[1]-fl.pos[1]; d = math.hypot(dx,dy)
                        if d < 6:
                            fl.taxi_index += 1
                        else:
                            vx = dx/(d+1e-6)*TAXI_SPEED*dt; vy = dy/(d+1e-6)*TAXI_SPEED*dt
                            fl.pos = (fl.pos[0]+vx, fl.pos[1]+vy)
                    else:
                        fl.taxi_index += 1
                else:
                    fl.state = "at_gate"; fl.gate_timer = time.time(); self.log(f"{fl.id} at gate")

            elif fl.state == "diverted":
                if fl.entry_edge == "left": fl.pos = (fl.pos[0]-160*dt, fl.pos[1])
                elif fl.entry_edge == "right": fl.pos = (fl.pos[0]+160*dt, fl.pos[1])
                elif fl.entry_edge == "top": fl.pos = (fl.pos[0], fl.pos[1]-160*dt)
                else: fl.pos = (fl.pos[0], fl.pos[1]+160*dt)
                if (fl.pos[0] < -200 or fl.pos[0] > self.width+200 or fl.pos[1] < -200 or fl.pos[1] > self.height+200):
                    remove.append(fl)

            elif fl.state == "at_gate":
                if fl.gate_timer is None: fl.gate_timer = time.time()
                if time.time() - fl.gate_timer > 8.0: remove.append(fl)

        for r in remove:
            if r in self.flights: self.flights.remove(r)

    def draw(self):
        self.screen.fill((12,18,36))
        pygame.draw.rect(self.screen, (28,140,58), (0, RUNWAY1_Y - 140, self.width, RUNWAY2_Y + RUNWAY_W - (RUNWAY1_Y - 140) + 260))
        r1 = (RUNWAY1_X, RUNWAY1_Y, RUNWAY_LEN, RUNWAY_W)
        r2 = (RUNWAY2_X, RUNWAY2_Y, RUNWAY_LEN, RUNWAY_W)
        pygame.draw.rect(self.screen, (50,50,50), r1, border_radius=12); pygame.draw.rect(self.screen, (50,50,50), r2, border_radius=12)
        for rx, ry in ((RUNWAY1_X, RUNWAY1_Y),(RUNWAY2_X, RUNWAY2_Y)):
            for s in range(20, RUNWAY_LEN-20, 64):
                pygame.draw.rect(self.screen, (230,230,230), (rx + s, ry + RUNWAY_W//2 -5, 30, 10), border_radius=3)
        # taxiways and centerlines
        for a,b in [("RWY1_EXIT","T_A"),("T_A","T_B"),("T_B","T_C"),("T_C","T_D"),("T_D","RWY2_EXIT")]:
            if a in TAXI_NODES and b in TAXI_NODES:
                pygame.draw.line(self.screen, (120,120,120), TAXI_NODES[a], TAXI_NODES[b], 14)
                pygame.draw.line(self.screen, (80,80,80), TAXI_NODES[a], TAXI_NODES[b], 6)
        # gates and labels
        font_sm = pygame.font.SysFont("Arial", 12)
        for g,p in GATE_POS.items():
            pygame.draw.rect(self.screen, (220,220,220), (p[0]-20, p[1]-12, 40, 26), border_radius=4)
            self.screen.blit(font_sm.render(g, True, (20,20,20)), (p[0]-10, p[1]-10))
        # taxi nodes & labels (explicitly mark T_A, T_B etc)
        for name,coord in TAXI_NODES.items():
            pygame.draw.circle(self.screen, (70,70,70), (int(coord[0]), int(coord[1])), 6)
            # show label for T_* and RWY exits and G*
            if name.startswith("T_") or name.endswith("_EXIT") or name.startswith("G"):
                lbl = font_sm.render(name, True, (240,240,240))
                self.screen.blit(lbl, (coord[0]+8, coord[1]-8))
        # flights
        now = time.time()
        font_sm = pygame.font.SysFont("Arial", 12)
        for fl in self.flights:
            x,y = int(fl.pos[0]), int(fl.pos[1])
            col = (255,60,60) if fl.emergency else (30,30,30)
            size = 6 + int(6*fl.priority)
            # highlight if selected or recently cleared
            is_highlight = (fl.highlight_until > now)
            if is_highlight:
                # flashing halo
                alpha = int(128 + 127 * math.sin(now*10))
                # draw halo as circle with varying brightness
                halo_col = (255, 200, 50) if fl.emergency else (50,200,255)
                pygame.draw.circle(self.screen, halo_col, (x,y), size+10, 2)
            pygame.draw.circle(self.screen, (0,0,0), (x,y), size+2)
            pygame.draw.circle(self.screen, col, (x,y), size)
            self.screen.blit(font_sm.render(fl.id, True, (255,255,255)), (x + size + 6, y - size - 6))
            self.screen.blit(font_sm.render(fl.state, True, (220,220,220)), (x + size + 6, y + 2))
        # logs overlay
        font_mono = pygame.font.SysFont("Consolas", 12)
        ly = 6
        for line in list(self.logs)[:6]:
            self.screen.blit(font_mono.render(line, True, (220,220,220)), (6, ly)); ly += 16
        pygame.display.flip()

    def integrate_tk(self, tk_root, tk_callback):
        self.tk_root = tk_root; self.tk_callback = tk_callback

    # select flight by id (for highlighting)
    def highlight_flight(self, flight_id, seconds=6.0):
        f = next((x for x in self.flights if x.id == flight_id), None)
        if f:
            f.highlight_until = time.time() + seconds
            self.log(f"{f.id} highlighted")

    def _start_thread(self):
        def loop():
            prev = time.time()
            while self.running:
                now = time.time(); dt = now - prev; prev = now
                try:
                    self.step(dt)
                    self.draw()
                except Exception as e:
                    self.logs.appendleft(f"ERR {e}")
                self.clock.tick(FPS)
            pygame.quit()
        t = threading.Thread(target=loop, daemon=True); t.start()

    def stop(self):
        self.running = False

# ---------------------------
# END PART 2/3
# ---------------------------
# ---------------------------
# PART 3/3: Tabbed UI, radar click-to-highlight, embedded matplotlib dashboard, exports, Intelligent System Design text
# ---------------------------

class MainApp:
    def __init__(self, root):
        self.root = root
        root.title("IAATCMS — Intelligent Airport (Updated)")
        root.geometry("1500x900")

        # Notebook tabs
        self.notebook = ttk.Notebook(root); self.notebook.pack(fill="both", expand=True)
        self.tab_sim = ttk.Frame(self.notebook); self.notebook.add(self.tab_sim, text="Simulation")
        self.tab_radar = ttk.Frame(self.notebook); self.notebook.add(self.tab_radar, text="Radar")
        self.tab_dash = ttk.Frame(self.notebook); self.notebook.add(self.tab_dash, text="Dashboard")
        self.tab_logs = ttk.Frame(self.notebook); self.notebook.add(self.tab_logs, text="Logs")

        # Simulation tab layout: left controls, center sim, right info
        left = ttk.Frame(self.tab_sim, width=320); left.pack(side="left", fill="y", padx=6, pady=6)
        center = ttk.Frame(self.tab_sim); center.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        right = ttk.Frame(self.tab_sim, width=360); right.pack(side="right", fill="y", padx=6, pady=6)

        # left controls
        ttk.Label(left, text="ATC Controls", font=("Arial",14,"bold")).pack(pady=6)
        ttk.Button(left, text="Spawn Flight", command=self.spawn_click).pack(fill="x", pady=4)
        ttk.Button(left, text="Spawn Emergency Flight", command=lambda: self.spawn_click(emergency=True)).pack(fill="x", pady=4)
        ttk.Button(left, text="Run CSP Scheduler", command=self.run_csp_click).pack(fill="x", pady=4)
        self.auto_spawn_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Auto Spawn", variable=self.auto_spawn_var, command=self.toggle_auto_spawn).pack(anchor="w", pady=2)
        self.auto_schedule_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Auto Schedule", variable=self.auto_schedule_var, command=self.toggle_auto_schedule).pack(anchor="w", pady=2)
        ttk.Separator(left).pack(fill="x", pady=6)
        ttk.Label(left, text="Auto Decision (AI)", font=("Arial",11)).pack(pady=(4,0))
        self.auto_decision_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Enable Auto Decision", variable=self.auto_decision_var, command=self.toggle_auto_decision).pack(anchor="w")
        ttk.Label(left, text="Threshold (0.0 - 1.0)").pack(anchor="w", pady=(6,0))
        self.threshold_var = tk.DoubleVar(value=0.55)
        ttk.Scale(left, from_=0.0, to=1.0, variable=self.threshold_var, orient="horizontal").pack(fill="x", pady=2)
        ttk.Separator(left).pack(fill="x", pady=6)
        ttk.Button(left, text="Optimize Order (GA)", command=self.run_ga).pack(fill="x", pady=4)
        ttk.Button(left, text="Export Schedule CSV", command=self.export_csv).pack(fill="x", pady=4)
        ttk.Button(left, text="Intelligent System Design (report)", command=self.show_intel_design).pack(fill="x", pady=8)
        ttk.Label(left, text="Taxi nodes (map): T_A → T_B → T_C → T_D", foreground="#555").pack(pady=(8,0))

        # center sim container + embedded pygame
        sim_container = tk.Frame(center, width=SIM_W, height=SIM_H, bg="black")
        sim_container.pack(); sim_container.pack_propagate(False)
        self.sim = PygameSim(sim_container, width=SIM_W, height=SIM_H)
        self.sim.integrate_tk(self.root, lambda fn: self.root.after(1, fn))

        # right: flight list + selection
        ttk.Label(right, text="Flights", font=("Arial",12,"bold")).pack(pady=6)
        self.flight_listbox = tk.Listbox(right, width=44, height=28)
        self.flight_listbox.pack()
        self.flight_listbox.bind("<<ListboxSelect>>", self.on_select_flight)
        ttk.Button(right, text="Highlight Selected", command=self.highlight_selected).pack(fill="x", pady=6)
        ttk.Separator(right).pack(fill="x", pady=6)
        ttk.Label(right, text="Logs / Live Info", font=("Arial",12,"bold")).pack(pady=6)
        self.logs_text = tk.Text(right, width=44, height=12)
        self.logs_text.pack()

        # Radar tab: canvas + click binding
        self.radar_canvas = tk.Canvas(self.tab_radar, width=760, height=760, bg="black")
        self.radar_canvas.pack(padx=10, pady=10)
        self.radar_canvas.bind("<Button-1>", self.on_radar_click)

        # Dashboard tab: inline matplotlib charts (if available)
        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(10,6), dpi=100)
            self.ax1 = self.fig.add_subplot(221)
            self.ax2 = self.fig.add_subplot(222)
            self.ax3 = self.fig.add_subplot(223)
            self.ax4 = self.fig.add_subplot(224)
            self.canvas_fig = FigureCanvasTkAgg(self.fig, master=self.tab_dash)
            self.canvas_fig.get_tk_widget().pack(fill="both", expand=True)
        else:
            ttk.Label(self.tab_dash, text="matplotlib not installed. Install to see inline dashboard.").pack(pady=20)
            self.canvas_fig = None

        # Logs tab: full logs
        ttk.Label(self.tab_logs, text="System Logs", font=("Arial",12,"bold")).pack(pady=6)
        self.full_logs = tk.Text(self.tab_logs, width=200, height=40)
        self.full_logs.pack()

        # schedule UI updates
        self.root.after(600, self.ui_update)
        self.root.after(120, self.radar_update)

    # UI callbacks
    def spawn_click(self, emergency=False):
        f = self.sim.spawn_flight(emergency=emergency); self.append_log(f"Spawn {f.id} EMG={f.emergency}"); self.refresh_flight_list()

    def run_csp_click(self):
        sol = self.sim.run_csp()
        if sol: self.append_log("CSP assigned"); self.refresh_flight_list()
        else: self.append_log("CSP had no solution")

    def toggle_auto_spawn(self):
        self.sim.auto_spawn = self.auto_spawn_var.get(); self.append_log(f"Auto spawn {self.sim.auto_spawn}")

    def toggle_auto_schedule(self):
        self.sim.auto_schedule = self.auto_schedule_var.get(); self.append_log(f"Auto schedule {self.sim.auto_schedule}")

    def toggle_auto_decision(self):
        self.sim.auto_decision_flag = self.auto_decision_var.get()
        self.sim.auto_decision_threshold = float(self.threshold_var.get())
        self.append_log(f"Auto decision {self.sim.auto_decision_flag} thr={self.sim.auto_decision_threshold}")

    def run_ga(self):
        ids = [f.id for f in self.sim.flights]
        if not ids: self.append_log("GA: no flights"); return
        def fitness(order):
            pos = {fid:i for i,fid in enumerate(order)}
            cost=0.0
            for f in self.sim.flights:
                cost += pos.get(f.id, len(order)) * (1.0 - f.priority)
            return cost
        best = ga_optimize_order(ids, fitness_fn=fitness, pop_size=36, gens=50)
        self.append_log(f"GA best (first 10): {best[:10]}")
        messagebox.showinfo("GA result", f"Best order (first 10):\n{best[:10]}")

    def export_csv(self):
        rows=[]
        for f in self.sim.flights:
            if f.assigned:
                rows.append({"flight":f.id, "runway":f.assigned[0], "gate":f.assigned[1], "slot":f.assigned[2]})
        if not rows:
            messagebox.showinfo("Export", "No assignments to export"); return
        fname = tempfile.gettempdir() + os.sep + "iaatcms_schedule.csv"
        import csv
        with open(fname, "w", newline="") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=["flight","runway","gate","slot"])
            writer.writeheader()
            for r in rows: writer.writerow(r)
        messagebox.showinfo("Export", f"Saved to {fname}")

    def show_intel_design(self):
        txt = (
            "Intelligent System Design\n\n"
            "Architecture:\n"
            "- Input layer: live flights (fuel, weather, emergency), wind, runway status\n"
            "- Reasoning: Fuzzy logic for priority scoring (fuel, weather, emergency)\n"
            "- Search & planning:\n"
            "    * A* for taxi routing (taxi-node graph)\n"
            "    * CSP (backtracking) for runway/gate/slot assignment\n"
            "    * GA for landing order optimization\n"
            "- Execution: Pygame simulation + ATC decision dialogs\n"
            "- Dashboard & radar: monitoring and human-in-the-loop control\n\n"
            "Innovative aspects:\n"
            "- Multi-technique integration: fuzzy + CSP + A* + GA\n"
            "- Interactive radar ↔ simulation highlighting\n"
            "- Inline live analytics inside GUI\n"
            "- Safety-first automated heuristics (separation, runway lookahead)\n"
        )
        messagebox.showinfo("Intelligent System Design", txt)

    # flight list & highlight
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

    def highlight_selected(self):
        sel = self.flight_listbox.curselection()
        if not sel: return
        idx = sel[0]; f = self.sim.flights[idx]
        self.sim.highlight_flight(f.id, seconds=6.0)

    def append_log(self, s):
        ts = time.strftime("%H:%M:%S")
        self.logs_text.insert("1.0", f"[{ts}] {s}\n")
        self.logs_text.see("1.0")
        self.full_logs.insert("1.0", f"[{ts}] {s}\n")
        self.full_logs.see("1.0")

    def ui_update(self):
        # pull logs from sim
        while self.sim.logs:
            ln = self.sim.logs.pop(); self.append_log(ln)
        self.refresh_flight_list()
        # update inline dashboard
        if MATPLOTLIB_AVAILABLE and self.canvas_fig:
            try:
                flights = self.sim.flights
                ids = [f.id for f in flights]; pr = [f.priority for f in flights]
                fuels = [f.fuel for f in flights]; we = [f.weather for f in flights]
                assigned = [f.assigned[0] if f.assigned else "None" for f in flights]
                cnt = Counter(assigned)
                # clear axes
                self.ax1.clear(); self.ax2.clear(); self.ax3.clear(); self.ax4.clear()
                # hue-like scatter: use HSV colormap converted
                import colorsys
                colors = [colorsys.hsv_to_rgb(i/max(1,len(ids)-1), 0.8, 0.9) if len(ids)>1 else (0.4,0.8,0.9) for i in range(len(ids))]
                colors_rgb = [(r,g,b) for (r,g,b) in colors]
                if ids:
                    # priority scatter
                    self.ax1.scatter(ids, pr)
                    self.ax1.set_title("Priority Scores")
                    # fuel line
                    self.ax2.plot(ids, fuels, marker='o')
                    self.ax2.set_title("Fuel (%)")
                    # weather line
                    self.ax3.plot(ids, we, marker='o')
                    self.ax3.set_title("Weather severity")
                    # runway usage bar
                    self.ax4.bar(list(cnt.keys()), list(cnt.values()))
                    self.ax4.set_title("Runway usage")
                else:
                    for a in (self.ax1,self.ax2,self.ax3,self.ax4):
                        a.text(0.5,0.5,"No data", ha='center')
                self.fig.tight_layout()
                self.canvas_fig.draw()
            except Exception as e:
                # do not crash UI
                print("Dashboard update error:", e)
        # schedule next update
        self.root.after(800, self.ui_update)

    # Radar click → find nearest blip and highlight
    def radar_update(self):
        c = self.radar_canvas; c.delete("all")
        w = int(c['width']); h = int(c['height']); cx,cy = w//2, h//2
        for r in (60,120,180,240,300): c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#133f2b")
        if not hasattr(self.sim, "radar_angle"): self.sim.radar_angle = 0.0
        self.sim.radar_angle = (self.sim.radar_angle + 4) % 360
        ang = math.radians(self.sim.radar_angle)
        ex = cx + 300*math.cos(ang); ey = cy + 300*math.sin(ang)
        c.create_line(cx,cy, ex,ey, fill="#32ff4f", width=2)
        map_cx, map_cy = SIM_W/2, SIM_H/2; scale = 0.35
        self._radar_blips = []  # store (mx,my,flight_id)
        for f in self.sim.flights:
            mx = (f.pos[0] - map_cx)*scale + cx; my = (f.pos[1] - map_cy)*scale + cy
            color = "#ff4040" if f.emergency else "#00ffff"
            c.create_oval(mx-5,my-5,mx+5,my+5, fill=color, outline="")
            c.create_text(mx+8, my-6, text=f.id, fill="white", font=("Arial",8))
            self._radar_blips.append((mx,my,f.id))
        self.root.after(80, self.radar_update)

    def on_radar_click(self, event):
        if not hasattr(self, "_radar_blips"): return
        x,y = event.x, event.y
        # find nearest blip within threshold
        closest=None; dmin=9999
        for bx,by,fid in self._radar_blips:
            d = math.hypot(bx-x, by-y)
            if d < dmin:
                dmin=d; closest=(fid, bx, by)
        if closest and dmin < 28:
            fid = closest[0]
            self.sim.highlight_flight(fid, seconds=6.0)
            # also select it in listbox if present
            for i,f in enumerate(self.sim.flights):
                if f.id == fid:
                    self.flight_listbox.selection_clear(0, tk.END)
                    self.flight_listbox.selection_set(i)
                    self.flight_listbox.see(i)
                    break
            self.append_log(f"Radar clicked: {fid} (highlighted)")

# run app
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
