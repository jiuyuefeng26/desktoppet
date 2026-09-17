import math
import time
import tkinter as tk
from PIL import Image, ImageTk

FPS = 30

class PlantCellPet:
    def __init__(self, root: tk.Tk) -> None:
        # 初始化窗口
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "#ffffff")
        self.root.configure(bg="#ffffff")
        try:
            self.root.wm_attributes('-transparent', True)
        except:
            pass
        
        # 打开原图并缩放
        with Image.open("plantcell.png") as original_image:
        # 计算目标尺寸，这里按1/4比例缩小
            target_size = (original_image.width // 4, original_image.height // 4)
        # 使用LANCZOS插值缩放（Pillow 9.1.0+用Resampling.LANCZOS，旧版本直接用Image.LANCZOS）
            resized_image = original_image.resize(target_size, Image.Resampling.LANCZOS)
            self.processed_image = self.make_background_transparent(resized_image.convert("RGB"))        # 转换为Tkinter可用的PhotoImage格式

        self.body_image = ImageTk.PhotoImage(self.processed_image) 

        self.body_w = self.body_image.width()
        self.body_h = self.body_image.height()
        self.margin = 12
        self.leg_room = 67
        self.width = self.body_w + self.margin * 2
        self.height = self.body_h + self.leg_room
        self.canvas = tk.Canvas(
            root,
            width=self.width,
            height=self.height,
            bg="#ffffff",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.left_leg = self.canvas.create_line(0, 0, 0, 0, fill="#24431d", width=10, capstyle=tk.ROUND)
        self.right_leg = self.canvas.create_line(0, 0, 0, 0, fill="#24431d", width=10, capstyle=tk.ROUND)
        self.left_foot = self.canvas.create_oval(0, 0, 0, 0, fill="#345c27", outline="#173c17", width=2)
        self.right_foot = self.canvas.create_oval(0, 0, 0, 0, fill="#345c27", outline="#173c17", width=2)
        self.body = self.canvas.create_image(self.margin, 0, anchor="nw", image=self.body_image)

        self.direction = 1
        self.speed = 95.0
        self.walking = True
        self.phase = 0.0
        self.last_time = time.perf_counter()
        self.drag_offset = None

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_x = max(0, (screen_w - self.width) // 2)
        start_y = max(0, screen_h - self.height - 70)
        self.x = float(start_x)
        self.y = float(start_y)
        self.root.geometry(f"{self.width}x{self.height}+{start_x}+{start_y}")

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="暂停走动", command=self.toggle_walking)
        self.menu.add_separator()
        self.menu.add_command(label="慢一点", command=lambda: self.change_speed(-25))
        self.menu.add_command(label="快一点", command=lambda: self.change_speed(25))
        self.menu.add_command(label="转身", command=self.turn_around)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.root.destroy)

        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<Double-Button-1>", lambda _event: self.toggle_walking())
        self.canvas.bind("<Button-3>", self.show_menu)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self.draw_pose(0.0)
        self.root.after(0, self.tick)

    def make_background_transparent(self, image):
        pixels = image.load()
        w, h = image.size
        for y in range(h):
            for x in range(w):
                r, g, b = pixels[x, y][:3]
                if min(r, g, b) >= 242:
                    pixels[x, y] = (255, 255, 255)
        return image
        
    def flip_image_horizontal(self):
        """水平翻转图像（基于当前图像）"""
        self.processed_image = self.processed_image.transpose(Image.FLIP_LEFT_RIGHT)
        self.body_image = ImageTk.PhotoImage(self.processed_image)
        self.canvas.itemconfig(self.body, image=self.body_image)   

    def toggle_walking(self) -> None:
        self.walking = not self.walking
        self.menu.entryconfigure(0, label="暂停走动" if self.walking else "继续走动")
        self.last_time = time.perf_counter()

    def change_speed(self, amount: float) -> None:
        self.speed = min(220.0, max(35.0, self.speed + amount))

    def turn_around(self) -> None:
        self.direction *= -1

    def show_menu(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def start_drag(self, event: tk.Event) -> None:
        self.drag_offset = (event.x_root - self.x, event.y_root - self.y)

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
        self.canvas.coords(self.body, self.margin, bob)

        hip_y = self.body_h - 25 + bob
        foot_y = self.body_h + 45
        stride = math.sin(phase) * 18 if self.walking else 0
        lift_left = max(0.0, math.sin(phase)) * 9 if self.walking else 0
        lift_right = max(0.0, -math.sin(phase)) * 9 if self.walking else 0

        left_hip = self.margin + self.body_w * 0.42
        right_hip = self.margin + self.body_w * 0.58
        left_x = left_hip + stride * self.direction
        right_x = right_hip - stride * self.direction
        left_y = foot_y - lift_left
        right_y = foot_y - lift_right

        self.canvas.coords(self.left_leg, left_hip, hip_y, left_x, left_y)
        self.canvas.coords(self.right_leg, right_hip, hip_y, right_x, right_y)
        self.canvas.coords(self.left_foot, left_x - 17, left_y - 5, left_x + 13, left_y + 7)
        self.canvas.coords(self.right_foot, right_x - 13, right_y - 5, right_x + 17, right_y + 7)

        # Keep the body in front so the legs appear attached underneath it.
        self.canvas.tag_raise(self.left_leg)
        self.canvas.tag_raise(self.right_leg)
        
    def tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, now - self.last_time)
        self.last_time = now

        if self.walking and self.drag_offset is None:
            self.phase = (self.phase + dt * 7.5) % (math.tau)
            self.x += self.direction * self.speed * dt

            screen_w = self.root.winfo_screenwidth()
            if self.x <= 0:
                self.x = 0.0
                self.direction = 1
                self.flip_image_horizontal()
            elif self.x + self.width >= screen_w:
                self.x = float(screen_w - self.width)
                self.direction = -1
                self.flip_image_horizontal()

            max_y = max(0, self.root.winfo_screenheight() - self.height - 35)
            self.y = min(max(0.0, self.y), float(max_y))
            self.root.geometry(f"+{round(self.x)}+{round(self.y)}")

        self.draw_pose(self.phase)
        self.root.after(round(1000 / FPS), self.tick)


def main() -> None:
    root = tk.Tk()
    PlantCellPet(root)
    root.mainloop()


if __name__ == "__main__":
    main()
