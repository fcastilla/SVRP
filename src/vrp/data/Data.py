class Customer:
    def __init__(self, id, x, y, zone=-1, isDepot=False):
        self.id = id
        self.x = x
        self.y = y
        self.zone = zone
        self.isDepot = isDepot
        self.isDayCustomer = False
        self.acceptedVehicleTypes = []

    def isDummy(self):
        return self.id < 0

    def __repr__(self):
        return str(self.id) \
               # + " - x:" + str(self.x) + " - y:" + str(self.y) + " - Zone:" + str(self.zone) + \
               # " - Depot:" + str(self.isDepot)

class Vehicle:
    def __init__(self, type, lvCost, hvCost, minFleet, maxFleet):
        self.type = type
        self.lvCost = lvCost
        self.hvCost = hvCost
        self.minFleet = minFleet
        self.maxFleet = maxFleet

