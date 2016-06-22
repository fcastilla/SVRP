import numpy as np
import time
import sys

from src.vrp.svrp.inputdata.ProblemData import ProblemData
from src.vrp.svrp.solver.Solver import Solver
from src.vrp.svrp.solver.BendersSolver import BendersSolver
from src.vrp.svrp.solver.BendersCBSolver import BendersCBSolver

# set the random seed
np.random.seed(1)

# read the input and create the problem data
path = ""
if len(sys.argv) >= 2:
    path = sys.argv[1]

pdata = ProblemData(path)

# Create the solver
solverCB = BendersSolver()

start_time = time.time()
solverCB.solve()
end_time = time.time()

pdata.problemSolution.elapsedTime = (end_time - start_time)
pdata.problemSolution.saveToFile()

print("--- %s seconds ---" % (end_time - start_time))

