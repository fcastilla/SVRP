class Variable:

    v_x = 1
    v_y = 2
    v_n = 3
    v_error = 10

    def __init__(self):
        self.name = ""
        self.col = 0
        self.solutionVal = 0
        self.depot = None
        self.scenario = None
        self.shift = -1
        self.route = None
        self.customer = None
        self.type = Variable.v_error