from __future__ import division

import cplex
import numpy as np
import matplotlib.pyplot as plt

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.svrp.inputdata.ProblemData import ProblemData
from src.vrp.svrp.inputdata.Scenario import Scenario
from src.vrp.svrp.solver.Variable import Variable

class Solver:
    def __init__(self, pdata):
        assert isinstance(pdata, ProblemData)

        self.pdata = pdata
        self.scenarios = {}

        self.lp = None
        self.variables = {}
        self.numCols = 0

    def reset(self):
        self.lp = None
        self.variables = {}
        self.numCols = 0

    def createLp(self):
        self.reset()
        self.lp = cplex.Cplex()
        self.lp.set_log_stream(None)
        self.lp.set_error_stream(None)
        self.lp.set_warning_stream(None)
        self.lp.set_results_stream(None)
        self.createModel()

    def createModel(self):
        self.lp.objective.set_sense(self.lp.objective.sense.minimize)
        self.createVariables()
        self.createConstraints()

    #region Variable Creation
    def createVariables(self):
        print "Creating variables... "
        num = self.createNVariables()
        num += self.createXYVariables()
        print str(num) + " variables created."

    def createNVariables(self):
        numVars = 0
        for k, d in self.pdata.depots.iteritems():
            v = Variable()
            v.type = Variable.v_n
            v.name = "n_" + str(d.id)
            v.col = self.numCols
            v.depot = d
            self.variables[v.name] = v
            self.lp.variables.add(obj=[self.pdata.depotOperationCost], types=["I"], names=[v.name])
            self.numCols += 1
            numVars += 1
        return numVars

    def createXYVariables(self):
        numVars = 0
        for t in range(self.pdata.shifts):
            for i in range(params.numberOfScenariosPerShift):
                scenario = self.scenarios[t][i]
                for cluster in scenario.clusterList:
                    for route in cluster.routes:
                        # Create x variable
                        v = Variable()
                        v.type = Variable.v_x
                        v.name = "x_" + str(t) + "_" + str(i) + \
                                 "_" + str(cluster.depot.id) + "_" + str(route.id)
                        v.col = self.numCols
                        v.shift = t
                        v.scenario = scenario
                        v.depot = cluster.depot
                        v.route = route

                        coef = float((1 / params.numberOfScenariosPerShift)) * self.pdata.lvCost * route.distance
                        self.variables[v.name] = v
                        self.lp.variables.add(obj=[coef], types=["B"], names=[v.name])
                        self.numCols += 1
                        numVars += 1

                        # Create y variable
                        v = Variable()
                        v.type = Variable.v_y
                        v.name = "y_" + str(t) + "_" + str(i) + \
                                 "_" + str(cluster.depot.id) + "_" + str(route.id)
                        v.col = self.numCols
                        v.shift = t
                        v.scenario = scenario
                        v.depot = cluster.depot
                        v.route = route

                        coef = (1 / params.numberOfScenariosPerShift) * self.pdata.hvCost * route.distance
                        self.variables[v.name] = v
                        self.lp.variables.add(obj=[coef], types=["B"], names=[v.name])
                        self.numCols += 1
                        numVars += 1
        return numVars

    def getVariable(self, vname):
        if vname in self.variables:
            return self.variables[vname]
        return None

    def getName(self, sufix, *params):
        s = sufix
        for p in params:
            s += "_" + str(p)
        return s
    #endregion

    #region Constraint Creation
    def createConstraints(self):
        print "Creating constraints..."
        num = self.fleetPerDepotConstraints()
        num += self.customerSatisfactionConstraints()
        print str(num) + " constraints created..."

    def fleetPerDepotConstraints(self):
        numCons = 0
        for t in range(self.pdata.shifts):
            for i in range(params.numberOfScenariosPerShift):
                scenario = self.scenarios[t][i]
                for cluster in scenario.clusterList:
                    mind = []
                    mval = []
                    rhs = 0.0

                    # get the N variable and add it to the constraint
                    nname = self.getName("n", cluster.depot.id)
                    nvar = self.getVariable(nname)
                    mind.append(nvar.col)
                    mval.append(-1.0)

                    for route in cluster.routes:
                        # get the x variable and add it to the constraint
                        xname = self.getName("x", t, i, cluster.depot.id, route.id)
                        xvar = self.getVariable(xname)
                        mind.append(xvar.col)
                        mval.append(1.0)

                    self.createConstraint(mind,mval,"L",rhs,self.getName("fleetSize",t,i,cluster.depot.id))
                    numCons += 1
        return numCons

    def customerSatisfactionConstraints(self):
        numCons = 0
        for t in range(self.pdata.shifts):
            for i in range(params.numberOfScenariosPerShift):
                scenario = self.scenarios[t][i]
                for cluster in scenario.clusterList:
                    for c in cluster.customers:
                        mind = []
                        mval = []
                        rhs = 1.0

                        for route in cluster.routes:
                            # check if customer c belongs in this route
                            if c in route.customers:
                                # add the x variable
                                xname = self.getName("x", t, i, cluster.depot.id, route.id)
                                xvar = self.getVariable(xname)
                                mind.append(xvar.col)
                                mval.append(1.0)

                                # add the y variable
                                yname = self.getName("y", t, i, cluster.depot.id, route.id)
                                yvar = self.getVariable(yname)
                                mind.append(yvar.col)
                                mval.append(1.0)

                        self.createConstraint(mind,mval,"E",rhs,self.getName("customerSatisfaction",t,i,cluster.depot.id,c.id))
                        numCons += 1
        return numCons

    def createConstraint(self, mind, mval, sense, rhs, name):
        mConstraint = cplex.SparsePair(ind=mind, val=mval)
        self.lp.linear_constraints.add(lin_expr=[mConstraint],
                                    senses=[sense], rhs=[rhs],
                                    names=[name])

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

        # create lp
        self.createLp()

        # write the lp
        self.lp.write("..\\..\\..\\lps\\svrp.lp")

        # solve the model
        self.lp.solve()

        # process solution
        solution = self.lp.solution
        sol = solution.get_values()

        print "Total cost = " , solution.get_objective_value()

        # get fleet dimension for each depot
        for key, d in self.pdata.depots.iteritems():
            nvar = self.getVariable(self.getName("n", d.id))
            nval = sol[nvar.col]
            print "Fleet size for depot ", str(d.id), ": ", nval

        # get routes for each shift and scenario
        for t in range(self.pdata.shifts):
            for i in range(params.numberOfScenariosPerShift):
                scenario = self.scenarios[t][i]
                routes = []
                for cluster in scenario.clusterList:
                    for route in cluster.routes:
                        # get x variable
                        xname = self.getName("x",t,i,cluster.depot.id,route.id)
                        xvar = self.getVariable(xname)
                        xval = sol[xvar.col]

                        if xval > 0:
                            # print xvar.name + ":" + str(xval)
                            xvar.route.vehicleType = 1
                            routes.append(xvar.route)
                            continue

                        # get y variable
                        yname = self.getName("y",t,i,cluster.depot.id,route.id)
                        yvar = self.getVariable(yname)
                        yval = sol[yvar.col]

                        if yval > 0:
                            # print yvar.name + ":" + str(yval)
                            yvar.route.vehicleType = 2
                            routes.append(yvar.route)
                            continue
                if len(routes) > 0:
                    self.plotShiftSolution(scenario, routes)

        plt.show()

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