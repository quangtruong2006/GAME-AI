class Skill:
    def __init__(self, name, damage, accuracy, cooldown):
        self.name = name
        self.damage = damage
        self.accuracy = accuracy
        self.max_cooldown = cooldown
        self.current_cooldown = 0

    def clone(self):
        new_skill = Skill(self.name, self.damage, self.accuracy, self.max_cooldown)
        new_skill.current_cooldown = self.current_cooldown
        return new_skill

    def is_ready(self):
        return self.current_cooldown == 0