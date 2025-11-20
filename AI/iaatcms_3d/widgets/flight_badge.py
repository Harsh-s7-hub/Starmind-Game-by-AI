# widgets/flight_badge.py
"""
Flight badge widget showing call sign, priority bar, and detailed tooltip
"""

import tkinter as tk
from tkinter import ttk


class FlightBadge:
    """Visual badge for flight information"""
    
    def __init__(self, canvas, flight, x, y):
        self.canvas = canvas
        self.flight = flight
        self.x = x
        self.y = y
        self.items = []
        
        self.width = 120
        self.height = 45
        
        self._create_badge()
    
    def _create_badge(self):
        """Create badge visual elements"""
        # Background rectangle
        bg_color = "#ff4444" if self.flight.emergency else "#2a2a2a"
        self.items.append(
            self.canvas.create_rectangle(
                self.x, self.y,
                self.x + self.width, self.y + self.height,
                fill=bg_color, outline="#555", width=1,
                tags=("badge", f"badge_{self.flight.id}")
            )
        )
        
        # Call sign text
        self.items.append(
            self.canvas.create_text(
                self.x + 5, self.y + 5,
                text=self.flight.id,
                fill="white",
                font=("Arial", 10, "bold"),
                anchor="nw",
                tags=("badge", f"badge_{self.flight.id}")
            )
        )
        
        # Priority bar background
        bar_x = self.x + 5
        bar_y = self.y + 22
        bar_width = self.width - 10
        bar_height = 8
        
        self.items.append(
            self.canvas.create_rectangle(
                bar_x, bar_y,
                bar_x + bar_width, bar_y + bar_height,
                fill="#444", outline="",
                tags=("badge", f"badge_{self.flight.id}")
            )
        )
        
        # Priority bar fill
        fill_width = int(bar_width * self.flight.priority)
        bar_color = self._get_priority_color(self.flight.priority)
        
        self.items.append(
            self.canvas.create_rectangle(
                bar_x, bar_y,
                bar_x + fill_width, bar_y + bar_height,
                fill=bar_color, outline="",
                tags=("badge", f"badge_{self.flight.id}")
            )
        )
        
        # Info text (fuel, ETA, etc.)
        info_text = f"Fuel:{self.flight.fuel}% | {self.flight.state}"
        self.items.append(
            self.canvas.create_text(
                self.x + 5, self.y + 33,
                text=info_text,
                fill="#aaa",
                font=("Arial", 7),
                anchor="nw",
                tags=("badge", f"badge_{self.flight.id}")
            )
        )
        
        # Bind hover for tooltip
        for item in self.items:
            self.canvas.tag_bind(item, "<Enter>", self._on_enter)
            self.canvas.tag_bind(item, "<Leave>", self._on_leave)
    
    def _get_priority_color(self, priority):
        """Get color based on priority level"""
        if priority >= 0.8:
            return "#ff3333"  # Red - urgent
        elif priority >= 0.5:
            return "#ffaa33"  # Orange - medium
        else:
            return "#33aa33"  # Green - low
    
    def _on_enter(self, event):
        """Show detailed tooltip on hover"""
        tooltip_text = self._build_tooltip_text()
        
        # Create tooltip window
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        
        label = tk.Label(
            self.tooltip,
            text=tooltip_text,
            background="#333",
            foreground="white",
            relief="solid",
            borderwidth=1,
            font=("Courier", 9),
            justify="left",
            padx=8,
            pady=5
        )
        label.pack()
    
    def _on_leave(self, event):
        """Hide tooltip"""
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()
            del self.tooltip
    
    def _build_tooltip_text(self):
        """Build detailed tooltip content"""
        lines = [
            f"Flight ID: {self.flight.id}",
            f"Type: {self.flight.type}",
            f"State: {self.flight.state}",
            f"Priority: {self.flight.priority:.3f}",
            f"Fuel: {self.flight.fuel}%",
            f"Weather: {self.flight.weather}",
            f"Emergency: {'YES' if self.flight.emergency else 'No'}",
        ]
        
        if self.flight.assigned:
            runway, gate, slot = self.flight.assigned
            lines.append(f"Assigned: {runway}/{gate}@{slot}")
        
        if self.flight.taxi_path:
            path_str = " → ".join(self.flight.taxi_path[:4])
            if len(self.flight.taxi_path) > 4:
                path_str += "..."
            lines.append(f"Taxi: {path_str}")
        
        return "\n".join(lines)
    
    def update_position(self, x, y):
        """Move badge to new position"""
        dx = x - self.x
        dy = y - self.y
        
        for item in self.items:
            self.canvas.move(item, dx, dy)
        
        self.x = x
        self.y = y
    
    def destroy(self):
        """Remove badge from canvas"""
        for item in self.items:
            self.canvas.delete(item)
        self.items.clear()
