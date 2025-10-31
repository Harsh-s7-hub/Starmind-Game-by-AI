# backend/a_star.py
"""
A* for graph of nodes.
API:
    AStar(graph_adj, positions)
    path, cost = astar.find_path(start_id, goal_id, avoid=set())
 - graph_adj: dict node_id -> list(node_id)
 - positions: dict node_id -> (x, y)  (for heuristic)
"""

import heapq
import math

class AStar:
    def __init__(self, graph_adj, positions):
        self.adj = graph_adj
        self.pos = positions

    def heuristic(self, a, b):
        ax, ay = self.pos[a]
        bx, by = self.pos[b]
        return abs(ax-bx) + abs(ay-by)  # manhattan

    def find_path(self, start, goal, avoid=None, cost_fn=None):
        if avoid is None:
            avoid = set()
        if cost_fn is None:
            def cost_fn(u, v):
                # default: euclidean length between positions
                ux, uy = self.pos[u]
                vx, vy = self.pos[v]
                return math.hypot(ux-vx, uy-vy)

        frontier = []
        heapq.heappush(frontier, (0, start))
        came_from = {start: None}
        cost_so_far = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                # reconstruct
                path = []
                n = current
                while n is not None:
                    path.append(n)
                    n = came_from[n]
                path.reverse()
                return path, cost_so_far[current]

            for neigh in self.adj.get(current, []):
                if neigh in avoid:
                    continue
                new_cost = cost_so_far[current] + cost_fn(current, neigh)
                if neigh not in cost_so_far or new_cost < cost_so_far[neigh]:
                    cost_so_far[neigh] = new_cost
                    priority = new_cost + self.heuristic(neigh, goal)
                    heapq.heappush(frontier, (priority, neigh))
                    came_from[neigh] = current
        return None, float('inf')
