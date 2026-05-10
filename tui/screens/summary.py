from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label

from tui.models import ConversionResult


class SummaryScreen(Screen):
    BINDINGS = [
        ("c", "convert_another", "Convert Another"),
        ("q", "quit", "Quit"),
        ("r", "try_again", "Try Again"),
        ("s", "start_over", "Start Over"),
    ]

    def __init__(self, result: ConversionResult) -> None:
        super().__init__()
        self.result = result

    def check_action(self, action: str, parameters: tuple) -> Optional[bool]:
        if self.result.success:
            if action in ("try_again", "start_over"):
                return False
        else:
            if action in ("convert_another", "quit"):
                return False
        return True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        if self.result.success:
            yield from self._compose_success()
        else:
            yield from self._compose_error()
        yield Footer()

    def _compose_success(self):
        yield Label(
            f"✓ {self.result.transaction_count} transactions converted",
            id="count-label",
        )
        yield Label("Output files:", id="output-header")
        for path in self.result.output_files:
            yield Label(str(path), classes="output-path")
        if self.result.warnings:
            yield Label("Warnings:", id="warn-header")
            for w in self.result.warnings:
                yield Label(f"• {w}", classes="warning")
        yield Button("Convert Another", id="btn-convert-another", variant="primary")
        yield Button("Quit", id="btn-quit", variant="default")

    def _compose_error(self):
        yield Label("✗ Conversion failed", id="error-title")
        yield Label(self.result.error_message, id="error-message")
        yield Button("Try Again", id="btn-try-again", variant="primary")
        yield Button("Start Over", id="btn-start-over", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-convert-another":
            self.action_convert_another()
        elif event.button.id == "btn-quit":
            self.app.exit()
        elif event.button.id == "btn-try-again":
            self.action_try_again()
        elif event.button.id == "btn-start-over":
            self.action_start_over()

    def action_convert_another(self) -> None:
        from tui.screens.welcome import WelcomeScreen
        self.app.switch_screen(WelcomeScreen())

    def action_try_again(self) -> None:
        from tui.screens.file_picker import FilePickerScreen
        self.app.switch_screen(FilePickerScreen(self.result.conversion_type))

    def action_start_over(self) -> None:
        from tui.screens.welcome import WelcomeScreen
        self.app.switch_screen(WelcomeScreen())
