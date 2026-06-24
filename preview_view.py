from __future__ import annotations

import tkinter as tk
from typing import Callable

from PIL import Image, ImageTk

CARD = "#2E2E2E"
MUTED = "#888888"


class ImageViewport(tk.Frame):
    ZOOM_MIN = 0.05
    ZOOM_MAX = 16.0
    ZOOM_STEP = 1.12

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_view_change: Callable[[], None] | None = None,
        corner_label: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, bg=CARD, **kwargs)
        self._on_view_change = on_view_change
        self._corner_label = corner_label
        self._sync_peers: list[ImageViewport] = []
        self._syncing = False

        self.canvas = tk.Canvas(self, bg=CARD, highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)

        self._image: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._image_item: int | None = None
        self._label_item: int | None = None
        self._placeholder_item: int | None = None
        self._placeholder_text = ""

        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._render_scale = 0.0
        self._render_size = (0, 0)

        self._drag_origin: tuple[int, int] | None = None
        self._view_origin: tuple[float, float] | None = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Configure>", self._on_resize)

    @property
    def has_image(self) -> bool:
        return self._image is not None

    def set_sync_peers(self, peers: list[ImageViewport]) -> None:
        self._sync_peers = [p for p in peers if p is not self]

    def set_image(self, image: Image.Image | None, *, placeholder: str = "", reset_view: bool = True) -> None:
        self._image = image
        self._placeholder_text = placeholder
        self._clear_canvas()
        if image is None:
            self._draw_placeholder()
            return
        if reset_view:
            self._fit_or_defer()
        else:
            self._draw_image()

    def update_image(self, image: Image.Image) -> None:
        previous_size = self._image.size if self._image is not None else None
        self._image = image
        self._render_scale = 0.0
        if previous_size != image.size:
            self._fit_or_defer()
        elif self._image_item is None:
            self._clear_canvas()
            self._draw_image()
        else:
            self._draw_image()

    def _canvas_ready(self) -> bool:
        return self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1

    def _fit_or_defer(self) -> None:
        if self._canvas_ready():
            self.fit_to_view()
            self._draw_image()
        else:
            self.after_idle(self._deferred_fit_and_draw)

    def _deferred_fit_and_draw(self) -> None:
        if self._image is None:
            return
        self.fit_to_view()
        self._draw_image()

    def fit_to_view(self) -> None:
        if self._image is None:
            return
        canvas_w = max(self.canvas.winfo_width(), 1)
        canvas_h = max(self.canvas.winfo_height(), 1)
        image_w, image_h = self._image.size
        self._scale = min(canvas_w / image_w, canvas_h / image_h, 1.0)
        self._offset_x = (canvas_w - image_w * self._scale) / 2
        self._offset_y = (canvas_h - image_h * self._scale) / 2
        self._render_scale = 0.0

    def get_view_state(self) -> tuple[float, float, float]:
        return self._scale, self._offset_x, self._offset_y

    def apply_view_state(self, scale: float, offset_x: float, offset_y: float) -> None:
        self._scale = max(self.ZOOM_MIN, min(self.ZOOM_MAX, scale))
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._render_scale = 0.0
        if self._image is not None:
            self._draw_image()

    def _clear_canvas(self) -> None:
        self.canvas.delete("all")
        self._image_item = None
        self._label_item = None
        self._placeholder_item = None
        self._photo = None

    def _draw_placeholder(self) -> None:
        canvas_w = max(self.canvas.winfo_width(), 1)
        canvas_h = max(self.canvas.winfo_height(), 1)
        self._placeholder_item = self.canvas.create_text(
            canvas_w / 2,
            canvas_h / 2,
            text=self._placeholder_text,
            fill=MUTED,
            font=("Segoe UI", 13),
            justify="center",
        )

    def _ensure_photo(self) -> None:
        if self._image is None:
            return
        width = max(1, int(self._image.width * self._scale))
        height = max(1, int(self._image.height * self._scale))
        if (width, height) == self._render_size and self._scale == self._render_scale:
            return
        resampling = Image.Resampling.NEAREST if self._scale >= 1.0 else Image.Resampling.LANCZOS
        preview = self._image.resize((width, height), resampling)
        self._photo = ImageTk.PhotoImage(preview)
        self._render_size = (width, height)
        self._render_scale = self._scale

    def _draw_image(self) -> None:
        if self._image is None:
            return
        self._ensure_photo()
        if self._photo is None:
            return
        if self._image_item is None:
            self._image_item = self.canvas.create_image(
                self._offset_x,
                self._offset_y,
                anchor="nw",
                image=self._photo,
            )
        else:
            self.canvas.itemconfig(self._image_item, image=self._photo)
            self.canvas.coords(self._image_item, self._offset_x, self._offset_y)

        if self._corner_label:
            if self._label_item is None:
                self._label_item = self.canvas.create_text(
                    12,
                    12,
                    text=self._corner_label,
                    anchor="nw",
                    fill=MUTED,
                    font=("Segoe UI", 10, "bold"),
                )
            else:
                self.canvas.itemconfig(self._label_item, text=self._corner_label)
                self.canvas.tag_raise(self._label_item)

    def _move_image(self) -> None:
        if self._image_item is not None:
            self.canvas.coords(self._image_item, self._offset_x, self._offset_y)

    def _notify_view_change(self) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            if self._on_view_change:
                self._on_view_change()
            state = self.get_view_state()
            for peer in self._sync_peers:
                peer.apply_view_state(*state)
        finally:
            self._syncing = False

    def _on_press(self, event: tk.Event) -> None:
        if self._image is None:
            return
        self._drag_origin = (event.x, event.y)
        self._view_origin = (self._offset_x, self._offset_y)
        self.canvas.config(cursor="fleur")

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_origin is None or self._view_origin is None:
            return
        dx = event.x - self._drag_origin[0]
        dy = event.y - self._drag_origin[1]
        self._offset_x = self._view_origin[0] + dx
        self._offset_y = self._view_origin[1] + dy
        self._move_image()
        self._notify_view_change()

    def _on_release(self, _event: tk.Event) -> None:
        self._drag_origin = None
        self._view_origin = None
        self.canvas.config(cursor="hand2")

    def _on_wheel(self, event: tk.Event) -> None:
        if self._image is None:
            return
        factor = self.ZOOM_STEP if event.delta > 0 else 1 / self.ZOOM_STEP
        new_scale = max(self.ZOOM_MIN, min(self.ZOOM_MAX, self._scale * factor))
        if new_scale == self._scale:
            return
        cursor_x, cursor_y = event.x, event.y
        self._offset_x = cursor_x - (cursor_x - self._offset_x) * (new_scale / self._scale)
        self._offset_y = cursor_y - (cursor_y - self._offset_y) * (new_scale / self._scale)
        self._scale = new_scale
        self._draw_image()
        self._notify_view_change()

    def _on_resize(self, event: tk.Event) -> None:
        width = max(event.width, 1)
        height = max(event.height, 1)
        previous = getattr(self, "_last_canvas_size", (1, 1))
        self._last_canvas_size = (width, height)

        if self._image is None:
            if self._placeholder_item is not None:
                self._clear_canvas()
                self._draw_placeholder()
            return

        became_visible = previous[0] <= 1 and width > 1 or previous[1] <= 1 and height > 1
        if self._image_item is None or became_visible:
            self.fit_to_view()
            self._draw_image()
