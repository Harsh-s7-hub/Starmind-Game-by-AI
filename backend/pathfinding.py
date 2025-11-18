# backend/pathfinding.py
from heapq import heappush, heappop
from typing import List, Tuple, Optional

GridPos = Tuple[int, int]

class Grid:
    def __init__(self, cols: int, rows: int, walkable=None):
        self.cols = cols
        self.rows = rows
        # walkable: optional set of blocked tiles; by default all walkable
        self.walkable = walkable if walkable is not None else set()

    def in_bounds(self, p: GridPos) -> bool:
        x, y = p
        return 0 <= x < self.cols and 0 <= y < self.rows

    def is_walkable(self, p: GridPos) -> bool:
        return p not in self.walkable

    def neighbors(self, p: GridPos) -> List[GridPos]:
        x, y = p
        results = [(x+1,y), (x-1,y), (x,y+1), (x,y-1),
                   (x+1,y+1),(x-1,y-1),(x+1,y-1),(x-1,y+1)]
        results = [n for n in results if self.in_bounds(n) and self.is_walkable(n)]
        return results

def heuristic(a: GridPos, b: GridPos) -> float:
    # Euclidean distance heuristic (since diagonals allowed)
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

def a_star_search(grid: Grid, start: GridPos, goal: GridPos) -> Optional[List[GridPos]]:
    if not grid.in_bounds(start) or not grid.in_bounds(goal) or not grid.is_walkable(start) or not grid.is_walkable(goal):
        return None

    frontier = []
    heappush(frontier, (0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}

    while frontier:
        _, current = heappop(frontier)

        if current == goal:
            # reconstruct path
            path = []
            while current:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for n in grid.neighbors(current):
            new_cost = cost_so_far[current] + heuristic(current, n)
            if n not in cost_so_far or new_cost < cost_so_far[n]:
                cost_so_far[n] = new_cost
                priority = new_cost + heuristic(n, goal)
                heappush(frontier, (priority, n))
                came_from[n] = current

    return None
