# demo_script.py
"""
Demo Script - 2-3 Minute Demonstration of IAATCMS
Shows all AI components and features
"""

import time
import sys


class DemoScript:
    """Automated demo script runner"""
    
    def __init__(self, app):
        self.app = app
        self.steps = []
        self.current_step = 0
        
        self._build_script()
    
    def _build_script(self):
        """Define demo steps with timing"""
        self.steps = [
            {
                "time": 0,
                "action": "intro",
                "description": "Welcome to IAATCMS - Intelligent Airport & ATC Management System"
            },
            {
                "time": 3,
                "action": "spawn_normal",
                "description": "Spawning normal traffic flights..."
            },
            {
                "time": 8,
                "action": "show_fuzzy",
                "description": "Fuzzy Logic: Calculating flight priorities based on fuel, weather, emergency"
            },
            {
                "time": 15,
                "action": "run_csp",
                "description": "CSP Scheduler: Assigning runways, gates, and time slots with constraint satisfaction"
            },
            {
                "time": 22,
                "action": "show_astar",
                "description": "A* Pathfinding: Planning optimal taxi routes avoiding conflicts"
            },
            {
                "time": 30,
                "action": "spawn_emergency",
                "description": "EMERGENCY: Low fuel aircraft requesting priority landing"
            },
            {
                "time": 38,
                "action": "auto_decision",
                "description": "Auto Decision Mode: AI automatically grants clearance to emergency flight"
            },
            {
                "time": 45,
                "action": "show_radar",
                "description": "Mini-Radar: Real-time aircraft tracking with sweep animation"
            },
            {
                "time": 52,
                "action": "run_ga",
                "description": "Genetic Algorithm: Optimizing landing order to minimize delays"
            },
            {
                "time": 65,
                "action": "show_dashboard",
                "description": "Live Dashboard: Priority distribution, fuel trends, runway utilization"
            },
            {
                "time": 75,
                "action": "stress_test",
                "description": "Peak Hour Surge: Multiple aircraft competing for limited resources"
            },
            {
                "time": 90,
                "action": "show_separation",
                "description": "Safety Systems: Minimum separation enforcement, conflict detection"
            },
            {
                "time": 100,
                "action": "human_override",
                "description": "Human-in-the-Loop: Controller can reassign gates, force landings, or divert"
            },
            {
                "time": 110,
                "action": "export_data",
                "description": "Exporting: Schedule CSV, KPI summary, GIF recording"
            },
            {
                "time": 120,
                "action": "show_kpis",
                "description": "Final KPIs: Landings, diversions, avg wait time, runway utilization"
            },
            {
                "time": 130,
                "action": "conclusion",
                "description": "IAATCMS: Multi-AI integration (Fuzzy + CSP + A* + GA) for intelligent airport management"
            }
        ]
    
    def run(self):
        """Run the demo script"""
        print("=" * 60)
        print("IAATCMS DEMO SCRIPT")
        print("Duration: ~2-3 minutes")
        print("=" * 60)
        print()
        
        start_time = time.time()
        
        for step in self.steps:
            # Wait until step time
            while time.time() - start_time < step["time"]:
                time.sleep(0.1)
            
            elapsed = time.time() - start_time
            print(f"[{elapsed:3.0f}s] {step['description']}")
            
            # Execute action
            self._execute_action(step["action"])
        
        print()
        print("=" * 60)
        print("DEMO COMPLETE")
        print(f"Total time: {time.time() - start_time:.1f}s")
        print("=" * 60)
    
    def _execute_action(self, action):
        """Execute demo action"""
        try:
            if action == "intro":
                pass  # Just display message
            
            elif action == "spawn_normal":
                for _ in range(3):
                    if hasattr(self.app, 'spawn_click'):
                        self.app.spawn_click()
            
            elif action == "show_fuzzy":
                # Highlight fuzzy logic visualization
                pass
            
            elif action == "run_csp":
                if hasattr(self.app, 'run_csp_click'):
                    self.app.run_csp_click()
            
            elif action == "show_astar":
                # Show A* visualization
                pass
            
            elif action == "spawn_emergency":
                if hasattr(self.app, 'spawn_click'):
                    self.app.spawn_click(emergency=True)
            
            elif action == "auto_decision":
                if hasattr(self.app, 'toggle_auto_decision'):
                    self.app.auto_decision_var.set(True)
                    self.app.toggle_auto_decision()
            
            elif action == "show_radar":
                # Switch to radar tab
                if hasattr(self.app, 'notebook'):
                    self.app.notebook.select(1)  # Radar tab
            
            elif action == "run_ga":
                if hasattr(self.app, 'run_ga'):
                    self.app.run_ga()
            
            elif action == "show_dashboard":
                # Switch to dashboard tab
                if hasattr(self.app, 'notebook'):
                    self.app.notebook.select(2)  # Dashboard tab
            
            elif action == "stress_test":
                for _ in range(5):
                    if hasattr(self.app, 'spawn_click'):
                        self.app.spawn_click()
                        time.sleep(0.3)
            
            elif action == "show_separation":
                pass
            
            elif action == "human_override":
                pass
            
            elif action == "export_data":
                if hasattr(self.app, 'export_csv'):
                    self.app.export_csv()
            
            elif action == "show_kpis":
                # Switch to logs tab
                if hasattr(self.app, 'notebook'):
                    self.app.notebook.select(3)
            
            elif action == "conclusion":
                pass
        
        except Exception as e:
            print(f"  Error executing {action}: {e}")


def print_demo_screens():
    """Print demo screen descriptions for documentation"""
    screens = [
        {
            "timestamp": "0:00-0:10",
            "screen": "Simulation Tab - Empty Airport",
            "description": "Show clean UI with runways, taxiways, gates labeled. Left panel controls visible."
        },
        {
            "timestamp": "0:10-0:25",
            "screen": "Simulation Tab - Flights Spawning",
            "description": "Aircraft appear with flight badges (call sign, priority bar, fuel). Approach paths visible."
        },
        {
            "timestamp": "0:25-0:40",
            "screen": "CSP Visualizer Window",
            "description": "Pop-up showing constraint checking, backtracking steps, final assignments."
        },
        {
            "timestamp": "0:40-0:55",
            "screen": "A* Pathfinding Visualizer",
            "description": "Show open/closed sets, explored nodes, dashed path animation from runway exit to gate."
        },
        {
            "timestamp": "0:55-1:10",
            "screen": "Emergency Landing Sequence",
            "description": "Red aircraft with flashing badge, priority bar at maximum, auto-clearance granted."
        },
        {
            "timestamp": "1:10-1:25",
            "screen": "Radar Tab",
            "description": "Circular radar with sweep line, aircraft blips, click to highlight."
        },
        {
            "timestamp": "1:25-1:40",
            "screen": "GA Visualizer",
            "description": "Line chart showing fitness convergence over generations."
        },
        {
            "timestamp": "1:40-1:55",
            "screen": "Dashboard Tab",
            "description": "Embedded matplotlib charts: priority histogram, fuel trends, runway usage bars."
        },
        {
            "timestamp": "1:55-2:10",
            "screen": "Peak Hour Stress Test",
            "description": "10+ aircraft, holding patterns visible, taxi conflicts shown with amber edges."
        },
        {
            "timestamp": "2:10-2:30",
            "screen": "Export & Summary",
            "description": "Show exported CSV files, KPI summary, final statistics on Logs tab."
        }
    ]
    
    print("\n" + "=" * 80)
    print("DEMO SCREEN SEQUENCE FOR VIDEO/PRESENTATION")
    print("=" * 80)
    
    for screen in screens:
        print(f"\n{screen['timestamp']}")
        print(f"  Screen: {screen['screen']}")
        print(f"  Description: {screen['description']}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Print demo screens for documentation
    print_demo_screens()
