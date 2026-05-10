from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label


class WelcomeScreen(Screen):
    BINDINGS = [
        ("1", "select_bac", "BAC CSV"),
        ("2", "select_davi", "Davi/Scotia XLS"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Credit Card Statement → YNAB Converter", id="title")
        yield Label("Select the type of statement to convert:", id="subtitle")
        yield Button("Convert BAC CSV", id="btn-bac", variant="primary")
        yield Button("Convert Davi/Scotia XLS", id="btn-davi", variant="default")
        yield Footer()

    def action_select_bac(self) -> None:
        from tui.models import ConversionType
        from tui.screens.file_picker import FilePickerScreen
        self.app.push_screen(FilePickerScreen(ConversionType.BAC))

    def action_select_davi(self) -> None:
        from tui.models import ConversionType
        from tui.screens.file_picker import FilePickerScreen
        self.app.push_screen(FilePickerScreen(ConversionType.DAVI))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from tui.models import ConversionType
        from tui.screens.file_picker import FilePickerScreen
        if event.button.id == "btn-bac":
            self.app.push_screen(FilePickerScreen(ConversionType.BAC))
        elif event.button.id == "btn-davi":
            self.app.push_screen(FilePickerScreen(ConversionType.DAVI))
