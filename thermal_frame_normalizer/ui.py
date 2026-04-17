from __future__ import annotations

import base64
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import cv2

from .models import ChoiceOption, ParameterSpec, ProcessingResult
from .batch import BatchRunSummary, run_batch_processing
from .presets import build_preset_payload, load_preset, save_preset
from .processing_core import BACKGROUND_METHODS, CORRECTION_METHODS, OUTPUT_PARAMETERS, process_frame


class ParameterPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, on_change: Callable[[], None]) -> None:
        super().__init__(master)
        self.on_change = on_change
        self.variables: dict[str, tk.Variable] = {}
        self.specs: tuple[ParameterSpec, ...] = ()
        self.choice_maps: dict[str, dict[str, str]] = {}

    def rebuild(self, specs: tuple[ParameterSpec, ...], initial_values: dict[str, Any] | None = None) -> None:
        self.specs = specs
        self.variables.clear()
        self.choice_maps.clear()
        initial_values = initial_values or {}

        for child in self.winfo_children():
            child.destroy()

        self.columnconfigure(0, weight=1)

        grid_row = 0
        for spec in specs:
            label = ttk.Label(self, text=spec.label)
            label.grid(row=grid_row, column=0, sticky="w", padx=(0, 8), pady=(6, 0))

            if spec.param_type in {"int", "float"}:
                self._build_scale(grid_row, spec, initial_values)
            elif spec.param_type == "bool":
                self._build_checkbox(grid_row, spec, initial_values)
            elif spec.param_type == "choice":
                self._build_choice(grid_row, spec, initial_values)
            elif spec.param_type == "path":
                self._build_path_input(grid_row, spec, initial_values)
            else:
                raise ValueError(f"Unsupported parameter type: {spec.param_type}")

            grid_row += 1
            if spec.description:
                hint = ttk.Label(self, text=spec.description, foreground="#5f6368", wraplength=320, justify="left")
                hint.grid(row=grid_row, column=0, columnspan=2, sticky="w", pady=(0, 4))
                grid_row += 1

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for spec in self.specs:
            variable = self.variables[spec.key]
            if spec.param_type == "choice":
                label = str(variable.get())
                result[spec.key] = self.choice_maps[spec.key][label]
            else:
                result[spec.key] = variable.get()
        return result

    def reset_to_defaults(self) -> None:
        for spec in self.specs:
            variable = self.variables[spec.key]
            if spec.param_type == "choice":
                variable.set(self._option_label(spec.options, str(spec.default)))
            else:
                variable.set(spec.default)
        self.on_change()

    def set_values(self, values: dict[str, Any]) -> None:
        for spec in self.specs:
            if spec.key not in values:
                continue
            variable = self.variables[spec.key]
            if spec.param_type == "choice":
                variable.set(self._option_label(spec.options, str(values[spec.key])))
            else:
                variable.set(values[spec.key])
        self.on_change()

    def _build_scale(self, row: int, spec: ParameterSpec, initial_values: dict[str, Any]) -> None:
        variable: tk.Variable
        initial_value = initial_values.get(spec.key, spec.default)
        if spec.param_type == "int":
            variable = tk.IntVar(value=int(initial_value))
        else:
            variable = tk.DoubleVar(value=float(initial_value))

        variable.trace_add("write", self._trace)
        self.variables[spec.key] = variable

        frame = ttk.Frame(self)
        frame.grid(row=row, column=1, sticky="ew", pady=(4, 0))
        frame.columnconfigure(0, weight=1)

        scale = tk.Scale(
            frame,
            variable=variable,
            from_=spec.minimum,
            to=spec.maximum,
            resolution=spec.step,
            orient=tk.HORIZONTAL,
            length=420,
            sliderlength=28,
            showvalue=False,
            command=lambda _value: self.on_change(),
        )
        scale.grid(row=0, column=0, sticky="ew")

        if spec.param_type == "int":
            value_box = ttk.Spinbox(
                frame,
                from_=spec.minimum,
                to=spec.maximum,
                increment=spec.step,
                textvariable=variable,
                width=10,
            )
        else:
            value_box = ttk.Spinbox(
                frame,
                from_=spec.minimum,
                to=spec.maximum,
                increment=spec.step,
                format="%.3f",
                textvariable=variable,
                width=10,
            )
        value_box.grid(row=0, column=1, padx=(10, 0))
        value_box.bind("<KeyRelease>", lambda _event: self.on_change())
        value_box.bind("<<Increment>>", lambda _event: self.on_change())
        value_box.bind("<<Decrement>>", lambda _event: self.on_change())

    def _build_checkbox(self, row: int, spec: ParameterSpec, initial_values: dict[str, Any]) -> None:
        variable = tk.BooleanVar(value=bool(initial_values.get(spec.key, spec.default)))
        variable.trace_add("write", self._trace)
        self.variables[spec.key] = variable

        checkbox = ttk.Checkbutton(self, variable=variable, text="Включено")
        checkbox.grid(row=row, column=1, sticky="w", pady=(4, 0))

    def _build_choice(self, row: int, spec: ParameterSpec, initial_values: dict[str, Any]) -> None:
        labels = [option.label for option in spec.options]
        mapping = {option.label: option.value for option in spec.options}
        self.choice_maps[spec.key] = mapping

        initial_value = str(initial_values.get(spec.key, spec.default))
        variable = tk.StringVar(value=self._option_label(spec.options, initial_value))
        variable.trace_add("write", self._trace)
        self.variables[spec.key] = variable

        combobox = ttk.Combobox(self, textvariable=variable, values=labels, state="readonly")
        combobox.grid(row=row, column=1, sticky="ew", pady=(4, 0))
        combobox.bind("<<ComboboxSelected>>", lambda _event: self.on_change())

    def _build_path_input(self, row: int, spec: ParameterSpec, initial_values: dict[str, Any]) -> None:
        variable = tk.StringVar(value=str(initial_values.get(spec.key, spec.default)))
        variable.trace_add("write", self._trace)
        self.variables[spec.key] = variable

        frame = ttk.Frame(self)
        frame.grid(row=row, column=1, sticky="ew", pady=(4, 0))
        frame.columnconfigure(0, weight=1)

        entry = ttk.Entry(frame, textvariable=variable)
        entry.grid(row=0, column=0, sticky="ew")
        entry.bind("<KeyRelease>", lambda _event: self.on_change())

        browse_button = ttk.Button(frame, text="Выбрать...", command=lambda: self._browse_path(spec, variable))
        browse_button.grid(row=0, column=1, padx=(8, 0))

        clear_button = ttk.Button(frame, text="Очистить", command=lambda: self._clear_path(variable))
        clear_button.grid(row=0, column=2, padx=(8, 0))

    def _trace(self, *_args: object) -> None:
        self.on_change()

    def _browse_path(self, spec: ParameterSpec, variable: tk.StringVar) -> None:
        current_value = variable.get().strip()
        initial_dir = ""
        if current_value:
            path = Path(current_value)
            initial_dir = str(path.parent if path.parent.exists() else Path.cwd())

        if spec.browse_mode == "open_dir":
            selected = filedialog.askdirectory(
                title=spec.browse_title or spec.label,
                initialdir=initial_dir or str(Path.cwd()),
            )
        else:
            selected = filedialog.askopenfilename(
                title=spec.browse_title or spec.label,
                initialdir=initial_dir or str(Path.cwd()),
                filetypes=list(spec.filetypes) if spec.filetypes else [("Все файлы", "*.*")],
            )

        if selected:
            variable.set(selected)
            self.on_change()

    def _clear_path(self, variable: tk.StringVar) -> None:
        variable.set("")
        self.on_change()

    @staticmethod
    def _option_label(options: tuple[ChoiceOption, ...], value: str) -> str:
        for option in options:
            if option.value == value:
                return option.label
        return value


class PreviewPane(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, title: str) -> None:
        super().__init__(master, text=title)
        self.image_label = ttk.Label(self, text="Нет изображения", anchor="center")
        self.image_label.pack(fill="both", expand=True, padx=8, pady=8)
        self.photo: tk.PhotoImage | None = None

    def show_image(self, image: Any) -> None:
        ok, encoded = cv2.imencode(".png", image)
        if not ok:
            self.show_text("Ошибка кодирования предпросмотра")
            return
        image_data = base64.b64encode(encoded.tobytes()).decode("ascii")
        self.photo = tk.PhotoImage(data=image_data)
        self.image_label.configure(image=self.photo, text="")

    def show_text(self, text: str) -> None:
        self.photo = None
        self.image_label.configure(image="", text=text)


class ThermalFrameNormalizerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("thermal_frame_normalizer")
        self.root.geometry("1440x900")
        self.root.minsize(1180, 760)

        self.image_path: Path | None = None
        self.source_frame: Any = None
        self.last_result: ProcessingResult | None = None
        self.render_job: str | None = None
        self.status_reset_job: str | None = None

        self.background_method_var = tk.StringVar(value=next(iter(BACKGROUND_METHODS)))
        self.correction_method_var = tk.StringVar(value=next(iter(CORRECTION_METHODS)))

        self.background_method_var.trace_add("write", self._on_method_changed)
        self.correction_method_var.trace_add("write", self._on_method_changed)

        self._build_layout()
        self._rebuild_parameter_panels()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self.root, padding=12)
        sidebar.grid(row=0, column=0, sticky="ns")

        content = ttk.Frame(self.root, padding=(0, 12, 12, 12))
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        controls = ttk.LabelFrame(sidebar, text="Controls", padding=12)
        controls.pack(fill="x")

        buttons = ttk.Frame(controls)
        buttons.pack(fill="x")

        ttk.Button(buttons, text="Открыть изображение", command=self.open_image).pack(fill="x")
        ttk.Button(buttons, text="Загрузить пресет", command=self.load_preset_dialog).pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Сохранить пресет", command=self.save_preset_dialog).pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Пакетная обработка", command=self.run_batch_dialog).pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Сохранить результат", command=self.save_corrected).pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Сбросить параметры", command=self.reset_visible_parameters).pack(fill="x", pady=(8, 0))

        info_frame = ttk.LabelFrame(controls, text="Изображение", padding=8)
        info_frame.pack(fill="x", pady=(12, 0))
        self.path_var = tk.StringVar(value="Изображение не выбрано")
        self.path_label = ttk.Label(info_frame, textvariable=self.path_var, wraplength=340, justify="left")
        self.path_label.pack(fill="x")

        background_frame = ttk.LabelFrame(controls, text="Оценка фона", padding=8)
        background_frame.pack(fill="x", pady=(12, 0))

        background_values = [spec.label for spec in BACKGROUND_METHODS.values()]
        self.background_selector = ttk.Combobox(background_frame, values=background_values, state="readonly")
        self.background_selector.set(BACKGROUND_METHODS[self.background_method_var.get()].label)
        self.background_selector.pack(fill="x")
        self.background_selector.bind("<<ComboboxSelected>>", self._select_background_method)

        self.background_description = tk.StringVar()
        ttk.Label(
            background_frame,
            textvariable=self.background_description,
            wraplength=340,
            justify="left",
            foreground="#5f6368",
        ).pack(fill="x", pady=(8, 0))

        self.background_params_frame = ttk.Frame(background_frame)
        self.background_params_frame.pack(fill="x", pady=(8, 0))
        self.background_panel = ParameterPanel(self.background_params_frame, on_change=self.schedule_render)
        self.background_panel.pack(fill="x")

        correction_frame = ttk.LabelFrame(controls, text="Метод коррекции", padding=8)
        correction_frame.pack(fill="x", pady=(12, 0))

        correction_values = [spec.label for spec in CORRECTION_METHODS.values()]
        self.correction_selector = ttk.Combobox(correction_frame, values=correction_values, state="readonly")
        self.correction_selector.set(CORRECTION_METHODS[self.correction_method_var.get()].label)
        self.correction_selector.pack(fill="x")
        self.correction_selector.bind("<<ComboboxSelected>>", self._select_correction_method)

        self.correction_description = tk.StringVar()
        ttk.Label(
            correction_frame,
            textvariable=self.correction_description,
            wraplength=340,
            justify="left",
            foreground="#5f6368",
        ).pack(fill="x", pady=(8, 0))

        self.correction_params_frame = ttk.Frame(correction_frame)
        self.correction_params_frame.pack(fill="x", pady=(8, 0))
        self.correction_panel = ParameterPanel(self.correction_params_frame, on_change=self.schedule_render)
        self.correction_panel.pack(fill="x")

        output_frame = ttk.LabelFrame(controls, text="Результат", padding=8)
        output_frame.pack(fill="x", pady=(12, 0))
        self.output_panel = ParameterPanel(output_frame, on_change=self.schedule_render)
        self.output_panel.pack(fill="x")

        summary_frame = ttk.LabelFrame(content, text="Сводка", padding=12)
        summary_frame.grid(row=0, column=0, sticky="ew")
        self.summary_var = tk.StringVar(
            value="Откройте кадр для подстройки коррекции виньетки. При смене метода интерфейс перестраивает набор параметров."
        )
        ttk.Label(summary_frame, textvariable=self.summary_var, justify="left", wraplength=960).pack(fill="x")

        self.status_var = tk.StringVar(value="Готово")
        status_label = ttk.Label(content, textvariable=self.status_var, foreground="#355e3b", anchor="w")
        status_label.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        previews = ttk.Frame(content)
        previews.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        previews.columnconfigure(0, weight=1)
        previews.columnconfigure(1, weight=1)
        previews.columnconfigure(2, weight=1)
        previews.rowconfigure(0, weight=1)

        self.original_preview = PreviewPane(previews, "Исходный кадр")
        self.original_preview.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.background_preview = PreviewPane(previews, "Оценённый фон")
        self.background_preview.grid(row=0, column=1, sticky="nsew", padx=6)

        self.corrected_preview = PreviewPane(previews, "Скорректированный кадр")
        self.corrected_preview.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        self.root.bind("<Configure>", self._on_resize)

    def open_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Открыть термокадр",
            filetypes=[
                ("Изображения", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return

        frame = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if frame is None:
            messagebox.showerror("Открытие изображения", "OpenCV не смог прочитать выбранный файл.")
            return

        self.image_path = Path(path)
        self.source_frame = frame
        self.path_var.set(str(self.image_path))
        self.set_status("Изображение загружено")
        self.schedule_render()

    def save_corrected(self) -> None:
        if self.last_result is None:
            messagebox.showinfo("Сохранение результата", "Сначала загрузите и обработайте изображение.")
            return

        initial_name = "corrected.png"
        if self.image_path is not None:
            initial_name = f"{self.image_path.stem}_corrected.png"

        path = filedialog.asksaveasfilename(
            title="Сохранить скорректированный кадр",
            defaultextension=".png",
            initialfile=initial_name,
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("TIFF", "*.tif")],
        )
        if not path:
            return

        success = cv2.imwrite(path, self.last_result.corrected)
        if not success:
            messagebox.showerror("Сохранение результата", "OpenCV не смог сохранить скорректированный кадр.")
            return

        messagebox.showinfo("Сохранение результата", f"Скорректированный кадр сохранён:\n{path}")

    def save_preset_dialog(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Сохранить пресет",
            defaultextension=".json",
            initialfile="thermal_preset.json",
            filetypes=[("JSON пресет", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return

        payload = self._collect_settings_payload()
        save_preset(path, payload)
        self.set_status("Пресет сохранён")
        messagebox.showinfo("Сохранение пресета", f"Пресет сохранён:\n{path}")

    def load_preset_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="Загрузить пресет",
            filetypes=[("JSON пресет", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return

        try:
            payload = load_preset(path)
            self._apply_preset_payload(payload)
        except Exception as exc:
            messagebox.showerror("Загрузка пресета", f"Не удалось загрузить пресет:\n{exc}")
            return

        if self.source_frame is not None:
            self.set_status("Пресет загружен и применён к текущему изображению")
        else:
            self.set_status("Пресет загружен и готов к применению")
        messagebox.showinfo("Загрузка пресета", f"Пресет загружен:\n{path}")

    def run_batch_dialog(self) -> None:
        initial_dir = str(self.image_path.parent) if self.image_path is not None else str(Path.cwd())
        input_dir = filedialog.askdirectory(title="Выберите входную папку", initialdir=initial_dir)
        if not input_dir:
            return

        output_dir = filedialog.askdirectory(title="Выберите папку для результата", initialdir=input_dir)
        if not output_dir:
            return

        settings = self._collect_processing_settings()
        try:
            summary = run_batch_processing(
                input_dir=input_dir,
                output_dir=output_dir,
                background_method_key=settings["background_method"],
                correction_method_key=settings["correction_method"],
                background_params=settings["background_params"],
                correction_params=settings["correction_params"],
                output_params=settings["output_params"],
            )
        except Exception as exc:
            messagebox.showerror("Пакетная обработка", f"Пакетная обработка завершилась с ошибкой:\n{exc}")
            return

        self.set_status("Пакетная обработка завершена")
        messagebox.showinfo("Пакетная обработка", self._format_batch_summary(summary))

    def reset_visible_parameters(self) -> None:
        self.background_panel.reset_to_defaults()
        self.correction_panel.reset_to_defaults()
        self.output_panel.reset_to_defaults()

    def schedule_render(self, *_args: object) -> None:
        if self.render_job is not None:
            self.root.after_cancel(self.render_job)
        self.render_job = self.root.after(120, self.render_preview)

    def render_preview(self) -> None:
        self.render_job = None
        if self.source_frame is None:
            self.original_preview.show_text("Откройте изображение")
            self.background_preview.show_text("Предпросмотр фона")
            self.corrected_preview.show_text("Предпросмотр результата")
            return

        try:
            result = process_frame(
                frame=self.source_frame,
                background_method_key=self.background_method_var.get(),
                correction_method_key=self.correction_method_var.get(),
                background_params=self.background_panel.values(),
                correction_params=self.correction_panel.values(),
                output_params=self.output_panel.values(),
            )
        except Exception as exc:
            self.summary_var.set(f"Ошибка обработки: {exc}")
            return

        self.last_result = result

        self.original_preview.show_image(self._fit_image(result.source))
        self.corrected_preview.show_image(self._fit_image(result.corrected))

        if result.background is None:
            self.background_preview.show_text("Для этого метода\nоценка фона не используется")
        else:
            background_display = self._normalize_preview(result.background)
            self.background_preview.show_image(self._fit_image(background_display))

        self.summary_var.set("\n".join(result.info_lines))

    def _rebuild_parameter_panels(self) -> None:
        background_values = self.background_panel.values() if self.background_panel.specs else {}
        correction_values = self.correction_panel.values() if self.correction_panel.specs else {}
        output_values = self.output_panel.values() if self.output_panel.specs else {}

        background_spec = BACKGROUND_METHODS[self.background_method_var.get()]
        correction_spec = CORRECTION_METHODS[self.correction_method_var.get()]

        self.background_description.set(background_spec.description)
        self.correction_description.set(correction_spec.description)
        self._sync_method_selectors()

        self.background_panel.rebuild(background_spec.parameters, background_values)
        self.correction_panel.rebuild(correction_spec.parameters, correction_values)
        self.output_panel.rebuild(OUTPUT_PARAMETERS, output_values)
        self.schedule_render()

    def _on_method_changed(self, *_args: object) -> None:
        self._rebuild_parameter_panels()

    def _select_background_method(self, _event: object) -> None:
        label = self.background_selector.get()
        for key, spec in BACKGROUND_METHODS.items():
            if spec.label == label:
                self.background_method_var.set(key)
                break

    def _select_correction_method(self, _event: object) -> None:
        label = self.correction_selector.get()
        for key, spec in CORRECTION_METHODS.items():
            if spec.label == label:
                self.correction_method_var.set(key)
                break

    def _sync_method_selectors(self) -> None:
        self.background_selector.set(BACKGROUND_METHODS[self.background_method_var.get()].label)
        self.correction_selector.set(CORRECTION_METHODS[self.correction_method_var.get()].label)

    def _on_resize(self, _event: object) -> None:
        if self.source_frame is not None:
            self.schedule_render()

    def _fit_image(self, image: Any) -> Any:
        pane_width = max(self.corrected_preview.winfo_width() - 20, 260)
        pane_height = max(self.corrected_preview.winfo_height() - 40, 220)

        height, width = image.shape[:2]
        scale = min(pane_width / width, pane_height / height)
        scale = max(scale, 0.1)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        return cv2.resize(image, new_size, interpolation=interpolation)

    @staticmethod
    def _normalize_preview(image: Any) -> Any:
        return cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype("uint8")

    def _collect_processing_settings(self) -> dict[str, Any]:
        return {
            "background_method": self.background_method_var.get(),
            "correction_method": self.correction_method_var.get(),
            "background_params": self.background_panel.values(),
            "correction_params": self.correction_panel.values(),
            "output_params": self.output_panel.values(),
        }

    def _collect_settings_payload(self) -> dict[str, Any]:
        settings = self._collect_processing_settings()
        return build_preset_payload(
            background_method=settings["background_method"],
            correction_method=settings["correction_method"],
            background_params=settings["background_params"],
            correction_params=settings["correction_params"],
            output_params=settings["output_params"],
        )

    def _apply_preset_payload(self, payload: dict[str, Any]) -> None:
        background_method = str(payload["background_method"])
        correction_method = str(payload["correction_method"])

        if background_method not in BACKGROUND_METHODS:
            raise ValueError(f"Unknown background method in preset: {background_method}")
        if correction_method not in CORRECTION_METHODS:
            raise ValueError(f"Unknown correction method in preset: {correction_method}")

        self.background_method_var.set(background_method)
        self.correction_method_var.set(correction_method)
        self.background_panel.set_values(payload.get("background_params", {}))
        self.correction_panel.set_values(payload.get("correction_params", {}))
        self.output_panel.set_values(payload.get("output_params", {}))
        self.schedule_render()

    @staticmethod
    def _format_batch_summary(summary: BatchRunSummary) -> str:
        lines = [
            f"Файлов во входной папке: {summary.total_files}",
            f"Успешно обработано: {summary.processed_files}",
            f"Ошибок: {summary.failed_files}",
            f"Папка результата: {summary.output_dir}",
        ]
        if summary.total_files == 0:
            lines.append("В выбранной папке не найдено поддерживаемых файлов изображений.")
        elif summary.errors:
            lines.append("")
            lines.append("Ошибки:")
            lines.extend(summary.errors[:8])
            if len(summary.errors) > 8:
                lines.append(f"... и ещё {len(summary.errors) - 8}")
        return "\n".join(lines)

    def set_status(self, message: str, timeout_ms: int = 5000) -> None:
        self.status_var.set(message)
        if self.status_reset_job is not None:
            self.root.after_cancel(self.status_reset_job)
        if timeout_ms > 0:
            self.status_reset_job = self.root.after(timeout_ms, lambda: self.status_var.set("Готово"))


def launch_app() -> None:
    root = tk.Tk()
    ThermalFrameNormalizerApp(root)
    root.mainloop()


__all__ = ["launch_app", "ThermalFrameNormalizerApp"]
