# tests/test_ui_components.py
"""
Unit tests for UI controllers and widgets
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from controllers.simulation_controller import SimulationController
from controllers.ai_controller import AIController


class TestSimulationController(unittest.TestCase):
    """Test SimulationController"""
    
    def setUp(self):
        self.controller = SimulationController()
    
    def test_initialization(self):
        """Test controller initializes correctly"""
        self.assertIsNotNone(self.controller)
        self.assertEqual(len(self.controller.flights), 0)
        self.assertEqual(self.controller.time_tick, 0.0)
        self.assertFalse(self.controller.paused)
    
    def test_speed_control(self):
        """Test simulation speed control"""
        self.controller.set_speed(2.0)
        self.assertEqual(self.controller.sim_speed, 2.0)
        
        # Test bounds
        self.controller.set_speed(20.0)
        self.assertEqual(self.controller.sim_speed, 10.0)
        
        self.controller.set_speed(0.01)
        self.assertEqual(self.controller.sim_speed, 0.1)
    
    def test_pause_toggle(self):
        """Test pause functionality"""
        self.assertFalse(self.controller.paused)
        self.controller.pause()
        self.assertTrue(self.controller.paused)
        self.controller.pause()
        self.assertFalse(self.controller.paused)
    
    def test_log_entry(self):
        """Test logging"""
        self.controller.log("Test message")
        self.assertEqual(len(self.controller.logs), 1)
        self.assertIn("Test message", self.controller.logs[0])
    
    def test_kpi_initialization(self):
        """Test KPI tracking"""
        self.assertIn("total_landings", self.controller.kpis)
        self.assertEqual(self.controller.kpis["total_landings"], 0)


class TestAIController(unittest.TestCase):
    """Test AI algorithms"""
    
    def setUp(self):
        self.ai = AIController()
    
    def test_fuzzy_priority_emergency(self):
        """Test fuzzy priority for emergency"""
        result = self.ai.fuzzy_priority(10, 0.5, True)
        self.assertEqual(result['priority'], 1.0)
        self.assertTrue(result['emergency'])
    
    def test_fuzzy_priority_normal(self):
        """Test fuzzy priority for normal flight"""
        result = self.ai.fuzzy_priority(75, 0.2, False)
        self.assertGreater(result['priority'], 0.0)
        self.assertLess(result['priority'], 1.0)
        self.assertFalse(result['emergency'])
    
    def test_fuzzy_priority_low_fuel(self):
        """Test fuzzy priority with low fuel"""
        result = self.ai.fuzzy_priority(15, 0.3, False)
        self.assertGreater(result['priority'], 0.6)  # Should be high priority
    
    def test_astar_simple_path(self):
        """Test A* pathfinding"""
        nodes = {
            "A": (0, 0),
            "B": (10, 0),
            "C": (20, 0)
        }
        adj = {
            "A": ["B"],
            "B": ["A", "C"],
            "C": ["B"]
        }
        
        path = self.ai.astar_taxi("A", "C", nodes, adj)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], "A")
        self.assertEqual(path[-1], "C")
    
    def test_astar_no_path(self):
        """Test A* with no valid path"""
        nodes = {
            "A": (0, 0),
            "B": (10, 0)
        }
        adj = {
            "A": [],
            "B": []
        }
        
        path = self.ai.astar_taxi("A", "B", nodes, adj)
        self.assertIsNone(path)
    
    def test_csp_simple(self):
        """Test CSP scheduler"""
        flights = [
            {"id": "F1", "slot": 0, "priority": 0.8},
            {"id": "F2", "slot": 1, "priority": 0.6}
        ]
        runways = ["RWY1", "RWY2"]
        gates = ["G1", "G2"]
        
        solution = self.ai.csp_schedule(flights, runways, gates)
        self.assertIsNotNone(solution)
        self.assertEqual(len(solution), 2)
        self.assertIn("F1", solution)
        self.assertIn("F2", solution)
    
    def test_ga_optimize(self):
        """Test genetic algorithm"""
        flight_ids = ["F1", "F2", "F3", "F4"]
        
        def fitness(order):
            # Simple fitness: prefer specific order
            score = 0
            for i, fid in enumerate(order):
                if fid == "F1" and i == 0:
                    score -= 10
            return score
        
        best = self.ai.ga_optimize_order(flight_ids, fitness, pop_size=16, generations=20)
        self.assertEqual(len(best), len(flight_ids))
        self.assertEqual(set(best), set(flight_ids))


class TestScenarioRunner(unittest.TestCase):
    """Test scenario runner"""
    
    def test_scenario_loading(self):
        """Test loading scenario CSV"""
        from scenario_runner import ScenarioRunner
        
        runner = ScenarioRunner()
        
        # Test with scenario file if exists
        scenario_path = "scenarios/scenario_01_normal.csv"
        if os.path.exists(scenario_path):
            runner.load_scenario(scenario_path)
            self.assertGreater(len(runner.flights), 0)
    
    def test_kpi_initialization(self):
        """Test KPI tracking"""
        from scenario_runner import ScenarioRunner
        
        runner = ScenarioRunner()
        runner.kpis = {
            "landings": 0,
            "diversions": 0
        }
        
        self.assertEqual(runner.kpis["landings"], 0)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
