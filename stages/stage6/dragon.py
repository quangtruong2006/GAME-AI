class Dragon:
    def __init__(self, name, element, max_hp):
        self.name = name
        self.element = element
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.alive = True
        self.skills = []
        self.switch_lock = 0

    def add_skill(self, skill):
        self.skills.append(skill)

    def take_damage(self, amount):
        self.current_hp -= amount
        if self.current_hp <= 0:
            self.current_hp = 0
            self.alive = False

    def clone(self):
        new_dragon = Dragon(self.name, self.element, self.max_hp)
        new_dragon.current_hp = self.current_hp
        new_dragon.alive = self.alive
        new_dragon.switch_lock = self.switch_lock
        new_dragon.skills = [skill.clone() for skill in self.skills]
        return new_dragon