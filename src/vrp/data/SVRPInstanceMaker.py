import Tkinter
import tkFileDialog
import re
from collections import deque
import matplotlib.pyplot as plt
import random
import numpy as np

from src.vrp.data.Data import *


class SVRPInstanceMaker:
    def __init__(self):
        self.n = 0
        self.customers = []
        self.depots = []
        self.distances = []
        self.shifts = 0
        self.depotOperationCost = 0
        self.minimumFleetSize = 0
        self.maximumFleetSize = 0
        self.lvCost = 0
        self.hvCost = 0
        self.demandMean = 0.0
        self.demandSD = 0.0
        self.shiftSwitchProb = 0.0
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

    def selectDayTimeCustomers(self, prob):
        for i in range(1, self.clusters + 1):
            clusterCustomers = [c for c in self.customers if c.zone == i and c.isDepot == False]
            for c in clusterCustomers:
                p = random.random()
                if p <= prob:
                    c.isDayCustomer = True

    def createNewInstance(self):
        # Open file dialog to select base vrp instance
        Tkinter.Tk().withdraw()
        path = tkFileDialog.askopenfilename(filetypes=[("VRP Instances", ".vrp")])

        # Read the selected instance file
        self.readCVRPInstance(path)

        # Get the number of shifts
        self.shifts = input("How many shifts for the instance?: ")

        # Get the cost for depot operation per vehicle:
        self.depotOperationCost = input("What's the depot operational cost per vehicle?: ")

        # Get the minimum and maximum fleet size per depot
        self.minimumFleetSize = input("What's the minimum fleet size allowed?: ")
        self.maximumFleetSize = input("What's the maximum fleet size allowed?: ")

        # Get the travel cost for leased and hired vehicles
        self.lvCost = input("What's the travel cost for leased vehicles (per distance unit)?: ")
        self.hvCost = input("What's the travel cost for short term hired vehicles (per distance unit)?: ")

        # Get how many depots should be created
        numDepots = input("How many depots should we create: ")

        # Create customer clusters
        self.createCustomerClusters(numDepots)

        # Randomly select a depot for each customer cluster
        self.setRandomDepots()

        # Get proportion of "day time" Customers
        dayProportion = input("Which proportion of customers should be day time? (0.0 to 1.0 are valid inputs): ")

        # Select day time customers
        self.selectDayTimeCustomers(dayProportion)

        # Get demand distribution mean
        self.demandMean = input("Enter the mean for the demand (normal) distribution function: ")

        # Get demand distribution standard deviation
        self.demandSD = input("Enter the standard deviation for the demand distribution function: ")

        # Get shift switch probability
        self.shiftSwitchProb = input("What's the probability of a customer changing demand to a different shift?: ")

        # Write the instance to file
        self.writeInstance()

        # Plot instance
        self.plotInstance()

    def writeInstance(self):
        f = open("../../../Instances/new_instance.svrp", "w")

        # Write number of customers
        f.write("DIMENSION: " + str(self.n) + "\n")

        # Write number of shifts
        f.write("SHIFTS: " + str(self.shifts) + "\n")

        # Write depot operational cost per vehicle
        f.write("DEPOT_COST:" + str(self.depotOperationCost) + "\n")

        # Write the minimum and maximum fleet size
        f.write("MINIMUM_FLEET_SIZE:" + str(self.minimumFleetSize) + "\n")
        f.write("MAXIMUM_FLEET_SIZE:" + str(self.maximumFleetSize) + "\n")

        # Write cost per leased and short hired vehicle
        f.write("LV_COST: " + str(self.lvCost) + "\n")
        f.write("HV_COST: " + str(self.hvCost) + "\n")

        # Write demand distribution parameters
        f.write("DEMAND_MEAN: " + str(self.demandMean) + "\n")
        f.write("DEMAND_SD: " + str(self.demandSD) + "\n")
        f.write("SHIFT_SWITCH_PROB: " + str(self.shiftSwitchProb) + "\n");

        # Write customer information
        f.write("NODE_COORD_SECTION \n")
        self.customers.sort(key=lambda c: c.id)
        for c in self.customers:
            f.write(str(c.id) + "\t" + str(c.x) + "\t" + str(c.y) + "\t" + str(c.zone) + "\n")

        # Write depots
        f.write("DEPOT_SECTION\n")
        for d in [c for c in self.customers if c.isDepot == True]:
            f.write(str(d.id) + "\n")

        # Write day time customers information
        f.write("DAYTIME_CUSTOMERS_SECTION\n")
        for c in self.customers:
            if c.isDayCustomer == True:
                f.write(str(c.id) + "\n")

        f.close()

    def plotInstance(self):
        # plot customers
        for i in range(1, self.clusters+1):
            color = np.random.rand(3,1)
            for c in self.customers:
                if c.zone == i:
                    marker = "o"
                    if c.isDepot:
                        marker = "s"
                    elif not c.isDayCustomer:
                        marker = "^"
                    plt.plot(c.x, c.y, color=color, marker=marker)

        plt.axis([0, max(self.customers, key=lambda c : c.x).x, 0, max(self.customers, key=lambda c : c.y).y])
        plt.grid()
        plt.show()

m = SVRPInstanceMaker()
m.createNewInstance()

m.customers.sort(key=lambda c : c.zone)
print m.customers