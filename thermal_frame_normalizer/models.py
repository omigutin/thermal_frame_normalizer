from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias

ParameterType = Literal["int", "float", "bool", "choice", "path"]
BrowseMode = Literal["open_file", "save_file", "open_dir"]


@dataclass(frozen=True)
class ChoiceOption:
    value: str
    label: str


@dataclass(frozen=True)
class ParameterSpec:
    key: str
    label: str
    param_type: ParameterType
    default: int | float | bool | str
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    options: tuple[ChoiceOption, ...] = field(default_factory=tuple)
    description: str = ""
    browse_mode: BrowseMode | None = None
    browse_title: str = ""
    filetypes: tuple[tuple[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MethodSpec:
    key: str
    label: str
    description: str
    parameters: tuple[ParameterSpec, ...] = field(default_factory=tuple)
    uses_background: bool = True


@dataclass(frozen=True)
class ProcessingResult:
    source: "FrameArray"
    corrected: "FrameArray"
    background: "FrameArray | None"
    info_lines: tuple[str, ...] = field(default_factory=tuple)


FrameArray: TypeAlias = Any
