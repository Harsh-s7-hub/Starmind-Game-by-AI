# widgets/mini_radar.py
"""
Mini radar display with sweep animation
"""

import tkinter as tk
import math


class MiniRadar(tk.Canvas):
    """Circular radar display with sweep line"""
    
    def __init__(self, parent, size=200, **kwargs):
        super().__init__(parent, width=size, height=size, 
                        bg="black", highlightthickness=0, **kwargs)
        
        self.size = size
        self.center_x = size // 2
        self.center_y = size // 2
        self.radius = size // 2 - 10
        
        self.sweep_angle = 0
        self.flights = []
        self.selected_flight = None
        
        self._draw_static_elements()
        self._start_sweep()
        
        self.bind("<Button-1>", self._on_click)
    
    def _draw_static_elements(self):
        """Draw radar rings and markers"""
        # Concentric circles
        for r in [0.33, 0.66, 1.0]:
            rad = int(self.radius * r)
            self.create_oval(
                self.center_x - rad, self.center_y - rad,
                self.center_x + rad, self.center_y + rad,
                outline="#0a3020", width=1
            )
        
        # Crosshairs
        self.create_line(
            self.center_x, self.center_y - self.radius,
            self.center_x, self.center_y + self.radius,
            fill="#0a3020", width=1
        )
        self.create_line(
            self.center_x - self.radius, self.center_y,
            self.center_x + self.radius, self.center_y,
            fill="#0a3020", width=1
        )
        
        # Labels
        self.create_text(
            self.center_x, 5,
            text="RADAR", fill="#32ff4f",
            font=("Arial", 8, "bold")
        )
    
    def _start_sweep(self):
        """Start sweep animation"""
        self._animate_sweep()
    
    def _animate_sweep(self):
        """Animate radar sweep line"""
        # Remove old sweep line
        self.delete("sweep")
        
        # Draw new sweep line
        angle_rad = math.radians(self.sweep_angle)
        end_x = self.center_x + self.radius * math.cos(angle_rad)
        end_y = self.center_y + self.radius * math.sin(angle_rad)
        
        self.create_line(
            self.center_x, self.center_y,
            end_x, end_y,
            fill="#32ff4f", width=2,
            tags="sweep"
        )
        
        # Update angle
        self.sweep_angle = (self.sweep_angle + 3) % 360
        
        # Schedule next frame
        self.after(50, self._animate_sweep)
    
    def update_flights(self, flights, map_bounds):
        """Update flight positions on radar"""
        # Remove old blips
        self.delete("blip")
        self.delete("blip_label")
        
        self.flights = []
        
        if not map_bounds:
            return
        
        x_min, y_min, x_max, y_max = map_bounds
        map_w = x_max - x_min
        map_h = y_max - y_min
        
        if map_w == 0 or map_h == 0:
            return
        
        for flight in flights:
            if flight.state in ("diverted", "removed", "completed"):
                continue
            
            # Normalize position to radar
            norm_x = (flight.pos[0] - x_min) / map_w
            norm_y = (flight.pos[1] - y_min) / map_h
            
            # Convert to radar coordinates (centered)
            radar_x = self.center_x + (norm_x - 0.5) * self.radius * 1.8
            radar_y = self.center_y + (norm_y - 0.5) * self.radius * 1.8
            
            # Choose color
            color = "#ff4040" if flight.emergency else "#00ffff"
            
            # Draw blip
            blip_size = 4
            blip = self.create_oval(
                radar_x - blip_size, radar_y - blip_size,
                radar_x + blip_size, radar_y + blip_size,
                fill=color, outline="", tags=("blip", f"blip_{flight.id}")
            )
            
            # Draw label
            label = self.create_text(
                radar_x + 8, radar_y - 6,
                text=flight.id,
                fill="white",
                font=("Arial", 7),
                anchor="w",
                tags=("blip_label", f"blip_{flight.id}")
            )
            
            self.flights.append((flight, blip, label, radar_x, radar_y))
    
    def _on_click(self, event):
        """Handle click on radar blip"""
        click_x = event.x
        click_y = event.y
        
        # Find nearest blip
        min_dist = float('inf')
        clicked_flight = None
        
        for flight, blip, label, radar_x, radar_y in self.flights:
            dist = math.hypot(radar_x - click_x, radar_y - click_y)
            if dist < 15 and dist < min_dist:
                min_dist = dist
                clicked_flight = flight
        
        if clicked_flight:
            self.selected_flight = clicked_flight
            self.event_generate("<<RadarFlightSelected>>")
