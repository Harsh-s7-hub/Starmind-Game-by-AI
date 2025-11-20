# widgets/ai_visualizer.py
"""
Visualizers for AI algorithms (A*, GA, CSP)
"""

import tkinter as tk
from tkinter import ttk
import math


class AStarVisualizer(tk.Toplevel):
    """Visualize A* pathfinding with open/closed sets"""
    
    def __init__(self, parent, nodes, path_data):
        super().__init__(parent)
        self.title("A* Pathfinding Visualization")
        self.geometry("800x600")
        
        self.nodes = nodes
        self.path_data = path_data
        self.current_step = 0
        
        # Controls
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(side="top", fill="x", padx=5, pady=5)
        
        ttk.Button(ctrl_frame, text="◀ Prev", command=self.prev_step).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="Next ▶", command=self.next_step).pack(side="left", padx=2)
        ttk.Button(ctrl_frame, text="▶▶ Play", command=self.play).pack(side="left", padx=2)
        
        self.step_label = ttk.Label(ctrl_frame, text="Step: 0 / 0")
        self.step_label.pack(side="left", padx=10)
        
        # Canvas
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Info panel
        info_frame = ttk.Frame(self)
        info_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        self.info_text = tk.Text(info_frame, height=4, wrap="word")
        self.info_text.pack(fill="x")
        
        self._draw_graph()
        if path_data:
            self.update_visualization()
    
    def _draw_graph(self):
        """Draw taxi network graph"""
        self.canvas.delete("all")
        
        # Find bounds
        xs = [coord[0] for coord in self.nodes.values()]
        ys = [coord[1] for coord in self.nodes.values()]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        # Scale to canvas
        canvas_w = self.canvas.winfo_width() or 780
        canvas_h = self.canvas.winfo_height() or 480
        
        margin = 50
        scale_x = (canvas_w - 2 * margin) / (x_max - x_min) if x_max > x_min else 1
        scale_y = (canvas_h - 2 * margin) / (y_max - y_min) if y_max > y_min else 1
        scale = min(scale_x, scale_y)
        
        self.scale = scale
        self.margin = margin
        self.x_min = x_min
        self.y_min = y_min
        
        # Draw nodes
        for name, (x, y) in self.nodes.items():
            sx = margin + (x - x_min) * scale
            sy = margin + (y - y_min) * scale
            
            self.canvas.create_oval(
                sx - 8, sy - 8, sx + 8, sy + 8,
                fill="#ddd", outline="#999", width=2,
                tags=("node", name)
            )
            self.canvas.create_text(
                sx, sy - 18,
                text=name, font=("Arial", 9)
            )
    
    def update_visualization(self):
        """Update visualization for current step"""
        if not self.path_data or self.current_step >= len(self.path_data):
            return
        
        step = self.path_data[self.current_step]
        
        # Clear previous highlights
        self.canvas.delete("highlight")
        
        # Draw closed set (explored)
        for node_name in step.get("closed", []):
            if node_name in self.nodes:
                x, y = self.nodes[node_name]
                sx = self.margin + (x - self.x_min) * self.scale
                sy = self.margin + (y - self.y_min) * self.scale
                
                self.canvas.create_oval(
                    sx - 8, sy - 8, sx + 8, sy + 8,
                    fill="#ffcccc", outline="#ff6666", width=2,
                    tags="highlight"
                )
        
        # Draw open set
        for node_name in step.get("open", []):
            if node_name in self.nodes:
                x, y = self.nodes[node_name]
                sx = self.margin + (x - self.x_min) * self.scale
                sy = self.margin + (y - self.y_min) * self.scale
                
                self.canvas.create_oval(
                    sx - 8, sy - 8, sx + 8, sy + 8,
                    fill="#ccffcc", outline="#66ff66", width=2,
                    tags="highlight"
                )
        
        # Draw current path
        path = step.get("path", [])
        for i in range(len(path) - 1):
            if path[i] in self.nodes and path[i + 1] in self.nodes:
                x1, y1 = self.nodes[path[i]]
                x2, y2 = self.nodes[path[i + 1]]
                
                sx1 = self.margin + (x1 - self.x_min) * self.scale
                sy1 = self.margin + (y1 - self.y_min) * self.scale
                sx2 = self.margin + (x2 - self.x_min) * self.scale
                sy2 = self.margin + (y2 - self.y_min) * self.scale
                
                self.canvas.create_line(
                    sx1, sy1, sx2, sy2,
                    fill="blue", width=3, dash=(5, 3),
                    tags="highlight"
                )
        
        # Highlight current node
        current = step.get("current")
        if current and current in self.nodes:
            x, y = self.nodes[current]
            sx = self.margin + (x - self.x_min) * self.scale
            sy = self.margin + (y - self.y_min) * self.scale
            
            self.canvas.create_oval(
                sx - 10, sy - 10, sx + 10, sy + 10,
                fill="yellow", outline="orange", width=3,
                tags="highlight"
            )
        
        # Update info
        self.step_label.config(text=f"Step: {self.current_step + 1} / {len(self.path_data)}")
        info = f"Current: {current}\n"
        info += f"G-score: {step.get('g_score', 0):.1f}\n"
        info += f"F-score: {step.get('f_score', 0):.1f}\n"
        info += f"Path length: {len(path)}"
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", info)
    
    def next_step(self):
        if self.path_data and self.current_step < len(self.path_data) - 1:
            self.current_step += 1
            self.update_visualization()
    
    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.update_visualization()
    
    def play(self):
        """Animate through steps"""
        if self.path_data and self.current_step < len(self.path_data) - 1:
            self.next_step()
            self.after(300, self.play)


class GAVisualizer(tk.Toplevel):
    """Visualize Genetic Algorithm generations"""
    
    def __init__(self, parent, ga_data):
        super().__init__(parent)
        self.title("Genetic Algorithm Visualization")
        self.geometry("700x500")
        
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            self.ga_data = ga_data
            
            # Create figure
            self.fig = Figure(figsize=(7, 5))
            self.ax = self.fig.add_subplot(111)
            
            # Plot fitness over generations
            gens = list(range(len(ga_data.get('best_fitness_history', []))))
            best = ga_data.get('best_fitness_history', [])
            avg = ga_data.get('avg_fitness_history', [])
            
            self.ax.plot(gens, best, 'b-', label='Best Fitness', linewidth=2)
            self.ax.plot(gens, avg, 'g--', label='Avg Fitness', linewidth=1)
            self.ax.set_xlabel('Generation')
            self.ax.set_ylabel('Fitness (lower is better)')
            self.ax.set_title('GA Convergence')
            self.ax.legend()
            self.ax.grid(True, alpha=0.3)
            
            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(self.fig, master=self)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except ImportError:
            ttk.Label(self, text="matplotlib required for GA visualization").pack(pady=20)


class CSPVisualizer(tk.Toplevel):
    """Visualize CSP backtracking"""
    
    def __init__(self, parent, csp_data):
        super().__init__(parent)
        self.title("CSP Scheduler Visualization")
        self.geometry("600x400")
        
        # Info display
        info_frame = ttk.Frame(self, padding=10)
        info_frame.pack(fill="both", expand=True)
        
        ttk.Label(info_frame, text="CSP Statistics", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        stats_text = f"""
        Total Assignments Tried: {csp_data.get('assignments_tried', 0)}
        Backtracks: {csp_data.get('backtracks', 0)}
        Steps: {len(csp_data.get('steps', []))}
        
        Status: {'Solution Found' if csp_data.get('solution') else 'No Solution'}
        """
        
        ttk.Label(info_frame, text=stats_text, 
                 justify="left", font=("Courier", 10)).pack(pady=10)
        
        # Tree visualization (simplified)
        canvas = tk.Canvas(info_frame, bg="white", height=200)
        canvas.pack(fill="both", expand=True, pady=10)
        
        canvas.create_text(
            300, 100,
            text=f"Backtracking tree\n{csp_data.get('backtracks', 0)} backtracks",
            font=("Arial", 12)
        )
