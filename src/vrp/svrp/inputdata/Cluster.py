import itertools

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.svrp.inputdata.Route import Route

class Cluster:
    def __init__(self, id, depot, pdata):
        self.id = id
        self.depot = depot
        self.pdata = pdata
        self.customers = []
        self.routes = []

    def createRoutes(self):
        routes = []
        for i in range(1, params.maxCustomersPerRoute+1):
            newroutes = list(itertools.combinations(self.customers, i))
            routes.extend(newroutes)

        t = (self.depot, )
        for i in range(len(routes)):
            r = routes[i]
            minRoute = r
            minDistance = 1000000000000000

            if len(r) >= 3:
                # try all possible permutations of the route, and pick the cheapest
                allRoutes = list(itertools.permutations(r, len(r)))

                for j in range(0, len(allRoutes)):
                    r = allRoutes[j]
                    r = t + r + t
                    distance = self.pdata.getRouteLength(r)
                    if minDistance > distance:
                        minDistance = distance
                        minRoute = r

            else:
                minRoute = t + minRoute + t
                minDistance = self.pdata.getRouteLength(minRoute)

            route = Route(i, minRoute, minDistance)
            self.routes.append(route)


