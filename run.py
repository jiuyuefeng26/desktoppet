import pygame as pg
import sys
import os
import ctypes
from ctypes import wintypes
from pathlib import Path
from collections import deque
from pygame.sprite import Sprite


class Animation(Sprite):
    def __init__(self, position, frame_list):
        super().__init__()
        self.images = []

        for filename in frame_list:
            try:
                image = pg.image.load(filename).convert_alpha()
                image = self._remove_background(image)  # 移除边缘连通的近白背景
                self.images.append(image)
            except pg.error:
                print(f"无法加载图片: {filename}")

        self.index = 0
        self.delay = 200
        self.last_update = pg.time.get_ticks()
        self.facing_left = False  # 当前朝向

        if self.images:
            self._base_image = self.images[self.index]
        else:
            # 加载失败时的占位图
            self._base_image = pg.Surface((50, 50), pg.SRCALPHA)
            self._base_image.fill((255, 0, 0, 255))

        self.image = self._base_image
        self.rect = self.image.get_rect()
        self.rect.center = position  # 真正使用传入的位置

        self.speed = 6  # 水平移动速度

    @staticmethod
    def _remove_background(image):
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

    def update(self):
        # 动画帧更新
        if len(self.images) > 1:
            now = pg.time.get_ticks()
            if now - self.last_update > self.delay:
                self.last_update = now
                self.index = (self.index + 1) % len(self.images)
                self._base_image = self.images[self.index]

        # 自动移动
        self.rect.x += self.speed

        # 边界反弹
        screen_rect = pg.display.get_surface().get_rect()
        if self.rect.left <= 0:
            self.speed = abs(self.speed)
            self.rect.left = 0
            self.facing_left = False
        elif self.rect.right >= screen_rect.width:
            self.speed = -abs(self.speed)
            self.rect.right = screen_rect.width
            self.facing_left = True

        # 每一帧根据朝向渲染，保持翻转状态
        if self.facing_left:
            self.image = pg.transform.flip(self._base_image, True, False)
        else:
            self.image = self._base_image


class Game:
    # Windows 扩展样式常量
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020  # 鼠标点击穿透
    LWA_COLORKEY = 0x00000001
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010

    def __init__(self):
        pg.init()

        if sys.platform != 'win32':
            raise RuntimeError('本程序的桌面透明效果需要 Windows。')

        os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
        self.clock = pg.time.Clock()
        self.screen = pg.display.set_mode((0, 0), pg.NOFRAME)
        self.screen_rect = self.screen.get_rect()
        self.bg_color = (255, 0, 255)  # Windows 透明色键
        self.screen.fill(self.bg_color)

        self._enable_desktop_transparency()
        pg.display.update()

        # 用脚本所在目录加载图片，避免工作目录不同导致找不到
        base = Path(__file__).resolve().parent
        frame_list = [str(base / f'{i}.png') for i in range(1, 5)]

        self.animation = Animation((400, 300), frame_list)
        self.group = pg.sprite.Group()
        self.group.add(self.animation)

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
        set_transparency.argtypes = [wintypes.HWND, wintypes.DWORD,
                                     wintypes.BYTE, wintypes.DWORD]
        set_transparency.restype = wintypes.BOOL

        set_position = self.user32.SetWindowPos
        set_position.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                 wintypes.UINT]
        set_position.restype = wintypes.BOOL

        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short

        hwnd = pg.display.get_wm_info()['window']

        # 设置 WS_EX_LAYERED（以及可选的 WS_EX_TRANSPARENT 让透明区域点击穿透）
        ctypes.set_last_error(0)
        ex_style = get_style(hwnd, self.GWL_EXSTYLE)
        new_style = ex_style | self.WS_EX_LAYERED
        # 如果希望透明区域可以直接操作后面的桌面，取消下一行注释
        # new_style |= self.WS_EX_TRANSPARENT
        previous = set_style(hwnd, self.GWL_EXSTYLE, new_style)
        if not previous and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())

        # 设置色键透明：bg_color 区域变透明
        r, g, b = self.bg_color
        color_key = r | (g << 8) | (b << 16)
        if not set_transparency(hwnd, color_key, 255, self.LWA_COLORKEY):
            raise ctypes.WinError(ctypes.get_last_error())

        # 置顶显示
        flags = self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE
        if not set_position(hwnd, wintypes.HWND(self.HWND_TOPMOST),
                            0, 0, 0, 0, flags):
            raise ctypes.WinError(ctypes.get_last_error())

    def run_game(self):
        running = True
        while running:
            running = self._check_events()
            self._update_screen()
            self.clock.tick(60)

    def _check_events(self):
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                pg.quit()
                sys.exit()
                return False
            elif ev.type == pg.KEYDOWN:
                if ev.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()
                    return False

        # 即使点击了桌面使窗口失去焦点，也可以用 Esc 退出。
        if self.user32.GetAsyncKeyState(0x1B) & 0x8000:  # VK_ESCAPE
            pg.quit()
            sys.exit()
            return False
        return True

    def _update_screen(self):
        self.screen.fill(self.bg_color)
        self.group.update()  # 自动调用精灵的 update()
        self.group.draw(self.screen)
        pg.display.update()


if __name__ == '__main__':
    game = Game()
    game.run_game()
