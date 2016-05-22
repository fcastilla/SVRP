import itertools

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.svrp.inputdata.Route import Route

class Cluster:
    def __init__(self, id, depot, pdata):
        self.id = id
        self.depot = depot
        self.pdata = pdata
        self.customers = []
        self.routes = {}
        self.numRoutes = 0

    def createRoutes(self, vt):
        routes = []

        # Select customers that accept the vehicle type vt
        customers = [c for c in self.customers if vt in c.acceptedVehicleTypes]

        for i in range(1, params.maxCustomersPerRoute+1):
            newroutes = list(itertools.combinations(customers, i))
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

            route = Route(self.numRoutes, minRoute, minDistance)

            if vt not in self.routes:
                self.routes[vt] = []
            self.routes[vt].append(route)

            self.numRoutes += 1


