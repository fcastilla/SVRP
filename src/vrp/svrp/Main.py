import numpy as np

from src.vrp.svrp.inputdata.ProblemData import ProblemData
from src.vrp.svrp.inputdata.Scenario import Scenario
from src.vrp.svrp.inputdata.Cluster import Cluster
from src.vrp.svrp.solver.Solver import Solver

# set the random seed
np.random.seed(1)

# read the input and create the problem data
pdata = ProblemData()

# Create the solver
solver = Solver(pdata)
solver.solve()

