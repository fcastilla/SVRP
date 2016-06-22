from __future__ import division

import cplex
import numpy as np
import matplotlib.pyplot as plt

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.svrp.inputdata.ProblemData import ProblemData
from src.vrp.svrp.solver.Variable import Variable
from src.vrp.svrp.solver.Constraint import Constraint
from src.vrp.svrp.solver.Model import Model
from src.vrp.svrp.solver.SVRPLazyCallback import SVRPLazyCallback


class BendersCBSolver:
    def __init__(self):
        self.pdata = ProblemData()
        self.master = Model()

    def createMaster(self):
        # initialize new lp for master problem
        self.master = Model()

        # set the objective sense of the master problem
        self.master.lp.objective.set_sense(self.master.lp.objective.sense.minimize)
        self.createNVariables(self.master)
        self.createAlphaVariables(self.master)
        self.createAlphaHVariables(self.master)
        self.createSingleVarDepotConstraint(self.master)
        self.minimumFleetSizeConstraints(self.master)
        self.maximumFleetSizeConstraints(self.master)
        self.createAlphaConstraints(self.master)
        # self.master.lp.write("lps\\svrpCB_master.lp")

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
                scenario = self.pdata.scenarios[t][i]
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
    #endregion

    def solve(self):
        # create the master problem
        self.createMaster()
        self.pdata.master = self.master
        lp = self.master.lp

        # need to use traditional branch-and-cut to allow for control callbacks
        # lp.parameters.preprocessing.presolve.set(lp.parameters.preprocessing.presolve.values.off)
        lp.parameters.threads.set(1)
        # lp.parameters.advance.set(0)
        # lp.parameters.mip.strategy.search.set(lp.parameters.mip.strategy.search.values.traditional)

        # Register the lazy cut callback
        lp.register_callback(SVRPLazyCallback)

        # solve the model
        lp.solve()

        solution = self.master.lp.solution
        status = solution.get_status()

        if status in [101,102]:
            sol = solution.get_values()
            obj = solution.get_objective_value()

            self.pdata.problemSolution.obj = obj

            # get the fleet for each depot and each vehicle type
            for k,d in self.pdata.depots.iteritems():
                for vt in self.pdata.vehicleTypes:
                    for i in range(vt.maxFleet + 1):
                        nvar = self.master.getVariable(self.master.getName("n", d.id, i, vt.type))
                        nvar.solutionVal = sol[nvar.col]
                        self.pdata.problemSolution.leasedFleet[d.id][vt.type] += (nvar.digit * nvar.solutionVal)



        print "**********************Resultado Final***********", str(obj)


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