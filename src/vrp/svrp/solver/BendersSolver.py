from __future__ import division

import cplex
import numpy as np
import matplotlib.pyplot as plt

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.svrp.inputdata.ProblemData import ProblemData
from src.vrp.svrp.inputdata.Scenario import Scenario
from src.vrp.svrp.solver.Variable import Variable
from src.vrp.svrp.solver.Constraint import Constraint
from src.vrp.svrp.solver.Model import Model

class BendersSolver:
    def __init__(self, pdata):
        assert isinstance(pdata, ProblemData)

        self.pdata = pdata
        self.scenarios = {}
        self.master = Model()
        self.subproblems = {}

        self.f_cons = 0
        self.o_cons = 0

    def initializeModel(self, model):
        model.variables = {}
        model.numCols = 0
        model.lp = cplex.Cplex()
        model.lp.set_log_stream(None)
        model.lp.set_error_stream(None)
        model.lp.set_warning_stream(None)
        model.lp.set_results_stream(None)

    def createMaster(self):
        # initialize new lp for master problem
        self.master = Model()
        self.initializeModel(self.master)

        # set the objective sense of the master problem
        self.master.lp.objective.set_sense(self.master.lp.objective.sense.minimize)
        self.createNVariables(self.master)
        self.minimumFleetSizeConstraints(self.master)
        self.maximumFleetSizeConstraints(self.master)

    def createSubproblems(self):
        self.subproblems = {}

        # create a subproblem for each shift, depot, scenario
        for t in range(self.pdata.shifts):
            self.subproblems[t] = {}
            for i in range(params.numberOfScenariosPerShift):
                self.subproblems[t][i] = {}
                scenario = self.scenarios[t][i]
                for cluster in scenario.clusterList:
                    d = cluster.depot
                    sp = self.subproblems[t][i][d.id] = Model()
                    self.initializeModel(sp)

                    # set the objective of the subproblem
                    sp.lp.objective.set_sense(sp.lp.objective.sense.minimize)
                    self.createXYVariables(sp, t, scenario, cluster)
                    self.fleetSizeConstraints(sp, t, scenario, cluster, 0)
                    self.customerSatisfactionConstraints(sp, t, scenario, cluster)

    def createNVariables(self, model):
        for k, d in self.pdata.depots.iteritems():
            for i in range(self.pdata.maximumFleetSize + 1):
                v = Variable()
                v.type = Variable.v_n
                v.name = model.getName("n", d.id, i)
                v.col = model.numCols
                v.depot = d
                v.digit = i
                model.variables[v.name] = v
                model.lp.variables.add(obj=[i * self.pdata.depotOperationCost], types=["I"], names=[v.name])
                model.numCols += 1

    def createAlphaVariables(self):
        pass

    def createXYVariables(self, model, shift, scenario, cluster):
        for route in cluster.routes:
            # Create x variable
            v = Variable()
            v.type = Variable.v_x
            v.name = model.getName("x", shift, scenario.id, cluster.depot.id, route.id)
            v.col = model.numCols
            v.shift = shift
            v.scenario = scenario
            v.depot = cluster.depot
            v.route = route

            coef = float((1 / params.numberOfScenariosPerShift)) * self.pdata.lvCost * route.distance
            model.variables[v.name] = v
            model.lp.variables.add(obj=[coef], types=["B"], names=[v.name])
            model.numCols += 1

            # Create y variable
            v = Variable()
            v.type = Variable.v_y
            v.name = model.getName("y", shift, scenario.id, cluster.depot.id, route.id)
            v.col = model.numCols
            v.shift = shift
            v.scenario = scenario
            v.depot = cluster.depot
            v.route = route

            coef = (1 / params.numberOfScenariosPerShift) * self.pdata.hvCost * route.distance
            model.variables[v.name] = v
            model.lp.variables.add(obj=[coef], types=["B"], names=[v.name])
            model.numCols += 1

    #endregion

    #region Constraint Creation
    def minimumFleetSizeConstraints(self, model):
        rhs = self.pdata.minimumFleetSize

        # If minimum fleet size is 0, ignore this constraint
        if rhs <= 0:
            return 0

        c = Constraint()
        c.type = Constraint.c_minFleet
        c.name = model.getName("minFleet")
        c.row = model.numRows

        mind = []
        mval = []

        for key, d in self.pdata.depots.iteritems():
            for i in range(self.pdata.maximumFleetSize + 1):
                nvar = model.getVariable(model.getName("n", d.id, i))
                mind.append(nvar.col)
                mval.append(nvar.digit)

        model.constraints[c.name] = c
        model.createConstraint(mind, mval, "G", rhs, c.name)
        model.numRows += 1

    def maximumFleetSizeConstraints(self, model):
        rhs = self.pdata.maximumFleetSize

        c = Constraint()
        c.type = Constraint.c_maxFleet
        c.name = model.getName("maxFleet")
        c.row = model.numRows

        mind = []
        mval = []

        for key, d in self.pdata.depots.iteritems():
            for i in range(self.pdata.maximumFleetSize + 1):
                nvar = model.getVariable(model.getName("n", d.id, i))
                mind.append(nvar.col)
                mval.append(nvar.digit)

        model.constraints[c.name] = c
        model.createConstraint(mind, mval, "L", rhs, c.name)
        model.numRows += 1

    def fleetSizeConstraints(self, model, shift, scenario, cluster, nval):
        c = Constraint()
        c.type = Constraint.c_fleetSize
        c.name = model.getName("fleetSize", shift, scenario.id, cluster.depot.id)
        c.shift = shift
        c.scenario = scenario
        c.depot = cluster.depot.id
        c.row = model.numRows

        mind = []
        mval = []
        rhs = nval

        for route in cluster.routes:
            # get the x variable and add it to the constraint
            xname = model.getName("x", shift, scenario.id, cluster.depot.id, route.id)
            xvar = model.getVariable(xname)
            mind.append(xvar.col)
            mval.append(1.0)

        model.constraints[c.name] = c
        model.createConstraint(mind, mval, "L", rhs, c.name)
        model.numRows += 1

    def customerSatisfactionConstraints(self, model, shift, scenario, cluster):
        for customer in cluster.customers:
            c = Constraint()
            c.type = Constraint.c_demand
            c.name = model.getName("demand", shift, scenario.id, cluster.depot.id)
            c.row = model.numRows

            mind = []
            mval = []
            rhs = 1.0

            for route in cluster.routes:
                # check if customer c belongs in this route
                if customer in route.customers:
                    # add the x variable
                    xname = model.getName("x", shift, scenario.id, cluster.depot.id, route.id)
                    xvar = model.getVariable(xname)
                    mind.append(xvar.col)
                    mval.append(1.0)

                    # add the y variable
                    yname = model.getName("y", shift, scenario.id, cluster.depot.id, route.id)
                    yvar = model.getVariable(yname)
                    mind.append(yvar.col)
                    mval.append(1.0)

            model.constraints[c.name] = c
            model.createConstraint(mind, mval, "E", rhs, c.name)
            model.numRows += 1

    def createFeasibilityCut(self, depot, rhs):
        c = Constraint()
        c.type = Constraint.c_feasibility
        c.name = self.master.getName("feasibility", self.f_cons)
        c.row = self.master.numRows

        mind = []
        mval = []

        for i in range(self.pdata.maximumFleetSize + 1):
            nvar = self.master.getVariable(self.master.getName("n", depot.id, i))
            mind.append(nvar.col)
            mval.append(1.0)

        self.master.constraints[c.name] = c
        self.master.createConstraint(mind, mval, "L", rhs, c.name)
        self.master.numRows += 1
        self.f_cons += 1

    def createOptimalityCut(self):
        pass

    #endregion

    def createScenarios(self):
        print "Creating scenarios..."
        for t in range(self.pdata.shifts):
            self.scenarios[t] = {}
            for i in range(params.numberOfScenariosPerShift):
                self.scenarios[t][i] = Scenario(i,t,self.pdata)

    def solve(self):
        # create scenarios
        self.createScenarios()

        # create subproblems
        self.createSubproblems()

        # create the master problem
        self.createMaster()
        zinf = -10000000000000
        zsup = 10000000000000
        infeasible = False

        # Benders algorithm
        while zsup - zinf > params.eps or infeasible:
            infeasible = False

            # write the master lp
            self.master.lp.write("..\\..\\..\\lps\\svrp_master.lp")

            # solve the (updated) master problem
            self.master.lp.solve()

            # get the trial solution
            solution = self.master.lp.solution
            sol = solution.get_values()

            nvals = {}

            for key, d in self.pdata.depots.iteritems():
                for i in range(self.pdata.maximumFleetSize + 1):
                    nvar = self.master.getVariable(self.master.getName("n", d.id, i))
                    nvar.solutionVal = sol[nvar.col]

                    if d.id in nvals:
                        nvals[d.id] += (nvar.digit * nvar.solutionVal)
                    else:
                        nvals[d.id] = (nvar.digit * nvar.solutionVal)


            # Run each subproblem with the updated n values of the trial solution
            # and add the proper feasibility and optimality cuts
            for t in range(self.pdata.shifts):
                for i in range(params.numberOfScenariosPerShift):
                    scenario = self.scenarios[t][i]
                    for cluster in scenario.clusterList:
                        depot = cluster.depot

                        # Get the subproblem
                        sp = self.subproblems[t][i][depot.id]

                        # change the rhs of the fleet size constraint with the value obtained from the master
                        nval = nvals[depot.id]
                        c = sp.getConstraint(sp.getName("fleetSize", t, i, depot.id))
                        sp.changeRHS(c.row, nval)

                        # write the subproblem lp file
                        sp.lp.write("..\\..\\..\\lps\\svrp_subproblem.lp")

                        # solve the subproblem
                        sp.lp.solve()

                        # get the subproblem status
                        sp_sol = sp.lp.solution
                        status = sp_sol.get_status()

                        if status in [101,102]: # feasible
                            # create optimality cut in the master problem
                            # aggregate to the objective function
                            pass
                        elif status in [103]: # infeasible
                            infeasible = True

                            # create an infeasiblity cut in the master problem
                            self.createFeasibilityCut(depot, nval - 1)

    def plotShiftSolution(self, scenario, routes):
        # create new plot
        fig = plt.figure()
        fig.suptitle('Shift:' + str(scenario.shift) + " - Scenario:" + str(scenario.id) , fontsize=20)
        ax = fig.add_subplot(111)

        # plot customers and depots
        for key, c in scenario.customers.iteritems():
            marker = "ko"
            if c.isDepot == True:
                marker = "ks"
            ax.plot([c.x], [c.y], marker)

        # plot routes
        for route in routes:
            color = np.random.rand(3,1)
            line = "-"
            if route.vehicleType == 2:
                line = "--"

            for i in range(len(route.customers)-1):
                c1 = route.customers[i]
                c2 = route.customers[i+1]
                ax.plot([c1.x, c2.x], [c1.y, c2.y], c=color, linestyle=line)