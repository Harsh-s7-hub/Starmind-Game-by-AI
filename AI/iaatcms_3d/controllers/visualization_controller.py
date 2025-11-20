# controllers/visualization_controller.py
"""
Coordinates rendering for both 2D and 3D views
Handles decluttering, highlighting, and visual effects
"""

import math
from typing import List, Dict, Tuple, Optional


class VisualizationController:
    """Manages all visualization and rendering logic"""
    
    def __init__(self):
        self.highlighted_flights = set()
        self.show_debug_overlay = False
        self.show_separation_corridors = False
        self.show_taxi_occupancy = False
        
        # Declutter settings
        self.label_force_layout_enabled = True
        self.min_label_distance = 30
        
        # Visual themes
        self.theme = "dark"  # or "light"
    
    def calculate_badge_positions(self, flights: List, canvas_width: int, canvas_height: int) -> Dict:
        """
        Calculate non-overlapping badge positions using force-directed layout
        
        Args:
            flights: List of flight objects with .pos attributes
            canvas_width: Canvas width in pixels
            canvas_height: Canvas height in pixels
        
        Returns:
            Dict of flight_id -> (badge_x, badge_y)
        """
        positions = {}
        
        if not flights:
            return positions
        
        # Initialize positions near aircraft
        for flight in flights:
            offset_x = 15  # Offset from aircraft icon
            offset_y = -10
            positions[flight.id] = (flight.pos[0] + offset_x, flight.pos[1] + offset_y)
        
        if not self.label_force_layout_enabled:
            return positions
        
        # Apply force-directed layout to reduce overlap
        for iteration in range(10):  # 10 iterations of force simulation
            forces = {fid: [0, 0] for fid in positions}
            
            # Repulsive forces between labels
            for i, (fid1, pos1) in enumerate(positions.items()):
                for j, (fid2, pos2) in enumerate(positions.items()):
                    if i >= j:
                        continue
                    
                    dx = pos2[0] - pos1[0]
                    dy = pos2[1] - pos1[1]
                    dist = math.hypot(dx, dy)
                    
                    if dist < self.min_label_distance and dist > 0:
                        # Repel
                        force_magnitude = (self.min_label_distance - dist) / dist
                        fx = -dx * force_magnitude
                        fy = -dy * force_magnitude
                        
                        forces[fid1][0] += fx
                        forces[fid1][1] += fy
                        forces[fid2][0] -= fx
                        forces[fid2][1] -= fy
            
            # Attractive forces to aircraft position
            for flight in flights:
                if flight.id in positions:
                    ideal_x = flight.pos[0] + 15
                    ideal_y = flight.pos[1] - 10
                    
                    current_x, current_y = positions[flight.id]
                    dx = ideal_x - current_x
                    dy = ideal_y - current_y
                    
                    forces[flight.id][0] += dx * 0.1
                    forces[flight.id][1] += dy * 0.1
            
            # Apply forces with damping
            damping = 0.5
            for fid in positions:
                x, y = positions[fid]
                fx, fy = forces[fid]
                
                new_x = x + fx * damping
                new_y = y + fy * damping
                
                # Clamp to canvas bounds
                new_x = max(10, min(canvas_width - 130, new_x))
                new_y = max(10, min(canvas_height - 55, new_y))
                
                positions[fid] = (new_x, new_y)
        
        return positions
    
    def get_separation_corridor_color(self, distance: float, min_separation: float) -> str:
        """
        Get color for separation corridor based on distance
        
        Args:
            distance: Current distance between aircraft
            min_separation: Minimum allowed separation
        
        Returns:
            Color string (hex)
        """
        if distance < min_separation * 0.7:
            return "#ff3333"  # Red - violation
        elif distance < min_separation:
            return "#ffaa33"  # Amber - warning
        else:
            return "#33aa33"  # Green - safe
    
    def get_taxi_edge_color(self, edge_id: Tuple[str, str], occupied_edges: Dict) -> str:
        """
        Get color for taxi edge based on occupancy
        
        Args:
            edge_id: Tuple of (node_a, node_b)
            occupied_edges: Dict of edge -> flight_id
        
        Returns:
            Color string (hex)
        """
        normalized_edge = tuple(sorted(edge_id))
        
        if normalized_edge in occupied_edges:
            return "#ff6666"  # Red - occupied
        else:
            return "#666666"  # Gray - free
    
    def highlight_flight(self, flight_id: str, duration: float = 5.0):
        """
        Add flight to highlight set
        
        Args:
            flight_id: ID of flight to highlight
            duration: How long to highlight (seconds)
        """
        self.highlighted_flights.add(flight_id)
        # Note: Caller should schedule removal after duration
    
    def unhighlight_flight(self, flight_id: str):
        """Remove flight from highlight set"""
        self.highlighted_flights.discard(flight_id)
    
    def is_highlighted(self, flight_id: str) -> bool:
        """Check if flight is currently highlighted"""
        return flight_id in self.highlighted_flights
    
    def get_flight_icon_size(self, flight) -> int:
        """
        Calculate icon size based on priority and highlight status
        
        Args:
            flight: Flight object
        
        Returns:
            Icon size in pixels
        """
        base_size = 10
        priority_bonus = int(6 * flight.priority)
        highlight_bonus = 4 if self.is_highlighted(flight.id) else 0
        
        return base_size + priority_bonus + highlight_bonus
    
    def get_flight_icon_color(self, flight) -> str:
        """
        Get color for flight icon
        
        Args:
            flight: Flight object
        
        Returns:
            Color string (hex)
        """
        if flight.emergency:
            return "#ff3333"  # Red
        elif self.is_highlighted(flight.id):
            return "#ffcc00"  # Yellow
        else:
            return "#333333"  # Dark gray
    
    def apply_theme(self, theme: str):
        """
        Switch visual theme
        
        Args:
            theme: "dark" or "light"
        """
        self.theme = theme
    
    def get_theme_colors(self) -> Dict[str, str]:
        """
        Get color palette for current theme
        
        Returns:
            Dict of color_name -> hex_color
        """
        if self.theme == "dark":
            return {
                "background": "#0c121c",
                "runway": "#323232",
                "taxiway": "#444444",
                "grass": "#1c4820",
                "text": "#ffffff",
                "text_dim": "#aaaaaa",
                "grid": "#0a3020"
            }
        else:  # light
            return {
                "background": "#e6f2ff",
                "runway": "#888888",
                "taxiway": "#999999",
                "grass": "#90ee90",
                "text": "#000000",
                "text_dim": "#555555",
                "grid": "#cccccc"
            }
    
    def calculate_world_bounds(self, flights: List) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box containing all flights
        
        Args:
            flights: List of flight objects
        
        Returns:
            (x_min, y_min, x_max, y_max)
        """
        if not flights:
            return (0, 0, 1100, 700)
        
        xs = [f.pos[0] for f in flights]
        ys = [f.pos[1] for f in flights]
        
        x_min = min(xs) - 100
        x_max = max(xs) + 100
        y_min = min(ys) - 100
        y_max = max(ys) + 100
        
        return (x_min, y_min, x_max, y_max)
    
    def draw_debug_overlay(self, canvas, data: Dict):
        """
        Draw debug information overlay
        
        Args:
            canvas: Canvas widget to draw on
            data: Debug data dict
        """
        if not self.show_debug_overlay:
            return
        
        # Draw debug text
        y_offset = 10
        for key, value in data.items():
            text = f"{key}: {value}"
            canvas.create_text(
                10, y_offset,
                text=text,
                fill="#00ff00",
                font=("Courier", 10),
                anchor="nw",
                tags="debug_overlay"
            )
            y_offset += 15
    
    def draw_separation_corridors(self, canvas, flights: List, min_separation: float):
        """
        Draw visual separation corridors between aircraft
        
        Args:
            canvas: Canvas widget
            flights: List of flights
            min_separation: Minimum separation distance
        """
        if not self.show_separation_corridors:
            return
        
        # Draw lines between nearby aircraft
        for i, flight1 in enumerate(flights):
            for flight2 in flights[i+1:]:
                dist = math.hypot(
                    flight1.pos[0] - flight2.pos[0],
                    flight1.pos[1] - flight2.pos[1]
                )
                
                if dist < min_separation * 2:
                    # Draw line with color based on distance
                    color = self.get_separation_corridor_color(dist, min_separation)
                    
                    canvas.create_line(
                        flight1.pos[0], flight1.pos[1],
                        flight2.pos[0], flight2.pos[1],
                        fill=color,
                        width=2,
                        dash=(3, 2),
                        tags="separation_corridor"
                    )
                    
                    # Draw distance label at midpoint
                    mid_x = (flight1.pos[0] + flight2.pos[0]) / 2
                    mid_y = (flight1.pos[1] + flight2.pos[1]) / 2
                    
                    canvas.create_text(
                        mid_x, mid_y,
                        text=f"{dist:.0f}px",
                        fill=color,
                        font=("Arial", 8),
                        tags="separation_corridor"
                    )
    
    def draw_taxi_occupancy(self, canvas, nodes: Dict, adj: Dict, occupied_edges: Dict):
        """
        Draw taxi network with occupancy coloring
        
        Args:
            canvas: Canvas widget
            nodes: Dict of node_name -> (x, y)
            adj: Dict of node_name -> [neighbors]
            occupied_edges: Dict of (node_a, node_b) -> flight_id
        """
        if not self.show_taxi_occupancy:
            return
        
        # Draw edges with occupancy colors
        drawn_edges = set()
        
        for node, neighbors in adj.items():
            if node not in nodes:
                continue
            
            x1, y1 = nodes[node]
            
            for neighbor in neighbors:
                if neighbor not in nodes:
                    continue
                
                edge = tuple(sorted([node, neighbor]))
                if edge in drawn_edges:
                    continue
                drawn_edges.add(edge)
                
                x2, y2 = nodes[neighbor]
                color = self.get_taxi_edge_color(edge, occupied_edges)
                
                canvas.create_line(
                    x1, y1, x2, y2,
                    fill=color,
                    width=6,
                    tags="taxi_occupancy"
                )
