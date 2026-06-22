# File: stages/stage3_inventory.py
import pygame

class Stage3Inventory:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager
        try:
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 36)
        except:
            self.font = pygame.font.SysFont("Arial", 36, bold=True)

    def handle_events(self, events):
        for event in events:
            # Nhấn ESC để thoát tạm về menu
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.stage_manager.change_stage("stage_select")

    def update(self):
        pass

    def draw(self):
        # Tô nền màu xám đen
        self.screen.fill((30, 30, 40))
        
        # In chữ ra giữa màn hình
        text = self.font.render("STAGE 3: INVENTORY (Coming Soon)", True, (255, 215, 0))
        text_rect = text.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
        self.screen.blit(text, text_rect)
        
        hint = pygame.font.SysFont("Arial", 20).render("Press ESC to go back", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 50)))