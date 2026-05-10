from textual.app import App


class CreditCardConverterApp(App):
    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def on_mount(self) -> None:
        from tui.screens.welcome import WelcomeScreen
        self.push_screen(WelcomeScreen())
