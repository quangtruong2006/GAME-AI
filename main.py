import pygame
import sys
import config

from stages.menu import MainMenu
from stages.stage_select import StageSelect
from stages.stage1_maze import Stage1Maze
from stages.stage2_city import Stage2City
from stages.stage3_inventory import Stage3Inventory
from stages.stage4_forest import Stage4Forest
from stages.stage5_seal import Stage5Seal
from stages.stage6_boss import Stage6Boss

class StageManager: 
    def __init__(self, screen):
        self.screen = screen
        # Mảng lưu danh sách các chặng đã được mở
        self.unlocked_stages = ["stage1", "stage2", "stage3", "stage4", "stage5", "stage6"]
        
        # --- THÊM 2 BIẾN NÀY ĐỂ QUẢN LÝ HOẠT ẢNH NỔ KHÓA ---
        self.current_stage_name = "menu"
        self.trigger_unlock_effect = None 
        
        self.stages = {
            "menu":   MainMenu(screen, self),
            "stage_select": StageSelect(screen, self),
            "stage1": Stage1Maze(screen, self),
            "stage2": Stage2City(screen, self),
            "stage3": Stage3Inventory(screen, self),
            "stage4": Stage4Forest(screen, self),
            "stage5": Stage5Seal(screen, self),
            "stage6": Stage6Boss(screen, self)
        }
        self.current_stage = self.stages["menu"]

    def unlock_stage(self, stage_name):
        if stage_name not in self.unlocked_stages:
            self.unlocked_stages.append(stage_name)
            print(f">>> ĐÃ MỞ KHÓA MÀN CHƠI: {stage_name}")

    def change_stage(self, stage_name):
        if stage_name in self.stages:
            self.current_stage = self.stages[stage_name]
            self.current_stage_name = stage_name # Cập nhật tên chặng hiện tại
        else:
            print(f"Không tìm thấy stage: {stage_name}")

    def handle_events(self, events):
        self.current_stage.handle_events(events)

    def update(self):
        self.current_stage.update()
        
        # --- BẮT TÍN HIỆU ĐỂ NỔ VỠ KHÓA CHẶNG TIẾP THEO ---
        if self.trigger_unlock_effect is not None:
            if self.current_stage_name == "stage_select":
                if hasattr(self.current_stage, 'trigger_unlock_animation'):
                    self.current_stage.trigger_unlock_animation(self.trigger_unlock_effect)
                self.trigger_unlock_effect = None

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