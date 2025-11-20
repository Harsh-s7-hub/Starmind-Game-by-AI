# controllers/simulation_controller.py
"""
Manages simulation state, flight lifecycle, and time progression
Thread-safe with callbacks for UI updates
"""

import time
import threading
import math
from collections import deque
from typing import List, Dict, Callable, Optional, Tuple


class SimulationController:
    """Central controller for simulation logic"""
    
    def __init__(self):
        self.flights = []
        self.time_tick = 0.0
        self.sim_speed = 1.0
        self.paused = False
        self.running = False
        
        self.runway_busy_until = {"RWY1": 0.0, "RWY2": 0.0}
        self.gate_busy_until = {}
        self.taxi_edge_occupied = {}  # (node_a, node_b) -> flight_id
        
        self.logs = deque(maxlen=500)
        self.kpis = {
            "total_landings": 0,
            "total_diversions": 0,
            "avg_wait_time": 0.0,
            "runway_utilization": {"RWY1": 0.0, "RWY2": 0.0},
            "emergency_handled": 0
        }
        
        # Callbacks for UI updates
        self.on_flight_updated = None
        self.on_log_added = None
        self.on_kpi_updated = None
        
        self._lock = threading.RLock()
    
    def start(self):
        """Start simulation loop"""
        with self._lock:
            self.running = True
    
    def stop(self):
        """Stop simulation"""
        with self._lock:
            self.running = False
    
    def pause(self):
        """Pause/unpause simulation"""
        with self._lock:
            self.paused = not self.paused
    
    def set_speed(self, speed: float):
        """Set simulation speed multiplier"""
        with self._lock:
            self.sim_speed = max(0.1, min(10.0, speed))
    
    def step(self, dt: float):
        """Advance simulation by dt seconds"""
        if self.paused or not self.running:
            return
        
        with self._lock:
            dt *= self.sim_speed
            self.time_tick += dt
            
            # Update all flights
            for flight in list(self.flights):
                self._update_flight(flight, dt)
            
            # Clean up finished flights
            self._cleanup_flights()
            
            # Update KPIs
            self._update_kpis()
    
    def _update_flight(self, flight, dt: float):
        """Update single flight state"""
        state = flight.state
        
        if state == "approaching":
            self._update_approaching(flight, dt)
        elif state == "holding":
            self._update_holding(flight, dt)
        elif state == "landing":
            self._update_landing(flight, dt)
        elif state == "taxiing":
            self._update_taxiing(flight, dt)
        elif state == "at_gate":
            self._update_at_gate(flight, dt)
        elif state == "diverted":
            self._update_diverted(flight, dt)
    
    def _update_approaching(self, flight, dt: float):
        """Update aircraft on approach"""
        if not hasattr(flight, 'approach_index'):
            flight.approach_index = 0
        
        if flight.approach_path and flight.approach_index < len(flight.approach_path) - 1:
            # Move along approach path
            speed = 160 * dt  # pixels per second
            flight.approach_index = min(len(flight.approach_path) - 1, 
                                       flight.approach_index + 1)
            flight.pos = flight.approach_path[int(flight.approach_index)]
            
            # Near threshold - request landing
            if flight.approach_index >= len(flight.approach_path) - 12:
                flight.state = "requesting"
    
    def _update_holding(self, flight, dt: float):
        """Update aircraft in holding pattern"""
        if not hasattr(flight, 'hold_angle'):
            flight.hold_angle = 0.0
        
        flight.hold_angle = (flight.hold_angle + 80 * dt) % 360
        cx, cy = getattr(flight, 'hold_center', (flight.pos[0], flight.pos[1] - 60))
        radius = 42
        
        angle_rad = math.radians(flight.hold_angle)
        flight.pos = (
            cx + radius * math.cos(angle_rad),
            cy + radius * math.sin(angle_rad)
        )
    
    def _update_landing(self, flight, dt: float):
        """Update aircraft during landing roll"""
        if hasattr(flight, 'landed_runway'):
            flight.pos = (flight.pos[0] + 160 * dt, flight.pos[1])
            
            # Check if reached rollout position
            if flight.pos[0] > 800:  # threshold
                flight.state = "rollout"
                self.log(f"{flight.id} completed landing roll")
    
    def _update_taxiing(self, flight, dt: float):
        """Update aircraft taxiing to gate"""
        if not flight.taxi_path or not hasattr(flight, 'taxi_index'):
            flight.state = "at_gate"
            return
        
        taxi_index = int(flight.taxi_index)
        if taxi_index >= len(flight.taxi_path):
            flight.state = "at_gate"
            flight.gate_timer = self.time_tick
            self.log(f"{flight.id} arrived at gate")
            return
        
        # Move toward next node
        target_node = flight.taxi_path[taxi_index]
        # Implementation continues with actual node positions
        flight.taxi_index += 70 * dt  # speed
    
    def _update_at_gate(self, flight, dt: float):
        """Update aircraft at gate (turnaround)"""
        if not hasattr(flight, 'gate_timer'):
            flight.gate_timer = self.time_tick
        
        # After 8 seconds at gate, mark for removal
        if self.time_tick - flight.gate_timer > 8.0:
            flight.state = "completed"
    
    def _update_diverted(self, flight, dt: float):
        """Update diverted aircraft leaving airspace"""
        # Move away from airport
        flight.pos = (flight.pos[0] - 160 * dt, flight.pos[1])
        
        # Remove when far away
        if flight.pos[0] < -200:
            flight.state = "removed"
    
    def _cleanup_flights(self):
        """Remove completed/diverted flights"""
        to_remove = [f for f in self.flights if f.state in ("completed", "removed")]
        for flight in to_remove:
            self.flights.remove(flight)
            if flight.state == "completed":
                self.kpis["total_landings"] += 1
            else:
                self.kpis["total_diversions"] += 1
    
    def _update_kpis(self):
        """Calculate current KPIs"""
        if self.on_kpi_updated:
            self.on_kpi_updated(self.kpis)
    
    def log(self, message: str):
        """Add log entry with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.appendleft(log_entry)
        
        if self.on_log_added:
            self.on_log_added(log_entry)
    
    def add_flight(self, flight):
        """Add new flight to simulation"""
        with self._lock:
            self.flights.append(flight)
            self.log(f"Flight {flight.id} spawned (Priority: {flight.priority:.2f})")
    
    def get_flights_safe(self) -> List:
        """Thread-safe copy of flights list"""
        with self._lock:
            return list(self.flights)
    
    def request_runway_clearance(self, flight, runway: str) -> bool:
        """Check if runway is available"""
        with self._lock:
            return self.time_tick >= self.runway_busy_until.get(runway, 0.0)
    
    def grant_runway(self, flight, runway: str, duration: float = 6.0):
        """Grant runway access to flight"""
        with self._lock:
            self.runway_busy_until[runway] = self.time_tick + duration
            flight.state = "landing"
            flight.landed_runway = runway
            self.log(f"{flight.id} cleared to land on {runway}")
            
            if flight.emergency:
                self.kpis["emergency_handled"] += 1
    
    def reserve_taxi_edge(self, flight, node_a: str, node_b: str) -> bool:
        """Reserve taxi edge for flight"""
        edge = tuple(sorted([node_a, node_b]))
        with self._lock:
            if edge not in self.taxi_edge_occupied:
                self.taxi_edge_occupied[edge] = flight.id
                return True
            return False
    
    def release_taxi_edge(self, flight, node_a: str, node_b: str):
        """Release taxi edge"""
        edge = tuple(sorted([node_a, node_b]))
        with self._lock:
            if self.taxi_edge_occupied.get(edge) == flight.id:
                del self.taxi_edge_occupied[edge]
