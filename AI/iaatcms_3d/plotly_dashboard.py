# plotly_dashboard.py
# ----------------------------------------------------------------
# Provides an interactive dashboard of flights using Plotly.
# Shows priority, fuel, weather, runway usage, etc.
# Requires: pip install plotly
# ----------------------------------------------------------------

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import tempfile
import webbrowser
import random

def build_dashboard(flights):
    """
    flights: list of dicts each having:
      'id', 'priority', 'fuel', 'weather', 'emergency', 'assigned' (optional)
    """
    ids   = [f["id"] for f in flights]
    pr    = [f["priority"] for f in flights]
    fuel  = [f["fuel"] for f in flights]
    we    = [f["weather"] for f in flights]
    em    = [1 if f.get("emergency", False) else 0 for f in flights]
    runs  = [f.get("assigned", ("None","",))[0] if f.get("assigned") else "None" for f in flights]

    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=("Priority Scores", "Fuel Trend (last)", "Weather Severity", "Runway Usage"))

    fig.add_trace(go.Bar(x=ids, y=pr,
                         marker_color=pr,
                         colorscale='Viridis',
                         hovertemplate='Flight %{x}<br>Priority %{y:.2f}<extra></extra>'),
                  row=1, col=1)

    fig.add_trace(go.Scatter(x=ids, y=fuel,
                         mode='lines+markers',
                         marker=dict(size=10, color=fuel, colorscale='Turbo'),
                         name="Fuel %"),
                  row=1, col=2)

    fig.add_trace(go.Scatter(x=ids, y=we,
                         mode='lines+markers',
                         marker=dict(size=10, color=we, colorscale='Inferno'),
                         name="Weather"),
                  row=2, col=1)

    # runway usage
    from collections import Counter
    cnt = Counter(runs)
    fig.add_trace(go.Bar(x=list(cnt.keys()), y=list(cnt.values()),
                         marker_color=list(range(len(cnt))), colorscale='Plasma'),
                  row=2, col=2)

    fig.update_layout(height=800, width=1000,
                      title="IAATCMS Live Analytics Dashboard",
                      hovermode='closest')

    return fig

def show_dashboard(flights):
    fig = build_dashboard(flights)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    fig.write_html(tmp.name, include_plotlyjs='cdn')
    webbrowser.open("file://" + tmp.name)
    print("Dashboard opened in browser:", tmp.name)

# Demo mode
if __name__ == "__main__":
    flights = []
    for i in range(5):
        flights.append({
            "id": f"F10{i}",
            "priority": random.random(),
            "fuel": random.randint(10, 90),
            "weather": random.random(),
            "emergency": (random.random() < 0.15),
            "assigned": None
        })
    show_dashboard(flights)
