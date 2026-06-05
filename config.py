import pygame

# Cấu hình kích thước màn hình
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Cấu hình ô lưới (Ma trận 2D Chặng 1)
TILE_SIZE = 40  

# Bảng màu hệ thống (RGB)
COLOR_BG = (20, 24, 30)         # Nền tối sâu
COLOR_PANEL = (35, 40, 50)      # Màu bảng thống kê
COLOR_TEXT = (240, 240, 240)    # Màu chữ trắng
COLOR_WALL = (50, 70, 90)       # Màu tường mê cung
COLOR_ROAD = (40, 45, 55)       # Màu đường đi
COLOR_VISITED = (30, 130, 76)   # Màu các ô AI đã duyệt qua (Xanh lá)
COLOR_PATH = (241, 196, 15)     # Đường đi ngắn nhất tìm được (Vàng)

# Màu nhân vật (Tạm thời khi chưa có ảnh)
COLOR_NOBITA = (52, 152, 219)   # Xanh dương sáng
COLOR_DORA = (231, 76, 60)      # Đỏ