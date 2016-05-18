import Tkinter
import tkFileDialog
import re
from collections import deque
import matplotlib.pyplot as plt
import random
import numpy as np

from src.vrp.data.Data import *


# ToDo Update Depot Section (depot, vehicle type, cost) (OK)
# ToDo Create Vehicle Types Section (type, lvCost, hvCost, minFleet, maxFleet) (OK)
# ToDo Create Demand Section with (customer_id, vehicle_types_list) (OK)
# ToDo Clusterization analyzing demands based on vehicle types?

class SVRPInstanceMaker:
    def __init__(self):
        self.n = 0
        self.customers = []
        self.depots = []
        self.distances = []
        self.shifts = 0
        self.depotOperationCost = 0
        self.demandMean = 0.0
        self.demandSD = 0.0
        self.shiftSwitchProb = 0.0
        self.clusters = 0
        self.vTypes = 0
        self.vehicleTypes = []
        self.depotCosts = {}

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

    def setCustomerVehicleTypes(self, prob):
        for i in range(1, self.clusters + 1):
            clusterCustomers = [c for c in self.customers if c.zone == i and c.isDepot == False]
            for c in clusterCustomers:
                c.acceptedVehicleTypes.append(0)
                p = random.random()
                if p > prob:
                    c.acceptedVehicleTypes.append(1)

    def createNewInstance(self):
        # Open file dialog to select base vrp instance
        Tkinter.Tk().withdraw()
        path = tkFileDialog.askopenfilename(filetypes=[("VRP Instances", ".vrp")])

        # Read the selected instance file
        self.readCVRPInstance(path)

        # Get the number of shifts
        self.shifts = input("How many shifts for the instance?: ")

        # Get how many depots should be created
        numDepots = input("How many depots should we create: ")

        # Get how many vehicle types
        self.vTypes = 2 # input("How many vehicle types?")

        # For each vehicle type, get lvCost, hvCost, minFleet and maxFleet
        for i in range(self.vTypes):
            lvCost = input("Please input leased vehicle cost for vehicle type " + str(i) + ": ")
            hvCost = input("Please input hired vehicle cost for vehicle type " + str(i) + ": ")
            minFleet = input("Please input min fleet size for vehicle type " + str(i) + ": ")
            maxFleet = input("Please input max fleet size for vehicle type " + str(i) + ": ")

            vt = Vehicle(i,lvCost,hvCost,minFleet,maxFleet)
            self.vehicleTypes.append(vt)

        # Create customer clusters
        self.createCustomerClusters(numDepots)

        # Randomly select a depot for each customer cluster
        self.setRandomDepots()

        # Get cost of having a vehicle per depot per vehicle type
        self.depots = [c for c in self.customers if c.isDepot == True]
        for d in self.depots:
            self.depotCosts[d.id] = {}
            for vt in self.vehicleTypes:
                self.depotCosts[d.id][vt.type] = input("Please provide the cost of having a vehicle of type " + str(vt.type) + " in depot " + str(d.id) + " :")

        # Get proportion of "day time" Customers
        dayProportion = input("Which proportion of customers should be day time? (0.0 to 1.0 are valid inputs): ")

        # Select day time customers
        self.selectDayTimeCustomers(dayProportion)

        # Get proportion of "one type of vehicle" customers
        vProportion = input("Which proportion of customers will accept only 1 type of vehicle? ")

        # Set the vehicle type acceptance for each customer
        self.setCustomerVehicleTypes(vProportion)

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

        # Write demand distribution parameters
        f.write("DEMAND_MEAN: " + str(self.demandMean) + "\n")
        f.write("DEMAND_SD: " + str(self.demandSD) + "\n")
        f.write("SHIFT_SWITCH_PROB: " + str(self.shiftSwitchProb) + "\n")

        # Write customer information
        f.write("NODE_COORD_SECTION \n")
        self.customers.sort(key=lambda c: c.id)
        for c in self.customers:
            f.write(str(c.id) + "\t" + str(c.x) + "\t" + str(c.y) + "\t" + str(c.zone) + "\n")

        # Write vehicle types information
        f.write("VEHICLE_SECTION \n")
        self.vehicleTypes.sort(key=lambda v: v.type)
        for vt in self.vehicleTypes:
            f.write(str(vt.type) + "\t" + str(vt.lvCost) + "\t" + str(vt.hvCost) + "\t" + str(vt.minFleet) + "\t" + str(vt.maxFleet) + "\n")

        # Write depots
        f.write("DEPOT_SECTION\n")
        for d in self.depots:
            for vt in self.vehicleTypes:
                f.write(str(d.id) + "\t" + str(vt.type) + "\t" + str(self.depotCosts[d.id][vt.type]) + "\n")

        # Write Demand section
        f.write("DEMAND_SECTION \n")
        for c in self.customers:
            s = str(c.id)
            for vt in c.acceptedVehicleTypes:
                s += "\t" + str(vt)
            f.write(s + "\n")

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