class Route:
    def __init__(self, id, customers, distance):
        self.id = id
        self.vehicleType = 0
        self.customers = customers
        self.distance = distance

    def __repr__(self):
        return "R:" + str(self.id) + " | " + str(self.customers)