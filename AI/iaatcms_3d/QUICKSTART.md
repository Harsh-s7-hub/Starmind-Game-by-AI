# QUICK START GUIDE

## 🚀 Get Running in 5 Minutes

### Step 1: Install (30 seconds)

```bash
cd AI/iaatcms_3d
pip install pygame PyOpenGL numpy plotly matplotlib pillow reportlab
```

### Step 2: Verify (10 seconds)

```bash
python -c "import pygame, OpenGL; print('✅ Ready!')"
```

### Step 3: Run (2 minutes)

```bash
# Option A: Run main app
python main.py

# Option B: Run demo
python demo_script.py

# Option C: Run tests
python tests/test_ui_components.py
```

---

## 🎮 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl + 0** | Reset view |
| **Ctrl + +** | Zoom in |
| **Ctrl + -** | Zoom out |
| **Mouse Wheel** | Zoom in/out |
| **Click + Drag** | Pan view |
| **Spacebar** | Pause/Resume |

---

## 🎯 Quick Actions

### Spawn Aircraft
```python
# Normal traffic
app.spawn_click()

# Emergency
app.spawn_click(emergency=True)
```

### Run Scheduler
```python
app.run_csp_click()  # CSP scheduler
app.run_ga()         # GA optimizer
```

### Export Data
```python
app.export_csv()  # Export schedule
```

---

## 📊 View AI Visualizations

### A* Pathfinding
1. Enable debug mode: `ai_controller.debug_mode = True`
2. Run A* pathfinding
3. Click "Show A* Viz" button

### GA Convergence
1. Click "Optimize Order (GA)"
2. Visualizer opens automatically
3. Shows fitness vs generation chart

### CSP Backtracking
1. Click "Run CSP Scheduler"
2. View statistics in pop-up

---

## 🎬 Demo Screens Reference

| Time | Screen | What to Show |
|------|--------|--------------|
| 0:00-0:10 | Simulation Tab | Empty airport, clean UI |
| 0:10-0:25 | Flights Spawning | Aircraft with badges appearing |
| 0:25-0:40 | CSP Visualizer | Constraint checking window |
| 0:40-0:55 | A* Visualizer | Open/closed sets, path |
| 0:55-1:10 | Emergency | Red aircraft, priority handling |
| 1:10-1:25 | Radar Tab | Circular radar with sweep |
| 1:25-1:40 | GA Visualizer | Fitness convergence chart |
| 1:40-1:55 | Dashboard Tab | Live matplotlib charts |
| 1:55-2:10 | Stress Test | 10+ aircraft, conflicts |
| 2:10-2:30 | Export & Summary | CSV files, KPI stats |

---

## 🐛 Quick Troubleshooting

**Canvas won't zoom?**  
→ Click canvas to focus, then use mouse wheel

**No matplotlib charts?**  
→ Install: `pip install matplotlib`

**GIF recording blank?**  
→ Install: `pip install pillow`

**Tests fail?**  
→ Check you're in `iaatcms_3d/` directory

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `main.py` | Main 3D application |
| `demo_script.py` | Automated demo |
| `scenario_runner.py` | Run test scenarios |
| `tests/test_ui_components.py` | Unit tests |
| `README.md` | Full documentation |

---

## 💡 Pro Tips

1. **Speed up simulation:** Set speed to 2-5x in controls
2. **Record demo:** Start GIF recording before demo
3. **Test scenarios:** Run all with `python scenario_runner.py`
4. **View KPIs:** Switch to Logs tab anytime
5. **Highlight aircraft:** Click radar blip or select in list

---

## 🎓 Code Examples

### Create Enhanced Canvas
```python
from widgets import EnhancedCanvas
canvas = EnhancedCanvas(root, width=800, height=600)
canvas.pack()
canvas.bind("<<ViewChanged>>", redraw)
```

### Add Flight Badge
```python
from widgets import FlightBadge
badge = FlightBadge(canvas, flight, x, y)
```

### Export Schedule
```python
from utils.export_utils import quick_export_schedule
filepath = quick_export_schedule(flights, assignments)
```

---

## ✅ Acceptance Checklist

Before demo/submission:

- [ ] Tests pass: `python tests/test_ui_components.py`
- [ ] Scenarios run: `python scenario_runner.py`
- [ ] App launches: `python main.py`
- [ ] Demo works: `python demo_script.py`
- [ ] Exports work: Try CSV/GIF/PDF export
- [ ] Documentation complete: Check README.md

---

**Version:** 2.0  
**Last Updated:** November 19, 2025  
**Status:** ✅ Production Ready
