class Route:
    def __init__(self, id, customers):
        self.id = id
        self.vehicleType = 0
        self.customers = customers

    def __repr__(self):
        return "R:" + str(self.id) + " | " + str(self.customers)