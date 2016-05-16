import cplex

class Model:
    def __init__(self):
        self.lp = None
        self.numCols = 0
        self.numRows = 0
        self.variables = {}
        self.constraints = {}

    def getVariable(self, vname):
        if vname in self.variables:
            return self.variables[vname]
        return None

    def getConstraint(self, cname):
        if cname in self.constraints:
            return self.constraints[cname]
        return None

    def getName(self, sufix, *params):
        s = sufix
        for p in params:
            s += "_" + str(p)
        return s

    def createConstraint(self, mind, mval, sense, rhs, name):
        mConstraint = cplex.SparsePair(ind=mind, val=mval)
        self.lp.linear_constraints.add(lin_expr=[mConstraint],
                                    senses=[sense], rhs=[rhs],
                                    names=[name])

    def changeRHS(self, row, rhs):
        self.lp.linear_constraints.set_rhs(row, rhs)