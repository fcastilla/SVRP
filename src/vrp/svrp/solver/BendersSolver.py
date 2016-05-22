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
        model.constraints = {}
        model.numCols = 0
        model.numRows = 0
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
        self.createAlphaVariables(self.master)
        self.createAlphaHVariables(self.master)
        self.createSingleVarDepotConstraint(self.master)
        self.minimumFleetSizeConstraints(self.master)
        self.maximumFleetSizeConstraints(self.master)
        self.createAlphaConstraints(self.master)

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
        for vt in self.pdata.vehicleTypes:
            for k, d in self.pdata.depots.iteritems():
                for i in range(vt.maxFleet + 1):
                    v = Variable()
                    v.type = Variable.v_n
                    v.name = model.getName("n", d.id, i, vt.type)
                    v.col = model.numCols
                    v.depot = d
                    v.digit = i
                    v.vehicleType = vt
                    model.variables[v.name] = v
                    model.lp.variables.add(obj=[i * self.pdata.depotCosts[d.id][vt.type]], types=["B"], names=[v.name])
                    model.numCols += 1

    def createAlphaVariables(self, model):
        for t in range(self.pdata.shifts):
            for i in range(params.numberOfScenariosPerShift):
                scenario = self.scenarios[t][i]
                for cluster in scenario.clusterList:
                    depot =  cluster.depot
                    v = Variable()
                    v.type = Variable.v_alpha
                    v.name = model.getName("alpha", t, i, depot.id)
                    v.depot = depot
                    v.shift = i
                    v.scenario = scenario
                    v.col = model.numCols
                    model.variables[v.name] = v
                    model.lp.variables.add(names=[v.name])
                    model.numCols += 1

    def createAlphaHVariables(self, model):
        for t in range(self.pdata.shifts):
            for k, depot in self.pdata.depots.iteritems():
                v = Variable()
                v.type = Variable.v_alphaH
                v.name = model.getName("alphaH", t, depot.id)
                v.shift = t
                v.depot = depot
                v.col = model.numCols
                model.variables[v.name] = v
                model.lp.variables.add(obj=[1.0], names=[v.name])
                model.numCols += 1

    def createXYVariables(self, model, shift, scenario, cluster):
        for vt in self.pdata.vehicleTypes:
            if vt.type not in cluster.routes:
                continue

            for route in cluster.routes[vt.type]:
                # Create x variable
                v = Variable()
                v.type = Variable.v_x
                v.name = model.getName("x", shift, scenario.id, cluster.depot.id, route.id, vt.type)
                v.col = model.numCols
                v.shift = shift
                v.scenario = scenario
                v.depot = cluster.depot
                v.route = route
                v.vehicleType = vt

                coef = vt.lvCost * route.distance
                model.variables[v.name] = v
                model.lp.variables.add(obj=[coef], types=["B"], names=[v.name])
                model.numCols += 1

                # Create y variable
                v = Variable()
                v.type = Variable.v_y
                v.name = model.getName("y", shift, scenario.id, cluster.depot.id, route.id, vt.type)
                v.col = model.numCols
                v.shift = shift
                v.scenario = scenario
                v.depot = cluster.depot
                v.route = route
                v.vehicleType = vt

                coef = vt.hvCost * route.distance
                model.variables[v.name] = v
                model.lp.variables.add(obj=[coef], types=["B"], names=[v.name])
                model.numCols += 1

    #endregion

    #region Constraint Creation
    def minimumFleetSizeConstraints(self, model):
        for vt in self.pdata.vehicleTypes:
            rhs = vt.minFleet

            # If minimum fleet size is 0, ignore this constraint
            if rhs <= 0:
                return 0

            c = Constraint()
            c.type = Constraint.c_minFleet
            c.name = model.getName("minFleet", vt.type)
            c.vehicleType = vt
            c.row = model.numRows

            mind = []
            mval = []

            for key, d in self.pdata.depots.iteritems():
                for i in range(vt.maxFleet + 1):
                    nvar = model.getVariable(model.getName("n", d.id, i, vt.type))
                    mind.append(nvar.col)
                    mval.append(nvar.digit)

            model.constraints[c.name] = c
            model.createConstraint(mind, mval, "G", rhs, c.name)
            model.numRows += 1

    def maximumFleetSizeConstraints(self, model):
        for vt in self.pdata.vehicleTypes:
            rhs = vt.maxFleet

            c = Constraint()
            c.type = Constraint.c_maxFleet
            c.name = model.getName("maxFleet", vt.type)
            c.vehicleType = vt
            c.row = model.numRows

            mind = []
            mval = []

            for key, d in self.pdata.depots.iteritems():
                for i in range(vt.maxFleet + 1):
                    nvar = model.getVariable(model.getName("n", d.id, i, vt.type))
                    mind.append(nvar.col)
                    mval.append(nvar.digit)

            model.constraints[c.name] = c
            model.createConstraint(mind, mval, "L", rhs, c.name)
            model.numRows += 1

    def createAlphaConstraints(self, model):
        for t in range(self.pdata.shifts):
            for k, depot in self.pdata.depots.iteritems():
                c = Constraint()
                c.type = Constraint.c_alpha
                c.name = model.getName("c_alpha", t, depot.id)
                c.depot = depot
                c.shift = t
                c.row = model.numRows

                mind = []
                mval = []
                rhs = 0.0

                # get the alphaH variable
                alpha1 = model.getVariable(model.getName("alphaH", t, depot.id))
                mind.append(alpha1.col)
                mval.append(1.0)

                # get the ohter alpha variables
                for i in range(params.numberOfScenariosPerShift):
                    alpha2 = model.getVariable(model.getName("alpha", t, i, depot.id))
                    mind.append(alpha2.col)
                    mval.append(-1/params.numberOfScenariosPerShift)

                model.constraints[c.name] = c
                model.createConstraint(mind, mval, "E", rhs, c.name)
                model.numRows += 1


    def fleetSizeConstraints(self, model, shift, scenario, cluster, nval):
        for vt in self.pdata.vehicleTypes:
            if vt.type not in cluster.routes:
                continue
            c = Constraint()
            c.type = Constraint.c_fleetSize
            c.name = model.getName("fleetSize", shift, scenario.id, cluster.depot.id, vt.type)
            c.shift = shift
            c.scenario = scenario
            c.depot = cluster.depot.id
            c.vehicleType = vt
            c.row = model.numRows

            mind = []
            mval = []
            rhs = nval

            for route in cluster.routes[vt.type]:
                # get the x variable and add it to the constraint
                xname = model.getName("x", shift, scenario.id, cluster.depot.id, route.id, vt.type)
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

            for vt in self.pdata.vehicleTypes:
                if vt.type not in cluster.routes:
                    continue

                for route in cluster.routes[vt.type]:
                    # check if customer c belongs in this route
                    if customer in route.customers:
                        # add the x variable
                        xname = model.getName("x", shift, scenario.id, cluster.depot.id, route.id, vt.type)
                        xvar = model.getVariable(xname)
                        mind.append(xvar.col)
                        mval.append(1.0)

                        # add the y variable
                        yname = model.getName("y", shift, scenario.id, cluster.depot.id, route.id, vt.type)
                        yvar = model.getVariable(yname)
                        mind.append(yvar.col)
                        mval.append(1.0)

            model.constraints[c.name] = c
            model.createConstraint(mind, mval, "E", rhs, c.name)
            model.numRows += 1

    def createSingleVarDepotConstraint(self, model):
        for vt in self.pdata.vehicleTypes:
            for key, depot in self.pdata.depots.iteritems():
                c = Constraint()
                c.type = Constraint.c_singlevar
                c.name = model.getName("singleVar", depot.id, vt.type)
                c.depot = depot
                c.vehicleType = vt
                c.row = model.numRows

                mind = []
                mval = []
                rhs = 1.0

                # get the "N" variables
                for i in range(vt.maxFleet + 1):
                    nvar = model.getVariable(model.getName("n", depot.id, i, vt.type))
                    mind.append(nvar.col)
                    mval.append(1.0)

                model.constraints[c.name] = c
                model.createConstraint(mind, mval, "E", rhs, c.name)
                model.numRows += 1

    def createFeasibilityCut(self, depot):
        c = Constraint()
        c.type = Constraint.c_feasibility
        c.name = self.master.getName("feasibility", self.f_cons)
        c.row = self.master.numRows

        mind = []
        mval = []
        rhs = 0

        for vt in self.pdata.vehicleTypes:
            for i in range(vt.maxFleet + 1):
                nvar = self.master.getVariable(self.master.getName("n", depot.id, i, vt.type))

                # check if the variable is in the current master solution
                if nvar.solutionVal != 0:
                    rhs += 1
                    mind.append(nvar.col)
                    mval.append(1.0)

        self.master.constraints[c.name] = c
        self.master.createConstraint(mind, mval, "L", rhs - 1, c.name)
        self.master.numRows += 1
        self.f_cons += 1

    def createOptimalityCut(self, shift, scenario, depot, cost):
        c = Constraint()
        c.type = Constraint.c_optimality
        c.name = self.master.getName("optimality", self.o_cons)
        c.shift = shift
        c.depot = depot
        c.scenario = scenario
        c.row = self.master.numRows

        mind = []
        mval = []
        contVars = 0

        # get the alpha variable
        alpha = self.master.getVariable(self.master.getName("alpha", shift, scenario.id, depot.id))
        mind.append(alpha.col)
        mval.append(1.0)

        #get the "N" variables
        for vt in self.pdata.vehicleTypes:
            for i in range(vt.maxFleet + 1):
                nvar = self.master.getVariable(self.master.getName("n", depot.id, i, vt.type))

                # check if the variable is part of the current master solution
                if nvar.solutionVal != 0:
                    contVars += 1
                    mind.append(nvar.col)
                    mval.append(-cost)

        contVars -= 1
        self.master.constraints[c.name] = c
        self.master.createConstraint(mind, mval, "G",cost*-contVars , c.name)
        self.master.numRows += 1
        self.o_cons += 1

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
        iter = 0

        # Benders algorithm
        while infeasible or zsup - zinf > params.eps:
            iter += 1
            print "Iter:", iter, " | Zinf:", zinf\
                , " | Zsup:", zsup, " | O:", self.o_cons, " | F:", self.f_cons

            infeasible = False
            zsup = 0

            # write the master lp
            self.master.lp.write("..\\..\\..\\lps\\svrp_master.lp")

            # solve the (updated) master problem
            print "Solving master problem... "
            self.master.lp.solve()

            # get the trial solution
            solution = self.master.lp.solution
            sol = solution.get_values()
            zinf = solution.get_objective_value()

            nvals = {}

            for key, d in self.pdata.depots.iteritems():
                nvals[d.id] = {}
                for vt in self.pdata.vehicleTypes:
                    nvals[d.id][vt.type] = 0

                    for i in range(vt.maxFleet + 1):
                        nvar = self.master.getVariable(self.master.getName("n", d.id, i, vt.type))
                        nvar.solutionVal = sol[nvar.col]
                        zsup += (nvar.digit * nvar.solutionVal) * self.pdata.depotCosts[d.id][vt.type]

                        nvals[d.id][vt.type] += (nvar.digit * nvar.solutionVal)

            # Run each subproblem with the updated n values of the trial solution
            # and add the proper feasibility and optimality cuts
            for t in range(self.pdata.shifts):
                for i in range(params.numberOfScenariosPerShift):
                    scenario = self.scenarios[t][i]
                    for cluster in scenario.clusterList:
                        depot = cluster.depot

                        # Get the subproblem
                        sp = self.subproblems[t][i][depot.id]

                        for vt in self.pdata.vehicleTypes:
                            # change the rhs of the fleet size constraint with the value obtained from the master
                            nval = nvals[depot.id][vt.type]
                            c = sp.getConstraint(sp.getName("fleetSize", t, i, depot.id, vt.type))
                            sp.changeRHS(c.row, nval)

                        # write the subproblem lp file
                        sp.lp.write("..\\..\\..\\lps\\svrp_subproblem.lp")

                        # solve the subproblem
                        sp.lp.solve()

                        # get the subproblem status
                        sp_sol = sp.lp.solution
                        status = sp_sol.get_status()

                        if status in [101,102]: # feasible
                            # add the objective value
                            sp_obj = sp_sol.get_objective_value()
                            zsup += (1/params.numberOfScenariosPerShift) * sp_obj

                            # create optimality cut in the master problem
                            self.createOptimalityCut(t, scenario, depot, sp_obj)

                        elif status in [103]: # infeasible
                            infeasible = True

                            # create an infeasiblity cut in the master problem
                            self.createFeasibilityCut(depot)

        print "Final sol: ", zinf, " | ", zsup

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