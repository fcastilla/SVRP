import Tkinter
import tkFileDialog
import re
import os

from collections import deque
import matplotlib.pyplot as plt
import random
import numpy as np

from src.vrp.data.Data import *


class SVRPInstanceMaker:
    def __init__(self):
        np.random.seed(1)
        self.instanceName = ""
        self.n = 0
        self.customers = []
        self.depots = []
        self.distances = []
        self.shifts = 0
        self.scenarios = 0
        self.depotOperationCost = 0
        self.demandMean = 0.0
        self.demandSD = 0.0
        self.shiftSwitchProb = 0.0
        self.clusters = 0
        self.vTypes = 0
        self.vehicleTypes = []
        self.depotCosts = {}

    def readCVRPInstance(self):
        # Open file dialog to select base vrp instance
        Tkinter.Tk().withdraw()
        path = tkFileDialog.askopenfilename(filetypes=[("VRP Instances", ".vrp")])

        # Read the selected instance file
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

        # Create customer clusters
        self.createCustomerClusters(2)

        # Get proportion of "day time" Customers
        dayProportion = 0.6  # input("Which proportion of customers should be day time? (0.0 to 1.0 are valid inputs): ")

        # Select day time customers
        self.selectDayTimeCustomers(dayProportion)

        # set manual depots
        l = [52,58]
        for c in self.customers:
            if c.id in l:
                c.isDepot = True
                self.depots.append(c)
            else:
                c.isDepot = False

        # Get demand distribution mean
        self.demandMean = 0.25  # input("Enter the mean for the demand (normal) distribution function: ")

        # Get demand distribution standard deviation
        self.demandSD = 0.1  # input("Enter the standard deviation for the demand distribution function: ")

        # Get shift switch probability
        self.shiftSwitchProb = 0.1  # input("What's the probability of a customer changing demand to a different shift?: ")

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

    def setCustomerVehicleTypes(self, p1, p2):
        for i in range(1, self.clusters + 1):
            clusterCustomers = [c for c in self.customers if c.zone == i and c.isDepot == False]
            for c in clusterCustomers:
                c.acceptedVehicleTypes = []
                c.acceptedVehicleTypes.append(0)
                p = random.random()
                if p > p1:
                    c.acceptedVehicleTypes.append(1)
                if p > p2:
                    c.acceptedVehicleTypes.append(2)

    def createNewInstance(self, vehicleTypes):
        self.vehicleTypes = []
        self.depotCosts = {}

        # Get how many vehicle types
        self.vTypes = vehicleTypes # input("How many vehicle types?")

        # For each vehicle type, get lvCost, hvCost, minFleet and maxFleet
        for i in range(self.vTypes):
            lvCost = 200 if i == 0 else 150 if i == 1 else 100 # input("Please input leased vehicle cost for vehicle type " + str(i) + ": ")
            hvCost = 250 if i == 0 else 190 if i == 1 else 130  # input("Please input hired vehicle cost for vehicle type " + str(i) + ": ")
            minFleet = 2  # input("Please input min fleet size for vehicle type " + str(i) + ": ")
            maxFleet = 8  # input("Please input max fleet size for vehicle type " + str(i) + ": ")

            vt = Vehicle(i,lvCost,hvCost,minFleet,maxFleet)
            self.vehicleTypes.append(vt)

        # Get cost of having a vehicle per depot per vehicle type
        for d in self.depots:
            self.depotCosts[d.id] = {}
            for vt in self.vehicleTypes:
                self.depotCosts[d.id][vt.type] = 30 if vt.type == 0 else 20 if vt.type == 1 else 15 # input("Please provide the cost of having a vehicle of type " + str(vt.type) + " in depot " + str(d.id) + " :")

        # Get proportion of "one type of vehicle" customers
        #vProportion = input("Which proportion of customers will accept only 1 type of vehicle? ")

        # Set the vehicle type acceptance for each customer
        p1 = 0.3 if self.vTypes >= 2 else 100
        p2 = 0.6 if self.vTypes >= 3 else 100
        self.setCustomerVehicleTypes(p1,p2)

        # Write instance files
        shift_options = [10,30,40,50]
        scenario_options = [10,20,50]

        for t in shift_options:
            for s in scenario_options:
                self.instanceName = "PS-n" + str(len(self.customers)) + "-d" + str(len(self.depots))
                self.writeInstance(t, s)

        # Plot Instance
        self.plotInstance()

    def writeInstance(self, shifts, scenarios):
        name = self.instanceName + "-vt" + str(self.vTypes) + "-t" + str(shifts) + "-s" + str(scenarios)
        f = open("../../../Instances/" + name + ".svrp", "w")

        # write instance name
        f.write("NAME: " + name + "\n")

        # Write number of customers
        f.write("DIMENSION: " + str(self.n) + "\n")

        # Write number of shifts
        f.write("SHIFTS: " + str(shifts) + "\n")

        # Write the number of scenarios
        f.write("SCENARIOS: " + str(scenarios) + "\n")

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
        fig = plt.figure()
        fig.patch.set_alpha(0.0)
        fig.suptitle(self.instanceName , fontsize=20)
        ax = fig.add_subplot(111)

        # plot daytime customers
        daytimeCustomers = [c for c in self.customers if c.isDepot == False and c.isDayCustomer]
        dot = ax.scatter([c.x for c in daytimeCustomers],[c.y for c in daytimeCustomers], c="#ffff00", marker="o", s=40)

        # plot night customers
        nightCustomers = [c for c in self.customers if c.isDepot == False and not c.isDayCustomer]
        triangle = ax.scatter([c.x for c in nightCustomers],[c.y for c in nightCustomers], c="#0B159E", marker="^", s=40)

        # plot depots
        square = ax.scatter([c.x for c in self.depots],[c.y for c in self.depots], c="#ff0000", marker="s", s=40)

        art = []
        art.append(plt.legend((dot, triangle, square), ("Day Customers", "Night Customers", "Depots"),
                   loc=9, bbox_to_anchor=(0.5, -0.1),
                   scatterpoints=1,
                   ncol=3,
                   fontsize=8))
        plt.xlim(0, max([c.x for c in self.customers]) * 1.05)
        plt.ylim(0, max([c.y for c in self.customers]) * 1.05)
        plt.grid()

        path = "../../../graphics/" + self.instanceName + "/"
        if not os.path.exists(path):
            os.makedirs(path)
        plt.savefig(path + "instancePlot.png", additional_artists=art, bbox_inches="tight")

m = SVRPInstanceMaker()
m.readCVRPInstance()

for vt in [2,3]:
    m.createNewInstance(vt)