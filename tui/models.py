from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from textual.message import Message


class ConversionType(Enum):
    BAC = "bac"
    DAVI = "davi"


@dataclass
class ConversionJob:
    conversion_type: ConversionType
    source_path: Path


@dataclass
class ConversionResult:
    success: bool
    transaction_count: int
    output_files: list
    warnings: list = field(default_factory=list)
    error_message: str = ""
    conversion_type: ConversionType = None


class ProgressUpdate(Message):
    def __init__(self, text: str, step: int, total_steps: int) -> None:
        super().__init__()
        self.text = text
        self.step = step
        self.total_steps = total_steps
