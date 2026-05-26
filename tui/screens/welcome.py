from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label


class WelcomeScreen(Screen):
    BINDINGS = [
        ("1", "select_bac", "BAC CSV"),
        ("2", "select_davi", "Davi/Scotia XLS"),
        ("3", "select_cascade", "Monthly Cascade"),
        ("s", "open_settings", "Settings"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label("Credit Card Statement → YNAB Converter", id="title")
        yield Label("Select the type of statement to convert:", id="subtitle")
        yield Button("Convert BAC CSV", id="btn-bac", variant="primary")
        yield Button("Convert Davi/Scotia XLS", id="btn-davi", variant="default")
        yield Button("Monthly Overspend Cascade", id="btn-cascade", variant="success")
        yield Footer()

    def action_select_bac(self) -> None:
        from tui.models import ConversionType
        from tui.screens.file_picker import FilePickerScreen
        self.app.push_screen(FilePickerScreen(ConversionType.BAC))

    def action_select_davi(self) -> None:
        from tui.models import ConversionType
        from tui.screens.file_picker import FilePickerScreen
        self.app.push_screen(FilePickerScreen(ConversionType.DAVI))

    def action_select_cascade(self) -> None:
        from tui.screens.cascade_setup import CascadeEntryScreen
        self.app.push_screen(CascadeEntryScreen())

    def action_open_settings(self) -> None:
        from tui.screens.cascade_setup import SettingsScreen
        self.app.push_screen(SettingsScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from tui.models import ConversionType
        from tui.screens.file_picker import FilePickerScreen
        if event.button.id == "btn-bac":
            self.app.push_screen(FilePickerScreen(ConversionType.BAC))
        elif event.button.id == "btn-davi":
            self.app.push_screen(FilePickerScreen(ConversionType.DAVI))
        elif event.button.id == "btn-cascade":
            self.action_select_cascade()
