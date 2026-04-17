from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .models import ChoiceOption, MethodSpec, ParameterSpec, ProcessingResult

OUTPUT_PARAMETERS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        key="auto_stretch",
        label="Авторастяжение контраста",
        param_type="bool",
        default=True,
        description="Растянуть результат по процентилям после коррекции.",
    ),
    ParameterSpec(
        key="low_percentile",
        label="Нижний процентиль",
        param_type="float",
        default=1.0,
        minimum=0.0,
        maximum=20.0,
        step=0.1,
        description="Нижний процентиль для растяжения.",
    ),
    ParameterSpec(
        key="high_percentile",
        label="Верхний процентиль",
        param_type="float",
        default=99.0,
        minimum=80.0,
        maximum=100.0,
        step=0.1,
        description="Верхний процентиль для растяжения.",
    ),
)

BACKGROUND_METHODS: dict[str, MethodSpec] = {
    "gaussian": MethodSpec(
        key="gaussian",
        label="Gaussian blur",
        description="Плавная оценка низкочастотной виньетки большим гауссовым размытием.",
        parameters=(
            ParameterSpec(
                key="pre_blur_kernel",
                label="Ядро предразмытия",
                param_type="int",
                default=5,
                minimum=1,
                maximum=31,
                step=2,
                description="Небольшое подавление шума перед оценкой фона.",
            ),
            ParameterSpec(
                key="pre_blur_sigma",
                label="Sigma предразмытия",
                param_type="float",
                default=0.0,
                minimum=0.0,
                maximum=15.0,
                step=0.1,
                description="Параметр sigma для предварительного размытия.",
            ),
            ParameterSpec(
                key="background_kernel",
                label="Ядро фона",
                param_type="int",
                default=151,
                minimum=3,
                maximum=401,
                step=2,
                description="Основное ядро, моделирующее поле виньетки.",
            ),
            ParameterSpec(
                key="background_sigma",
                label="Sigma фона",
                param_type="float",
                default=0.0,
                minimum=0.0,
                maximum=60.0,
                step=0.5,
                description="Дополнительная sigma для размытия фона.",
            ),
            ParameterSpec(
                key="background_floor",
                label="Нижняя граница фона",
                param_type="float",
                default=1.0,
                minimum=0.1,
                maximum=50.0,
                step=0.1,
                description="Защита от слишком сильного усиления на тёмных пикселях.",
            ),
        ),
    ),
    "morphology": MethodSpec(
        key="morphology",
        label="MorphologyEx",
        description="Использует морфологическую фильтрацию для оценки плавного поля освещённости.",
        parameters=(
            ParameterSpec(
                key="pre_blur_kernel",
                label="Ядро предразмытия",
                param_type="int",
                default=5,
                minimum=1,
                maximum=31,
                step=2,
                description="Небольшое подавление шума перед морфологией.",
            ),
            ParameterSpec(
                key="morph_operation",
                label="Операция",
                param_type="choice",
                default="close",
                options=(
                    ChoiceOption("open", "Открытие"),
                    ChoiceOption("close", "Закрытие"),
                ),
                description="Открытие подавляет мелкие яркие детали, закрытие подавляет мелкие тёмные.",
            ),
            ParameterSpec(
                key="morph_shape",
                label="Форма ядра",
                param_type="choice",
                default="ellipse",
                options=(
                    ChoiceOption("ellipse", "Эллипс"),
                    ChoiceOption("rect", "Прямоугольник"),
                    ChoiceOption("cross", "Крест"),
                ),
                description="Форма структурирующего элемента.",
            ),
            ParameterSpec(
                key="morph_kernel",
                label="Размер ядра",
                param_type="int",
                default=61,
                minimum=3,
                maximum=301,
                step=2,
                description="Размер структурирующего элемента для morphologyEx.",
            ),
            ParameterSpec(
                key="morph_iterations",
                label="Итерации",
                param_type="int",
                default=1,
                minimum=1,
                maximum=5,
                step=1,
                description="Сколько раз повторять морфологическую операцию.",
            ),
            ParameterSpec(
                key="post_blur_kernel",
                label="Ядро постразмытия",
                param_type="int",
                default=21,
                minimum=1,
                maximum=101,
                step=2,
                description="Дополнительное сглаживание после морфологии.",
            ),
            ParameterSpec(
                key="background_floor",
                label="Нижняя граница фона",
                param_type="float",
                default=1.0,
                minimum=0.1,
                maximum=50.0,
                step=0.1,
                description="Защита от слишком сильного усиления на тёмных пикселях.",
            ),
        ),
    ),
}

CORRECTION_METHODS: dict[str, MethodSpec] = {
    "gain": MethodSpec(
        key="gain",
        label="Мультипликативная коррекция",
        description="Мультипликативная нормализация, близкая к вашему текущему OpenCV-коду.",
        parameters=(
            ParameterSpec(
                key="strength",
                label="Сила эффекта",
                param_type="float",
                default=1.0,
                minimum=0.0,
                maximum=2.0,
                step=0.05,
                description="Насколько сильно применять рассчитанное поле усиления.",
            ),
            ParameterSpec(
                key="gain_min",
                label="Минимальный gain",
                param_type="float",
                default=0.75,
                minimum=0.1,
                maximum=1.5,
                step=0.01,
                description="Нижнее ограничение gain, чтобы не переусилить затемнение.",
            ),
            ParameterSpec(
                key="gain_max",
                label="Максимальный gain",
                param_type="float",
                default=1.35,
                minimum=1.0,
                maximum=4.0,
                step=0.01,
                description="Верхнее ограничение gain, чтобы не раздувать шум.",
            ),
        ),
    ),
    "subtract": MethodSpec(
        key="subtract",
        label="Вычитание фона",
        description="Аддитивная коррекция, когда виньетка похожа скорее на смещение, чем на масштабирование.",
        parameters=(
            ParameterSpec(
                key="strength",
                label="Сила эффекта",
                param_type="float",
                default=1.0,
                minimum=0.0,
                maximum=2.0,
                step=0.05,
                description="Насколько сильно вычитать отклонение фона.",
            ),
        ),
    ),
    "homomorphic": MethodSpec(
        key="homomorphic",
        label="Гомоморфная коррекция",
        description="Корректирует мультипликативную неравномерность в логарифмическом пространстве.",
        parameters=(
            ParameterSpec(
                key="strength",
                label="Сила эффекта",
                param_type="float",
                default=1.0,
                minimum=0.0,
                maximum=2.0,
                step=0.05,
                description="Насколько сильно убирать низкочастотную неравномерность в лог-пространстве.",
            ),
        ),
    ),
    "clahe": MethodSpec(
        key="clahe",
        label="Только CLAHE",
        description="Локальное усиление контраста без явной оценки фона.",
        parameters=(
            ParameterSpec(
                key="clip_limit",
                label="Порог clip limit",
                param_type="float",
                default=2.0,
                minimum=0.5,
                maximum=10.0,
                step=0.1,
                description="Ограничение контраста для CLAHE.",
            ),
            ParameterSpec(
                key="tile_grid",
                label="Размер сетки",
                param_type="int",
                default=8,
                minimum=2,
                maximum=32,
                step=1,
                description="Размер сетки плиток для CLAHE.",
            ),
        ),
        uses_background=False,
    ),
}


def process_frame(
    frame: np.ndarray,
    background_method_key: str,
    correction_method_key: str,
    background_params: dict[str, Any],
    correction_params: dict[str, Any],
    output_params: dict[str, Any],
) -> ProcessingResult:
    source = prepare_grayscale(frame)
    correction_spec = CORRECTION_METHODS[correction_method_key]

    background = None
    if correction_spec.uses_background:
        background = estimate_background(source, background_method_key, background_params)

    corrected = apply_correction(source, background, correction_method_key, correction_params)
    corrected = postprocess_output(corrected, output_params)

    info_lines = build_info_lines(source, background, corrected, background_method_key, correction_method_key)
    return ProcessingResult(source=source, corrected=corrected, background=background, info_lines=info_lines)


def prepare_grayscale(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    frame_f = frame.astype(np.float32)
    min_value = float(np.min(frame_f))
    max_value = float(np.max(frame_f))

    if max_value - min_value < 1e-6:
        return np.zeros_like(frame_f, dtype=np.uint8)

    normalized = (frame_f - min_value) / (max_value - min_value)
    return np.clip(normalized * 255.0, 0.0, 255.0).astype(np.uint8)


def estimate_background(frame: np.ndarray, method_key: str, params: dict[str, Any]) -> np.ndarray:
    frame_f = frame.astype(np.float32)

    if method_key == "gaussian":
        pre_blur = apply_gaussian(frame_f, params["pre_blur_kernel"], params["pre_blur_sigma"])
        background = apply_gaussian(pre_blur, params["background_kernel"], params["background_sigma"])
    elif method_key == "morphology":
        pre_blur = apply_gaussian(frame_f, params["pre_blur_kernel"], 0.0)
        kernel = cv2.getStructuringElement(
            _morph_shape(params["morph_shape"]),
            (_odd(params["morph_kernel"]), _odd(params["morph_kernel"])),
        )
        operation = cv2.MORPH_OPEN if params["morph_operation"] == "open" else cv2.MORPH_CLOSE
        background = cv2.morphologyEx(
            pre_blur,
            operation,
            kernel,
            iterations=int(params["morph_iterations"]),
        )
        background = apply_gaussian(background, params["post_blur_kernel"], 0.0)
    else:
        raise KeyError(f"Unknown background method: {method_key}")

    return np.clip(background, float(params["background_floor"]), None)


def apply_correction(
    source: np.ndarray,
    background: np.ndarray | None,
    method_key: str,
    params: dict[str, Any],
) -> np.ndarray:
    source_f = source.astype(np.float32)

    if method_key == "gain":
        if background is None:
            raise ValueError("Background is required for flat-field gain correction.")
        background_mean = float(np.mean(background))
        gain = background_mean / background
        gain = 1.0 + (gain - 1.0) * float(params["strength"])
        gain = np.clip(gain, float(params["gain_min"]), float(params["gain_max"]))
        corrected = source_f * gain
    elif method_key == "subtract":
        if background is None:
            raise ValueError("Background is required for subtraction correction.")
        background_mean = float(np.mean(background))
        corrected = source_f - float(params["strength"]) * (background - background_mean)
    elif method_key == "homomorphic":
        if background is None:
            raise ValueError("Background is required for homomorphic correction.")
        safe_source = np.log1p(source_f)
        safe_background = np.log1p(background)
        background_mean = float(np.mean(safe_background))
        corrected_log = safe_source - float(params["strength"]) * (safe_background - background_mean)
        corrected = np.expm1(corrected_log)
    elif method_key == "clahe":
        tile = max(2, int(params["tile_grid"]))
        clahe = cv2.createCLAHE(
            clipLimit=float(params["clip_limit"]),
            tileGridSize=(tile, tile),
        )
        corrected = clahe.apply(source.astype(np.uint8)).astype(np.float32)
    else:
        raise KeyError(f"Unknown correction method: {method_key}")

    return np.clip(corrected, 0.0, 255.0)


def postprocess_output(frame: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    corrected = frame.astype(np.float32)

    if bool(params["auto_stretch"]):
        low = float(np.percentile(corrected, float(params["low_percentile"])))
        high = float(np.percentile(corrected, float(params["high_percentile"])))
        if high - low > 1e-6:
            corrected = (corrected - low) * (255.0 / (high - low))

    return np.clip(corrected, 0.0, 255.0).astype(np.uint8)


def build_info_lines(
    source: np.ndarray,
    background: np.ndarray | None,
    corrected: np.ndarray,
    background_method_key: str,
    correction_method_key: str,
) -> tuple[str, ...]:
    correction_spec = CORRECTION_METHODS[correction_method_key]
    background_spec = BACKGROUND_METHODS[background_method_key]

    lines = [
        f"Исходный кадр: min={int(source.min())}, max={int(source.max())}, mean={source.mean():.2f}",
        f"Метод коррекции: {correction_spec.label}",
    ]
    if correction_spec.uses_background and background is not None:
        lines.append(
            f"Фон: {background_spec.label}, min={background.min():.2f}, max={background.max():.2f}, mean={background.mean():.2f}"
        )
    else:
        lines.append("Фон: для выбранного метода не используется")
    lines.append(
        f"Результат: min={int(corrected.min())}, max={int(corrected.max())}, mean={corrected.mean():.2f}"
    )
    return tuple(lines)


def apply_gaussian(frame: np.ndarray, kernel_size: int, sigma: float) -> np.ndarray:
    kernel_size = _odd(kernel_size)
    if kernel_size <= 1:
        return frame.copy()
    return cv2.GaussianBlur(frame, (kernel_size, kernel_size), float(sigma))


def _odd(value: int | float) -> int:
    kernel = max(1, int(round(float(value))))
    return kernel if kernel % 2 == 1 else kernel + 1


def _morph_shape(shape: str) -> int:
    return {
        "rect": cv2.MORPH_RECT,
        "ellipse": cv2.MORPH_ELLIPSE,
        "cross": cv2.MORPH_CROSS,
    }[shape]
