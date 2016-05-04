class Customer:
    def __init__(self, id, x, y, zone=-1, isDepot=False):
        self.id = id
        self.x = x
        self.y = y
        self.zone = zone
        self.isDepot = isDepot

    def isDummy(self):
        return self.id < 0

    def __repr__(self):
        return str(self.id) \
               # + " - x:" + str(self.x) + " - y:" + str(self.y) + " - Zone:" + str(self.zone) + \
               # " - Depot:" + str(self.isDepot)

