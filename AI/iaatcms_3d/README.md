# IAATCMS - Intelligent Airport & ATC Management System

## 🚀 Complete Refactored Implementation

**Version:** 2.0  
**Date:** November 19, 2025  
**Status:** Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [What's New](#whats-new)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Architecture](#architecture)
6. [Features](#features)
7. [Demo Scenarios](#demo-scenarios)
8. [Testing](#testing)
9. [Export Capabilities](#export-capabilities)
10. [AI Components](#ai-components)
11. [Troubleshooting](#troubleshooting)

---

## Overview

IAATCMS is an advanced airport traffic control simulation system that integrates multiple AI techniques:

- **Fuzzy Logic** - Priority scoring based on fuel, weather, emergency status
- **Constraint Satisfaction (CSP)** - Optimal runway/gate/slot assignment
- **A* Pathfinding** - Intelligent taxi routing with conflict avoidance
- **Genetic Algorithms (GA)** - Landing order optimization

### Dual Interface System

1. **2D Tkinter UI** (`iaatcms_gui.py`) - Comprehensive 2D simulation
2. **3D OpenGL/Pygame UI** (`iaatcms_3d/main.py`) - Immersive 3D visualization

---

## What's New

### Version 2.0 Enhancements

#### ✅ Modular Architecture
- **Controllers:** Separated business logic from presentation
  - `SimulationController` - Flight lifecycle, time progression, KPI tracking
  - `AIController` - Fuzzy, CSP, A*, GA with debug hooks
  - `VisualizationController` - Rendering coordination

#### ✅ Enhanced UI Widgets
- **EnhancedCanvas** - Zoom/pan with mouse wheel, anti-aliased rendering
- **FlightBadge** - Compact info display with priority bars and hover tooltips
- **MiniRadar** - Circular radar with sweep animation and click-to-highlight
- **AI Visualizers** - Step-by-step A*, CSP, GA visualizations

#### ✅ Fixed Issues
- **Taxi Clustering** - Explicit graph with edge occupancy tracking
- **Visual Decluttering** - Force-directed label layout
- **Separation Enforcement** - Real-time violation detection with visual warnings
- **Thread Safety** - Proper locking for concurrent UI updates

#### ✅ New Features
- **Human-in-the-Loop Controls** - Reassign gate, force land, divert, hold buttons
- **Explain Button** - Natural language justification for AI decisions
- **Demo Mode** - Automated 2-3 minute demonstration
- **Export Suite** - CSV schedules, GIF recordings, PDF summaries
- **Scenario Runner** - Headless execution with KPI validation

---

## Installation

### Prerequisites

```bash
Python 3.8+
```

### Install Dependencies

```bash
pip install pygame PyOpenGL numpy plotly matplotlib pillow reportlab
```

### Verify Installation

```bash
cd iaatcms_3d
python -c "import pygame, OpenGL, numpy, matplotlib; print('All dependencies OK')"
```

---

## Quick Start

### Run 2D Simulation

```bash
cd AI
python iaatcms_gui.py
```

### Run 3D Simulation

```bash
cd AI/iaatcms_3d
python main.py
```

### Run Demo Script

```bash
cd AI/iaatcms_3d
python demo_script.py
```

### Run Tests

```bash
cd AI/iaatcms_3d
python -m pytest tests/
# Or
python tests/test_ui_components.py
```

### Run Scenarios

```bash
cd AI/iaatcms_3d
python scenario_runner.py scenarios/scenario_01_normal.csv
# Or run all
python scenario_runner.py
```

---

## Architecture

### Directory Structure

```
AI/
├── iaatcms_gui.py              # 2D Tkinter simulation
├── iaatcms_3d/
│   ├── main.py                 # 3D Pygame+OpenGL simulation
│   ├── controllers/            # NEW: Business logic
│   │   ├── simulation_controller.py
│   │   ├── ai_controller.py
│   │   └── visualization_controller.py
│   ├── widgets/                # NEW: Reusable UI components
│   │   ├── enhanced_canvas.py
│   │   ├── flight_badge.py
│   │   ├── mini_radar.py
│   │   └── ai_visualizer.py
│   ├── utils/                  # NEW: Utilities
│   │   └── export_utils.py
│   ├── scenarios/              # NEW: Demo scenarios
│   │   ├── scenario_01_normal.csv
│   │   ├── scenario_02_runway_closure.csv
│   │   ├── scenario_03_weather_surge.csv
│   │   ├── scenario_04_emergency.csv
│   │   └── scenario_05_peak_surge.csv
│   ├── tests/                  # NEW: Unit tests
│   │   └── test_ui_components.py
│   ├── scenario_runner.py      # NEW: Automated testing
│   ├── demo_script.py          # NEW: Demo automation
│   ├── aircraft.py             # 3D model loader
│   ├── atc_ui.py              # ATC dialogs
│   ├── graphics3d.py          # OpenGL utilities
│   ├── runway_scene.py        # Ground rendering
│   ├── shader_utils.py        # GLSL helpers
│   ├── plotly_dashboard.py    # Interactive charts
│   ├── shaders/               # GLSL shaders
│   │   ├── phong.vert
│   │   └── phong.frag
│   └── assets/                # Textures
│       └── runway_tex.jpg
└── exports/                    # Generated outputs
```

### Controller Pattern

```python
# Separation of concerns
SimulationController  → Manages state, physics, time
AIController         → Runs algorithms with debug hooks
VisualizationController → Coordinates rendering

# UI → Controller → Model → Controller → UI
```

---

## Features

### 🎮 Interactive Controls

#### Simulation Tab
- **Play/Pause** - Control simulation time
- **Speed Slider** - 0.1x to 10x real-time
- **Spawn Flight** - Add normal traffic
- **Spawn Emergency** - Add low-fuel critical flight
- **Run CSP Scheduler** - Assign runway/gate/slots
- **Optimize Order (GA)** - Genetic algorithm optimization
- **Auto Spawn** - Continuous traffic generation
- **Auto Schedule** - Periodic CSP execution
- **Auto Decision** - AI auto-approves landings above threshold

#### Canvas Controls
- **Mouse Wheel** - Zoom in/out
- **Click + Drag** - Pan view
- **Ctrl+0** - Reset view
- **Ctrl++** - Zoom in
- **Ctrl+-** - Zoom out
- **Fit to Window** - Auto-scale to fit all aircraft

#### Human-in-the-Loop
- **Reassign Gate** - Override CSP gate assignment
- **Force Land** - Immediate landing clearance
- **Divert** - Send aircraft to alternate airport
- **Hold** - Send to holding pattern
- **Explain** - Get AI decision justification

### 📊 Visualization Features

#### Flight Badges
- **Call Sign** - Aircraft ID
- **Priority Bar** - Visual 0-1 priority with color coding
- **Fuel %** - Current fuel level
- **State** - approaching/landing/taxiing/at_gate
- **Hover Tooltip** - Full flight details

#### Mini-Radar
- **Sweep Animation** - Rotating radar beam
- **Aircraft Blips** - Color-coded (red=emergency, cyan=normal)
- **Click to Highlight** - Select flight in main view
- **Normalized Coordinates** - Full airport coverage

#### AI Visualizers

**A* Pathfinding**
- Open set (green) - Nodes being evaluated
- Closed set (red) - Nodes already explored
- Current path (blue dashed) - Route in progress
- Current node (yellow) - Active exploration
- Step-by-step replay controls

**CSP Scheduler**
- Assignments tried counter
- Backtrack count
- Constraint check visualization
- Final solution display

**Genetic Algorithm**
- Fitness over generations chart
- Best vs average fitness
- Convergence visualization
- Generation replay

### 📈 Dashboard & Analytics

#### Live Charts (Matplotlib/Plotly)
1. **Priority Distribution** - Scatter plot of all flights
2. **Fuel Trends** - Line chart of fuel levels
3. **Weather Severity** - Weather impact visualization
4. **Runway Usage** - Bar chart of runway assignments
5. **Gate Occupancy** - Current gate utilization

#### KPIs Panel
- Total landings
- Total diversions
- Average wait time
- Maximum wait time
- Emergency flights handled
- Runway utilization %
- Taxi conflicts detected

---

## Demo Scenarios

### Scenario 1: Normal Traffic (Baseline)
- **File:** `scenarios/scenario_01_normal.csv`
- **Duration:** ~60 seconds
- **Flights:** 8 aircraft
- **Expected KPIs:**
  - Avg delay < 30s
  - Diversions = 0
  - Runway utilization > 60%

### Scenario 2: Runway Closure
- **File:** `scenarios/scenario_02_runway_closure.csv`
- **Duration:** ~80 seconds
- **Event:** RWY2 closes at t=30s
- **Flights:** 10 aircraft
- **Expected KPIs:**
  - Avg delay increases
  - RWY1 utilization > 90%
  - Some diversions possible

### Scenario 3: Weather Surge
- **File:** `scenarios/scenario_03_weather_surge.csv`
- **Duration:** ~90 seconds
- **Conditions:** High weather severity (0.7-0.9)
- **Flights:** 10 aircraft
- **Expected KPIs:**
  - Avg delay > 45s
  - Increased holding patterns
  - All safe landings

### Scenario 4: Emergency Landing
- **File:** `scenarios/scenario_04_emergency.csv`
- **Duration:** ~70 seconds
- **Flights:** 9 aircraft (3 emergencies)
- **Expected KPIs:**
  - Emergency_handled = 3
  - Priority aircraft land first
  - No emergency diversions

### Scenario 5: Peak Surge
- **File:** `scenarios/scenario_05_peak_surge.csv`
- **Duration:** ~100 seconds
- **Flights:** 15 aircraft (high density)
- **Event:** Taxi congestion
- **Expected KPIs:**
  - Taxi conflicts > 0
  - Gate delays
  - High utilization
  - Possible diversions

### Running Scenarios

```bash
# Single scenario
python scenario_runner.py scenarios/scenario_01_normal.csv

# All scenarios
python scenario_runner.py

# Results saved to scenarios/results_summary.json
```

---

## Testing

### Unit Tests

```bash
cd iaatcms_3d
python tests/test_ui_components.py
```

### Test Coverage

- ✅ `SimulationController` - Initialization, speed control, pause, logging, KPIs
- ✅ `AIController` - Fuzzy logic, A*, CSP, GA
- ✅ `ScenarioRunner` - CSV loading, KPI tracking
- ✅ Widget initialization and interaction

### Acceptance Criteria

✅ Smooth canvas pan/zoom  
✅ No major label overlap after decluster  
✅ A* path appears for taxiing flights  
✅ GA/CSP visualizers display step-by-step  
✅ Demo script runs end-to-end  
✅ Exports generate valid files  

---

## Export Capabilities

### CSV Export

**Schedule Export**
```python
from utils.export_utils import quick_export_schedule

filepath = quick_export_schedule(flights, assignments)
# Generates: exports/schedule_YYYYMMDD_HHMMSS.csv
```

**KPI Export**
```python
from utils.export_utils import quick_export_kpis

filepath = quick_export_kpis(kpis)
# Generates: exports/kpis_YYYYMMDD_HHMMSS.csv
```

### GIF Recording

```python
from utils.export_utils import ExportManager

exporter = ExportManager()
exporter.start_gif_recording(canvas_widget)
# ... run simulation ...
filepath = exporter.stop_gif_recording()
# Generates: exports/simulation_YYYYMMDD_HHMMSS.gif
```

### PDF Summary

```python
filepath = exporter.export_pdf_summary(flights, kpis, assignments)
# Generates: exports/summary_YYYYMMDD_HHMMSS.pdf
# Requires: pip install reportlab
```

---

## AI Components

### 1. Fuzzy Logic Priority Scoring

**Inputs:**
- Fuel percentage (0-100%)
- Weather severity (0.0-1.0)
- Emergency flag (boolean)

**Process:**
1. Fuzzification using triangular membership functions
2. Rule evaluation (IF fuel=low OR weather=poor THEN priority=high)
3. Defuzzification using centroid method

**Output:** Priority score (0.0-1.0)

**Visualization:** Bar chart with membership breakdowns

### 2. Constraint Satisfaction (CSP)

**Variables:** Flight assignments  
**Domains:** {(runway, gate, slot) for each flight}  
**Constraints:**
- Runway separation (minimum time between landings)
- Gate capacity (aircraft type compatibility)
- Gate occupancy (minimum turnaround time)

**Algorithm:** Backtracking with MRV (Minimum Remaining Values) heuristic

**Debug Output:** Assignment attempts, backtracks, final solution

### 3. A* Pathfinding

**Problem:** Find shortest taxi path from runway exit to assigned gate  
**Graph:** Taxi network nodes with weighted edges  
**Heuristic:** Euclidean distance to goal  
**Constraints:** Avoid occupied edges

**Visualization:** Open/closed sets, explored nodes, path animation

### 4. Genetic Algorithm

**Problem:** Optimize landing order to minimize total delay  
**Encoding:** Permutation of flight IDs  
**Fitness:** Weighted sum of delays and priority violations  
**Operators:**
- Selection: Top 50%
- Crossover: Ordered crossover
- Mutation: Swap random elements

**Visualization:** Fitness convergence chart over generations

---

## Troubleshooting

### Issue: Canvas doesn't respond to zoom/pan
**Solution:** Click on canvas to give it focus, ensure mouse wheel events are bound

### Issue: A* visualizer shows no path
**Solution:** Verify taxi network connectivity in `TAXI_NODES` and `TAXI_ADJ`

### Issue: GIF recording produces blank frames
**Solution:** Ensure Pillow is installed: `pip install pillow`

### Issue: PDF export fails
**Solution:** Install reportlab: `pip install reportlab`

### Issue: Matplotlib charts don't update
**Solution:** Check `MATPLOTLIB_AVAILABLE` flag, verify backend is TkAgg

### Issue: Flights overlap during taxi
**Solution:** Enable taxi edge occupancy tracking in `SimulationController`

### Issue: CSP finds no solution
**Solution:** Increase domain size (more time slots) or reduce constraints

---

## Migration Notes

### From Version 1.0 to 2.0

**Breaking Changes:** None (backward compatible)

**New Modules:**
- Import controllers: `from controllers import SimulationController, AIController`
- Import widgets: `from widgets import EnhancedCanvas, FlightBadge`
- Import utilities: `from utils.export_utils import ExportManager`

**Deprecated:** None

**Enhanced:** All existing functions have debug hooks for visualization

---

## Performance Tips

1. **Large Simulations:** Set `sim_speed` to 2-5x for faster execution
2. **Recording:** GIF recording adds overhead, stop when not needed
3. **Visualization:** Disable debug visualizers when running scenarios
4. **Threading:** CSP and GA run in worker threads, don't block UI

---

## Credits

**Development:** AI-Assisted Development (ChatGPT + GitHub Copilot)  
**Architecture:** Model-View-Controller with Observer pattern  
**AI Techniques:** Fuzzy Logic, CSP, A*, Genetic Algorithms  
**Graphics:** PyGame + PyOpenGL + GLSL shaders  

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review test cases in `tests/test_ui_components.py`
3. Run demo scenarios to verify setup
4. Check logs in `Logs` tab for runtime errors

---

**Last Updated:** November 19, 2025  
**Version:** 2.0.0  
**Status:** ✅ Production Ready
