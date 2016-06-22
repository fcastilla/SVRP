import os

from src.vrp.svrp.inputdata.Parameters import Parameters as params

class ProblemSolution:
    def __init__(self):
        self.pdata = None
        self.instanceName = ""
        self.obj = -1
        self.callbacks = 0
        self.elapsedTime = 0
        self.o_cuts = 0
        self.f_cuts = 0

    def initialize(self, pdata):
        self.pdata = pdata
        self.instanceName = pdata.instanceName

        # initiate fleet
        self.leasedFleet = {}
        self.hiredFleet = {}
        for k,d in self.pdata.depots.iteritems():
            self.leasedFleet[d.id] = {}
            self.hiredFleet[d.id] = {}
            for vt in self.pdata.vehicleTypes:
                self.leasedFleet[d.id][vt.type] = 0
                self.hiredFleet[d.id][vt.type] = 0

    def saveToFile(self):
        # Save stats file
        statsFileName = "output/stats.csv"
        f = open(statsFileName, "a")

        # Write stats csv header if needed.
        header = "Instance;Customers;Depots;VTypes;Shifts;Scenarios;Obj;O_Cuts;F_Cuts;Callbacks;Time(s)"

        if os.stat(statsFileName).st_size == 0:
            f.write(header + "\n")

        # write stats data
        f.write(self.instanceName + ";")
        f.write(str(self.pdata.n) + ";")
        f.write(str(len(self.pdata.depots)) + ";")
        f.write(str(len(self.pdata.vehicleTypes)) + ";")
        f.write(str(self.pdata.shifts) + ";")
        f.write(str(params.numberOfScenariosPerShift) + ";")
        f.write("{:.2f}".format(self.obj).replace(".",",") + ";")
        f.write(str(self.o_cuts) + ";")
        f.write(str(self.f_cuts) + ";")
        f.write(str(self.callbacks) + ";")
        f.write("{:.2f}".format(self.elapsedTime).replace(".",",") + "\n")

        f.close()

        # Write sol file
        solFileName = "output/" + self.instanceName + ".sol.csv"
        f = open(solFileName, "w")

        # Get the header
        header = "Instance;Obj;"
        for k,d in self.pdata.depots.iteritems():
            for vt in self.pdata.vehicleTypes:
                header += "LV Fleet(" + str(d.id) + ":" + str(vt.type) + ");"

        for k,d in self.pdata.depots.iteritems():
            for vt in self.pdata.vehicleTypes:
                header += "HV Fleet(" + str(d.id) + ":" + str(vt.type) + ");"

        f.write(header + "\n")

        # write data
        f.write(self.instanceName + ";")
        f.write("{:.2f}".format(self.obj).replace(".",",") + ";")

        # write leased fleet sizes
        for k, d in self.pdata.depots.iteritems():
            for vt in self.pdata.vehicleTypes:
                fsize = "{:10.2f}".format(self.leasedFleet[d.id][vt.type]).replace(".",",")
                f.write(str(fsize) + ";")

        # write hired fleet sizes
        for k, d in self.pdata.depots.iteritems():
            for vt in self.pdata.vehicleTypes:
                fsize = "{:10.2f}".format(self.hiredFleet[d.id][vt.type]).replace(".",",")
                f.write(fsize + ";")

        f.close()


#print "{:10.2f}".format(12345678912345.1231230123)
