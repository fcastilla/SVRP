import Tkinter
import tkFileDialog
import re
from collections import deque
import matplotlib.pyplot as plt
import random

from src.vrp.data.Data import *


class SVRPInstanceMaker:
    def __init__(self):
        self.n = 0
        self.customers = []
        self.depots = []
        self.distances = []
        self.lvCost = 0
        self.hvCost = 0
        self.clusters = 0

    def readCVRPInstance(self, path):
        f = open(path)
        section = 0

        for line in f:
            if "DIMENSION" in line:
                self.n = int(re.search(r'\d+', line).group())
            elif "NODE_COORD_SECTION" in line:
                section = 1
            elif "DEMAND_SECTION" in line:
                section = 2
            elif section == 1:
                # Obtain customer information
                info = [float(x) for x in line.split()]

                # Create new customer and add it to the list
                c = Customer(int(info[0]), float(info[1]), float(info[2]), False)
                self.customers.append(c)

        f.close()
        print self.customers

    def createCustomerClusters(self, num):
        groups = deque([self.customers])
        while len(groups) < num:
            # Obtain the next customer group to be partitioned
            g = groups.popleft()

            # define a partition direction (X or Y)
            minx = min(g, key=lambda c : c.x).x
            maxx = max(g, key=lambda c : c.x).x
            difx = maxx - minx

            miny = min(g, key=lambda c : c.y).y
            maxy = max(g, key=lambda c : c.y).y
            dify = maxy - miny

            if difx >= dify: # partition on x
                g.sort(key=lambda c : c.x)
            else:
                g.sort(key=lambda c : c.y)

            # Partition the group in 2
            mid = int(len(g)/2)
            g1 = g[:mid]
            g2 = g[mid:]

            # Add the new partitions to the end of the queue
            groups.extend([g1,g2])

        cont = 1
        for group in groups:
            for c in group:
                c.zone = cont
            cont += 1
        self.clusters = cont - 1

    def setRandomDepots(self):
        for i in range(1,self.clusters+1):
            random.choice([c for c in self.customers if c.zone == i]).isDepot = True

    def createNewInstance(self):
        # Open file dialog to select base vrp instance
        Tkinter.Tk().withdraw()
        path = tkFileDialog.askopenfilename(filetypes=[("VRP Instances", ".vrp")])

        # Read the selected instance file
        self.readCVRPInstance(path)

        # Get the travel cost for leased and hired vehicles
        self.lvCost = input("What's the travel cost for leased vehicles (per distance unit)? ")
        self.hvCost = input("What's the travel cost for short term hired vehicles (per distance unit)? ")

        # Create clusters of customers
        num = input("How many customer clusters should we create: ")
        self.createCustomerClusters(num)

        # Randomly select a depot for each customer cluster
        self.setRandomDepots()

        # Write the instance to file
        self.writeInstance()

        # Plot instance
        self.plotInstance()

    def writeInstance(self):
        f = open("../../../Instances/new_instance.solver", "w")

        # Write number of customers
        f.write("DIMENSION: " + str(self.n) + "\n")

        # Write cost per leased and short hired vehicle
        f.write("LV COST: " + str(self.lvCost) + "\n")
        f.write("HV COST: " + str(self.hvCost) + "\n")

        # Write customer information
        f.write("NODE_COORD_SECTION \n")
        self.customers.sort(key=lambda c : c.id)
        for c in self.customers:
            f.write(str(c.id) + "\t" + str(c.x) + "\t" + str(c.y) + "\t" + str(c.zone) + "\n")

        # Write depots
        f.write("DEPOT_SECTION\n")
        for d in [c for c in self.customers if c.isDepot == True]:
            f.write(str(d.id) + "\n")

        f.close()

    def plotInstance(self):
        colors = ["y", "r", "c", "m", "b"]
        cont = 0

        # plot customers
        for i in range(1, self.clusters+1):
            plt.plot([c.x for c in self.customers if c.zone == i], [c.y for c in self.customers if c.zone == i], colors[cont] + "o")
            cont += 1
            if cont >= len(colors):
                cont = 0

        # plot depots
        depots = [c for c in self.customers if c.isDepot == True]
        plt.plot([c.x for c in depots], [c.y for c in depots], "k*")

        plt.axis([0, max(self.customers, key=lambda c : c.x).x, 0, max(self.customers, key=lambda c : c.y).y])
        plt.grid()
        plt.show()

m = SVRPInstanceMaker()
m.createNewInstance()

m.customers.sort(key=lambda c : c.zone)
print m.customers