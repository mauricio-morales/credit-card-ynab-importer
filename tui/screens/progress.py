import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ProgressBar

from tui.models import ConversionJob, ConversionResult, ConversionType, ProgressUpdate

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class ProgressScreen(Screen):
    BINDINGS = []

    def __init__(self, job: ConversionJob) -> None:
        super().__init__()
        self.job = job

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Label(f"Converting: {self.job.source_path.name}", id="conv-label")
        yield ProgressBar(total=1.0, show_eta=False, id="progress-bar")
        yield Label("Starting…", id="status-label")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._run_conversion, thread=True, exclusive=True)

    def on_progress_update(self, message: ProgressUpdate) -> None:
        bar = self.query_one("#progress-bar", ProgressBar)
        bar.update(progress=message.step / message.total_steps)
        self.query_one("#status-label", Label).update(
            f"Step {message.step} of {message.total_steps}: {message.text}"
        )

    def _post_progress(self, text: str, step: int, total: int) -> None:
        # post_message is thread-safe in Textual
        self.post_message(ProgressUpdate(text, step, total))

    def _switch_to_summary_from_thread(self, result: ConversionResult) -> None:
        self.app.call_from_thread(self._switch_to_summary, result)

    def _switch_to_summary(self, result: ConversionResult) -> None:
        from tui.screens.summary import SummaryScreen
        self.app.switch_screen(SummaryScreen(result))

    def _run_conversion(self) -> None:
        import bac_stage1
        import bac_stage2
        import bac_stage3
        import davi_stage1
        import davi_stage2
        import davi_stage3

        src = self.job.source_path
        d = src.parent
        stem = src.stem
        if stem.endswith("-in"):
            stem = stem[:-3]

        try:
            if self.job.conversion_type == ConversionType.BAC:
                result = self._run_bac(src, d, stem, bac_stage1, bac_stage2, bac_stage3)
            else:
                result = self._run_davi(src, d, stem, davi_stage1, davi_stage2, davi_stage3)
        except Exception as exc:
            result = ConversionResult(
                success=False,
                transaction_count=0,
                output_files=[],
                error_message=_plain_english(exc),
                conversion_type=self.job.conversion_type,
            )

        self._switch_to_summary_from_thread(result)

    def _run_bac(self, src, d, stem, s1, s2, s3) -> ConversionResult:
        out1 = d / f"{stem}-out1.csv"
        out2_crc = d / f"{stem}-out2-crc.csv"
        out2_usd = d / f"{stem}-out2-usd.csv"
        out3_crc = d / f"{stem}-out3-crc.csv"
        out3_usd = d / f"{stem}-out3-usd.csv"

        self._post_progress("Running Stage 1…", 1, 4)
        s1.process(src, out1)

        self._post_progress("Running Stage 2…", 2, 4)
        s2.process(out1, out2_crc, out2_usd)

        self._post_progress("Running Stage 3 (CRC)…", 3, 4)
        s3.process(out2_crc, out3_crc, currency="crc")

        self._post_progress("Running Stage 3 (USD)…", 4, 4)
        s3.process(out2_usd, out3_usd, currency="usd")

        count = _count_rows(out3_crc)
        return ConversionResult(
            success=True,
            transaction_count=count,
            output_files=[out3_crc, out3_usd],
            conversion_type=self.job.conversion_type,
        )

    def _run_davi(self, src, d, stem, s1, s2, s3) -> ConversionResult:
        out1 = d / f"{stem}-out1.csv"
        out2_crc = d / f"{stem}-out2-crc.csv"
        out2_usd = d / f"{stem}-out2-usd.csv"
        out3_crc = d / f"{stem}-out3-crc.csv"
        out3_usd = d / f"{stem}-out3-usd.csv"

        self._post_progress("Running Stage 1…", 1, 4)
        s1.process(src, out1)

        self._post_progress("Running Stage 2…", 2, 4)
        s2.process(out1, out2_crc, out2_usd)

        self._post_progress("Running Stage 3 (CRC)…", 3, 4)
        s3.process(out2_crc, out3_crc, currency="crc")

        self._post_progress("Running Stage 3 (USD)…", 4, 4)
        s3.process(out2_usd, out3_usd, currency="usd")

        count = _count_rows(out3_crc)
        return ConversionResult(
            success=True,
            transaction_count=count,
            output_files=[out3_crc, out3_usd],
            conversion_type=self.job.conversion_type,
        )


def _count_rows(csv_path: Path) -> int:
    try:
        lines = csv_path.read_text(encoding="utf-8").splitlines()
        return max(0, len(lines) - 1)  # subtract header
    except Exception:
        return 0


def _plain_english(exc: Exception) -> str:
    msg = str(exc)
    if not msg:
        msg = type(exc).__name__
    return f"The conversion could not be completed. {msg}"
