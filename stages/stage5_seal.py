# File: stages/stage5_seal.py
import pygame

class Stage5Seal:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager
        try:
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 36)
        except:
            self.font = pygame.font.SysFont("Arial", 36, bold=True)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.stage_manager.change_stage("stage_select")

    def update(self):
        pass

    def draw(self):
        # Tone màu tím huyền bí
        self.screen.fill((35, 25, 45))
        
        text = self.font.render("STAGE 5: SEAL (Coming Soon)", True, (155, 89, 182))
        text_rect = text.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
        self.screen.blit(text, text_rect)
        
        hint = pygame.font.SysFont("Arial", 20).render("Press ESC to go back", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 50)))