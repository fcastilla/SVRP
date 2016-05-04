import itertools

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.svrp.inputdata.Route import Route

class Cluster:
    def __init__(self, id, depot):
        self.id = id
        self.depot = depot
        self.customers = []
        self.routes = []

    def createRoutes(self):
        routes = []
        for i in range(1, params.maxCustomersPerRoute+1):
            newroutes = list(itertools.permutations(self.customers, i))
            routes.extend(newroutes)

        t = (self.depot, )
        for i in range(len(routes)):
            r = routes[i]
            r = t + r + t
            route = Route(i,r)
            self.routes.append(route)


