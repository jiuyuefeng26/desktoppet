import sys
import os
import ctypes
from ctypes import wintypes
from pathlib import Path
from collections import deque
import pygame

class Player:
    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError('本程序的桌面透明效果需要 Windows。')
        os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
        pygame.init()
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
        self.screen_rect = self.screen.get_rect()
        self.bg_color = (255, 0, 255)  # Windows 透明色键
        self.screen.fill(self.bg_color)
        self._enable_desktop_transparency()
        pygame.display.update()
        
        # 加载原始图像
        self.original_image = pygame.image.load(str(Path(__file__).resolve().parent / 'plantcell20%.png')).convert_alpha()
        self.original_image = self._remove_background(self.original_image)
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        
        # 初始化位置和速度
        self.rect.x = 100
        self.rect.y = 300
        self.speed = 1.5
        self.direction_x = 1
        self.direction_y = -1
              
    def _enable_desktop_transparency(self):
        # 使用标准库 ctypes，无需安装 pywin32。声明指针类型以兼容 64 位 Python。
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        get_style = self.user32.GetWindowLongW
        get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        get_style.restype = wintypes.LONG
        set_style = self.user32.SetWindowLongW
        set_style.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
        set_style.restype = wintypes.LONG
        set_transparency = self.user32.SetLayeredWindowAttributes
        set_transparency.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.BYTE, wintypes.DWORD]
        set_transparency.restype = wintypes.BOOL
        set_position = self.user32.SetWindowPos
        set_position.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        set_position.restype = wintypes.BOOL
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        hwnd = pygame.display.get_wm_info()['window']
        ctypes.set_last_error(0)
        previous = set_style(hwnd, -20, get_style(hwnd, -20) | 0x00080000)
        if not previous and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())
        r, g, b = self.bg_color
        if not set_transparency(hwnd, r | (g << 8) | (b << 16), 255, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        # 置顶显示；透明区域可直接操作后面的桌面。
        if not set_position(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0010):
            raise ctypes.WinError(ctypes.get_last_error())

    def _remove_background(self, image):
        """只移除与边缘连通的近白色背景，保留内部浅色细节。"""
        width, height = image.get_size()
        visited = bytearray(width * height)
        pending = deque()

        def visit(x, y):
            index = y * width + x
            if visited[index]:
                return
            visited[index] = 1
            r, g, b, a = image.get_at((x, y))
            if a < 128 or min(r, g, b) >= 240:
                image.set_at((x, y), (0, 0, 0, 0))
                pending.append((x, y))

        for x in range(width):
            visit(x, 0)
            visit(x, height - 1)
        for y in range(height):
            visit(0, y)
            visit(width - 1, y)
        while pending:
            x, y = pending.popleft()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < width and 0 <= ny < height:
                    visit(nx, ny)

        # 色键透明为二值透明，避免半透明像素混合后出现紫色边缘。
        for y in range(height):
            for x in range(width):
                r, g, b, a = image.get_at((x, y))
                image.set_at((x, y), (r, g, b, 255 if a >= 128 else 0))
        return image

    def run_game(self):
        running = True
        while running:
            running = self._check_events()
            self._move()
            self._update_screen()
            self.clock.tick(60)

    def _check_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                return False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                    return False
        # 即使点击了桌面使窗口失去焦点，也可以用 Esc 退出。
        if self.user32.GetAsyncKeyState(0x1B) & 0x8000:
            pygame.quit()
            sys.exit()
        return True

    def _update_screen(self):
        self.screen.fill(self.bg_color)
        self.screen.blit(self.image, self.rect)
        pygame.display.update()
        
    def _move(self):
        # 水平移动
        self.rect.x += self.speed * self.direction_x
        # 垂直移动
        self.rect.y += self.speed * self.direction_y
        
        # 只在朝向边界移动时触发，避免停在边缘时连续翻转。
        flip_x = False
        flip_y = False
        if self.direction_x > 0 and self.rect.right >= self.screen_rect.right:
            self.rect.right = self.screen_rect.right
            self.direction_x = -1
            flip_x = True
        elif self.direction_x < 0 and self.rect.left <= self.screen_rect.left:
            self.rect.left = self.screen_rect.left
            self.direction_x = 1
            flip_x = True

        if self.direction_y > 0 and self.rect.bottom >= self.screen_rect.bottom:
            self.rect.bottom = self.screen_rect.bottom
            self.direction_y = -1
            flip_y = True
        elif self.direction_y < 0 and self.rect.top <= self.screen_rect.top:
            self.rect.top = self.screen_rect.top
            self.direction_y = 1
            flip_y = True

        # 左右边界水平翻转，上下边界垂直翻转；撞角时同时翻转。
        if flip_x or flip_y:
            self.image = pygame.transform.flip(self.image, flip_x, flip_y)

if __name__ == '__main__':
    Player().run_game()
