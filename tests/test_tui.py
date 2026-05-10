"""TUI integration tests using Textual's Pilot API.

All tests are async and run with asyncio_mode=auto (set in pytest.ini).
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from tui.app import CreditCardConverterApp
from tui.models import ConversionJob, ConversionResult, ConversionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_success_result(tmp_path: Path) -> ConversionResult:
    out_crc = tmp_path / "file-out3-crc.csv"
    out_usd = tmp_path / "file-out3-usd.csv"
    out_crc.write_text('"Date","Payee","Memo","Amount"\n')
    out_usd.write_text('"Date","Payee","Memo","Amount"\n')
    return ConversionResult(
        success=True,
        transaction_count=47,
        output_files=[out_crc, out_usd],
        warnings=[],
        error_message="",
        conversion_type=ConversionType.BAC,
    )


def _make_error_result(conversion_type: ConversionType) -> ConversionResult:
    return ConversionResult(
        success=False,
        transaction_count=0,
        output_files=[],
        error_message="The file could not be read. Please check it is a valid CSV.",
        conversion_type=conversion_type,
    )


# ---------------------------------------------------------------------------
# T011: WelcomeScreen — BAC flow
# ---------------------------------------------------------------------------

async def test_welcome_screen_bac_flow():
    """T011: Two buttons visible; pressing '1' transitions to FilePickerScreen."""
    from tui.screens.file_picker import FilePickerScreen
    from tui.screens.welcome import WelcomeScreen

    app = CreditCardConverterApp()
    async with app.run_test(size=(120, 40)) as pilot:
        assert isinstance(app.screen, WelcomeScreen)

        buttons = app.screen.query("Button")
        assert len(buttons) == 2, f"Expected 2 buttons, got {len(buttons)}"

        await pilot.press("1")
        await pilot.pause()

        assert isinstance(app.screen, FilePickerScreen), (
            f"Expected FilePickerScreen after pressing '1', got {type(app.screen).__name__}"
        )


# ---------------------------------------------------------------------------
# T012: FilePickerScreen — BAC only shows .csv; Escape goes back
# ---------------------------------------------------------------------------

async def test_file_picker_bac():
    """T012: FilePickerScreen filters to .csv; Escape returns to WelcomeScreen."""
    from tui.screens.file_picker import FilePickerScreen, FilteredDirectoryTree
    from tui.screens.welcome import WelcomeScreen

    app = CreditCardConverterApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("1")
        await pilot.pause()

        assert isinstance(app.screen, FilePickerScreen)

        # The tree should only allow .csv files
        tree = app.screen.query_one(FilteredDirectoryTree)
        assert ".csv" in tree.allowed_extensions
        assert ".xls" not in tree.allowed_extensions

        # Escape pops back to WelcomeScreen
        await pilot.press("escape")
        await pilot.pause()

        assert isinstance(app.screen, WelcomeScreen), (
            f"Expected WelcomeScreen after Escape, got {type(app.screen).__name__}"
        )


# ---------------------------------------------------------------------------
# T013: ProgressScreen — BAC stages called; transitions to SummaryScreen
# ---------------------------------------------------------------------------

async def test_progress_screen_bac(tmp_path):
    """T013: ProgressScreen runs BAC stages (mocked) and switches to SummaryScreen."""
    from textual.app import App
    from tui.screens.progress import ProgressScreen
    from tui.screens.summary import SummaryScreen

    fixture = tmp_path / "BAC Sample-in.csv"
    fixture.write_text("dummy")
    job = ConversionJob(ConversionType.BAC, fixture)

    mock_out1 = tmp_path / "BAC Sample-out1.csv"
    mock_out2_crc = tmp_path / "BAC Sample-out2-crc.csv"
    mock_out2_usd = tmp_path / "BAC Sample-out2-usd.csv"
    mock_out3_crc = tmp_path / "BAC Sample-out3-crc.csv"
    mock_out3_usd = tmp_path / "BAC Sample-out3-usd.csv"

    for f in [mock_out1, mock_out2_crc, mock_out2_usd, mock_out3_crc, mock_out3_usd]:
        f.write_text('"Date","Payee","Memo","Amount"\n"2024/01/15","Shop","","-100"\n')

    class _TestApp(App):
        def on_mount(self) -> None:
            self.push_screen(ProgressScreen(job))

    with patch("bac_stage1.process", return_value=str(mock_out1)), \
         patch("bac_stage2.process", return_value=(str(mock_out2_crc), str(mock_out2_usd))), \
         patch("bac_stage3.process", side_effect=[str(mock_out3_crc), str(mock_out3_usd)]):
        app = _TestApp()
        async with app.run_test(size=(120, 40)) as pilot:
            # Wait for the background worker thread to complete
            await pilot.pause(2.0)

            assert isinstance(app.screen, SummaryScreen), (
                f"Expected SummaryScreen after conversion, got {type(app.screen).__name__}"
            )


# ---------------------------------------------------------------------------
# T014: SummaryScreen — success view
# ---------------------------------------------------------------------------

async def test_summary_screen_success(tmp_path):
    """T014: SummaryScreen shows transaction count and file paths; 'c' goes to Welcome."""
    from textual.app import App
    from tui.screens.summary import SummaryScreen
    from tui.screens.welcome import WelcomeScreen

    result = _make_success_result(tmp_path)

    class _TestApp(App):
        def on_mount(self) -> None:
            self.push_screen(SummaryScreen(result))

    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Assert the result is stored on the screen correctly
        assert isinstance(app.screen, SummaryScreen)
        assert app.screen.result.transaction_count == 47
        assert app.screen.result.success is True
        assert len(app.screen.result.output_files) == 2

        # Output file paths are in the result
        for out in result.output_files:
            assert out in app.screen.result.output_files

        # 'c' should switch to WelcomeScreen
        await pilot.press("c")
        await pilot.pause()
        assert isinstance(app.screen, WelcomeScreen), (
            f"Expected WelcomeScreen after 'c', got {type(app.screen).__name__}"
        )


# ---------------------------------------------------------------------------
# T021: Davi full flow
# ---------------------------------------------------------------------------

async def test_davi_full_flow(tmp_path):
    """T021: '2' key opens FilePickerScreen for .xls/.xlsx; Davi pipeline runs; SummaryScreen shows paths."""
    from textual.app import App
    from tui.screens.file_picker import FilePickerScreen, FilteredDirectoryTree
    from tui.screens.progress import ProgressScreen
    from tui.screens.summary import SummaryScreen

    # Check '2' goes to FilePickerScreen with XLS filter
    app = CreditCardConverterApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("2")
        await pilot.pause()

        assert isinstance(app.screen, FilePickerScreen), (
            f"Expected FilePickerScreen after '2', got {type(app.screen).__name__}"
        )

        tree = app.screen.query_one(FilteredDirectoryTree)
        assert ".xls" in tree.allowed_extensions
        assert ".xlsx" in tree.allowed_extensions
        assert ".csv" not in tree.allowed_extensions

    # Now test full Davi pipeline via a direct ProgressScreen
    fixture = tmp_path / "DaviBank Sample-in.xls"
    fixture.write_bytes(b"dummy")
    job = ConversionJob(ConversionType.DAVI, fixture)

    mock_out1 = tmp_path / "DaviBank Sample-out1.csv"
    mock_out2_crc = tmp_path / "DaviBank Sample-out2-crc.csv"
    mock_out2_usd = tmp_path / "DaviBank Sample-out2-usd.csv"
    mock_out3_crc = tmp_path / "DaviBank Sample-out3-crc.csv"
    mock_out3_usd = tmp_path / "DaviBank Sample-out3-usd.csv"

    for f in [mock_out1, mock_out2_crc, mock_out2_usd, mock_out3_crc, mock_out3_usd]:
        f.write_text('"Date","Payee","Memo","Amount"\n"2024/01/15","Shop","","-100"\n')

    class _TestApp(App):
        def on_mount(self) -> None:
            self.push_screen(ProgressScreen(job))

    with patch("davi_stage1.process", return_value=str(mock_out1)), \
         patch("davi_stage2.process", return_value=(str(mock_out2_crc), str(mock_out2_usd))), \
         patch("davi_stage3.process", side_effect=[str(mock_out3_crc), str(mock_out3_usd)]):
        app2 = _TestApp()
        async with app2.run_test(size=(120, 40)) as pilot:
            await pilot.pause(2.0)
            assert isinstance(app2.screen, SummaryScreen), (
                f"Expected SummaryScreen after Davi conversion, got {type(app2.screen).__name__}"
            )
            assert app2.screen.result.success is True
            output_names = {p.name for p in app2.screen.result.output_files}
            assert mock_out3_crc.name in output_names or mock_out3_usd.name in output_names


# ---------------------------------------------------------------------------
# T024: Error recovery flow
# ---------------------------------------------------------------------------

async def test_error_recovery_flow(tmp_path):
    """T024: When orchestrator raises, SummaryScreen shows error; 'r' retries, 's' starts over."""
    from textual.app import App
    from tui.screens.file_picker import FilePickerScreen
    from tui.screens.progress import ProgressScreen
    from tui.screens.summary import SummaryScreen
    from tui.screens.welcome import WelcomeScreen

    fixture = tmp_path / "bad-file.csv"
    fixture.write_text("corrupted data")
    job = ConversionJob(ConversionType.BAC, fixture)

    class _TestApp(App):
        def on_mount(self) -> None:
            self.push_screen(ProgressScreen(job))

    with patch("bac_stage1.process", side_effect=Exception("bad file")):
        app = _TestApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause(2.0)

            assert isinstance(app.screen, SummaryScreen), (
                f"Expected SummaryScreen after error, got {type(app.screen).__name__}"
            )

            # Result stored with error state (SC-004: no traceback in message)
            assert app.screen.result.success is False
            assert app.screen.result.error_message != ""
            assert "Traceback" not in app.screen.result.error_message
            assert "Exception" not in app.screen.result.error_message

            # 's' should start over at WelcomeScreen
            await pilot.press("s")
            await pilot.pause()
            assert isinstance(app.screen, WelcomeScreen), (
                f"Expected WelcomeScreen after 's', got {type(app.screen).__name__}"
            )

    # Separate test for 'r' retry
    class _TestApp2(App):
        def on_mount(self) -> None:
            self.push_screen(ProgressScreen(job))

    with patch("bac_stage1.process", side_effect=Exception("bad file")):
        app2 = _TestApp2()
        async with app2.run_test(size=(120, 40)) as pilot:
            await pilot.pause(2.0)
            assert isinstance(app2.screen, SummaryScreen)

            await pilot.press("r")
            await pilot.pause()
            assert isinstance(app2.screen, FilePickerScreen), (
                f"Expected FilePickerScreen after 'r', got {type(app2.screen).__name__}"
            )
