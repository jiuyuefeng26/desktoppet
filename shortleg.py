import ctypes
import sys
from ctypes import wintypes
from pathlib import Path
from collections import deque

import pygame as pg
from pygame.sprite import Sprite


def remove_background(image):
    """移除与边缘连通的近白色背景，保留内部浅色细节。"""
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
        for nx, ny in (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ):
            if 0 <= nx < width and 0 <= ny < height:
                visit(nx, ny)

    # Windows 色键透明使用二值透明，减少紫色边缘。
    for y in range(height):
        for x in range(width):
            r, g, b, a = image.get_at((x, y))
            image.set_at((x, y), (r, g, b, 255 if a >= 128 else 0))

    return image


class Animation(Sprite):
    def __init__(self, position, frame_list):
        super().__init__()

        self.images = []

        for filename in frame_list:
            try:
                image = pg.image.load(str(filename)).convert_alpha()
                self.images.append(remove_background(image))
            except (pg.error, OSError) as exc:
                print(f"无法加载图片: {filename}，原因: {exc}")

        if not self.images:
            image = pg.Surface((50, 50), pg.SRCALPHA)
            image.fill((255, 0, 0))
            self.images.append(image)

        # 将所有帧放入同尺寸画布，避免切换帧时碰撞边界变化。
        width = max(image.get_width() for image in self.images)
        height = max(image.get_height() for image in self.images)

        frames = []
        for image in self.images:
            canvas = pg.Surface((width, height), pg.SRCALPHA)
            canvas.blit(image, image.get_rect(midbottom=(width // 2, height)))
            frames.append(canvas)

        # 假设原图朝右。预先生成朝左的帧，切换帧时保留方向。
        self.frames_right = frames
        self.frames_left = [
            pg.transform.flip(image, True, False)
            for image in frames
        ]

        self.index = 0
        self.delay = 200
        self.last_update = pg.time.get_ticks()
        self.speed_x = 180.0  # 像素/秒，约等于 60 FPS 下每帧 1.5 像素

        self.image = self.frames_right[self.index]
        self.rect = self.image.get_rect(center=position)
        self.rect.clamp_ip(pg.display.get_surface().get_rect())
        self.x = float(self.rect.x)

    def update(self, dt):
        now = pg.time.get_ticks()
        steps = (now - self.last_update) // self.delay

        if steps:
            self.last_update += steps * self.delay
            self.index = (self.index + steps) % len(self.frames_right)

        screen_width = pg.display.get_surface().get_width()
        max_x = max(0, screen_width - self.rect.width)

        self.x += self.speed_x * dt

        if max_x == 0:
            self.x = 0.0
        elif self.x <= 0:
            self.x = 0.0
            self.speed_x = abs(self.speed_x)
        elif self.x >= max_x:
            self.x = float(max_x)
            self.speed_x = -abs(self.speed_x)

        self.rect.x = round(self.x)

        frames = (
            self.frames_right if self.speed_x >= 0
            else self.frames_left
        )
        self.image = frames[self.index]


class Game:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("本程序的桌面透明效果需要 Windows。")

        pg.init()
        self.clock = pg.time.Clock()
        self.screen = pg.display.set_mode((0, 0), pg.NOFRAME)
        self.bg_color = (255, 0, 255)

        self.screen.fill(self.bg_color)
        self._enable_desktop_transparency()
        pg.display.update()

        base_dir = Path(__file__).resolve().parent
        frame_list = [base_dir / f"{i}.png" for i in range(1, 5)]

        self.animation = Animation((400, 300), frame_list)
        self.group = pg.sprite.Group(self.animation)

    def _enable_desktop_transparency(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)

        get_style = self.user32.GetWindowLongW
        get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        get_style.restype = wintypes.LONG

        set_style = self.user32.SetWindowLongW
        set_style.argtypes = [
            wintypes.HWND, ctypes.c_int, wintypes.LONG
        ]
        set_style.restype = wintypes.LONG

        set_transparency = self.user32.SetLayeredWindowAttributes
        set_transparency.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            wintypes.BYTE,
            wintypes.DWORD,
        ]
        set_transparency.restype = wintypes.BOOL

        set_position = self.user32.SetWindowPos
        set_position.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        set_position.restype = wintypes.BOOL

        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short

        hwnd = pg.display.get_wm_info()["window"]

        ctypes.set_last_error(0)
        style = get_style(hwnd, -20)
        error = ctypes.get_last_error()
        if style == 0 and error:
            raise ctypes.WinError(error)

        ctypes.set_last_error(0)
        previous = set_style(hwnd, -20, style | 0x00080000)
        error = ctypes.get_last_error()
        if previous == 0 and error:
            raise ctypes.WinError(error)

        r, g, b = self.bg_color
        color_key = r | (g << 8) | (b << 16)

        if not set_transparency(hwnd, color_key, 255, 0x00000001):
            raise ctypes.WinError(ctypes.get_last_error())

        # 窗口置顶，并移动到主屏幕左上角。
        if not set_position(
            hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0010
        ):
            raise ctypes.WinError(ctypes.get_last_error())

    def _check_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return False
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                return False

        # 窗口失去焦点后仍可按 Esc 退出。
        if self.user32.GetAsyncKeyState(0x1B) & 0x8000:
            return False

        return True

    def run_game(self):
        while True:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)

            if not self._check_events():
                break

            self.screen.fill(self.bg_color)
            self.group.update(dt)
            self.group.draw(self.screen)
            pg.display.update()


if __name__ == "__main__":
    try:
        game = Game()
        game.run_game()
    finally:
        pg.quit()
