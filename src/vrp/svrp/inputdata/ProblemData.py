import Tkinter
import tkFileDialog
import re
import math

from src.vrp.svrp.inputdata.Parameters import Parameters as params
from src.vrp.data.Data import *


class ProblemData:
    def __init__(self):
        self.n = 0
        self.customers = {}
        self.depots = {}
        self.distances = {}
        self.lvCost = 0
        self.hvCost = 0
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
            elif "LV" in line:
                self.lvCost = int(re.search(r'\d+', line).group())
            elif "HV" in line:
                self.hvCost = int(re.search(r'\d+', line).group())
            elif "NODE_COORD_SECTION" in line:
                section = 1
            elif "DEPOT_SECTION" in line:
                section = 2
            elif section == 1:
                # Obtain customer information
                info = [float(x) for x in line.split()]

                # Create new customer and add it to the list
                c = Customer(int(info[0]), float(info[1]), float(info[2]), False)
                self.customers[c.id] = c
            elif section == 2:
                id = int(line)
                c = self.customers[id]
                c.isDepot = True
                self.depots[id] = c

        f.close()
        self.computeDistances()

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
# data.readInstance()
# data.computeDistances()
