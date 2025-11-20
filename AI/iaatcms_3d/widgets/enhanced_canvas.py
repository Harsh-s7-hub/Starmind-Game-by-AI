# widgets/enhanced_canvas.py
"""
Enhanced canvas widget with zoom, pan, and anti-aliased rendering
"""

import tkinter as tk
from tkinter import Canvas
import math


class EnhancedCanvas(Canvas):
    """Canvas with zoom/pan capabilities and smooth rendering"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # View transformation
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.zoom_level = 1.0
        
        # Pan state
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_panning = False
        
        # Bind mouse events
        self.bind("<ButtonPress-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.bind("<Button-4>", self._on_mouse_wheel)  # Linux scroll up
        self.bind("<Button-5>", self._on_mouse_wheel)  # Linux scroll down
        
        # Keyboard shortcuts
        self.bind("<Control-0>", lambda e: self.reset_view())
        self.bind("<Control-equal>", lambda e: self.zoom_in())
        self.bind("<Control-minus>", lambda e: self.zoom_out())
    
    def _on_mouse_down(self, event):
        """Start panning"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.is_panning = True
        self.config(cursor="fleur")
    
    def _on_mouse_drag(self, event):
        """Pan the view"""
        if self.is_panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            
            self.view_offset_x += dx
            self.view_offset_y += dy
            
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            
            # Trigger redraw (parent should handle)
            self.event_generate("<<ViewChanged>>")
    
    def _on_mouse_up(self, event):
        """Stop panning"""
        self.is_panning = False
        self.config(cursor="")
    
    def _on_mouse_wheel(self, event):
        """Zoom in/out"""
        # Get mouse position
        mx = event.x
        my = event.y
        
        # Determine zoom direction
        if event.num == 5 or event.delta < 0:
            # Zoom out
            factor = 0.9
        else:
            # Zoom in
            factor = 1.1
        
        # Calculate new zoom
        old_zoom = self.zoom_level
        self.zoom_level *= factor
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        
        # Adjust offset to zoom toward mouse
        zoom_delta = self.zoom_level / old_zoom
        self.view_offset_x = mx - (mx - self.view_offset_x) * zoom_delta
        self.view_offset_y = my - (my - self.view_offset_y) * zoom_delta
        
        self.event_generate("<<ViewChanged>>")
    
    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates"""
        sx = x * self.zoom_level + self.view_offset_x
        sy = y * self.zoom_level + self.view_offset_y
        return sx, sy
    
    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates"""
        x = (sx - self.view_offset_x) / self.zoom_level
        y = (sy - self.view_offset_y) / self.zoom_level
        return x, y
    
    def zoom_in(self):
        """Zoom in centered"""
        w = self.winfo_width()
        h = self.winfo_height()
        cx, cy = w / 2, h / 2
        
        old_zoom = self.zoom_level
        self.zoom_level *= 1.2
        self.zoom_level = min(5.0, self.zoom_level)
        
        zoom_delta = self.zoom_level / old_zoom
        self.view_offset_x = cx - (cx - self.view_offset_x) * zoom_delta
        self.view_offset_y = cy - (cy - self.view_offset_y) * zoom_delta
        
        self.event_generate("<<ViewChanged>>")
    
    def zoom_out(self):
        """Zoom out centered"""
        w = self.winfo_width()
        h = self.winfo_height()
        cx, cy = w / 2, h / 2
        
        old_zoom = self.zoom_level
        self.zoom_level *= 0.8
        self.zoom_level = max(0.1, self.zoom_level)
        
        zoom_delta = self.zoom_level / old_zoom
        self.view_offset_x = cx - (cx - self.view_offset_x) * zoom_delta
        self.view_offset_y = cy - (cy - self.view_offset_y) * zoom_delta
        
        self.event_generate("<<ViewChanged>>")
    
    def reset_view(self):
        """Reset to default view"""
        self.zoom_level = 1.0
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.event_generate("<<ViewChanged>>")
    
    def fit_to_window(self, world_bounds):
        """Fit world bounds to window"""
        x_min, y_min, x_max, y_max = world_bounds
        world_w = x_max - x_min
        world_h = y_max - y_min
        
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()
        
        if world_w == 0 or world_h == 0:
            return
        
        # Calculate zoom to fit
        zoom_x = canvas_w / world_w * 0.9  # 90% to leave margin
        zoom_y = canvas_h / world_h * 0.9
        self.zoom_level = min(zoom_x, zoom_y)
        
        # Center on bounds
        world_cx = (x_min + x_max) / 2
        world_cy = (y_min + y_max) / 2
        
        self.view_offset_x = canvas_w / 2 - world_cx * self.zoom_level
        self.view_offset_y = canvas_h / 2 - world_cy * self.zoom_level
        
        self.event_generate("<<ViewChanged>>")
    
    def draw_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        """Draw anti-aliased rounded rectangle"""
        # Convert to screen coords
        sx1, sy1 = self.world_to_screen(x1, y1)
        sx2, sy2 = self.world_to_screen(x2, y2)
        
        # Ensure correct order
        if sx1 > sx2:
            sx1, sx2 = sx2, sx1
        if sy1 > sy2:
            sy1, sy2 = sy2, sy1
        
        radius = radius * self.zoom_level
        
        # Draw using polygon approximation
        points = []
        
        # Top-left corner
        for i in range(0, 91, 15):
            angle = math.radians(180 + i)
            px = sx1 + radius + radius * math.cos(angle)
            py = sy1 + radius + radius * math.sin(angle)
            points.append((px, py))
        
        # Top-right corner
        for i in range(0, 91, 15):
            angle = math.radians(270 + i)
            px = sx2 - radius + radius * math.cos(angle)
            py = sy1 + radius + radius * math.sin(angle)
            points.append((px, py))
        
        # Bottom-right corner
        for i in range(0, 91, 15):
            angle = math.radians(0 + i)
            px = sx2 - radius + radius * math.cos(angle)
            py = sy2 - radius + radius * math.sin(angle)
            points.append((px, py))
        
        # Bottom-left corner
        for i in range(0, 91, 15):
            angle = math.radians(90 + i)
            px = sx1 + radius + radius * math.cos(angle)
            py = sy2 - radius + radius * math.sin(angle)
            points.append((px, py))
        
        return self.create_polygon(points, **kwargs, smooth=True)
    
    def draw_dashed_line(self, x1, y1, x2, y2, dash=(5, 3), **kwargs):
        """Draw dashed line with proper dash pattern"""
        sx1, sy1 = self.world_to_screen(x1, y1)
        sx2, sy2 = self.world_to_screen(x2, y2)
        
        return self.create_line(sx1, sy1, sx2, sy2, dash=dash, **kwargs)
    
    def draw_circle(self, cx, cy, radius, **kwargs):
        """Draw circle at world coordinates"""
        scx, scy = self.world_to_screen(cx, cy)
        sr = radius * self.zoom_level
        
        return self.create_oval(
            scx - sr, scy - sr,
            scx + sr, scy + sr,
            **kwargs
        )
    
    def draw_text(self, x, y, text, **kwargs):
        """Draw text at world coordinates"""
        sx, sy = self.world_to_screen(x, y)
        
        # Adjust font size for zoom
        if 'font' in kwargs:
            font_parts = kwargs['font']
            if isinstance(font_parts, tuple) and len(font_parts) >= 2:
                font_name, font_size = font_parts[0], font_parts[1]
                adjusted_size = max(8, int(font_size * self.zoom_level))
                kwargs['font'] = (font_name, adjusted_size) + font_parts[2:]
        
        return self.create_text(sx, sy, text=text, **kwargs)
