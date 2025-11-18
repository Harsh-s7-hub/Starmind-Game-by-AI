# backend/game_engine.py
import random
import time
import threading
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple
from backend.pathfinding import Grid, a_star_search

SECTOR_COLS = 20
SECTOR_ROWS = 20

def coord_to_sector(x_percent: float, y_percent: float) -> Tuple[int,int]:
    """Convert 0-100 float coords to grid sector coords (0..cols-1)"""
    sx = min(SECTOR_COLS-1, max(0, int(x_percent / 100.0 * SECTOR_COLS)))
    sy = min(SECTOR_ROWS-1, max(0, int(y_percent / 100.0 * SECTOR_ROWS)))
    return (sx, sy)

def sector_to_coord(sx: int, sy: int) -> Tuple[float, float]:
    """Convert sector back to center percent coordinates (0..100)"""
    cx = (sx + 0.5) / SECTOR_COLS * 100.0
    cy = (sy + 0.5) / SECTOR_ROWS * 100.0
    return (cx, cy)

@dataclass
class Fleet:
    id: int
    owner: str            # civilization name or 'HUMANITY'
    from_sector: Tuple[int,int]
    to_sector: Tuple[int,int]
    path: List[Tuple[int,int]] = field(default_factory=list)
    position_index: int = 0   # index along path
    speed: float = 1.0        # steps per tick
    strength: int = 50

    def to_dict(self):
        return {
            "id": self.id,
            "owner": self.owner,
            "from_sector": self.from_sector,
            "to_sector": self.to_sector,
            "path": self.path,
            "position_index": self.position_index,
            "speed": self.speed,
            "strength": self.strength
        }

@dataclass
class Civilization:
    id: int
    name: str
    type: str
    x: float
    y: float
    power: int
    trust: int
    relation: str = "unknown"
    territory: int = 3
    contacted: bool = False
    resources: Dict[str, int] = field(default_factory=dict)
    allied_with: List[str] = field(default_factory=list)
    trades_with: List[str] = field(default_factory=list)
    at_war_with: List[str] = field(default_factory=list)
    strategy: str = "balanced"   # placeholder strategy label

    def to_dict(self):
        d = asdict(self)
        return d

class GameEngine:
    def __init__(self, num_civs=60, tick_rate=1.0):
        self.num_civs = num_civs
        self.civs: List[Civilization] = []
        self.fleets: Dict[int, Fleet] = {}
        self.next_fleet_id = 1
        self.player = {
            "name": "Commander",
            "credits": 5000,
            "power": 120,
            "systems": 1,
            "allies": 0,
        }
        self.tick_rate = tick_rate  # seconds per tick
        self.running = False
        self.lock = threading.RLock()
        self.grid = Grid(SECTOR_COLS, SECTOR_ROWS)
        self.generate_civs(num_civs)
        self._ai_tick_hooks = []
        self._thread = None

    def generate_civs(self, n=60):
        # fixed name list for determinism
        names = [
            "Nexus Collective","Quantum Dominion","Ethereal Syndicate","Void Sentinels",
            "Stellar Commonwealth","Nova Empire","Crimson Legion","Azure Federation",
            "Golden Dynasty","Shadow Concord","Crystal Alliance","Iron Imperium",
            "Cosmic Brotherhood","Titan Confederacy","Phoenix Coalition","Dragon Supremacy",
            "Omega Hegemony","Alpha Consortium","Beta Republic","Gamma Sovereignty",
            "Delta Order","Epsilon League","Zeta Kingdom","Theta Union","Iota Dominion",
            "Kappa Empire","Lambda State","Sigma Collective","Tau Federation","Omega Alliance",
            "Celestial Empire","Astral Kingdom","Nebula Confederacy","Starborn Union","Void Walkers",
            "Light Bearers","Dark Matter Syndicate","Gravity Lords","Time Keepers","Space Nomads",
            "Galactic Traders","Merchant Guild","Warrior Clans","Priest Council","Scholar Society",
            "Artist Commune","Builder Federation","Explorer League","Guardian Order","Sentinel Watch",
            "Protector Alliance","Defender Pact","Hunter Brotherhood","Seeker Collective","Finder Guild",
            "Keeper Society","Watcher Network","Observer Union","Monitor Coalition","Tracker Federation"
        ]
        civ_types = ['peaceful','aggressive','trading','isolationist','expansionist','diplomatic']
        self.civs = []
        for i in range(min(n, len(names))):
            x = random.uniform(5, 95)
            y = random.uniform(5, 95)
            civ = Civilization(
                id=i,
                name=names[i],
                type=random.choice(civ_types),
                x=x,
                y=y,
                power=random.randint(40, 100),
                trust=random.randint(20, 80),
                relation='unknown',
                territory=random.randint(3, 12),
                resources={
                    "energy": random.randint(200, 1000),
                    "minerals": random.randint(200, 1000),
                    "technology": random.randint(100, 700),
                    "population": random.randint(1000, 8000)
                },
                strategy=random.choice(['aggressive','defensive','trader','diplomat','balanced'])
            )
            self.civs.append(civ)

    def set_player_name(self, name):
        with self.lock:
            self.player['name'] = name

    def get_state(self):
        with self.lock:
            return {
                "player": dict(self.player),
                "civilizations": [c.to_dict() for c in self.civs],
                "fleets": [f.to_dict() for f in self.fleets.values()],
                "timestamp": time.time()
            }

    # ---------------- Actions: negotiate / trade / attack / send_fleet ----------------
    def action_negotiate(self, civ_id: int):
        with self.lock:
            if civ_id < 0 or civ_id >= len(self.civs):
                return False, "Invalid civ id"
            civ = self.civs[civ_id]
            chance = civ.trust / 100.0 + 0.25
            success = random.random() < chance
            if success:
                civ.trust = min(100, civ.trust + 20)
                if civ.trust > 60 and 'HUMANITY' not in civ.allied_with:
                    civ.relation = 'friendly'
                    civ.allied_with.append('HUMANITY')
                    self.player['credits'] += 800
                    self.player['allies'] = sum(1 for c in self.civs if 'HUMANITY' in c.allied_with)
                    return True, f"Alliance formed with {civ.name} (+800 credits)."
                return True, f"Negotiation successful with {civ.name}. Trust +20%."
            else:
                civ.trust = max(0, civ.trust - 15)
                civ.relation = 'neutral' if civ.trust > 40 else 'hostile'
                return False, f"Negotiation failed with {civ.name}. Trust -15%."

    def action_trade(self, civ_id: int):
        with self.lock:
            if civ_id < 0 or civ_id >= len(self.civs):
                return False, "Invalid civ id"
            civ = self.civs[civ_id]
            if civ.relation == 'hostile' or 'HUMANITY' in civ.at_war_with:
                return False, f"{civ.name} refuses to trade (hostile)."
            if self.player['credits'] < 400:
                return False, "Insufficient credits to trade."
            self.player['credits'] -= 400
            self.player['power'] += 25
            civ.trust = min(100, civ.trust + 10)
            if civ.name not in civ.trades_with:
                civ.trades_with.append('HUMANITY')
            return True, f"Traded with {civ.name}: -400 credits, +25 power."

    def action_attack(self, civ_id: int):
        with self.lock:
            if civ_id < 0 or civ_id >= len(self.civs):
                return False, "Invalid civ id"
            civ = self.civs[civ_id]
            # simple resolution; can be replaced by fleet combat later
            player_strength = self.player['power'] + random.randint(0, 50)
            civ_strength = civ.power + random.randint(0, 50)
            if player_strength >= civ_strength:
                credits_gained = civ.territory * 150
                self.player['credits'] += credits_gained
                self.player['systems'] += max(0, civ.territory // 2)
                civ.power = max(20, civ.power - 40)
                civ.territory = max(1, civ.territory - 3)
                civ.trust = 0
                civ.relation = 'hostile'
                if 'HUMANITY' not in civ.at_war_with:
                    civ.at_war_with.append('HUMANITY')
                return True, f"Victory over {civ.name}! +{credits_gained} credits."
            else:
                credits_lost = int(self.player['credits'] * 0.25)
                self.player['credits'] = max(0, self.player['credits'] - credits_lost)
                self.player['power'] = max(10, self.player['power'] - 25)
                civ.relation = 'hostile'
                if 'HUMANITY' not in civ.at_war_with:
                    civ.at_war_with.append('HUMANITY')
                return False, f"Defeat against {civ.name}. Lost {credits_lost} credits."

    def send_fleet(self, owner: str, from_percent: Tuple[float,float], to_percent: Tuple[float,float], strength=50, speed=1.0):
        """Create a fleet that travels via A* between sectors."""
        with self.lock:
            from_sector = coord_to_sector(from_percent[0], from_percent[1])
            to_sector = coord_to_sector(to_percent[0], to_percent[1])
            path = a_star_search(self.grid, from_sector, to_sector)
            if not path:
                return False, "No path available"
            fleet = Fleet(
                id=self.next_fleet_id,
                owner=owner,
                from_sector=from_sector,
                to_sector=to_sector,
                path=path,
                position_index=0,
                speed=speed,
                strength=strength
            )
            self.fleets[self.next_fleet_id] = fleet
            self.next_fleet_id += 1
            return True, f"Fleet {fleet.id} launched from {from_sector} to {to_sector}."

    # ---------------- Engine tick / autonomous AI ----------------
    def tick(self):
        """Single engine tick doing: move fleets, simple AI decisions, random events."""
        with self.lock:
            # Move fleets
            remove_ids = []
            for fid, fleet in list(self.fleets.items()):
                # increment position according to speed
                fleet.position_index += int(fleet.speed)
                if fleet.position_index >= len(fleet.path):
                    # fleet arrived
                    # resolve arrival: if fleet owned by player -> capture/attack presence
                    # find civs at arrival sector
                    sx, sy = fleet.to_sector
                    # convert to percent center to compare
                    cx, cy = sector_to_coord(sx, sy)
                    # resolve simple arrival: if any civ with sector matches -> combat or diplomacy
                    for civ in self.civs:
                        csx, csy = coord_to_sector(civ.x, civ.y)
                        if (csx, csy) == (sx, sy):
                            # simple battle resolution: fleet strength vs civ.power
                            if fleet.owner == 'HUMANITY':
                                if fleet.strength + random.randint(0,30) > civ.power:
                                    # victory: reduce civ and claim systems
                                    credit_gain = civ.territory * 100
                                    self.player['credits'] += credit_gain
                                    civ.power = max(20, civ.power - 30)
                                    civ.relation = 'hostile'
                                    if 'HUMANITY' not in civ.at_war_with:
                                        civ.at_war_with.append('HUMANITY')
                                    # fleet disbands on victory
                                    remove_ids.append(fid)
                                else:
                                    # fleet destroyed
                                    remove_ids.append(fid)
                            else:
                                # AI fleet arrival — can attack player or other civs (basic)
                                if civ.name == 'HUMANITY' or ('HUMANITY' in civ.allied_with):
                                    # attack player (simple effect)
                                    self.player['power'] = max(0, self.player['power'] - 20)
                                remove_ids.append(fid)
                    # If no civ there, just remove (arrived)
                    if fid not in remove_ids:
                        remove_ids.append(fid)

            for fid in remove_ids:
                self.fleets.pop(fid, None)

            # AI decisions per civ
            for civ in self.civs:
                # small chance to perform a local action depending on strategy and trust
                if random.random() < 0.08:
                    # pick other civ to interact with
                    target = random.choice(self.civs)
                    if target.id == civ.id:
                        continue
                    # if aggressive -> possible attack
                    if civ.strategy == 'aggressive' and random.random() < 0.5:
                        # launch fleet towards target
                        self.send_fleet(civ.name, (civ.x, civ.y), (target.x, target.y),
                                        strength=int(civ.power * 0.5), speed=1.0)
                    elif civ.strategy == 'trader' and random.random() < 0.6:
                        # trading increases resources
                        civ.trust = min(100, civ.trust + 5)
                        civ.resources['minerals'] += random.randint(10,50)
                    elif civ.strategy == 'diplomat' and random.random() < 0.5:
                        # attempt to form alliance
                        if civ.trust > 50 and 'HUMANITY' not in civ.allied_with and random.random() < 0.2:
                            civ.allied_with.append('HUMANITY')
                            self.player['allies'] = sum(1 for c in self.civs if 'HUMANITY' in c.allied_with)
                    # small resource drift
                    civ.resources['energy'] = max(0, civ.resources['energy'] + random.randint(-20, 30))
                    civ.resources['population'] = max(0, civ.resources['population'] + random.randint(-30, 50))

            # random events
            if random.random() < 0.03:
                # a random civ does a big move: expansion or war
                c = random.choice(self.civs)
                if c.type == 'expansionist' and random.random() < 0.6:
                    c.territory += 1
                    c.power = min(100, c.power + 5)
                elif c.type == 'aggressive' and random.random() < 0.4:
                    # declare war on another civ
                    target = random.choice(self.civs)
                    if target.id != c.id:
                        c.at_war_with.append(target.name)
                        c.relation = 'hostile'

            # periodic small trust drift
            for civ in self.civs:
                if random.random() < 0.02:
                    civ.trust = max(0, min(100, civ.trust + random.randint(-3, 3)))
                    if civ.trust < 30:
                        civ.relation = 'hostile'
                    elif civ.trust > 65:
                        civ.relation = 'friendly'

            # hook callbacks (if frontend needs custom behavior)
            for hook in self._ai_tick_hooks:
                try:
                    hook(self)
                except Exception:
                    pass

    # simple GA: tweak strategies over time (placeholder)
    def evolve_strategies(self):
        with self.lock:
            # score civs by resources & power
            scored = [(c.power + (c.resources.get('technology',0)//10), c) for c in self.civs]
            scored.sort(reverse=True, key=lambda x: x[0])
            top = [c for _,c in scored[:max(1, len(scored)//6)]]
            # let top influence others
            for c in self.civs:
                if c not in top and random.random() < 0.2:
                    influencer = random.choice(top)
                    c.strategy = influencer.strategy if random.random() < 0.6 else c.strategy
                    # mutation chance
                    if random.random() < 0.05:
                        c.strategy = random.choice(['aggressive','defensive','trader','diplomat','balanced'])

    # ---------------- engine run control ----------------
    def start(self):
        if self.running:
            return
        self.running = True
        def loop():
            last_evolve = time.time()
            while self.running:
                self.tick()
                # evolve every 60 ticks (approx)
                if time.time() - last_evolve > 60:
                    self.evolve_strategies()
                    last_evolve = time.time()
                time.sleep(self.tick_rate)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None
