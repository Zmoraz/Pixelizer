from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class ToggleSwitch(tk.Canvas):
    """Modern on/off switch drawn on a canvas."""

    WIDTH = 48
    HEIGHT = 26

    def __init__(
        self,
        master: tk.Misc,
        *,
        variable: tk.BooleanVar | None = None,
        command: Callable[[], None] | None = None,
        accent: str = "#5B8DEF",
        track_off: str = "#4A4A4A",
        thumb: str = "#FFFFFF",
        bg: str = "#2E2E2E",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=self.WIDTH,
            height=self.HEIGHT,
            highlightthickness=0,
            bd=0,
            bg=bg,
            cursor="hand2",
            **kwargs,
        )
        self._accent = accent
        self._track_off = track_off
        self._thumb = thumb
        self._command = command
        self.variable = variable or tk.BooleanVar(value=False)
        self._pressed = False

        self.variable.trace_add("write", self._on_variable_write)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Leave>", self._on_leave)
        self._draw()

    def _on_variable_write(self, *_args) -> None:
        self._draw()

    def _on_press(self, _event: tk.Event) -> None:
        self._pressed = True
        self._draw()

    def _on_release(self, _event: tk.Event) -> None:
        if self._pressed:
            self.variable.set(not self.variable.get())
            if self._command is not None:
                self._command()
        self._pressed = False
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._pressed = False
        self._draw()

    def _round_track(self, x1: int, y1: int, x2: int, y2: int, color: str) -> None:
        radius = (y2 - y1) // 2
        self.create_oval(x1, y1, x1 + 2 * radius, y2, fill=color, outline=color)
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=color, outline=color)
        self.create_oval(x2 - 2 * radius, y1, x2, y2, fill=color, outline=color)

    def _draw(self) -> None:
        self.delete("all")
        enabled = bool(self.variable.get())
        track = self._accent if enabled else self._track_off
        if self._pressed:
            track = self._accent if enabled else "#555555"

        self._round_track(1, 1, self.WIDTH - 1, self.HEIGHT - 1, track)

        pad = 3
        thumb_d = self.HEIGHT - pad * 2
        x_off = self.WIDTH - pad - thumb_d if enabled else pad
        self.create_oval(
            x_off,
            pad,
            x_off + thumb_d,
            pad + thumb_d,
            fill=self._thumb,
            outline="#E0E0E0" if enabled else "#CCCCCC",
            width=1,
        )
