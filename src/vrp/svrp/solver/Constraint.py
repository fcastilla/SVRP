class Constraint:
    c_minFleet = 1
    c_maxFleet = 2
    c_fleetSize = 3
    c_demand = 4
    c_feasibility = 5
    c_optimality = 6
    c_error = 10

    def __init__(self):
        self.name = ""
        self.row = 0
        self.depot = None
        self.scenario = None
        self.shift = -1
        self.type = Constraint.c_error