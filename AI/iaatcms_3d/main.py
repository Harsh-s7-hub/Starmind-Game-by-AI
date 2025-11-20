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

# Import professional airport layout system
from airport_layout_config import (
    SIM_W, SIM_H, TAXI_NODES, TAXI_ADJ, GATES, GATE_POS, KB,
    RUNWAY_MAIN, RUNWAY_SECONDARY
)
from airport_drawing import draw_complete_airport_layout, get_runway_threshold_position

# ---------------------------
# Configuration & geometry
# ---------------------------
FPS = 60

# All airport layout configuration now loaded from airport_layout_config.py
# TAXI_NODES, TAXI_ADJ, GATES, GATE_POS, KB, runways are imported above

# simulation params
MIN_SEPARATION_PX = 80
HOLD_RADIUS = 42
APPROACH_STEPS = 160
TAXI_SPEED = 70
APPROACH_SPEED = 160
RUNWAY_SEP_SEC = 6.0

# Flight management limits
MAX_FLIGHTS = 8  # Maximum simultaneous flights to prevent clustering
MAX_ACTIVE_FLIGHTS = 6  # Max flights in air/approaching (not at gates)

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

def draw_airplane(surface, x, y, heading=0, scale=1.0, color=(255,255,255), emergency=False):
    """Draw a realistic airplane shape (top-down view)"""
    # Define airplane shape (fuselage + wings + tail)
    if emergency:
        color = (255, 80, 80)  # Red for emergency
    
    # Scale points
    s = scale
    
    # Airplane body points (relative to center)
    fuselage = [
        (0, -12*s), (2*s, -10*s), (3*s, -6*s),  # nose
        (3*s, 6*s), (2*s, 10*s), (0, 12*s),     # tail
        (-2*s, 10*s), (-3*s, 6*s), (-3*s, -6*s), # left side
        (-2*s, -10*s)
    ]
    
    # Rotate and translate points
    angle = math.radians(heading)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    
    rotated = []
    for px, py in fuselage:
        rx = px * cos_a - py * sin_a + x
        ry = px * sin_a + py * cos_a + y
        rotated.append((rx, ry))
    
    # Draw airplane body
    pygame.draw.polygon(surface, color, rotated)
    pygame.draw.polygon(surface, (0,0,0), rotated, 2)  # outline
    
    # Draw wings
    wing_left = [
        (-3*s, -2*s), (-12*s, 0), (-12*s, 2*s), (-3*s, 2*s)
    ]
    wing_right = [
        (3*s, -2*s), (12*s, 0), (12*s, 2*s), (3*s, 2*s)
    ]
    
    for wing in [wing_left, wing_right]:
        wing_rot = []
        for px, py in wing:
            rx = px * cos_a - py * sin_a + x
            ry = px * sin_a + py * cos_a + y
            wing_rot.append((rx, ry))
        pygame.draw.polygon(surface, color, wing_rot)
        pygame.draw.polygon(surface, (0,0,0), wing_rot, 1)
    
    # Draw tail fins
    tail = [
        (-2*s, 8*s), (-6*s, 11*s), (-2*s, 11*s),
        (2*s, 8*s), (6*s, 11*s), (2*s, 11*s)
    ]
    
    for i in range(0, len(tail), 3):
        fin = [tail[i], tail[i+1], tail[i+2]]
        fin_rot = []
        for px, py in fin:
            rx = px * cos_a - py * sin_a + x
            ry = px * sin_a + py * cos_a + y
            fin_rot.append((rx, ry))
        pygame.draw.polygon(surface, color, fin_rot)
        pygame.draw.polygon(surface, (0,0,0), fin_rot, 1)

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

        # Load grass texture
        self.grass_texture = None
        grass_path = os.path.join(os.path.dirname(__file__), "assets", "grass_texture.jpg")
        if os.path.exists(grass_path):
            try:
                self.grass_texture = pygame.image.load(grass_path)
                # Scale to tile nicely
                self.grass_texture = pygame.transform.scale(self.grass_texture, (200, 200))
            except Exception as e:
                print(f"Could not load grass texture: {e}")
                self.grass_texture = None

        self.flights = []
        self.logs = deque(maxlen=1000)
        self.auto_spawn = False
        self.auto_schedule = False
        self.auto_decision_flag = False
        self.auto_decision_threshold = 0.55
        self.last_spawn = time.time()
        self.last_schedule = time.time()
        self.runway_sep = RUNWAY_SEP_SEC
        self.tk_root = None
        self.tk_callback = None
        self.running = True
        self.radar_angle = 0.0

        # Approach funnels - updated for new professional runway layout
        rwy_main = RUNWAY_MAIN
        self.funnels = {
            "09": {"start": (-140, rwy_main['y']+25), "mid": (rwy_main['x'] + rwy_main['length']/2, rwy_main['y'] + 200), "threshold": (rwy_main['x'] + 50, rwy_main['y'] + rwy_main['width']//2)},
            "27": {"start": (self.width+140, rwy_main['y']+25), "mid": (rwy_main['x'] + rwy_main['length']/2, rwy_main['y'] - 50), "threshold": (rwy_main['x'] + rwy_main['length'] - 50, rwy_main['y'] + rwy_main['width']//2)}
        }
        
        # Runway busy tracking (using new runway IDs)
        self.runway_busy_until = {"09": 0.0, "27": 0.0}

        self._start_thread()

    def log(self, s):
        self.logs.appendleft(f"[{time.strftime('%H:%M:%S')}] {s}")

    def choose_runway_by_wind(self):
        return random.choice(["09", "27"])
    
    def count_active_flights(self):
        """Count flights that are not at gates (to prevent clustering)"""
        active_states = ["approaching", "holding", "requesting", "landing", "rollout", "taxiing"]
        return sum(1 for f in self.flights if f.state in active_states)

    def spawn_flight(self, ftype=None, emergency=None, prefer_runway=None):
        # Check flight limits to prevent clustering
        if len(self.flights) >= MAX_FLIGHTS:
            self.log("Max flights reached. Wait for clearance.")
            return None
        
        active_count = self.count_active_flights()
        if active_count >= MAX_ACTIVE_FLIGHTS:
            self.log("Too many active flights. Wait for landings.")
            return None
        
        typ = ftype if ftype else random.choice(["A320","B737","A330","Turboprop"])
        if emergency is None: emergency = (random.random() < EMERGENCY_PROB)
        edge = random.choice(["left","right","top","bottom"])
        r = prefer_runway if prefer_runway else self.choose_runway_by_wind()
        # Constrain spawn positions to stay within reasonable bounds
        if edge == "left":
            start = (-100, random.randint(200, self.height-200))
        elif edge == "right":
            start = (self.width+100, random.randint(200, self.height-200))
        elif edge == "top":
            start = (random.randint(200, self.width-200), -100)
        else:
            start = (random.randint(200, self.width-200), self.height+100)

        funnel = self.funnels[r]
        # Constrain mid point to stay within bounds
        mid_x = clamp(funnel["mid"][0] + random.uniform(-60,60), 150, self.width-150)
        mid_y = clamp(funnel["mid"][1] + random.uniform(-20,20), 150, self.height-150)
        mid = (mid_x, mid_y)
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
        cs = CSP_Scheduler(to_sched, ["09", "27"], GATES, separation_slots=1)
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
            # Only spawn if under limits
            if len(self.flights) < MAX_FLIGHTS and self.count_active_flights() < MAX_ACTIVE_FLIGHTS:
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
                runway = getattr(fl, "target_runway", "09")
                if time.time() < self.runway_busy_until.get(runway,0.0):
                    fl.state = "holding"; fl.hold_center = (fl.pos[0], fl.pos[1]-80); fl.hold_angle = 0.0
                    self.log(f"{fl.id} to hold (busy)")
                pass

            elif fl.state == "landing":
                rwy = RUNWAY_MAIN
                # Aircraft rolling down runway towards exit
                if fl.landed_runway == "09":
                    fl.pos = (fl.pos[0] + 160*dt, fl.pos[1])
                    if fl.pos[0] > rwy['x'] + rwy['length']*0.7: fl.state = "rollout"
                else:  # 27
                    fl.pos = (fl.pos[0] + 160*dt, fl.pos[1])
                    if fl.pos[0] > rwy['x'] + rwy['length']*0.7: fl.state = "rollout"

            elif fl.state == "rollout":
                if fl.assigned and not fl.taxi_path:
                    # Use main runway exit (09 end)
                    exit_node = "RWY_09_EXIT" if fl.landed_runway == "09" else "RWY_27_EXIT"
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
        # Draw grass texture background
        if self.grass_texture:
            # Tile grass texture across entire screen
            tex_w, tex_h = self.grass_texture.get_size()
            for x in range(0, self.width, tex_w):
                for y in range(0, self.height, tex_h):
                    self.screen.blit(self.grass_texture, (x, y))
        else:
            # Fallback: nice grass green
            self.screen.fill((34, 139, 34))
        
        # ★★★ NEW PROFESSIONAL AIRPORT LAYOUT ★★★
        # Draw complete international airport with realistic markings
        draw_complete_airport_layout(self.screen)
        # flights - draw realistic airplane shapes
        now = time.time()
        font_sm = pygame.font.SysFont("Arial", 11, bold=True)
        font_state = pygame.font.SysFont("Arial", 9)
        
        for fl in self.flights:
            x, y = int(fl.pos[0]), int(fl.pos[1])
            
            # Calculate heading based on movement direction
            heading = 0
            if fl.state in ["approaching", "landing", "rollout"]:
                # Heading based on approach path or runway direction
                if hasattr(fl, 'approach_path') and fl.approach_path and fl.approach_index > 0:
                    if fl.approach_index < len(fl.approach_path):
                        curr = fl.approach_path[fl.approach_index]
                        prev = fl.approach_path[max(0, fl.approach_index - 5)]
                        dx = curr[0] - prev[0]
                        dy = curr[1] - prev[1]
                        if abs(dx) > 1 or abs(dy) > 1:
                            heading = math.degrees(math.atan2(dx, -dy))
            elif fl.state == "taxiing":
                # Heading based on taxi direction
                if fl.taxi_path and int(fl.taxi_index) < len(fl.taxi_path):
                    node = fl.taxi_path[int(fl.taxi_index)]
                    tgt = TAXI_NODES.get(node)
                    if tgt:
                        dx = tgt[0] - fl.pos[0]
                        dy = tgt[1] - fl.pos[1]
                        if abs(dx) > 1 or abs(dy) > 1:
                            heading = math.degrees(math.atan2(dx, -dy))
            elif fl.state == "holding":
                # Rotate in holding pattern
                heading = (now * 50) % 360
            
            # Scale based on priority (larger = higher priority)
            scale = 0.8 + (fl.priority * 0.4)
            
            # Highlight if selected or recently cleared
            is_highlight = (fl.highlight_until > now)
            if is_highlight:
                # Draw pulsing halo
                pulse = int(128 + 127 * math.sin(now * 8))
                halo_col = (255, 200, 50) if fl.emergency else (50, 200, 255)
                halo_radius = 25 + int(5 * math.sin(now * 6))
                pygame.draw.circle(self.screen, halo_col, (x, y), halo_radius, 3)
            
            # Draw airplane shape
            airplane_color = (255, 255, 255) if not fl.emergency else (255, 100, 100)
            draw_airplane(self.screen, x, y, heading, scale, airplane_color, fl.emergency)
            
            # Flight ID label (with background for readability)
            id_label = font_sm.render(fl.id, True, (255, 255, 255))
            id_bg_rect = id_label.get_rect(center=(x + 30, y - 15))
            id_bg_rect.inflate_ip(6, 2)
            pygame.draw.rect(self.screen, (0, 0, 0, 200), id_bg_rect, border_radius=3)
            if fl.emergency:
                pygame.draw.rect(self.screen, (255, 0, 0), id_bg_rect, width=2, border_radius=3)
            self.screen.blit(id_label, (x + 30 - id_label.get_width()//2, y - 15 - id_label.get_height()//2))
            
            # State label (smaller, below ID)
            state_label = font_state.render(fl.state, True, (200, 200, 200))
            self.screen.blit(state_label, (x + 30 - state_label.get_width()//2, y + 2))
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
        
        # Modern dark theme styling
        self.setup_modern_theme()
        root.configure(bg='#0f1419')

        # Notebook tabs with modern styling
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self.tab_sim = tk.Frame(self.notebook, bg='#0f1419')
        self.notebook.add(self.tab_sim, text="Simulation")
        self.tab_radar = tk.Frame(self.notebook, bg='#0f1419')
        self.notebook.add(self.tab_radar, text="Radar")
        self.tab_dash = tk.Frame(self.notebook, bg='#0f1419')
        self.notebook.add(self.tab_dash, text="Dashboard")
        self.tab_logs = tk.Frame(self.notebook, bg='#0f1419')
        self.notebook.add(self.tab_logs, text="Logs")

        # Simulation tab layout: left controls, center sim, right info
        left = tk.Frame(self.tab_sim, width=320, bg='#1a1f2e', highlightbackground='#2d3548', highlightthickness=1)
        left.pack(side="left", fill="y", padx=8, pady=8)
        center = tk.Frame(self.tab_sim, bg='#0f1419')
        center.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        right = tk.Frame(self.tab_sim, width=360, bg='#1a1f2e', highlightbackground='#2d3548', highlightthickness=1)
        right.pack(side="right", fill="y", padx=8, pady=8)

        # left controls with modern styling
        # Header with gradient effect
        header_frame = tk.Frame(left, bg='#1a1f2e', height=60)
        header_frame.pack(fill="x", pady=(0, 12))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="✈ ATC Controls", 
                              font=("Segoe UI", 18, "bold"), 
                              bg='#1a1f2e', fg='#ffffff')
        title_label.pack(pady=15)
        
        # Status indicator
        status_frame = tk.Frame(left, bg='#2d3548', height=35)
        status_frame.pack(fill="x", padx=12, pady=(0, 10))
        status_frame.pack_propagate(False)
        
        self.status_indicator = tk.Label(status_frame, text="● SYSTEM READY",
                                        font=("Segoe UI", 9, "bold"),
                                        bg='#2d3548', fg='#2ecc71')
        self.status_indicator.pack(pady=7)
        
        # Control section header
        controls_header = tk.Label(left, text="Flight Management",
                                  font=("Segoe UI", 11, "bold"),
                                  bg='#1a1f2e', fg='#95a5a6')
        controls_header.pack(anchor="w", padx=12, pady=(8, 6))
        
        # Create styled buttons with icons
        self.create_modern_button(left, "🛫 Spawn Flight", self.spawn_click).pack(fill="x", padx=12, pady=4)
        self.create_modern_button(left, "🚨 Spawn Emergency", 
                                 lambda: self.spawn_click(emergency=True), 
                                 bg='#e74c3c').pack(fill="x", padx=12, pady=4)
        self.create_modern_button(left, "📋 Run CSP Scheduler", self.run_csp_click).pack(fill="x", padx=12, pady=4)
        
        # Card-style auto controls
        auto_card = tk.Frame(left, bg='#252d3d', highlightbackground='#3d4a5f', highlightthickness=1)
        auto_card.pack(fill="x", padx=12, pady=10)
        
        auto_card_label = tk.Label(auto_card, text="Automation",
                                  font=("Segoe UI", 10, "bold"),
                                  bg='#252d3d', fg='#3498db')
        auto_card_label.pack(anchor="w", padx=10, pady=(8, 4))
        
        # Auto controls with modern checkboxes
        self.auto_spawn_var = tk.BooleanVar(value=False)
        auto_spawn_check = tk.Checkbutton(auto_card, text="⚡ Auto Spawn", variable=self.auto_spawn_var, 
                                         command=self.toggle_auto_spawn,
                                         bg='#252d3d', fg='#ffffff', selectcolor='#2d3548',
                                         activebackground='#252d3d', activeforeground='#3498db',
                                         font=("Segoe UI", 10))
        auto_spawn_check.pack(anchor="w", padx=10, pady=3)
        
        self.auto_schedule_var = tk.BooleanVar(value=False)
        auto_sched_check = tk.Checkbutton(auto_card, text="🔄 Auto Schedule", variable=self.auto_schedule_var,
                                         command=self.toggle_auto_schedule,
                                         bg='#252d3d', fg='#ffffff', selectcolor='#2d3548',
                                         activebackground='#252d3d', activeforeground='#3498db',
                                         font=("Segoe UI", 10))
        auto_sched_check.pack(anchor="w", padx=10, pady=(3, 8))
        
        # AI Decision card
        ai_card = tk.Frame(left, bg='#252d3d', highlightbackground='#3d4a5f', highlightthickness=1)
        ai_card.pack(fill="x", padx=12, pady=10)
        
        ai_label = tk.Label(ai_card, text="🤖 Auto Decision (AI)", font=("Segoe UI", 11, "bold"),
                           bg='#252d3d', fg='#3498db')
        ai_label.pack(anchor="w", padx=10, pady=(8, 4))
        
        self.auto_decision_var = tk.BooleanVar(value=False)
        auto_dec_check = tk.Checkbutton(ai_card, text="Enable Auto Decision", variable=self.auto_decision_var,
                                       command=self.toggle_auto_decision,
                                       bg='#252d3d', fg='#ffffff', selectcolor='#2d3548',
                                       activebackground='#252d3d', activeforeground='#3498db',
                                       font=("Segoe UI", 10))
        auto_dec_check.pack(anchor="w", padx=10, pady=3)
        
        # Threshold with value display
        thresh_container = tk.Frame(ai_card, bg='#252d3d')
        thresh_container.pack(fill="x", padx=10, pady=(6, 8))
        
        thresh_label = tk.Label(thresh_container, text="Decision Threshold", 
                               bg='#252d3d', fg='#95a5a6', font=("Segoe UI", 9))
        thresh_label.pack(anchor="w")
        
        self.threshold_var = tk.DoubleVar(value=0.55)
        self.threshold_display = tk.Label(thresh_container, text="0.55",
                                         bg='#252d3d', fg='#3498db', font=("Segoe UI", 11, "bold"))
        self.threshold_display.pack(anchor="e")
        
        threshold_scale = tk.Scale(thresh_container, from_=0.0, to=1.0, variable=self.threshold_var,
                                  orient="horizontal", resolution=0.01,
                                  bg='#252d3d', fg='#ffffff', troughcolor='#1a1f2e',
                                  highlightthickness=0, sliderrelief='flat',
                                  activebackground='#3498db',
                                  command=self.update_threshold_display)
        threshold_scale.pack(fill="x", pady=(2, 0))
        
        # Optimization section header
        opt_header = tk.Label(left, text="Optimization & Export",
                             font=("Segoe UI", 11, "bold"),
                             bg='#1a1f2e', fg='#95a5a6')
        opt_header.pack(anchor="w", padx=12, pady=(16, 6))
        
        # Additional controls
        self.create_modern_button(left, "⚙ Optimize Order (GA)", self.run_ga).pack(fill="x", padx=12, pady=4)
        self.create_modern_button(left, "💾 Export Schedule CSV", self.export_csv).pack(fill="x", padx=12, pady=4)
        self.create_modern_button(left, "📊 System Design Report", self.show_intel_design,
                                 bg='#9b59b6').pack(fill="x", padx=12, pady=4)
        
        # Info footer with icon
        info_footer = tk.Frame(left, bg='#252d3d')
        info_footer.pack(fill="x", padx=12, pady=(16, 8))
        
        info_label = tk.Label(info_footer, text="ℹ Taxi Path: T_A → T_B → T_C → T_D",
                             bg='#252d3d', fg='#7f8c8d', font=("Consolas", 8))
        info_label.pack(pady=6)

        # center sim container + embedded pygame
        sim_container = tk.Frame(center, width=SIM_W, height=SIM_H, bg="black")
        sim_container.pack(); sim_container.pack_propagate(False)
        self.sim = PygameSim(sim_container, width=SIM_W, height=SIM_H)
        self.sim.integrate_tk(self.root, lambda fn: self.root.after(1, fn))

        # right: flight list + selection with modern styling
        # Header with gradient
        flights_header = tk.Frame(right, bg='#1a1f2e', height=60)
        flights_header.pack(fill="x", pady=(0, 8))
        flights_header.pack_propagate(False)
        
        flights_label = tk.Label(flights_header, text="✈ Active Flights", font=("Segoe UI", 16, "bold"),
                                bg='#1a1f2e', fg='#ffffff')
        flights_label.pack(pady=15)
        
        # Flight count badge
        self.flight_count_label = tk.Label(right, text="0 Flights Active",
                                          font=("Segoe UI", 9),
                                          bg='#2d3548', fg='#3498db',
                                          padx=10, pady=4)
        self.flight_count_label.pack(padx=12, pady=(0, 8))
        
        # Flight listbox card
        listbox_card = tk.Frame(right, bg='#252d3d', highlightbackground='#3d4a5f', highlightthickness=1)
        listbox_card.pack(padx=12, pady=(0, 8), fill="both", expand=True)
        
        self.flight_listbox = tk.Listbox(listbox_card, width=40, height=24,
                                         bg='#252d3d', fg='#ffffff',
                                         selectbackground='#3498db', selectforeground='#ffffff',
                                         font=("Consolas", 9),
                                         highlightthickness=0, borderwidth=0)
        self.flight_listbox.pack(padx=2, pady=2, fill="both", expand=True)
        self.flight_listbox.bind("<<ListboxSelect>>", self.on_select_flight)
        
        self.create_modern_button(right, "🎯 Highlight Selected", self.highlight_selected).pack(fill="x", padx=12, pady=8)
        
        # Logs section with card
        logs_header = tk.Label(right, text="📋 Live System Logs", font=("Segoe UI", 12, "bold"),
                             bg='#1a1f2e', fg='#ffffff')
        logs_header.pack(pady=(12, 8))
        
        logs_card = tk.Frame(right, bg='#252d3d', highlightbackground='#3d4a5f', highlightthickness=1)
        logs_card.pack(padx=12, pady=(0, 12), fill="both", expand=True)
        
        self.logs_text = tk.Text(logs_card, width=40, height=10,
                                bg='#252d3d', fg='#95a5a6',
                                font=("Consolas", 8),
                                highlightthickness=0, borderwidth=0,
                                wrap="word")
        self.logs_text.pack(padx=2, pady=2, fill="both", expand=True)

        # Radar tab: canvas + click binding with modern styling
        self.radar_canvas = tk.Canvas(self.tab_radar, width=760, height=760, 
                                     bg="#0a0e14", highlightthickness=0)
        self.radar_canvas.pack(padx=20, pady=20)
        self.radar_canvas.bind("<Button-1>", self.on_radar_click)

        # Dashboard tab: inline matplotlib charts (if available)
        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(10,6), dpi=100, facecolor='#1a1f2e')
            self.ax1 = self.fig.add_subplot(221, facecolor='#2d3548')
            self.ax2 = self.fig.add_subplot(222, facecolor='#2d3548')
            self.ax3 = self.fig.add_subplot(223, facecolor='#2d3548')
            self.ax4 = self.fig.add_subplot(224, facecolor='#2d3548')
            self.canvas_fig = FigureCanvasTkAgg(self.fig, master=self.tab_dash)
            self.canvas_fig.get_tk_widget().pack(fill="both", expand=True)
        else:
            no_mpl_label = tk.Label(self.tab_dash, 
                                   text="matplotlib not installed. Install to see inline dashboard.",
                                   bg='#0f1419', fg='#95a5a6', font=("Segoe UI", 12))
            no_mpl_label.pack(pady=20)
            self.canvas_fig = None

        # Logs tab: full logs with modern styling
        logs_title = tk.Label(self.tab_logs, text="System Logs", font=("Segoe UI", 14, "bold"),
                             bg='#0f1419', fg='#ffffff')
        logs_title.pack(pady=12)
        
        logs_container = tk.Frame(self.tab_logs, bg='#2d3548')
        logs_container.pack(padx=20, pady=(0, 20), fill="both", expand=True)
        
        self.full_logs = tk.Text(logs_container, width=200, height=40,
                                bg='#2d3548', fg='#95a5a6',
                                font=("Consolas", 9),
                                highlightthickness=0, borderwidth=0)
        self.full_logs.pack(padx=2, pady=2, fill="both", expand=True)

        # schedule UI updates
        self.root.after(600, self.ui_update)
        self.root.after(120, self.radar_update)

    def setup_modern_theme(self):
        """Configure modern dark theme styling"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure notebook tabs
        style.configure('TNotebook', background='#0f1419', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1a1f2e', foreground='#95a5a6',
                       padding=[20, 10], font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab',
                 background=[('selected', '#2d3548')],
                 foreground=[('selected', '#ffffff')])
    
    def create_modern_button(self, parent, text, command, bg='#3498db'):
        """Create a modern styled button with hover effects"""
        btn = tk.Button(parent, text=text, command=command,
                       bg=bg, fg='#ffffff',
                       font=('Segoe UI', 10, 'bold'),
                       relief='flat', borderwidth=0,
                       padx=20, pady=10,
                       cursor='hand2',
                       activebackground=self.lighten_color(bg),
                       activeforeground='#ffffff')
        
        # Hover effects
        def on_enter(e):
            btn['background'] = self.lighten_color(bg)
        
        def on_leave(e):
            btn['background'] = bg
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    def lighten_color(self, hex_color, factor=0.2):
        """Lighten a hex color by a factor"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def update_threshold_display(self, value):
        """Update the threshold value display"""
        self.threshold_display.config(text=f"{float(value):.2f}")
    
    def update_status(self, message, color='#2ecc71'):
        """Update the status indicator"""
        self.status_indicator.config(text=f"● {message}", fg=color)
    
    def update_flight_count(self):
        """Update the flight count badge"""
        count = len(self.sim.flights)
        active = self.sim.count_active_flights()
        self.flight_count_label.config(text=f"{count} Total | {active} Active")

    # UI callbacks
    def spawn_click(self, emergency=False):
        f = self.sim.spawn_flight(emergency=emergency)
        if f:
            self.append_log(f"Spawn {f.id} EMG={f.emergency}")
            self.refresh_flight_list()
            status_msg = "EMERGENCY SPAWNED" if emergency else "FLIGHT SPAWNED"
            self.update_status(status_msg, '#e74c3c' if emergency else '#2ecc71')
        else:
            self.append_log("Cannot spawn: Flight limit reached or too many active flights")
            self.update_status("SPAWN FAILED - LIMIT REACHED", '#e74c3c')
            messagebox.showwarning("Flight Limit", 
                f"Cannot spawn new flight.\n\nCurrent: {len(self.sim.flights)}/{MAX_FLIGHTS} flights\nActive: {self.sim.count_active_flights()}/{MAX_ACTIVE_FLIGHTS}\n\nWait for flights to land and reach gates.")

    def run_csp_click(self):
        sol = self.sim.run_csp()
        if sol:
            self.append_log("CSP assigned")
            self.refresh_flight_list()
            self.update_status("CSP SCHEDULE COMPLETE", '#3498db')
        else:
            self.append_log("CSP had no solution")
            self.update_status("CSP FAILED - NO SOLUTION", '#e67e22')

    def toggle_auto_spawn(self):
        self.sim.auto_spawn = self.auto_spawn_var.get()
        self.append_log(f"Auto spawn {self.sim.auto_spawn}")
        status = "AUTO SPAWN ENABLED" if self.sim.auto_spawn else "AUTO SPAWN DISABLED"
        self.update_status(status, '#3498db' if self.sim.auto_spawn else '#95a5a6')

    def toggle_auto_schedule(self):
        self.sim.auto_schedule = self.auto_schedule_var.get()
        self.append_log(f"Auto schedule {self.sim.auto_schedule}")
        status = "AUTO SCHEDULE ENABLED" if self.sim.auto_schedule else "AUTO SCHEDULE DISABLED"
        self.update_status(status, '#3498db' if self.sim.auto_schedule else '#95a5a6')

    def toggle_auto_decision(self):
        self.sim.auto_decision_flag = self.auto_decision_var.get()
        self.sim.auto_decision_threshold = float(self.threshold_var.get())
        self.append_log(f"Auto decision {self.sim.auto_decision_flag} thr={self.sim.auto_decision_threshold}")
        status = "AI DECISION ENABLED" if self.sim.auto_decision_flag else "AI DECISION DISABLED"
        self.update_status(status, '#9b59b6' if self.sim.auto_decision_flag else '#95a5a6')

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
            tag = " 🚨" if f.emergency else ""
            ass = f.assigned[0] if f.assigned else "None"
            self.flight_listbox.insert(tk.END, f"{f.id} | {f.type} | pr:{f.priority:.2f} | {f.state} | {ass}{tag}")
        # Update flight count badge
        self.update_flight_count()

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
