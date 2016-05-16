import numpy as np

from src.vrp.svrp.inputdata.ProblemData import ProblemData
from src.vrp.svrp.solver.Solver import Solver
from src.vrp.svrp.solver.BendersSolver import BendersSolver

# set the random seed
np.random.seed(1)

# read the input and create the problem data
pdata = ProblemData()

# Create the solver
solver = BendersSolver(pdata)
solver.solve()

