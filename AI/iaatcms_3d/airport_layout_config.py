"""
Professional Airport Layout Configuration
==========================================
Modern international airport design with realistic runway, taxiway, apron, and facilities.
Based on ICAO standards and reference airport layouts.
"""

import math

# Canvas dimensions
SIM_W, SIM_H = 1100, 700

# ============================================================================
# RUNWAY CONFIGURATION - Realistic International Airport Runway
# ============================================================================

# Main Runway 09/27 (3500m length)
RUNWAY_MAIN = {
    'id': '09/27',
    'x': 120,
    'y': 150,
    'length': 800,
    'width': 50,
    'shoulder_width': 12,  # Runway shoulder on each side
    'designation_09': '09',
    'designation_27': '27',
    'threshold_length': 40,  # Threshold markings length
    'touchdown_zone_length': 120,  # TDZ markings
    'centerline_dash_length': 25,
    'centerline_gap': 15,
    'blast_pad_length': 30,  # Blast pad / stopway
}

# Parallel taxiway runway (shorter, for emergencies/training)
RUNWAY_SECONDARY = {
    'id': '09R/27L',
    'x': 120,
    'y': 280,
    'length': 600,
    'width': 40,
    'shoulder_width': 8,
    'designation_09': '09R',
    'designation_27': '27L',
}

# ============================================================================
# TAXIWAY NETWORK - Complete taxiway system with nodes
# ============================================================================

# Primary parallel taxiway (Alpha)
TAXIWAY_ALPHA = {
    'name': 'TWY A',
    'y': 220,  # Between runways
    'x_start': 150,
    'x_end': 900,
    'width': 25,
}

# Connector taxiways (perpendicular to runway)
TAXIWAY_CONNECTORS = [
    {'name': 'A1', 'x': 200, 'y_start': 200, 'y_end': 220, 'type': 'runway_to_parallel'},
    {'name': 'A2', 'x': 350, 'y_start': 200, 'y_end': 220, 'type': 'runway_to_parallel'},
    {'name': 'A3', 'x': 500, 'y_start': 200, 'y_end': 220, 'type': 'runway_to_parallel'},
    {'name': 'A4', 'x': 650, 'y_start': 200, 'y_end': 220, 'type': 'runway_to_parallel'},
    {'name': 'A5', 'x': 800, 'y_start': 200, 'y_end': 220, 'type': 'runway_to_parallel'},
    
    # Connectors to apron
    {'name': 'B1', 'x': 250, 'y_start': 220, 'y_end': 420, 'type': 'parallel_to_apron'},
    {'name': 'B2', 'x': 400, 'y_start': 220, 'y_end': 420, 'type': 'parallel_to_apron'},
    {'name': 'B3', 'x': 550, 'y_start': 220, 'y_end': 420, 'type': 'parallel_to_apron'},
    {'name': 'B4', 'x': 700, 'y_start': 220, 'y_end': 420, 'type': 'parallel_to_apron'},
    {'name': 'B5', 'x': 850, 'y_start': 220, 'y_end': 420, 'type': 'parallel_to_apron'},
    {'name': 'B6', 'x': 980, 'y_start': 220, 'y_end': 420, 'type': 'parallel_to_apron'},
]

# Taxiway node graph for A* pathfinding
TAXI_NODES = {
    # Runway exits
    'RWY_09_EXIT': (200, 150 + 25),
    'RWY_27_EXIT': (820, 150 + 25),
    
    # Alpha taxiway nodes (parallel to runway)
    'TWY_A1': (200, 220),
    'TWY_A2': (350, 220),
    'TWY_A3': (500, 220),
    'TWY_A4': (650, 220),
    'TWY_A5': (800, 220),
    
    # Bravo taxiway nodes (perpendicular - to apron)
    'TWY_B1': (250, 320),
    'TWY_B2': (400, 320),
    'TWY_B3': (550, 320),
    'TWY_B4': (700, 320),
    'TWY_B5': (850, 320),
    'TWY_B6': (980, 320),
    
    # Apron entry nodes
    'APRON_ENTRY_1': (250, 420),
    'APRON_ENTRY_2': (400, 420),
    'APRON_ENTRY_3': (550, 420),
    'APRON_ENTRY_4': (700, 420),
    'APRON_ENTRY_5': (850, 420),
    'APRON_ENTRY_6': (980, 420),
    
    # Gate positions (parking spots) - aligned with taxiway connectors
    'GATE_1': (250, 500),
    'GATE_2': (400, 500),
    'GATE_3': (550, 500),
    'GATE_4': (700, 500),
    'GATE_5': (850, 500),
    'GATE_6': (980, 500),
}

# Taxiway adjacency for A* routing
TAXI_ADJ = {
    'RWY_09_EXIT': ['TWY_A1'],
    'TWY_A1': ['RWY_09_EXIT', 'TWY_A2', 'TWY_B1'],
    'TWY_A2': ['TWY_A1', 'TWY_A3', 'TWY_B2'],
    'TWY_A3': ['TWY_A2', 'TWY_A4', 'TWY_B3'],
    'TWY_A4': ['TWY_A3', 'TWY_A5', 'TWY_B4'],
    'TWY_A5': ['TWY_A4', 'RWY_27_EXIT'],
    'RWY_27_EXIT': ['TWY_A5'],
    
    'TWY_B1': ['TWY_A1', 'APRON_ENTRY_1'],
    'TWY_B2': ['TWY_A2', 'APRON_ENTRY_2'],
    'TWY_B3': ['TWY_A3', 'APRON_ENTRY_3'],
    'TWY_B4': ['TWY_A4', 'APRON_ENTRY_4'],
    'TWY_B5': ['TWY_A5', 'APRON_ENTRY_5'],
    'TWY_B6': ['TWY_A5', 'APRON_ENTRY_6'],
    
    'APRON_ENTRY_1': ['TWY_B1', 'GATE_1'],
    'APRON_ENTRY_2': ['TWY_B2', 'GATE_2'],
    'APRON_ENTRY_3': ['TWY_B3', 'GATE_3'],
    'APRON_ENTRY_4': ['TWY_B4', 'GATE_4'],
    'APRON_ENTRY_5': ['TWY_B5', 'GATE_5'],
    'APRON_ENTRY_6': ['TWY_B6', 'GATE_6'],
    
    'GATE_1': ['APRON_ENTRY_1'],
    'GATE_2': ['APRON_ENTRY_2'],
    'GATE_3': ['APRON_ENTRY_3'],
    'GATE_4': ['APRON_ENTRY_4'],
    'GATE_5': ['APRON_ENTRY_5'],
    'GATE_6': ['APRON_ENTRY_6'],
}

# Gate list for backwards compatibility
GATES = ['GATE_1', 'GATE_2', 'GATE_3', 'GATE_4', 'GATE_5', 'GATE_6']
GATE_POS = {g: TAXI_NODES[g] for g in GATES}

# ============================================================================
# APRON & TERMINAL CONFIGURATION
# ============================================================================

APRON = {
    'x': 180,
    'y': 430,
    'width': 880,  # Extended to accommodate all 6 gates
    'height': 230,
    'color': (180, 180, 170),  # Concrete gray
    'border_color': (140, 140, 130),
}

TERMINAL_BUILDING = {
    'x': 200,
    'y': 580,
    'width': 840,  # Extended to cover all 6 gates
    'height': 70,
    'color': (200, 200, 190),  # Light beige
    'roof_color': (160, 160, 150),
    'windows': True,  # Draw window grid
}

# Jetway/air bridge positions (from terminal to aircraft)
JETWAYS = [
    {'gate': 'GATE_1', 'x': 250, 'y': 520, 'length': 30, 'angle': 90},
    {'gate': 'GATE_2', 'x': 400, 'y': 520, 'length': 30, 'angle': 90},
    {'gate': 'GATE_3', 'x': 550, 'y': 520, 'length': 30, 'angle': 90},
    {'gate': 'GATE_4', 'x': 700, 'y': 520, 'length': 30, 'angle': 90},
    {'gate': 'GATE_5', 'x': 850, 'y': 520, 'length': 30, 'angle': 90},
    {'gate': 'GATE_6', 'x': 980, 'y': 520, 'length': 30, 'angle': 90},
]

# Ground service areas
GROUND_SERVICE_MARKINGS = [
    {'x': 250, 'y': 490, 'type': 'pushback_line'},
    {'x': 400, 'y': 490, 'type': 'pushback_line'},
    {'x': 550, 'y': 490, 'type': 'pushback_line'},
    {'x': 700, 'y': 490, 'type': 'pushback_line'},
    {'x': 850, 'y': 490, 'type': 'pushback_line'},
    {'x': 980, 'y': 490, 'type': 'pushback_line'},
]

# ============================================================================
# AIRPORT FACILITIES
# ============================================================================

# ATC Tower
ATC_TOWER = {
    'x': 950,
    'y': 180,
    'width': 40,
    'height': 60,
    'base_height': 30,  # Tower base
    'cab_height': 30,   # Glass control cab
    'color': (180, 180, 180),
    'cab_color': (100, 150, 200),  # Light blue glass
}

# Hangars (maintenance facilities)
HANGARS = [
    {'x': 920, 'y': 400, 'width': 120, 'height': 80, 'name': 'Hangar 1'},
    {'x': 920, 'y': 500, 'width': 120, 'height': 80, 'name': 'Hangar 2'},
]

# Fuel station
FUEL_STATION = {
    'x': 100,
    'y': 480,
    'width': 60,
    'height': 60,
    'tanks': 3,  # Number of fuel tanks
}

# Fire station
FIRE_STATION = {
    'x': 80,
    'y': 350,
    'width': 70,
    'height': 50,
    'color': (200, 50, 50),  # Red
}

# Service roads (vehicle access)
SERVICE_ROADS = [
    # Perimeter road
    {'points': [(60, 100), (60, 650), (1040, 650), (1040, 100)], 'width': 8, 'type': 'perimeter'},
    # Access roads to apron
    {'points': [(100, 400), (180, 450)], 'width': 6, 'type': 'access'},
    {'points': [(900, 400), (860, 450)], 'width': 6, 'type': 'access'},
]

# Ground vehicle parking areas
VEHICLE_PARKING = [
    {'x': 900, 'y': 280, 'width': 80, 'height': 40, 'type': 'ground_support'},
    {'x': 100, 'y': 250, 'width': 60, 'height': 30, 'type': 'maintenance'},
]

# Perimeter fence (airport boundary)
PERIMETER_FENCE = {
    'points': [(50, 90), (50, 660), (1050, 660), (1050, 90), (50, 90)],
    'color': (80, 80, 80),
    'width': 2,
}

# ============================================================================
# HOLD-SHORT LINES (before runway entry)
# ============================================================================

HOLD_SHORT_LINES = [
    # At each runway connector
    {'x': 200, 'y': 202, 'width': 25, 'orientation': 'horizontal'},
    {'x': 350, 'y': 202, 'width': 25, 'orientation': 'horizontal'},
    {'x': 500, 'y': 202, 'width': 25, 'orientation': 'horizontal'},
    {'x': 650, 'y': 202, 'width': 25, 'orientation': 'horizontal'},
    {'x': 800, 'y': 202, 'width': 25, 'orientation': 'horizontal'},
]

# ============================================================================
# VISUAL STYLING CONSTANTS
# ============================================================================

COLORS = {
    # Runways
    'runway_surface': (50, 50, 50),  # Dark asphalt
    'runway_shoulder': (70, 70, 65),  # Lighter asphalt
    'runway_markings': (245, 245, 245),  # White
    'chevrons': (255, 200, 0),  # Yellow chevrons
    
    # Taxiways
    'taxiway_surface': (60, 60, 60),
    'taxiway_centerline': (255, 215, 0),  # Yellow
    'taxiway_edge': (0, 0, 0),  # Black outline
    'hold_short_solid': (255, 215, 0),
    'hold_short_dashed': (255, 215, 0),
    
    # Apron & Terminal
    'apron_concrete': (180, 180, 170),
    'apron_markings': (255, 215, 0),
    'terminal_building': (200, 200, 190),
    'terminal_roof': (160, 160, 150),
    'terminal_windows': (100, 150, 200),
    'jetway': (220, 220, 220),
    
    # Facilities
    'atc_tower_base': (180, 180, 180),
    'atc_tower_cab': (100, 150, 200),
    'hangar': (160, 160, 160),
    'fuel_station': (200, 200, 200),
    'fire_station': (200, 50, 50),
    
    # Ground
    'grass': (34, 139, 34),  # If no texture
    'service_road': (80, 80, 80),
    'parking_lot': (90, 90, 90),
    'fence': (80, 80, 80),
}

# Font sizes for labeling
LABEL_FONTS = {
    'runway_number': ('Arial', 24, 'bold'),
    'taxiway_label': ('Arial', 10, 'bold'),
    'gate_number': ('Arial', 14, 'bold'),
    'facility_label': ('Arial', 9, 'normal'),
}

# ============================================================================
# HELPER FUNCTION - Curved taxiway generation
# ============================================================================

def generate_curved_taxiway(start_point, end_point, control_offset=50, steps=30):
    """
    Generate smooth Bézier curve for taxiway turns.
    Returns list of (x, y) points.
    """
    x1, y1 = start_point
    x2, y2 = end_point
    
    # Calculate control point for smooth curve
    cx = (x1 + x2) / 2 + control_offset
    cy = (y1 + y2) / 2
    
    points = []
    for i in range(steps + 1):
        t = i / steps
        # Quadratic Bézier curve formula
        x = (1-t)**2 * x1 + 2*(1-t)*t * cx + t**2 * x2
        y = (1-t)**2 * y1 + 2*(1-t)*t * cy + t**2 * y2
        points.append((x, y))
    
    return points

# ============================================================================
# KNOWLEDGE BASE UPDATE
# ============================================================================

KB = {
    "airport_name": "IAATCMS International Airport",
    "airport_code": "ICAO: IAAC",
    "runways": {
        "09/27": {"length_m": 3500, "width_m": 50, "surface": "Asphalt"},
        "09R/27L": {"length_m": 3200, "width_m": 40, "surface": "Asphalt"}
    },
    "gates": {
        "GATE_1": {"size": "large", "aircraft_type": "Wide-body"},
        "GATE_2": {"size": "large", "aircraft_type": "Wide-body"},
        "GATE_3": {"size": "medium", "aircraft_type": "Narrow-body"},
        "GATE_4": {"size": "medium", "aircraft_type": "Narrow-body"},
        "GATE_5": {"size": "small", "aircraft_type": "Regional"}
    },
    "taxiways": ["TWY A", "TWY A1", "TWY A2", "TWY A3", "TWY A4", "TWY A5",
                 "TWY B1", "TWY B2", "TWY B3", "TWY B4"],
    "facilities": ["ATC Tower", "Hangar 1", "Hangar 2", "Fire Station", "Fuel Station"],
    "taxi_nodes": TAXI_NODES
}
