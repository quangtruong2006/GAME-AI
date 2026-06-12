# ── VẼ LƯỚI GRID Ở GIỮA ──────────────────────────────
        for r in range(self.rows):
            for c in range(self.cols):
                rect = pygame.Rect(
                    self.grid_offset_x + c * self.tile_size,
                    self.grid_offset_y + r * self.tile_size,
                    self.tile_size - 1,
                    self.tile_size - 1
                )
                
                # Xác định màu ô
                color = self.c_grid
                if self.grid[r][c] == 1:
                    color = self.c_wall
                elif (r, c) == self.start_node:
                    color = self.c_nobita
                elif (r, c) == self.goal_node:
                    color = self.c_dora
                elif (r, c) in self.path:
                    color = self.c_path
                elif (r, c) in self.visited_order:
                    color = self.c_visited

                pygame.draw.rect(self.screen, color, rect, border_radius=4)

        # ── PANEL TRÁI (MENU THUẬT TOÁN) ────────────────────
        left_panel_width = 255
        left_surface = pygame.Surface((left_panel_width, sh), pygame.SRCALPHA)
        left_surface.fill((38, 41, 44, 200))
        self.screen.blit(left_surface, (0, 0))
        pygame.draw.line(self.screen, (80, 85, 90), (left_panel_width, 0), (left_panel_width, sh), 2)

        self.screen.blit(self.title_font.render("INFORMED AI", True, self.c_text), (15, 30))

        algorithms = [
            ("Greedy BFS", "Greedy", pygame.Rect(10, 80,  220, 40)),
            ("A* Search", "A*", pygame.Rect(10, 130, 220, 40)),
            ("IDA* Search", "IDA*", pygame.Rect(10, 180, 220, 40)),
        ]

        for label, algo_key, btn_rect in algorithms:
            if self.selected_algorithm == algo_key:
                pygame.draw.rect(self.screen, (40, 110, 190), btn_rect, border_radius=5)
                text_color = self.c_text
                prefix = "> "
            else:
                text_color = (130, 135, 140)
                prefix = "  "
            self.screen.blit(self.font.render(f"{prefix}{label}", True, text_color), (btn_rect.x + 10, btn_rect.y + 10))

        # Nút Clear Tường
        clear_btn = pygame.Rect(10, 240, 220, 40)
        pygame.draw.rect(self.screen, (100, 50, 50), clear_btn, border_radius=5)
        self.screen.blit(self.font.render("  Clear Walls", True, (200, 150, 150)), (clear_btn.x + 10, clear_btn.y + 10))

        # Nút RUN và BACK
        run_btn  = pygame.Rect(20, sh - 130, 200, 45)
        back_btn = pygame.Rect(20, sh - 70,  200, 45)

        pygame.draw.rect(self.screen, (46, 204, 113), run_btn,  border_radius=6)
        run_text = self.font.render("RUN AI", True, (255, 255, 255))
        self.screen.blit(run_text, run_text.get_rect(center=run_btn.center))

        pygame.draw.rect(self.screen, (231, 76, 60), back_btn, border_radius=6)
        back_text = self.font.render("BACK", True, (255, 255, 255))
        self.screen.blit(back_text, back_text.get_rect(center=back_btn.center))

        # ── PANEL PHẢI (STATS) ───────────────────────────────
        right_panel_width = 180
        right_surface = pygame.Surface((right_panel_width, sh), pygame.SRCALPHA)
        right_surface.fill((38, 41, 44, 200))
        self.screen.blit(right_surface, (sw - right_panel_width, 0))
        pygame.draw.line(self.screen, (80, 85, 90), (sw - right_panel_width, 0), (sw - right_panel_width, sh), 2)

        rx = sw - right_panel_width + 15
        self.screen.blit(self.title_font.render("STATS",         True, self.c_text),        (rx, 30))
        self.screen.blit(self.font.render(f"Algo: {self.selected_algorithm}", True, (200, 202, 205)), (rx, 75))
        self.screen.blit(self.font.render(f"Nodes: {self.nodes_expanded}",   True, (200, 202, 205)), (rx, 120))
        self.screen.blit(self.font.render(f"Time: {self.execution_time}",    True, (200, 202, 205)), (rx, 165))
        self.screen.blit(self.font.render(f"Cost: {self.path_cost}",         True, (200, 202, 205)), (rx, 210))
        
        # Hướng dẫn
        hint1 = self.font.render("Left Click: Draw Wall", True, (100, 100, 100))
        hint2 = self.font.render("Right Click: Erase", True, (100, 100, 100))
        self.screen.blit(hint1, (rx, sh - 100))
        self.screen.blit(hint2, (rx, sh - 70))