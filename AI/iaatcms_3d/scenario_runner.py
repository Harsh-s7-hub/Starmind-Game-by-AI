# scenario_runner.py
"""
Automated scenario runner for IAATCMS
Loads CSV scenarios and runs them headlessly with KPI collection
"""

import csv
import time
import json
from typing import Dict, List


class Flight:
    """Simple flight object for scenarios"""
    counter = 1000
    
    def __init__(self, flight_id, ftype, fuel, weather, emergency, spawn_time, edge):
        self.id = flight_id
        self.type = ftype
        self.fuel = int(fuel)
        self.weather = float(weather)
        self.emergency = emergency.lower() == 'true'
        self.spawn_time = float(spawn_time)
        self.edge = edge
        
        self.state = "pending"
        self.pos = (0, 0)
        self.assigned = None
        self.priority = 0.5
        self.landed_at = None
        self.diverted = False


class ScenarioRunner:
    """Run scenarios and collect KPIs"""
    
    def __init__(self):
        self.flights = []
        self.events = []
        self.kpis = {}
        self.sim_time = 0.0
        self.max_sim_time = 180.0  # 3 minutes
    
    def load_scenario(self, csv_path: str):
        """Load scenario from CSV file"""
        self.flights = []
        self.events = []
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(
                (row for row in f if not row.startswith('#')),
                fieldnames=['flight_id', 'type', 'fuel', 'weather', 'emergency', 'spawn_time', 'edge']
            )
            
            next(reader)  # Skip header
            
            for row in reader:
                # Check if it's an event
                if row['flight_id'].startswith('RUNWAY_CLOSURE'):
                    self.events.append({
                        'type': 'runway_closure',
                        'runway': row['type'],
                        'start_time': float(row['fuel']),
                        'duration': float(row['weather'])
                    })
                elif row['flight_id'].startswith('WEATHER_EVENT'):
                    self.events.append({
                        'type': 'weather',
                        'severity': float(row['type']),
                        'start_time': float(row['fuel']),
                        'duration': float(row['weather'])
                    })
                elif row['flight_id'].startswith('TAXI_CONGESTION'):
                    self.events.append({
                        'type': 'taxi_congestion',
                        'factor': float(row['type']),
                        'start_time': float(row['fuel']),
                        'duration': float(row['weather'])
                    })
                else:
                    # Regular flight
                    flight = Flight(
                        row['flight_id'],
                        row['type'],
                        row['fuel'],
                        row['weather'],
                        row['emergency'],
                        row['spawn_time'],
                        row['edge']
                    )
                    self.flights.append(flight)
    
    def run_scenario(self, headless=True, verbose=False):
        """
        Run the scenario simulation
        
        Args:
            headless: Run without GUI
            verbose: Print detailed logs
        
        Returns:
            dict: KPI results
        """
        if verbose:
            print(f"Running scenario with {len(self.flights)} flights...")
        
        start_time = time.time()
        
        # Initialize KPIs
        self.kpis = {
            "total_flights": len(self.flights),
            "landings": 0,
            "diversions": 0,
            "emergency_handled": 0,
            "avg_wait_time": 0.0,
            "max_wait_time": 0.0,
            "runway_utilization": {"RWY1": 0.0, "RWY2": 0.0},
            "taxi_conflicts": 0,
            "scenario_duration": 0.0
        }
        
        # Simplified simulation loop
        dt = 0.1  # 100ms steps
        wait_times = []
        
        while self.sim_time < self.max_sim_time:
            # Spawn pending flights
            for flight in self.flights:
                if flight.state == "pending" and self.sim_time >= flight.spawn_time:
                    flight.state = "approaching"
                    if verbose:
                        print(f"[{self.sim_time:.1f}s] {flight.id} spawned")
            
            # Process active flights (simplified)
            for flight in self.flights:
                if flight.state == "approaching":
                    # Simulate approach time
                    if self.sim_time - flight.spawn_time > 10.0:
                        flight.state = "landing"
                        
                elif flight.state == "landing":
                    # Land flight
                    flight.state = "landed"
                    flight.landed_at = self.sim_time
                    wait_time = flight.landed_at - flight.spawn_time
                    wait_times.append(wait_time)
                    self.kpis["landings"] += 1
                    
                    if flight.emergency:
                        self.kpis["emergency_handled"] += 1
                    
                    if verbose:
                        print(f"[{self.sim_time:.1f}s] {flight.id} landed (wait: {wait_time:.1f}s)")
            
            # Check for completed scenario
            all_done = all(f.state in ("landed", "diverted") for f in self.flights)
            if all_done:
                break
            
            self.sim_time += dt
        
        # Calculate final KPIs
        if wait_times:
            self.kpis["avg_wait_time"] = sum(wait_times) / len(wait_times)
            self.kpis["max_wait_time"] = max(wait_times)
        
        self.kpis["scenario_duration"] = time.time() - start_time
        
        # Estimate runway utilization (simplified)
        self.kpis["runway_utilization"]["RWY1"] = min(1.0, self.kpis["landings"] / (len(self.flights) * 0.6))
        self.kpis["runway_utilization"]["RWY2"] = min(1.0, self.kpis["landings"] / (len(self.flights) * 0.7))
        
        if verbose:
            print(f"\nScenario complete in {self.kpis['scenario_duration']:.2f}s")
            print(f"Landings: {self.kpis['landings']}")
            print(f"Avg wait: {self.kpis['avg_wait_time']:.1f}s")
        
        return self.kpis
    
    def save_results(self, output_path: str):
        """Save KPI results to JSON"""
        with open(output_path, 'w') as f:
            json.dump(self.kpis, f, indent=2)
    
    def validate_kpis(self, expected: Dict) -> bool:
        """Validate KPIs against expected thresholds"""
        passed = True
        
        for key, threshold in expected.items():
            if key in self.kpis:
                actual = self.kpis[key]
                if isinstance(threshold, tuple):
                    # Range check (min, max)
                    if not (threshold[0] <= actual <= threshold[1]):
                        print(f"FAIL: {key} = {actual} not in range {threshold}")
                        passed = False
                elif isinstance(threshold, (int, float)):
                    # Less than threshold
                    if actual > threshold:
                        print(f"FAIL: {key} = {actual} exceeds {threshold}")
                        passed = False
        
        return passed


def run_all_scenarios(scenario_dir="scenarios"):
    """Run all scenario files and generate report"""
    import os
    import glob
    
    scenario_files = glob.glob(os.path.join(scenario_dir, "scenario_*.csv"))
    results = {}
    
    print(f"Found {len(scenario_files)} scenarios\n")
    
    for scenario_file in sorted(scenario_files):
        print(f"Running {os.path.basename(scenario_file)}...")
        
        runner = ScenarioRunner()
        runner.load_scenario(scenario_file)
        kpis = runner.run_scenario(headless=True, verbose=False)
        
        results[os.path.basename(scenario_file)] = kpis
        
        print(f"  Landings: {kpis['landings']}/{kpis['total_flights']}")
        print(f"  Avg wait: {kpis['avg_wait_time']:.1f}s")
        print()
    
    # Save summary report
    with open(os.path.join(scenario_dir, "results_summary.json"), 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {scenario_dir}/results_summary.json")
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run specific scenario
        runner = ScenarioRunner()
        runner.load_scenario(sys.argv[1])
        kpis = runner.run_scenario(headless=True, verbose=True)
        print("\nKPIs:", json.dumps(kpis, indent=2))
    else:
        # Run all scenarios
        run_all_scenarios()
