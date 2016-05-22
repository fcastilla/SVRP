import Tkinter
import tkFileDialog
import re
import math
import numpy as np

from src.vrp.data.Data import *


class ProblemData:
    def __init__(self):
        self.n = 0
        self.shifts = 0
        self.depotOperationCost = 0
        self.minimumFleetSize = 0
        self.maximumFleetSize = 0
        self.lvCost = 0
        self.hvCost = 0
        self.demandDistributionMean = 0
        self.demandDistributionSD = 0
        self.shiftSwitchProb = 0
        self.demandDistribution = []
        self.dayCustomers = {}
        self.afternoonCustomers = {}
        self.customers = {}
        self.depots = {}
        self.depotCosts = {}
        self.distances = {}
        self.vehicleTypes = []
        self.readInstance()

    def readInstance(self):
        # Open file dialog to select base vrp instance
        Tkinter.Tk().withdraw()
        path = tkFileDialog.askopenfilename(filetypes=[("VRP Instances", ".svrp")])

        f = open(path)
        section = 0

        for line in f:
            if "DIMENSION" in line:
                self.n = int(re.search(r'\d+', line).group())
            elif "SHIFTS" in line:
                self.shifts = int(re.search(r'\d+', line).group())
            elif "DEMAND_MEAN" in line:
                self.demandDistributionMean = float(re.search(r"[-+]?\d*\.\d+|\d+", line).group())
            elif "DEMAND_SD" in line:
                self.demandDistributionSD = float(re.search(r"[-+]?\d*\.\d+|\d+", line).group())
            elif "SHIFT_SWITCH_PROB" in line:
                self.shiftSwitchProb = float(re.search(r"[-+]?\d*\.\d+|\d+", line).group())
            elif "NODE_COORD_SECTION" in line:
                section = 1
            elif "VEHICLE_SECTION" in line:
                section = 2
            elif "DEPOT_SECTION" in line:
                section = 3
            elif "DEMAND_SECTION" in line:
                section = 4
            elif "DAYTIME_CUSTOMERS_SECTION" in line:
                section = 5
            elif section == 1:
                # Obtain customer information
                info = [float(x) for x in line.split()]

                # Create new customer and add it to the list
                c = Customer(int(info[0]), float(info[1]), float(info[2]), False)
                self.customers[c.id] = c
            elif section == 2:
                info = [int(x) for x in line.split()]
                vt = Vehicle(info[0], info[1], info[2], info[3], info[4])
                self.vehicleTypes.append(vt)
            elif section == 3:
                info = [float(x) for x in line.split()]

                id = int(info[0])
                vt = int(info[1])
                cost = float(info[2])

                d = self.customers[id]
                d.isDepot = True
                self.depots[id] = d
                if id not in self.depotCosts:
                    self.depotCosts[id] = {}
                self.depotCosts[id][vt] = cost
            elif section == 4:
                info = [int(x) for x in line.split()]

                cid = info[0]
                self.customers[cid].acceptedVehicleTypes = info[1:]
            elif section == 5:
                id = int(line)
                c = self.customers[id]
                c.isDayCustomer = True
                self.dayCustomers[c.id] = c

        f.close()
        self.setAfternoonCustomers()
        self.makeDemandDistribution()
        self.computeDistances()

    def setAfternoonCustomers(self):
        for key, c in self.customers.iteritems():
            if not c.isDayCustomer:
                self.afternoonCustomers[c.id] = c

    def makeDemandDistribution(self):
        self.demandDistribution = list(np.random.normal(self.demandDistributionMean, self.demandDistributionSD, self.shifts))
        print self.demandDistribution

    def computeDistances(self):
        for k1, c1 in self.customers.iteritems():
            self.distances[c1.id] = {}
            for k2, c2 in self.customers.iteritems():
                if c1.id == c2.id:
                    continue

                x1 = c1.x
                y1 = c1.y
                y2 = c2.y
                x2 = c2.x

                dist = math.sqrt(pow(x2 - x1, 2) + pow(y2 - y1, 2))
                self.distances[c1.id][c2.id] = dist

    def getDistance(self, c1, c2):
        return self.distances[c1.id][c2.id]

    def getRouteLength(self, customers):
        distance = 0
        for i in range(len(customers)-1):
            c1 = customers[i]
            c2 = customers[i+1]
            distance += self.getDistance(c1,c2)

        return distance


    def getClosestDepot(self, c):
        depot = None
        minVal = 1000000000
        for k, d in self.depots.iteritems():
            try:
                dist = self.distances[c.id][d.id]
                if dist < minVal:
                    minVal = dist
                    depot = d
            except KeyError:
                pass
        return depot

# data = ProblemData()