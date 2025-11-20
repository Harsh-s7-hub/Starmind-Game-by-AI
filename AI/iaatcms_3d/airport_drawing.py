"""
Professional Airport Layout Drawing Functions
==============================================
Complete rendering system for realistic airport visualization.
Implements ICAO-standard runway markings, taxiway system, apron, facilities.
"""

import pygame
import math
from airport_layout_config import *

# ============================================================================
# RUNWAY DRAWING FUNCTIONS
# ============================================================================

def draw_runway_main(surface):
    """
    Draw main runway (09/27) with complete ICAO-standard markings:
    - Runway surface with shoulders
    - Centerline stripes
    - Threshold markings
    - Touchdown zone markings
    - Runway designation numbers
    - Edge lines
    - Blast pad / stopway
    """
    rwy = RUNWAY_MAIN
    x, y, length, width = rwy['x'], rwy['y'], rwy['length'], rwy['width']
    shoulder_w = rwy['shoulder_width']
    
    # Draw blast pad (at runway 09 end)
    blast_pad_09 = (x - rwy['blast_pad_length'], y - 5, rwy['blast_pad_length'], width + 10)
    pygame.draw.rect(surface, (70, 70, 65), blast_pad_09)
    # Chevrons on blast pad
    for i in range(3):
        cx = x - rwy['blast_pad_length'] + i * 10
        points = [(cx, y), (cx + 10, y + width//2), (cx, y + width)]
        pygame.draw.lines(surface, COLORS['chevrons'], False, points, 3)
    
    # Draw blast pad (at runway 27 end)
    blast_pad_27 = (x + length, y - 5, rwy['blast_pad_length'], width + 10)
    pygame.draw.rect(surface, (70, 70, 65), blast_pad_27)
    for i in range(3):
        cx = x + length + i * 10
        points = [(cx, y), (cx + 10, y + width//2), (cx, y + width)]
        pygame.draw.lines(surface, COLORS['chevrons'], False, points, 3)
    
    # Runway shoulders
    pygame.draw.rect(surface, COLORS['runway_shoulder'], 
                    (x - shoulder_w, y - shoulder_w, length + shoulder_w*2, width + shoulder_w*2))
    
    # Main runway surface (dark asphalt)
    pygame.draw.rect(surface, COLORS['runway_surface'], (x, y, length, width))
    
    # Runway edge lines (white)
    pygame.draw.rect(surface, COLORS['runway_markings'], (x, y, length, 2))  # Top edge
    pygame.draw.rect(surface, COLORS['runway_markings'], (x, y + width - 2, length, 2))  # Bottom edge
    
    # Centerline stripes (white dashed)
    dash_len = rwy['centerline_dash_length']
    gap = rwy['centerline_gap']
    center_y = y + width // 2
    current_x = x + 50
    while current_x < x + length - 50:
        pygame.draw.rect(surface, COLORS['runway_markings'], 
                        (current_x, center_y - 2, dash_len, 4))
        current_x += dash_len + gap
    
    # Threshold markings at 09 end (8 stripes)
    threshold_x_09 = x + 15
    stripe_width = 4
    stripe_spacing = (width - 20) // 9
    for i in range(8):
        stripe_y = y + 10 + i * stripe_spacing
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (threshold_x_09, stripe_y, rwy['threshold_length'], stripe_width))
    
    # Threshold markings at 27 end
    threshold_x_27 = x + length - 15 - rwy['threshold_length']
    for i in range(8):
        stripe_y = y + 10 + i * stripe_spacing
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (threshold_x_27, stripe_y, rwy['threshold_length'], stripe_width))
    
    # Touchdown zone markings (blocks) at 09 end
    tdz_start_09 = x + 80
    tdz_block_width = 8
    tdz_block_height = 15
    for block_set in range(3):  # 3 sets of TDZ markings
        bx = tdz_start_09 + block_set * 40
        # Left side blocks
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx, y + 12, tdz_block_width, tdz_block_height))
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx + 12, y + 12, tdz_block_width, tdz_block_height))
        # Right side blocks
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx, y + width - 12 - tdz_block_height, tdz_block_width, tdz_block_height))
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx + 12, y + width - 12 - tdz_block_height, tdz_block_width, tdz_block_height))
    
    # Touchdown zone markings at 27 end
    tdz_start_27 = x + length - 200
    for block_set in range(3):
        bx = tdz_start_27 + block_set * 40
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx, y + 12, tdz_block_width, tdz_block_height))
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx + 12, y + 12, tdz_block_width, tdz_block_height))
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx, y + width - 12 - tdz_block_height, tdz_block_width, tdz_block_height))
        pygame.draw.rect(surface, COLORS['runway_markings'],
                        (bx + 12, y + width - 12 - tdz_block_height, tdz_block_width, tdz_block_height))
    
    # Runway designation numbers (09 and 27)
    font_large = pygame.font.SysFont('Arial', 32, bold=True)
    
    # "09" at runway 09 end
    text_09 = font_large.render(rwy['designation_09'], True, COLORS['runway_markings'])
    text_rect_09 = text_09.get_rect(center=(x + 60, center_y))
    pygame.draw.rect(surface, COLORS['runway_surface'], text_rect_09.inflate(4, 4))
    surface.blit(text_09, text_rect_09)
    
    # "27" at runway 27 end
    text_27 = font_large.render(rwy['designation_27'], True, COLORS['runway_markings'])
    text_rect_27 = text_27.get_rect(center=(x + length - 60, center_y))
    pygame.draw.rect(surface, COLORS['runway_surface'], text_rect_27.inflate(4, 4))
    surface.blit(text_27, text_rect_27)


def draw_runway_secondary(surface):
    """Draw secondary/parallel runway with basic markings"""
    rwy = RUNWAY_SECONDARY
    x, y, length, width = rwy['x'], rwy['y'], rwy['length'], rwy['width']
    shoulder_w = rwy['shoulder_width']
    
    # Shoulders
    pygame.draw.rect(surface, COLORS['runway_shoulder'],
                    (x - shoulder_w, y - shoulder_w, length + shoulder_w*2, width + shoulder_w*2))
    
    # Main surface
    pygame.draw.rect(surface, COLORS['runway_surface'], (x, y, length, width))
    
    # Edge lines
    pygame.draw.rect(surface, COLORS['runway_markings'], (x, y, length, 2))
    pygame.draw.rect(surface, COLORS['runway_markings'], (x, y + width - 2, length, 2))
    
    # Centerline (simpler)
    center_y = y + width // 2
    pygame.draw.line(surface, COLORS['runway_markings'], 
                    (x + 20, center_y), (x + length - 20, center_y), 3)
    
    # Runway numbers
    font = pygame.font.SysFont('Arial', 24, bold=True)
    text_09r = font.render(rwy['designation_09'], True, COLORS['runway_markings'])
    text_27l = font.render(rwy['designation_27'], True, COLORS['runway_markings'])
    surface.blit(text_09r, (x + 40, center_y - 12))
    surface.blit(text_27l, (x + length - 80, center_y - 12))


# ============================================================================
# TAXIWAY DRAWING FUNCTIONS
# ============================================================================

def draw_taxiway_alpha(surface):
    """Draw main parallel taxiway (Alpha) with yellow centerline"""
    twy = TAXIWAY_ALPHA
    y = twy['y']
    x_start = twy['x_start']
    x_end = twy['x_end']
    width = twy['width']
    
    # Taxiway surface
    pygame.draw.rect(surface, COLORS['taxiway_surface'],
                    (x_start, y - width//2, x_end - x_start, width))
    
    # Yellow centerline with black outline
    pygame.draw.line(surface, COLORS['taxiway_edge'],
                    (x_start, y), (x_end, y), 5)
    pygame.draw.line(surface, COLORS['taxiway_centerline'],
                    (x_start, y), (x_end, y), 3)
    
    # Taxiway label
    font = pygame.font.SysFont('Arial', 11, bold=True)
    label = font.render('TWY A', True, (255, 255, 255))
    label_rect = label.get_rect()
    # Black background for readability
    bg_rect = label_rect.inflate(6, 4)
    bg_rect.center = ((x_start + x_end) // 2, y - 20)
    pygame.draw.rect(surface, (0, 0, 0), bg_rect, border_radius=3)
    label_rect.center = bg_rect.center
    surface.blit(label, label_rect)


def draw_taxiway_connectors(surface):
    """Draw all connector taxiways with labels"""
    font = pygame.font.SysFont('Arial', 9, bold=True)
    
    for connector in TAXIWAY_CONNECTORS:
        name = connector['name']
        x = connector['x']
        y_start = connector['y_start']
        y_end = connector['y_end']
        width = 20  # Connector width
        
        # Draw taxiway surface
        pygame.draw.rect(surface, COLORS['taxiway_surface'],
                        (x - width//2, y_start, width, y_end - y_start))
        
        # Yellow centerline
        pygame.draw.line(surface, COLORS['taxiway_edge'],
                        (x, y_start), (x, y_end), 4)
        pygame.draw.line(surface, COLORS['taxiway_centerline'],
                        (x, y_start), (x, y_end), 2)
        
        # Taxiway label
        label = font.render(name, True, (255, 255, 255))
        label_rect = label.get_rect()
        bg_rect = label_rect.inflate(4, 2)
        bg_rect.center = (x + 15, (y_start + y_end) // 2)
        pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect, border_radius=2)
        label_rect.center = bg_rect.center
        surface.blit(label, label_rect)


def draw_hold_short_lines(surface):
    """Draw hold-short markings before runway entry (double solid + dashed pattern)"""
    for hold_line in HOLD_SHORT_LINES:
        x = hold_line['x']
        y = hold_line['y']
        width = hold_line['width']
        
        if hold_line['orientation'] == 'horizontal':
            # Four parallel lines (ICAO standard)
            # Two solid lines
            pygame.draw.line(surface, COLORS['hold_short_solid'],
                           (x - width//2, y), (x + width//2, y), 3)
            pygame.draw.line(surface, COLORS['hold_short_solid'],
                           (x - width//2, y + 5), (x + width//2, y + 5), 3)
            
            # Two dashed lines (closer spacing)
            dash_len = 5
            gap = 3
            current_x = x - width//2
            while current_x < x + width//2:
                pygame.draw.line(surface, COLORS['hold_short_dashed'],
                               (current_x, y + 10), (min(current_x + dash_len, x + width//2), y + 10), 2)
                pygame.draw.line(surface, COLORS['hold_short_dashed'],
                               (current_x, y + 13), (min(current_x + dash_len, x + width//2), y + 13), 2)
                current_x += dash_len + gap


def draw_taxiway_nodes(surface):
    """Draw visual markers at taxiway nodes for debugging/visualization"""
    font = pygame.font.SysFont('Arial', 8, bold=True)
    
    for node_name, (x, y) in TAXI_NODES.items():
        # Skip gate nodes (they have their own rendering)
        if node_name.startswith('GATE'):
            continue
        
        # Draw node marker
        pygame.draw.circle(surface, (255, 200, 0), (int(x), int(y)), 7)
        pygame.draw.circle(surface, (60, 60, 60), (int(x), int(y)), 5)
        
        # Draw label for TWY nodes
        if node_name.startswith('TWY') or 'EXIT' in node_name:
            label = font.render(node_name.replace('_', ' '), True, (255, 255, 255))
            label_rect = label.get_rect()
            bg_rect = label_rect.inflate(3, 2)
            bg_rect.center = (x, y - 12)
            pygame.draw.rect(surface, (0, 0, 0, 200), bg_rect, border_radius=2)
            label_rect.center = bg_rect.center
            surface.blit(label, label_rect)


# ============================================================================
# APRON & TERMINAL DRAWING FUNCTIONS
# ============================================================================

def draw_apron(surface):
    """Draw airport apron (aircraft parking area) with ground markings"""
    apron = APRON
    
    # Main apron surface (concrete)
    pygame.draw.rect(surface, apron['color'],
                    (apron['x'], apron['y'], apron['width'], apron['height']))
    
    # Apron border/edge marking
    pygame.draw.rect(surface, apron['border_color'],
                    (apron['x'], apron['y'], apron['width'], apron['height']), 3)
    
    # Ground service markings (yellow lines/boxes)
    for marking in GROUND_SERVICE_MARKINGS:
        x = marking['x']
        y = marking['y']
        
        if marking['type'] == 'pushback_line':
            # Dotted yellow line for pushback guidance
            for i in range(0, 40, 8):
                pygame.draw.circle(surface, COLORS['apron_markings'], (int(x), int(y - i)), 2)


def draw_terminal_building(surface):
    """Draw main passenger terminal building with windows"""
    term = TERMINAL_BUILDING
    
    # Terminal building shadow
    pygame.draw.rect(surface, (120, 120, 110),
                    (term['x'] + 3, term['y'] + 3, term['width'], term['height']),
                    border_radius=5)
    
    # Main terminal body
    pygame.draw.rect(surface, term['color'],
                    (term['x'], term['y'], term['width'], term['height']),
                    border_radius=5)
    
    # Roof accent (darker strip on top)
    pygame.draw.rect(surface, term['roof_color'],
                    (term['x'], term['y'], term['width'], 12),
                    border_radius=5)
    
    # Terminal border
    pygame.draw.rect(surface, (140, 140, 130),
                    (term['x'], term['y'], term['width'], term['height']),
                    width=2, border_radius=5)
    
    # Windows (grid pattern)
    if term['windows']:
        window_rows = 3
        window_cols = 20
        window_w = 8
        window_h = 10
        window_spacing_x = (term['width'] - 40) // window_cols
        window_spacing_y = (term['height'] - 30) // window_rows
        
        for row in range(window_rows):
            for col in range(window_cols):
                wx = term['x'] + 20 + col * window_spacing_x
                wy = term['y'] + 18 + row * window_spacing_y
                pygame.draw.rect(surface, COLORS['terminal_windows'],
                               (wx, wy, window_w, window_h), border_radius=2)
    
    # Terminal label
    font = pygame.font.SysFont('Arial', 14, bold=True)
    label = font.render('PASSENGER TERMINAL', True, (80, 80, 80))
    label_rect = label.get_rect(center=(term['x'] + term['width']//2, term['y'] + term['height']//2))
    surface.blit(label, label_rect)


def draw_gates_and_jetways(surface):
    """Draw aircraft gates with jetways (air bridges)"""
    font_gate = pygame.font.SysFont('Arial', 13, bold=True)
    font_label = pygame.font.SysFont('Arial', 9, bold=True)
    
    for i, gate_name in enumerate(GATES):
        x, y = GATE_POS[gate_name]
        jetway_info = JETWAYS[i]
        
        # Draw jetway (air bridge) - rectangular with slight perspective
        jetway_length = jetway_info['length']
        jetway_width = 12
        jetway_x = jetway_info['x']
        jetway_y = jetway_info['y']
        
        # Jetway structure
        pygame.draw.rect(surface, COLORS['jetway'],
                        (jetway_x - jetway_width//2, jetway_y, jetway_width, jetway_length),
                        border_radius=3)
        pygame.draw.rect(surface, (180, 180, 180),
                        (jetway_x - jetway_width//2, jetway_y, jetway_width, jetway_length),
                        width=1, border_radius=3)
        
        # Gate stand marking (circle for aircraft nose position)
        pygame.draw.circle(surface, COLORS['apron_markings'], (int(x), int(y)), 25, 3)
        pygame.draw.circle(surface, COLORS['apron_markings'], (int(x), int(y)), 3)
        
        # Gate number box
        gate_num = gate_name.split('_')[1]  # Extract number from "GATE_1"
        gate_box_size = 35
        
        # Gate box background
        pygame.draw.rect(surface, (100, 120, 180),
                        (x - gate_box_size//2, y - 50, gate_box_size, 22),
                        border_radius=4)
        
        # "GATE" label
        label_gate = font_label.render('GATE', True, (255, 255, 255))
        surface.blit(label_gate, (x - label_gate.get_width()//2, y - 48))
        
        # Gate number
        label_num = font_gate.render(gate_num, True, (255, 255, 255))
        surface.blit(label_num, (x - label_num.get_width()//2, y - 36))


# ============================================================================
# AIRPORT FACILITIES DRAWING FUNCTIONS
# ============================================================================

def draw_atc_tower(surface):
    """Draw Air Traffic Control tower with glass cab"""
    tower = ATC_TOWER
    
    # Tower base (concrete)
    base_rect = (tower['x'], tower['y'] + tower['cab_height'], tower['width'], tower['base_height'])
    pygame.draw.rect(surface, tower['color'], base_rect)
    pygame.draw.rect(surface, (140, 140, 140), base_rect, width=2)
    
    # Control cab (glass - light blue)
    cab_rect = (tower['x'], tower['y'], tower['width'], tower['cab_height'])
    pygame.draw.rect(surface, tower['cab_color'], cab_rect, border_radius=3)
    pygame.draw.rect(surface, (80, 80, 80), cab_rect, width=2, border_radius=3)
    
    # Windows on cab (4 sides visible)
    for i in range(4):
        wx = tower['x'] + 5 + i * 8
        wy = tower['y'] + 8
        pygame.draw.rect(surface, (150, 200, 255), (wx, wy, 6, 15), border_radius=1)
    
    # Label
    font = pygame.font.SysFont('Arial', 8, bold=True)
    label = font.render('ATC TOWER', True, (255, 255, 255))
    label_rect = label.get_rect(center=(tower['x'] + tower['width']//2, tower['y'] + tower['height'] + 15))
    bg_rect = label_rect.inflate(4, 2)
    pygame.draw.rect(surface, (0, 0, 0), bg_rect, border_radius=2)
    surface.blit(label, label_rect)


def draw_hangars(surface):
    """Draw maintenance hangars"""
    font = pygame.font.SysFont('Arial', 10, bold=True)
    
    for hangar in HANGARS:
        x, y, w, h = hangar['x'], hangar['y'], hangar['width'], hangar['height']
        
        # Hangar structure
        pygame.draw.rect(surface, COLORS['hangar'], (x, y, w, h), border_radius=4)
        pygame.draw.rect(surface, (120, 120, 120), (x, y, w, h), width=2, border_radius=4)
        
        # Large door (darker section)
        door_w = w - 20
        door_h = h - 20
        pygame.draw.rect(surface, (100, 100, 100), (x + 10, y + 10, door_w, door_h))
        
        # Horizontal door segments
        for i in range(1, 5):
            seg_y = y + 10 + i * (door_h // 5)
            pygame.draw.line(surface, (80, 80, 80), (x + 10, seg_y), (x + 10 + door_w, seg_y), 2)
        
        # Label
        label = font.render(hangar['name'], True, (255, 255, 255))
        label_rect = label.get_rect(center=(x + w//2, y + h//2))
        surface.blit(label, label_rect)


def draw_fuel_station(surface):
    """Draw fuel station with tanks"""
    fuel = FUEL_STATION
    x, y, w, h = fuel['x'], fuel['y'], fuel['width'], fuel['height']
    
    # Fuel station building
    pygame.draw.rect(surface, (220, 220, 220), (x, y, w, h), border_radius=3)
    pygame.draw.rect(surface, (180, 180, 180), (x, y, w, h), width=2, border_radius=3)
    
    # Fuel tanks (circular)
    tank_radius = 8
    tank_spacing = w // (fuel['tanks'] + 1)
    for i in range(fuel['tanks']):
        tank_x = x + tank_spacing * (i + 1)
        tank_y = y + h//2
        pygame.draw.circle(surface, (200, 200, 200), (tank_x, tank_y), tank_radius)
        pygame.draw.circle(surface, (150, 150, 150), (tank_x, tank_y), tank_radius, 2)
    
    # Label
    font = pygame.font.SysFont('Arial', 8, bold=True)
    label = font.render('FUEL', True, (80, 80, 80))
    surface.blit(label, (x + w//2 - label.get_width()//2, y + h + 5))


def draw_fire_station(surface):
    """Draw fire station (emergency services)"""
    fire = FIRE_STATION
    x, y, w, h = fire['x'], fire['y'], fire['width'], fire['height']
    
    # Fire station building (red)
    pygame.draw.rect(surface, fire['color'], (x, y, w, h), border_radius=3)
    pygame.draw.rect(surface, (150, 30, 30), (x, y, w, h), width=2, border_radius=3)
    
    # White stripe
    pygame.draw.rect(surface, (255, 255, 255), (x + 5, y + h//2 - 2, w - 10, 4))
    
    # Label
    font = pygame.font.SysFont('Arial', 9, bold=True)
    label = font.render('FIRE STATION', True, (255, 255, 255))
    surface.blit(label, (x + w//2 - label.get_width()//2, y + h//2 - label.get_height()//2))


def draw_service_roads(surface):
    """Draw ground service vehicle roads"""
    for road in SERVICE_ROADS:
        points = road['points']
        width = road['width']
        
        if len(points) > 1:
            pygame.draw.lines(surface, COLORS['service_road'], False, points, width)


def draw_vehicle_parking(surface):
    """Draw ground vehicle parking areas"""
    font = pygame.font.SysFont('Arial', 7)
    
    for parking in VEHICLE_PARKING:
        x, y, w, h = parking['x'], parking['y'], parking['width'], parking['height']
        
        pygame.draw.rect(surface, COLORS['parking_lot'], (x, y, w, h))
        pygame.draw.rect(surface, (70, 70, 70), (x, y, w, h), width=1)
        
        # Parking stripes
        for i in range(1, 4):
            stripe_x = x + (w // 4) * i
            pygame.draw.line(surface, (100, 100, 100), (stripe_x, y), (stripe_x, y + h), 1)


def draw_perimeter_fence(surface):
    """Draw airport perimeter fence"""
    fence = PERIMETER_FENCE
    pygame.draw.lines(surface, fence['color'], True, fence['points'], fence['width'])


# ============================================================================
# MASTER DRAWING FUNCTION
# ============================================================================

def draw_complete_airport_layout(surface):
    """
    Master function to draw the complete professional airport layout.
    Call this from your main draw() method.
    """
    # Draw in correct layering order (back to front)
    
    # 1. Perimeter fence (background)
    draw_perimeter_fence(surface)
    
    # 2. Service roads
    draw_service_roads(surface)
    
    # 3. Vehicle parking
    draw_vehicle_parking(surface)
    
    # 4. Runways (with all markings)
    draw_runway_main(surface)
    draw_runway_secondary(surface)
    
    # 5. Taxiways
    draw_taxiway_alpha(surface)
    draw_taxiway_connectors(surface)
    draw_hold_short_lines(surface)
    draw_taxiway_nodes(surface)
    
    # 6. Apron and terminal
    draw_apron(surface)
    draw_terminal_building(surface)
    draw_gates_and_jetways(surface)
    
    # 7. Airport facilities
    draw_atc_tower(surface)
    draw_hangars(surface)
    draw_fuel_station(surface)
    draw_fire_station(surface)
    
    # Note: Aircraft are drawn separately in main draw loop


# ============================================================================
# UTILITY FUNCTIONS FOR AIRCRAFT INTEGRATION
# ============================================================================

def get_runway_threshold_position(runway_id, end='09'):
    """Get exact threshold position for aircraft landing"""
    if runway_id == '09/27':
        rwy = RUNWAY_MAIN
        if end == '09':
            return (rwy['x'] + 50, rwy['y'] + rwy['width']//2)
        else:  # 27
            return (rwy['x'] + rwy['length'] - 50, rwy['y'] + rwy['width']//2)
    return (0, 0)


def get_gate_parking_position(gate_name):
    """Get exact aircraft parking position at gate"""
    return GATE_POS.get(gate_name, (0, 0))


def get_taxiway_path_smooth(start_node, end_node):
    """
    Get smooth taxiway path with curves.
    Returns list of (x, y) points for smooth aircraft movement.
    """
    if start_node not in TAXI_NODES or end_node not in TAXI_NODES:
        return []
    
    start_pos = TAXI_NODES[start_node]
    end_pos = TAXI_NODES[end_node]
    
    # For now, return straight line; can enhance with Bézier curves
    return [start_pos, end_pos]
