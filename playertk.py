import math
import time
import tkinter as tk
from PIL import Image, ImageOps, ImageTk

FPS = 30

class Player:
    def __init__(self, root: tk.Tk) -> None:
        # 初始化窗口
        self.root = root
        self.root.overrideredirect(True)      #隐藏标题栏
        self.root.attributes("-topmost", True)
        
        # 设置透明色键 - 使用白色作为透明色
        self.root.configure(bg="#ffffff")
        self.root.wm_attributes('-transparentcolor', '#ffffff')
        
        # 设置窗口透明
        try:
            self.root.wm_attributes('-transparent', True)
        except:
            pass

        # 打开原图
        with Image.open("plantcell20%.png") as original_image:          
            # 处理白色背景为透明（在图像层面）
            self.processed_image = self.make_background_transparent(original_image)

        self.body_image = ImageTk.PhotoImage(self.processed_image)       
        self.width = self.body_image.width()
        self.height = self.body_image.height()
        # Canvas背景也设为白色（透明色）
        self.canvas = tk.Canvas(
            root,
            width=self.width,
            height=self.height,
            bg="#ffffff",
            highlightthickness=0,      #禁用边框高亮
            bd=0,                      #boderwidth=0
        )
        self.canvas.pack()

        self.body = self.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.body_image,
        )

        self.direction_x = 1  # x方向: 1向右, -1向左
        self.direction_y = 1  # y方向: 1向下, -1向上
        self.speed = 95.0
        self.walking = True
        self.phase = 0.0
        self.last_time = time.perf_counter()
        self.drag_offset = None

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        start_x = min(0, (self.screen_w - self.width) // 2)
        start_y = max(0, self.screen_h - self.height - 70)
        self.x = float(start_x)
        self.y = float(start_y)
        self.root.geometry(f"{self.width}x{self.height}+{start_x}+{start_y}")

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="暂停走动", command=self.toggle_walking)
        self.menu.add_command(label="慢一点", command=lambda: self.change_speed(-25))
        self.menu.add_command(label="快一点", command=lambda: self.change_speed(25))
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.root.destroy)

        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<Double-Button-1>", lambda _event: self.toggle_walking())
        self.canvas.bind("<Button-3>", self.show_menu)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self.draw_pose(0.0)
        self.root.after(0, self.tick)

    def make_background_transparent(self, image: Image.Image) -> Image.Image:
        """将图像中的白色背景转换为透明"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        try:
            data = list(image.get_flattened_data())
        except AttributeError:
            data = list(image.getdata())
        
        new_data = []
        
        for pixel in data:
            r, g, b, a = pixel
            if r >= 240 and g >= 240 and b >= 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(pixel)
        
        image.putdata(new_data)
        return image

    def toggle_walking(self) -> None:
        self.walking = not self.walking
        self.menu.entryconfigure(0, label="暂停走动" if self.walking else "继续走动")
        self.last_time = time.perf_counter()

    def change_speed(self, amount: float) -> None:
        self.speed = min(220.0, max(35.0, self.speed + amount))

    def show_menu(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def drag(self, event: tk.Event) -> None:
        if self.drag_offset is None:
            return
        self.x = float(event.x_root - self.drag_offset[0])
        self.y = float(event.y_root - self.drag_offset[1])
        self.root.geometry(f"+{round(self.x)}+{round(self.y)}")

    def end_drag(self, _event: tk.Event) -> None:
        self.drag_offset = None
        self.last_time = time.perf_counter()

    def draw_pose(self, phase: float) -> None:
        bob = -abs(math.sin(phase)) * 4 if self.walking else 0

        stride = math.sin(phase) * 18 if self.walking else 0
        lift_left = max(0.0, math.sin(phase)) * 9 if self.walking else 0
        lift_right = max(0.0, -math.sin(phase)) * 9 if self.walking else 0

    def tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, now - self.last_time)
        self.last_time = now

        if self.walking and self.drag_offset is None:
            self.phase = (self.phase + dt * 7.5) % (math.tau)
            
            # 移动
            self.x += self.direction_x * self.speed * dt
            self.y += self.direction_y * self.speed * dt
            
            # 边界碰撞检测 - X轴
            if self.x <= 0:
                self.x = 0.0
                self.direction_x = 1
            elif self.x + self.width >= self.screen_w:
                self.x = float(self.screen_w - self.width)
                self.direction_x = -1
            
            # 边界碰撞检测 - Y轴
            if self.y <= 0:
                self.y = 0.0
                self.direction_y = 1
            elif self.y + self.height >= self.screen_h:
                self.y = float(self.screen_h - self.height)
                self.direction_y = -1
          
            self.root.geometry(f"+{round(self.x)}+{round(self.y)}")

        self.draw_pose(self.phase)
        self.root.after(round(1000 / FPS), self.tick)


def main() -> None:
    root = tk.Tk()
    Player(root)
    root.mainloop()


if __name__ == "__main__":
    main()
