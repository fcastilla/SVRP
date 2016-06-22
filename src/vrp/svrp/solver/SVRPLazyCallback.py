from __future__ import division

import time
import cplex
from cplex.callbacks import LazyConstraintCallback

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.svrp.inputdata.ProblemData import ProblemData
from src.vrp.svrp.solver.Variable import Variable
from src.vrp.svrp.solver.Constraint import Constraint
from src.vrp.svrp.solver.Model import Model


class SVRPLazyCallback(LazyConstraintCallback):
    def __init__(self, env):
        LazyConstraintCallback.__init__(self, env)
        self.iter = 0
        self.initTime = time.time()
        self.f_cons = 0
        self.o_cons = 0
        self.initcuts()

    def initcuts(self):
        self.pdata = ProblemData()

        # create log files
        f = open("output/" + self.pdata.instanceName + ".log.csv", "w")
        header = "Callbacks; Zinf; Zsup; Incumbent; O_Cuts; F_Cuts; Time (s)\n"
        f.write(header)
        f.close()

        f = open("output/" + self.pdata.instanceName + ".log", "w")
        f.close()

        # create structure
        self.master = self.pdata.master
        self.createSubproblems()

    def createSubproblems(self):
        print "Creating subproblems..."
        self.subproblems = {}

        # create a subproblem for each shift, depot, scenario
        for t in range(self.pdata.shifts):
            self.subproblems[t] = {}
            for i in range(params.numberOfScenariosPerShift):
                self.subproblems[t][i] = {}
                scenario = self.pdata.scenarios[t][i]
                for cluster in scenario.clusterList:
                    d = cluster.depot
                    sp = self.subproblems[t][i][d.id] = Model()

                    # set the objective of the subproblem
                    sp.lp.objective.set_sense(sp.lp.objective.sense.minimize)
                    self.createXYVariables(sp, t, scenario, cluster)
                    self.createYDVariables(sp, t, scenario, cluster)
                    self.fleetSizeConstraints(sp, t, scenario, cluster, 0)
                    self.customerSatisfactionConstraints(sp, t, scenario, cluster)
                    self.createYCouplingConstraints(sp, t, scenario, cluster)
                    # sp.lp.write("lps\\svrpCB_subproblem_" + str(t) + "_" + str(i) + "_" + str(d.id) + ".lp")

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

    def createYDVariables(self, model, shift, scenario, cluster):
        for vt in self.pdata.vehicleTypes:
            if vt.type not in cluster.routes:
                continue

            # Create yd variable
            v = Variable()
            v.type = Variable.v_yd
            v.name = model.getName("yd", shift, scenario.id, cluster.depot.id, vt.type)
            v.col = model.numCols
            v.shift = shift
            v.scenario = scenario
            v.depot = cluster.depot
            v.vehicleType = vt

            coef = 0
            model.variables[v.name] = v
            model.lp.variables.add(obj=[coef], types=["I"], names=[v.name])
            model.numCols += 1

    def createYCouplingConstraints(self, model, shift, scenario, cluster):
        for vt in self.pdata.vehicleTypes:
            if vt.type not in cluster.routes:
                continue

            c = Constraint()
            c.type = Constraint.c_hvfleetSize
            c.name = model.getName("HVfleetSize", shift, scenario.id, cluster.depot.id, vt.type)
            c.shift = shift
            c.scenario = scenario
            c.depot = cluster.depot.id
            c.vehicleType = vt
            c.row = model.numRows

            mind = []
            mval = []
            rhs = 0.0

            # get the yd variable
            ydvar = model.getVariable(model.getName("yd", shift, scenario.id, cluster.depot.id, vt.type))
            mind.append(ydvar.col)
            mval.append(-1.0)

            for route in cluster.routes[vt.type]:
                # get the y variable and add it to the constraint
                yname = model.getName("y", shift, scenario.id, cluster.depot.id, route.id, vt.type)
                yvar = model.getVariable(yname)
                mind.append(yvar.col)
                mval.append(1.0)

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

    def __call__(self):
        self.iter += 1
        self.pdata.problemSolution.callbacks += 1
        #self.master.lp.write("..\\..\\..\\lps\\svrpCB_master" + str(self.iter) + ".lp")

        # get the current solution
        master_sol = self.get_values()
        zinf = self.get_objective_value()

        nvals = {}
        hfleet = {}
        zsup = 0
        infeasible = False
        iter = 0

        for key, d in self.pdata.depots.iteritems():
            nvals[d.id] = {}
            hfleet[d.id] = {}
            for vt in self.pdata.vehicleTypes:
                nvals[d.id][vt.type] = 0
                hfleet[d.id][vt.type] = 0

                for i in range(vt.maxFleet + 1):
                    nvar = self.master.getVariable(self.master.getName("n", d.id, i, vt.type))
                    nvar.solutionVal = master_sol[nvar.col]
                    zsup += (nvar.digit * nvar.solutionVal) * self.pdata.depotCosts[d.id][vt.type]

                    nvals[d.id][vt.type] += (nvar.digit * nvar.solutionVal)

        constraints = []
        senses = []
        rhs = []
        names = []
        oCont = 0

        # Run each subproblem with the updated n values of the trial solution
        # and add the proper feasibility and optimality cuts
        for t in range(self.pdata.shifts):
            for i in range(params.numberOfScenariosPerShift):
                scenario = self.pdata.scenarios[t][i]
                for cluster in scenario.clusterList:
                    depot = cluster.depot

                    # Get the subproblem
                    sp = self.subproblems[t][i][depot.id]

                    for vt in self.pdata.vehicleTypes:
                        # change the rhs of the fleet size constraint with the value obtained from the master
                        nval = nvals[depot.id][vt.type]
                        c = sp.getConstraint(sp.getName("fleetSize", t, i, depot.id, vt.type))
                        if c is not None: # there might be no demands for a depot in a given cenario.
                            sp.changeRHS(c.row, nval)

                    # solve the subproblem
                    sp.lp.solve()

                    # get the subproblem status
                    sp_sol = sp.lp.solution
                    status = sp_sol.get_status()

                    if status in [101,102]: # feasible optimum
                        sol = sp_sol.get_values()

                        # add the objective value
                        sp_obj = sp_sol.get_objective_value()
                        zsup += (1/params.numberOfScenariosPerShift) * sp_obj

                        # get the hired vehicles fleet size, for each vehicle type, for this subproblem
                        for vt in self.pdata.vehicleTypes:
                            ydvar = sp.getVariable(sp.getName("yd", t, i, depot.id, vt.type))
                            if ydvar is not None:
                                fsize = sol[ydvar.col]
                                currentSize = hfleet[depot.id][vt.type]
                                hfleet[depot.id][vt.type] = max(fsize, currentSize)

                        # create optimality cut in the master problem
                        mind = []
                        mval = []
                        contVars = 0

                        # get the alpha variable
                        alpha = self.master.getVariable(self.master.getName("alpha", t, scenario.id, depot.id))
                        mind.append(alpha.col)
                        mval.append(1.0)

                        #get the "N" variables
                        for vt in self.pdata.vehicleTypes:
                            for k in range(vt.maxFleet + 1):
                                nvar = self.master.getVariable(self.master.getName("n", depot.id, k, vt.type))

                                # check if the variable is part of the current master solution
                                if nvar.solutionVal != 0:
                                    contVars += 1
                                    mind.append(nvar.col)
                                    mval.append(-sp_obj)

                        contVars -= 1

                        # create constraint an add it to the list
                        oCont += 1
                        constraints.append(cplex.SparsePair(ind=mind, val=mval))
                        senses.append("G")
                        rhs.append(sp_obj*-contVars)
                        names.append("optimality_" + str(self.o_cons + oCont))

                    elif status in [103]: # infeasible
                        print "INFEASIBLE SUBPROBLEM-------------------------------------"
                        infeasible = True

                        # create an infeasiblity cut in the master problem
                        #self.createFeasibilityCut(depot)
                    else:
                        pass
                        # print "shift: ", str(t), " | scenario: ", str(i), " | depot: ", str(depot.id)

        # Add all the cuts to the problem
        if(infeasible or zsup - zinf > params.eps):
            for i in range(len(constraints)):
                self.o_cons += 1
                self.pdata.problemSolution.o_cuts += 1
                self.add(constraint = constraints[i], sense = senses[i], rhs = rhs[i], use=True)

        else:
            # accept the incumbent, save the hired vehicles fleet solution
            self.pdata.problemSolution.hiredFleet = hfleet


        incumbent = self.get_incumbent_objective_value()
        currentTime = time.time()
        elapsed = currentTime - self.initTime

        s_iter = str(self.iter)
        s_zinf = "{:.2f}".format(zinf).replace(".",",")
        s_zsup = "{:.2f}".format(zsup).replace(".",",")
        s_incumbent = "{:.2f}".format(incumbent).replace(".",",")
        s_ocons = str(self.o_cons)
        s_fcons = str(self.f_cons)
        s_elapsed = "{:.2f}".format(elapsed).replace(".",",")

        line = s_iter + ";" + s_zinf + ";" + \
               s_zsup + ";" + s_incumbent + \
               ";" + s_ocons + ";" + s_fcons + ";" + s_elapsed


        s_formatted = "Iter: %s | Zinf: %s | Zsup: %s | Incumbent: %s | O_Cuts: %s | FCuts: %s | Time: %s (s)" \
              % (s_iter, s_zinf, s_zsup, s_incumbent, s_ocons, s_fcons, s_elapsed)

        # print to screen
        print s_formatted

        # Update log files
        f = open("output/" + self.pdata.instanceName + ".log", "a")
        f.write(s_formatted + "\n")
        f.close()

        f = open("output/" + self.pdata.instanceName + ".log.csv", "a")
        f.write(line + "\n")
        f.close()

