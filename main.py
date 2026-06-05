# File: main.py
import pygame
import sys
import config

from stages.menu import MainMenu
from stages.stage1_maze import Stage1Maze

class StageManager:
    def __init__(self, screen):
        self.screen = screen
        self.stages = {
            "menu":   MainMenu(screen, self),
            "stage1": Stage1Maze(screen, self)
        }
        self.current_stage = self.stages["menu"]

    def change_stage(self, stage_name):
        if stage_name in self.stages:
            self.current_stage = self.stages[stage_name]
        else:
            print(f"Không tìm thấy stage: {stage_name}")

    def handle_events(self, events):
        self.current_stage.handle_events(events)

    def update(self):
        self.current_stage.update()

    def draw(self):
        self.current_stage.draw()


def main():
    pygame.init()
    pygame.mixer.init()

    fps = getattr(config, 'FPS', 60)

    screen = pygame.display.set_mode(
        (1400, 900),
        pygame.RESIZABLE
    )

    # MAXIMIZE WINDOW
    import ctypes

    try:
        hwnd = pygame.display.get_wm_info()["window"]
        ctypes.windll.user32.ShowWindow(hwnd, 3)
    except:
        pass
    pygame.display.set_caption("Nobita AI Game")

    stage_manager = StageManager(screen)
    clock = pygame.time.Clock()

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        stage_manager.handle_events(events)
        stage_manager.update()
        stage_manager.draw()

        pygame.display.flip()
        clock.tick(fps)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()