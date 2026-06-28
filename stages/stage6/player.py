class Player:
    def __init__(self, name, is_ai=True):
        self.name = name
        self.dragons = []
        self.active_index = 0
        self.is_ai = is_ai

    def add_dragon(self, dragon):
        self.dragons.append(dragon)

    def get_active_dragon(self):
        return self.dragons[self.active_index]

    def has_alive_dragons(self):
        return any(d.alive for d in self.dragons)

    def get_alive_indices(self):
        return [i for i, d in enumerate(self.dragons) if d.alive]

    def clone(self):
        new_player = Player(self.name, self.is_ai)
        new_player.dragons = [d.clone() for d in self.dragons]
        new_player.active_index = self.active_index
        return new_player