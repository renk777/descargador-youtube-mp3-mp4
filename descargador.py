from __future__ import annotations

import os
import queue
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


DEFAULT_OUTPUT_DIR = Path(r"C:\Users\kenne\Music\canciones")


def _application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _ffmpeg_location() -> str | None:
    search_dirs = [_application_dir() / "ffmpeg" / "bin"]
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            search_dirs.insert(0, Path(bundle_dir) / "ffmpeg" / "bin")
    for directory in search_dirs:
        if (directory / "ffmpeg.exe").is_file():
            return str(directory)
    if shutil.which("ffmpeg"):
        return None
    return None


class DescargadorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Descargador de YouTube")
        self.root.minsize(820, 620)
        self.root.geometry("980x720")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#0f1722")
        style.configure("Panel.TFrame", background="#141e2c")
        style.configure("Title.TLabel", background="#0f1722", foreground="#f4f7fb",
                        font=("Segoe UI", 21, "bold"))
        style.configure("Subtitle.TLabel", background="#0f1722", foreground="#9aa9bd",
                        font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#141e2c", foreground="#f4f7fb",
                        font=("Segoe UI", 12, "bold"))
        style.configure("Field.TLabel", background="#141e2c", foreground="#b7c5d8",
                        font=("Segoe UI", 9))
        style.configure("Status.TLabel", background="#0f1722", foreground="#9aa9bd")
        style.configure("Primary.TButton", background="#287cf5", foreground="#ffffff",
                        font=("Segoe UI", 10, "bold"), padding=(16, 9))
        style.map("Primary.TButton", background=[("active", "#4590ff")])
        style.configure("Secondary.TButton", background="#1d2a3b", foreground="#dbe7f5",
                        padding=(10, 7))
        style.configure("Dark.TEntry", fieldbackground="#1a2636", foreground="#e5edf7",
                        insertcolor="#ffffff", bordercolor="#30425a", padding=8)
        style.configure("Dark.TCombobox", fieldbackground="#1a2636", foreground="#e5edf7",
                        background="#1a2636", arrowcolor="#9aa9bd")
        style.configure("Dark.TRadiobutton", background="#141e2c", foreground="#dbe7f5")

        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.format_var = tk.StringVar(value="mp3")
        self.status = tk.StringVar(value="Listo para descargar.")
        self.url_vars: list[tk.StringVar] = []
        self.url_entries: list[ttk.Entry] = []
        self.is_downloading = False
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_ui()
        self.root.after(100, self._process_events)

    def _build_ui(self) -> None:
        self.root.configure(bg="#0f1722")
        main = ttk.Frame(self.root, padding=(28, 24), style="App.TFrame")
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        ttk.Label(
            main,
            text="Descargador de YouTube",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            main,
            text=(
                "Descarga tus videos favoritos en MP3 o MP4"
            ),
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 22))

        content = ttk.Frame(main, style="App.TFrame")
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        links_panel = ttk.Frame(content, padding=18, style="Panel.TFrame")
        links_panel.grid(row=0, column=0, sticky="ew")
        links_panel.columnconfigure(0, weight=1)
        ttk.Label(
            links_panel, text="Enlaces de YouTube", style="Section.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            links_panel,
            text="Pega un enlace y aparecerá automáticamente otro campo para añadir más.",
            style="Field.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        self.links_container = ttk.Frame(links_panel, style="Panel.TFrame")
        self.links_container.grid(row=2, column=0, sticky="ew")
        self.links_container.columnconfigure(0, weight=1)
        self._add_url_field()

        options = ttk.Frame(content, padding=(0, 18, 0, 0), style="App.TFrame")
        options.grid(row=1, column=0, sticky="nsew")
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        options.columnconfigure(2, weight=1)
        ttk.Label(options, text="Formato", style="Field.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        ttk.Label(options, text="Carpeta de destino", style="Field.TLabel").grid(
            row=0, column=1, columnspan=2, sticky="w"
        )
        format_frame = ttk.Frame(options, style="Panel.TFrame")
        format_frame.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(6, 0))
        ttk.Radiobutton(
            format_frame,
            text="MP3 (audio)",
            variable=self.format_var,
            value="mp3",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=12, pady=10)
        ttk.Radiobutton(
            format_frame,
            text="MP4 (video)",
            variable=self.format_var,
            value="mp4",
            style="Dark.TRadiobutton",
        ).pack(side=tk.LEFT, padx=12, pady=10)

        folder_frame = ttk.Frame(options, style="Panel.TFrame")
        folder_frame.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(6, 0))
        folder_frame.columnconfigure(0, weight=1)
        ttk.Entry(
            folder_frame, textvariable=self.output_dir, style="Dark.TEntry"
        ).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            folder_frame, text="Buscar...", command=self._choose_folder,
            style="Secondary.TButton"
        ).grid(row=0, column=1, padx=(8, 0))

        self.progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self.progress.grid(row=3, column=0, sticky="ew", pady=(18, 4))
        ttk.Label(main, textvariable=self.status, style="Status.TLabel").grid(
            row=4, column=0, sticky="w"
        )

        buttons = ttk.Frame(main)
        buttons.grid(row=5, column=0, sticky="e", pady=(16, 0))
        ttk.Button(
            buttons, text="Limpiar enlaces", command=self._clear_urls,
            style="Secondary.TButton"
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.download_button = ttk.Button(
            buttons, text="Descargar MP3", command=self._start_download,
            style="Primary.TButton"
        )
        self.download_button.pack(side=tk.RIGHT)
        self.format_var.trace_add("write", self._update_download_button)

        self.url_entries[0].focus_set()

    def _add_url_field(self) -> None:
        variable = tk.StringVar()
        entry = ttk.Entry(
            self.links_container, textvariable=variable, style="Dark.TEntry"
        )
        entry.grid(row=len(self.url_entries), column=0, sticky="ew", pady=3)
        entry.bind("<KeyRelease>", self._on_url_change)
        self.url_vars.append(variable)
        self.url_entries.append(entry)

    def _on_url_change(self, _event: tk.Event[tk.Entry]) -> None:
        if self.url_vars and self.url_vars[-1].get().strip():
            self._add_url_field()

    def _collect_urls(self) -> list[str]:
        return [variable.get().strip() for variable in self.url_vars if variable.get().strip()]

    def _update_download_button(self, *_args: object) -> None:
        self.download_button.configure(
            text="Descargar MP4" if self.format_var.get() == "mp4" else "Descargar MP3"
        )

    def _clear_urls(self) -> None:
        for entry in self.url_entries[1:]:
            entry.destroy()
        self.url_vars = self.url_vars[:1]
        self.url_entries = self.url_entries[:1]
        self.url_vars[0].set("")
        self.status.set("Listo para descargar.")

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Selecciona la carpeta donde guardar los MP3"
        )
        if selected:
            self.output_dir.set(selected)

    def _start_download(self) -> None:
        if yt_dlp is None:
            messagebox.showerror(
                "Falta una dependencia",
                "Instala las dependencias ejecutando:\n\n"
                "python -m pip install -r requirements.txt",
            )
            return

        urls = self._collect_urls()
        invalid_urls = [url for url in urls if not self._is_youtube_url(url)]
        if not urls:
            messagebox.showwarning("Faltan enlaces", "Pega al menos un enlace de YouTube.")
            return
        if invalid_urls:
            messagebox.showerror(
                "Enlace no válido",
                "Estos enlaces no parecen ser de YouTube:\n\n"
                + "\n".join(invalid_urls),
            )
            return

        output = Path(self.output_dir.get().strip()).expanduser()
        if not self.output_dir.get().strip():
            messagebox.showwarning("Falta la carpeta", "Indica una carpeta de destino.")
            return

        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            messagebox.showerror(
                "No se puede usar la carpeta",
                f"No fue posible crear la carpeta de destino:\n{error}",
            )
            return

        self.is_downloading = True
        self.download_button.configure(state=tk.DISABLED)
        self.progress.configure(value=0)
        if self.format_var.get() == "mp4":
            self._choose_video_quality(urls, output)
        else:
            self._begin_download(urls, output)

    def _begin_download(
        self, urls: list[str], output: Path, video_formats: dict[str, int] | None = None
    ) -> None:
        if not _ffmpeg_location():
            messagebox.showerror(
                "Falta FFmpeg",
                "No se encontró FFmpeg. Instálalo y agrégalo al PATH, o coloca "
                "ffmpeg.exe en la carpeta ffmpeg\\bin junto al programa.",
            )
            self.is_downloading = False
            self.download_button.configure(state=tk.NORMAL)
            return
        self.status.set("Iniciando descarga...")
        threading.Thread(
            target=self._download,
            args=(urls, output, video_formats),
            daemon=True,
        ).start()

    def _choose_video_quality(self, urls: list[str], output: Path) -> None:
        choice = messagebox.askyesnocancel(
            "Calidad de video",
            "¿Quieres descargar todos los videos a la máxima calidad disponible?\n\n"
            "Sí: máxima calidad para todos.\n"
            "No: elegir la calidad de cada video individualmente.",
        )
        if choice is None:
            self.is_downloading = False
            self.download_button.configure(state=tk.NORMAL)
        elif choice:
            self._begin_download(urls, output)
        else:
            self.status.set("Consultando calidades disponibles...")
            threading.Thread(
                target=self._get_video_formats,
                args=(urls, output),
                daemon=True,
            ).start()

    def _get_video_formats(self, urls: list[str], output: Path) -> None:
        try:
            formats: dict[str, list[int]] = {}
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as downloader:
                for url in urls:
                    info = downloader.extract_info(url, download=False)
                    entries = info.get("entries") if isinstance(info, dict) else None
                    videos = entries if entries else [info]
                    for video in videos:
                        if not isinstance(video, dict):
                            continue
                        video_url = str(video.get("webpage_url") or video.get("original_url") or url)
                        title = str(video.get("title") or video_url)
                        heights = {
                            int(item["height"])
                            for item in video.get("formats", [])
                            if isinstance(item, dict)
                            and isinstance(item.get("height"), int)
                            and item.get("vcodec") not in {None, "none"}
                        }
                        formats[f"{title}\n{video_url}"] = sorted(heights)
            self.events.put(("video_formats", (output, formats)))
        except Exception as error:
            self.events.put(("error", str(error)))

    def _show_quality_dialog(
        self, output: Path, formats: dict[str, list[int]]
    ) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Elegir calidad por video")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(600, 300)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            frame,
            text="Selecciona una resolución para cada video:",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 10))
        choices: dict[str, tk.StringVar] = {}
        rows = ttk.Frame(frame)
        rows.pack(fill=tk.BOTH, expand=True)
        for key, heights in formats.items():
            title, url = key.split("\n", 1)
            row = ttk.Frame(rows)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=title, width=48).pack(side=tk.LEFT, anchor="w")
            values = [f"{height}p" for height in heights] or ["Mejor disponible"]
            selected = tk.StringVar(value=values[-1])
            choices[url] = selected
            ttk.Combobox(
                row, textvariable=selected, values=values, state="readonly", width=18
            ).pack(side=tk.RIGHT)

        def accept() -> None:
            selected_formats = {
                url: int(value[:-1])
                for url, value in choices.items()
                if value.endswith("p")
            }
            dialog.destroy()
            self._begin_download(list(choices), output, selected_formats)

        def cancel() -> None:
            dialog.destroy()
            self.is_downloading = False
            self.download_button.configure(state=tk.NORMAL)
            self.status.set("Descarga cancelada.")

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(14, 0))
        ttk.Button(buttons, text="Cancelar", command=cancel).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Descargar", command=accept).pack(
            side=tk.RIGHT, padx=(0, 8)
        )
        dialog.protocol("WM_DELETE_WINDOW", cancel)

    @staticmethod
    def _is_youtube_url(value: str) -> bool:
        parsed = urlparse(value)
        host = parsed.netloc.lower().split(":")[0]
        return parsed.scheme in {"http", "https"} and (
            host == "youtu.be"
            or host == "youtube.com"
            or host.endswith(".youtube.com")
        )

    def _download(
        self, urls: list[str], output: Path, video_formats: dict[str, int] | None = None
    ) -> None:
        archive = output / ".youtube-download-archive.txt"
        options: dict[str, object] = {
            "outtmpl": str(output / "%(title)s [%(id)s].%(ext)s"),
            "paths": {"home": str(output)},
            "noplaylist": video_formats is not None,
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
            "continuedl": True,
            "download_archive": str(archive),
            "progress_hooks": [self._progress_hook],
        }
        ffmpeg_location = _ffmpeg_location()
        if ffmpeg_location:
            options["ffmpeg_location"] = ffmpeg_location
        if self.format_var.get() == "mp3":
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        else:
            options["format"] = "bestvideo+bestaudio/best"
            options["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                for url in urls:
                    if video_formats and url in video_formats:
                        format_selector = (
                            f"bestvideo[height<={video_formats[url]}]+"
                            f"bestaudio/best[height<={video_formats[url]}]"
                        )
                        downloader.params["format"] = format_selector
                    self.events.put(("status", f"Procesando: {url}"))
                    downloader.download([url])
        except Exception as error:
            self.events.put(("error", str(error)))
        else:
            self.events.put(("done", None))

    def _progress_hook(self, data: dict[str, object]) -> None:
        state = data.get("status")
        if state == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            if isinstance(total, (int, float)) and total > 0:
                percent = float(downloaded) / float(total) * 100
                self.events.put(("progress", percent))
            filename = os.path.basename(str(data.get("filename", "")))
            self.events.put(("status", f"Descargando: {filename}"))
        elif state == "finished":
            self.events.put(("progress", 100.0))
            self.events.put(("status", "Convirtiendo a MP3..."))

    def _process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "progress":
                    self.progress.configure(value=float(value))
                elif event == "status":
                    self.status.set(str(value))
                elif event == "video_formats":
                    output, formats = value
                    if formats:
                        self._show_quality_dialog(output, formats)
                    else:
                        self.is_downloading = False
                        self.download_button.configure(state=tk.NORMAL)
                        self.status.set("No se encontraron videos para descargar.")
                        messagebox.showwarning(
                            "Sin videos", "No se encontraron videos en los enlaces."
                        )
                elif event == "error":
                    self.is_downloading = False
                    self.download_button.configure(state=tk.NORMAL)
                    self.status.set("La descarga terminó con errores.")
                    messagebox.showerror("Error de descarga", str(value))
                elif event == "done":
                    self.is_downloading = False
                    self.download_button.configure(state=tk.NORMAL)
                    self.progress.configure(value=100)
                    self.status.set("Descarga terminada.")
                    messagebox.showinfo(
                        "Listo", "Los MP3 se guardaron en la carpeta seleccionada."
                    )
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_events)


def main() -> None:
    root = tk.Tk()
    DescargadorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
