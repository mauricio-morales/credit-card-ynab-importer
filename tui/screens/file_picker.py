from pathlib import Path
from typing import Iterable, Optional, Set

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Header, Label
from textual.widgets._directory_tree import DirEntry

from tui.models import ConversionJob, ConversionType


class FilteredDirectoryTree(DirectoryTree):
    def __init__(self, path: str, allowed_extensions: set, **kwargs):
        super().__init__(path, **kwargs)
        self.allowed_extensions = allowed_extensions

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for p in paths:
            if p.is_dir() or p.suffix.lower() in self.allowed_extensions:
                yield p


class FilePickerScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("b", "go_back", "Back"),
    ]

    def __init__(self, conversion_type: ConversionType) -> None:
        super().__init__()
        self.conversion_type = conversion_type
        if conversion_type == ConversionType.BAC:
            self._extensions = {".csv"}
        else:
            self._extensions = {".xls", ".xlsx"}
        self._selected_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label(self._header_text(), id="picker-header")
        yield FilteredDirectoryTree(
            str(Path.home()),
            allowed_extensions=self._extensions,
            id="dir-tree",
        )
        yield Label("No file selected", id="selected-label")
        yield Button("Select This File", id="btn-confirm", disabled=True)
        yield Footer()

    def _header_text(self) -> str:
        if self.conversion_type == ConversionType.BAC:
            return "Select a BAC CSV file:"
        return "Select a Davi/Scotia XLS file:"

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self._selected_path = event.path
        self.query_one("#selected-label", Label).update(str(event.path))
        self.query_one("#btn-confirm", Button).disabled = False

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm" and self._selected_path:
            from tui.screens.progress import ProgressScreen
            job = ConversionJob(self.conversion_type, self._selected_path)
            self.app.switch_screen(ProgressScreen(job))
