import numpy as np
import matplotlib.pyplot as plt

from ProblemData import *
from Cluster import *
from Parameters import Parameters as params

class Scenario:
    def __init__(self, id, shift, pdata):
        self.id = id
        self.shift = shift
        self.pdata = pdata
        self.customers = {}
        self.clusters = {}
        self.clusterList = []
        self.selectRandomCustomers()
        self.allocateCustomers()
        self.createClusterRoutes()

    def selectRandomCustomers(self):
        # Get the demand ratio for the associated shift
        dprob = self.pdata.demandDistribution[self.shift]

        # We're assuming odd shifts as day shifts
        isDayShift = (self.shift % 2 != 0)
        sCustomers = {}
        oCustomers = {}

        if isDayShift:
            sCustomers = self.pdata.dayCustomers
            oCustomers = self.pdata.afternoonCustomers
        else:
            sCustomers = self.pdata.afternoonCustomers
            oCustomers = self.pdata.dayCustomers

        # get customers for this type off shift
        for key, c in sCustomers.iteritems():
            p = np.random.uniform()
            if p <= dprob:
                self.customers[c.id] = c

        # see if any customer of other shift changes mind
        for key, c in oCustomers.iteritems():
            p = np.random.uniform()
            if p <= self.pdata.shiftSwitchProb:
                self.customers[c.id] = c

    def allocateCustomers(self):
        # create initial clusters with only depots
        self.clusterList = []
        self.clusters = {}
        cont = 0
        for key1, d in self.pdata.depots.iteritems():
            cluster = Cluster(cont, d, self.pdata)
            self.clusterList.append(cluster)
            self.clusters[d.id] = cluster
            cont += 1

        for key2, c in self.customers.iteritems():
            if c.isDepot == True:
                continue
            # allocate customer to closest depot
            depot = self.pdata.getClosestDepot(c)
            cluster = self.clusters[depot.id]
            cluster.customers.append(c)

    def createClusterRoutes(self):
        for c in self.clusterList:
            for vt in self.pdata.vehicleTypes:
                c.createRoutes(vt.type)

    def plotClusters(self):
        colors = ["y", "r", "c", "m", "b"]
        cont = 0

        # plot customers
        for cluster in self.clusterList:
            assert isinstance(cluster, Cluster)
            plt.plot([cluster.depot.x], [cluster.depot.y], colors[cont] + "s")
            for c in cluster.customers:
                plt.plot([c.x], [c.y], colors[cont] + ".")

            cont += 1
            if cont >= len(colors):
                cont = 0

        plt.grid()
        plt.show()




