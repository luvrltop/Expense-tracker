import tkinter as tk
from ttkbootstrap.style import Colors


class StripedProgressBar(tk.Canvas):
    """progress bar with diagonal stripes that keep sliding (canvas, ttk can't animate stripes)"""

    STRIPE_WIDTH = 10   # width of one stripe, gap is the same
    STEP = 1            # px moved per frame
    FRAME_MS = 40

    def __init__(self, master, height=14, **kw):
        super().__init__(master, height=height, highlightthickness=0, borderwidth=0, **kw)
        self.value = 0
        self.fill_color = "#02b875"
        self.trough_color = "#e5e5e5"
        self.offset = 0
        self.bind("<Configure>", lambda e: self.redraw())
        self.after(self.FRAME_MS, self.animate)

    def set(self, value, fill_color, trough_color, bg):
        """value 0-100"""
        self.value = max(0, min(value, 100))
        self.fill_color = fill_color
        self.trough_color = trough_color
        self.configure(background=bg)
        self.redraw()

    def animate(self):
        if not self.winfo_exists():
            return
        if self.value > 0:
            self.offset = (self.offset + self.STEP) % (self.STRIPE_WIDTH * 2)
            self.redraw()
        self.after(self.FRAME_MS, self.animate)

    def redraw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        fill_width = int(width * self.value / 100)

        self.create_rectangle(0, 0, width, height, fill=self.trough_color, width=0)
        if fill_width <= 0:
            return
        self.create_rectangle(0, 0, fill_width, height, fill=self.fill_color, width=0)

        # diagonal stripes, start left of 0 so the sliding has no gap
        stripe_color = Colors.update_hsv(self.fill_color, sd=-0.15, vd=0.12)
        period = self.STRIPE_WIDTH * 2
        x = self.offset - period - height
        while x < fill_width:
            self.create_polygon(
                x, height,
                x + self.STRIPE_WIDTH, height,
                x + self.STRIPE_WIDTH + height, 0,
                x + height, 0,
                fill=stripe_color, width=0,
            )
            x += period

        # cover stripes that went past the filled part
        self.create_rectangle(fill_width, 0, width, height, fill=self.trough_color, width=0)
