# backend/csp_solver.py
"""
Tiny CSP solver (backtracking) and a CSPPlanner wrapper.
Used for example tasks: allocate targets to empires under capacity/resource constraints.
"""

def csp_solve(variables, domains, constraints):
    vars_list = list(variables)
    assignment = {}
    def backtrack(i=0):
        if i == len(vars_list):
            return assignment.copy()
        v = vars_list[i]
        for val in domains[v]:
            assignment[v] = val
            ok = True
            for cons in constraints:
                try:
                    if not cons(assignment):
                        ok = False
                        break
                except KeyError:
                    # constraint refers to unassigned var -> ignore
                    pass
            if not ok:
                del assignment[v]
                continue
            sol = backtrack(i+1)
            if sol is not None:
                return sol
            del assignment[v]
        return None
    return backtrack()

class CSPPlanner:
    def __init__(self):
        pass

    def choose_colonization(self, empire_id, candidate_systems, empire_resources, system_costs, max_take=1):
        """
        Simple wrapper: choose up to max_take systems to colonize
        - candidate_systems: list of system ids
        - system_costs: dict system_id -> cost
        - empire_resources: int
        Returns chosen list (may be empty)
        """
        # build domains: each variable is index 0..max_take-1 with domain candidate_systems + [None]
        vars_ = [f"slot{i}" for i in range(max_take)]
        domains = {v: candidate_systems + [None] for v in vars_}
        # constraints: no duplicate system (excluding None), and total cost <= resources
        def constraint_no_dup(assign):
            vals = [v for v in assign.values() if v is not None]
            return len(vals) == len(set(vals))
        def constraint_cost(assign):
            vals = [v for v in assign.values() if v is not None]
            total = sum(system_costs.get(sid, 0) for sid in vals)
            return total <= empire_resources

        sol = csp_solve(vars_, domains, [constraint_no_dup, constraint_cost])
        if not sol:
            return []
        chosen = [sol[v] for v in vars_ if sol[v] is not None]
        return chosen
