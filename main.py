from __future__ import annotations

import io
import tkinter as tk
from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image
from tkinterdnd2 import DND_FILES, TkinterDnD

from preview_view import ImageViewport
from toggle_switch import ToggleSwitch
from worker import pixelize_bytes

ACCENT = "#5B8DEF"
ACCENT_HOVER = "#4A7AD9"
BG = "#1A1A1A"
SURFACE = "#242424"
CARD = "#2E2E2E"
TEXT = "#F0F0F0"
MUTED = "#888888"

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg"}
PREVIEW_DEBOUNCE_MS = 80
FULL_RESULT_DEBOUNCE_MS = 400
LIVE_PROCESS_MAX = (1280, 1280)
PLACEHOLDER = "Drop a PNG or JPEG here\n\nor click Upload"


class PixelizerApp(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Pixelizer")
        self.geometry("1060x720")
        self.minsize(920, 640)
        self.configure(bg=BG)

        self.source_image: Image.Image | None = None
        self.result_image: Image.Image | None = None
        self.display_image: Image.Image | None = None
        self.source_path: str | None = None
        self._source_bytes: bytes | None = None
        self._live_bytes: bytes | None = None

        self._preview_job: str | None = None
        self._full_result_job: str | None = None
        self._render_generation = 0
        self._live_future: Future[bytes] | None = None
        self._full_future: Future[bytes] | None = None
        self._pool = ProcessPoolExecutor(max_workers=1)
        self._compare_mode = False

        self._setup_styles()
        self._build_ui()
        self._show_placeholder()
        self.after(100, self._poll_futures)

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, troughcolor=CARD, bordercolor=CARD)
        style.configure("TFrame", background=BG)
        style.configure("Sidebar.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Sidebar.TLabel", background=SURFACE, foreground=TEXT)
        style.configure("Muted.TLabel", background=SURFACE, foreground=MUTED)
        style.configure("Title.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 24, "bold"))
        style.configure("Section.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 11, "bold"))
        style.configure("Horizontal.TScale", background=SURFACE)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=280)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        header = ttk.Frame(sidebar, style="Sidebar.TFrame")
        header.pack(fill="x", padx=24, pady=(28, 28))
        ttk.Label(header, text="Pixelizer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="PNG · JPEG", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))

        controls = ttk.Frame(sidebar, style="Sidebar.TFrame")
        controls.pack(fill="x", padx=24)

        ttk.Label(controls, text="Pixelation level", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        level_row = ttk.Frame(controls, style="Sidebar.TFrame")
        level_row.pack(fill="x", pady=(0, 6))

        self.level_var = tk.IntVar(value=40)
        self.level_spin = tk.Spinbox(
            level_row,
            from_=1,
            to=100,
            width=4,
            justify="center",
            textvariable=self.level_var,
            font=("Consolas", 15, "bold"),
            fg=ACCENT,
            bg=SURFACE,
            insertbackground=ACCENT,
            relief="flat",
            buttonbackground=SURFACE,
            highlightthickness=1,
            highlightbackground="#3A3A3A",
        )
        self.level_spin.pack(side="right")
        self.level_spin.bind("<Return>", self._commit_level)
        self.level_spin.bind("<FocusOut>", self._commit_level)

        self.level_slider = tk.Scale(
            controls,
            from_=1,
            to=100,
            orient="horizontal",
            variable=self.level_var,
            command=self._on_level_change,
            showvalue=0,
            resolution=1,
            bg=SURFACE,
            fg=TEXT,
            troughcolor=CARD,
            activebackground=ACCENT,
            highlightthickness=0,
            sliderlength=18,
            relief="flat",
        )
        self.level_slider.pack(fill="x", pady=(0, 20))

        smooth_card = tk.Frame(controls, bg=CARD, padx=14, pady=12)
        smooth_card.pack(fill="x", pady=(0, 16))

        smooth_text = tk.Frame(smooth_card, bg=CARD)
        smooth_text.pack(side="left", fill="x", expand=True)
        tk.Label(smooth_text, text="Smoothing", bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(
            smooth_text,
            text="Soft blocks instead of sharp pixels",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        self.smooth_var = tk.BooleanVar(value=False)
        ToggleSwitch(
            smooth_card,
            variable=self.smooth_var,
            command=self._on_smooth_change,
            accent=ACCENT,
            bg=CARD,
        ).pack(side="right")

        self.compare_btn = tk.Button(
            controls,
            text="Compare",
            font=("Segoe UI", 11),
            bg="#3A3A3A",
            fg=TEXT,
            activebackground="#4A4A4A",
            activeforeground=TEXT,
            relief="flat",
            padx=12,
            pady=10,
            cursor="hand2",
            command=self._toggle_compare,
        )
        self.compare_btn.pack(fill="x", pady=(0, 8))

        self.upload_btn = tk.Button(
            controls,
            text="Upload",
            font=("Segoe UI", 11),
            bg="#3A3A3A",
            fg=TEXT,
            activebackground="#4A4A4A",
            activeforeground=TEXT,
            relief="flat",
            padx=12,
            pady=10,
            cursor="hand2",
            command=self.upload_image,
        )
        self.upload_btn.pack(fill="x", pady=(0, 8))

        self.save_btn = tk.Button(
            controls,
            text="Save",
            font=("Segoe UI", 11),
            bg="#3A3A3A",
            fg=TEXT,
            activebackground="#4A4A4A",
            activeforeground=TEXT,
            relief="flat",
            padx=12,
            pady=10,
            cursor="hand2",
            state="disabled",
            command=self.save_image,
        )
        self.save_btn.pack(fill="x")

        self.status_var = tk.StringVar(value="Upload an image or drop a file onto the preview")
        ttk.Label(sidebar, textvariable=self.status_var, style="Muted.TLabel", wraplength=230).pack(
            side="bottom", anchor="w", padx=24, pady=24
        )

        main = ttk.Frame(self)
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self.preview_card = tk.Frame(main, bg=CARD, highlightbackground="#3A3A3A", highlightthickness=1)
        self.preview_card.grid(row=0, column=0, sticky="nsew")
        self.preview_card.grid_rowconfigure(0, weight=1)
        self.preview_card.grid_columnconfigure(0, weight=1)

        self.single_view = ImageViewport(self.preview_card)
        self.single_view.pack(fill="both", expand=True)

        self.split_frame = tk.Frame(self.preview_card, bg=CARD)
        self.split_frame.grid_rowconfigure(0, weight=1)
        self.split_frame.grid_columnconfigure(0, weight=1)
        self.split_frame.grid_columnconfigure(2, weight=1)

        self.processed_view = ImageViewport(self.split_frame, corner_label="Processed")
        self.processed_view.grid(row=0, column=0, sticky="nsew")
        tk.Frame(self.split_frame, width=1, bg="#3A3A3A").grid(row=0, column=1, sticky="ns")
        self.original_view = ImageViewport(self.split_frame, corner_label="Original")
        self.original_view.grid(row=0, column=2, sticky="nsew")

        self.processed_view.set_sync_peers([self.original_view])
        self.original_view.set_sync_peers([self.processed_view])

        self.preview_card.drop_target_register(DND_FILES)
        self.preview_card.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event) -> None:
        paths = [path.strip("{}") for path in self.tk.splitlist(event.data)]
        if paths:
            self._load_image_from_path(paths[0])

    def _commit_level(self, _event: tk.Event | None = None) -> str | None:
        try:
            level = int(self.level_var.get())
        except (tk.TclError, ValueError):
            level = 40
        level = max(1, min(100, level))
        self.level_var.set(level)
        self._schedule_live_preview()
        return "break"

    def _on_level_change(self, _value: str) -> None:
        self._schedule_live_preview()

    def _on_smooth_change(self) -> None:
        self._schedule_live_preview()

    def _toggle_compare(self) -> None:
        self._compare_mode = not self._compare_mode
        if self._compare_mode:
            self.single_view.pack_forget()
            self.split_frame.pack(fill="both", expand=True)
            self.compare_btn.configure(bg=ACCENT, fg="white", activebackground=ACCENT_HOVER)
        else:
            self.split_frame.pack_forget()
            self.single_view.pack(fill="both", expand=True)
            self.compare_btn.configure(bg="#3A3A3A", fg=TEXT, activebackground="#4A4A4A")
        self.update_idletasks()
        self._refresh_preview(force=True)

    def _cancel_job(self, attr: str) -> None:
        job = getattr(self, attr)
        if job is not None:
            self.after_cancel(job)
            setattr(self, attr, None)

    def _schedule_live_preview(self) -> None:
        if self._source_bytes is None:
            return
        self._cancel_job("_preview_job")
        self._cancel_job("_full_result_job")
        self._preview_job = self.after(PREVIEW_DEBOUNCE_MS, self._run_live_preview)
        self._full_result_job = self.after(FULL_RESULT_DEBOUNCE_MS, self._run_full_result)

    def _current_settings(self) -> tuple[int, bool]:
        try:
            level = int(self.level_var.get())
        except (tk.TclError, ValueError):
            level = 40
        return max(1, min(100, level)), bool(self.smooth_var.get())

    def _run_live_preview(self) -> None:
        self._preview_job = None
        if self._live_bytes is None:
            return
        self._render_generation += 1
        generation = self._render_generation
        level, smooth = self._current_settings()
        self._live_future = self._pool.submit(pixelize_bytes, self._live_bytes, level, smooth)
        self._live_future.generation = generation  # type: ignore[attr-defined]
        self._live_future.mode = "live"  # type: ignore[attr-defined]

    def _run_full_result(self) -> None:
        self._full_result_job = None
        if self._source_bytes is None:
            return
        level, smooth = self._current_settings()
        self._full_future = self._pool.submit(pixelize_bytes, self._source_bytes, level, smooth)
        self._full_future.generation = self._render_generation  # type: ignore[attr-defined]
        self._full_future.mode = "full"  # type: ignore[attr-defined]

    def _poll_futures(self) -> None:
        for future in (self._live_future, self._full_future):
            if future is None or not future.done():
                continue
            try:
                png_bytes = future.result()
            except Exception:
                continue

            generation = getattr(future, "generation", 0)
            mode = getattr(future, "mode", "live")
            if mode == "live" and generation != self._render_generation:
                continue

            try:
                image = Image.open(io.BytesIO(png_bytes))
                image.load()
            except OSError:
                continue

            self.display_image = image
            if mode == "full":
                self.result_image = image
                self.save_btn.configure(state="normal")
                level, smooth = self._current_settings()
                self._update_status(level, smooth, processing=False)
            else:
                level, smooth = self._current_settings()
                self._update_status(level, smooth, processing=True)

            self._refresh_preview()

            if future is self._live_future:
                self._live_future = None
            if future is self._full_future:
                self._full_future = None

        self.after(50, self._poll_futures)

    def _refresh_preview(self, *, force: bool = False) -> None:
        if self._compare_mode:
            if not force and self.display_image is not None and self.processed_view.has_image:
                self.processed_view.update_image(self.display_image)
            else:
                self.processed_view.set_image(self.display_image, placeholder=PLACEHOLDER)

            if not force and self.source_image is not None and self.original_view.has_image:
                self.original_view.update_image(self.source_image)
            else:
                self.original_view.set_image(self.source_image, placeholder=PLACEHOLDER)
        elif not force and self.display_image is not None and self.single_view.has_image:
            self.single_view.update_image(self.display_image)
        else:
            self.single_view.set_image(self.display_image, placeholder=PLACEHOLDER)

    def _update_status(self, level: int, smooth: bool, *, processing: bool) -> None:
        mode = "smooth" if smooth else "sharp"
        name = Path(self.source_path).name if self.source_path else "image"
        suffix = " · rendering…" if processing else ""
        self.status_var.set(f"{name} · level {level} · {mode}{suffix}")

    def _show_placeholder(self) -> None:
        self.display_image = None
        self._refresh_preview()

    def _set_source_image(self, image: Image.Image, path: str) -> None:
        self.source_image = image
        self.result_image = None
        self.display_image = None
        self.source_path = path

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        self._source_bytes = buffer.getvalue()

        live = image.copy()
        live.thumbnail(LIVE_PROCESS_MAX, Image.Resampling.LANCZOS)
        live_buffer = io.BytesIO()
        live.save(live_buffer, format="PNG")
        self._live_bytes = live_buffer.getvalue()

        self.save_btn.configure(state="disabled")
        self.status_var.set(f"Loaded: {Path(path).name}")
        self._refresh_preview()
        self._schedule_live_preview()

    def _load_image_from_path(self, path: str) -> bool:
        suffix = Path(path).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            messagebox.showwarning("Unsupported file", "Please use a PNG or JPEG image.")
            return False

        try:
            image = Image.open(path)
            image.load()
        except OSError as exc:
            messagebox.showerror("Error", f"Could not open the file:\n{exc}")
            return False

        self._set_source_image(image, path)
        return True

    def upload_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.PNG *.JPG *.JPEG"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._load_image_from_path(path)

    def save_image(self) -> None:
        if self.result_image is None:
            messagebox.showwarning("No result", "Load an image and adjust the slider to generate a result.")
            return

        default_ext = ".png"
        if self.source_path and self.source_path.lower().endswith((".jpg", ".jpeg")):
            default_ext = ".jpg"

        path = filedialog.asksaveasfilename(
            title="Save result",
            defaultextension=default_ext,
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All files", "*.*")],
        )
        if not path:
            return

        image = self.result_image.copy()
        save_kwargs: dict = {}
        if path.lower().endswith((".jpg", ".jpeg")):
            if image.mode == "RGBA":
                bg = Image.new("RGB", image.size, (255, 255, 255))
                bg.paste(image, mask=image.split()[3])
                image = bg
            elif image.mode != "RGB":
                image = image.convert("RGB")
            save_kwargs["quality"] = 95

        try:
            image.save(path, **save_kwargs)
        except OSError as exc:
            messagebox.showerror("Error", f"Could not save the file:\n{exc}")
            return

        self.status_var.set(f"Saved: {Path(path).name}")
        messagebox.showinfo("Done", f"File saved:\n{path}")

    def destroy(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
        super().destroy()


def main() -> None:
    import multiprocessing

    multiprocessing.freeze_support()
    app = PixelizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
