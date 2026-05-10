# Quickstart: Credit Card → YNAB Converter

This guide is written for non-technical users. No programming knowledge is required.

---

## Before You Start (one-time setup)

You only need to do this once. Open your terminal and run these two commands:

```bash
pip install textual
```

That's it. The tool is now ready to use.

---

## How to Launch the Tool

In your terminal, navigate to the folder where you saved this project, then run:

```bash
python -m tui
```

Or, if you prefer, double-click `run.py` (if your system is configured to open Python files).

---

## Step-by-Step Walkthrough

### Step 1 — Welcome Screen

When the tool opens, you will see two options:

```
┌──────────────────────────────────────────┐
│   Credit Card → YNAB Converter           │
│                                          │
│   What would you like to convert?        │
│                                          │
│   [ 1 ] BAC credit card (CSV file)       │
│   [ 2 ] Davi / Scotia credit card        │
│         (XLS file)                       │
└──────────────────────────────────────────┘
```

Press `1` for a BAC statement, or `2` for a Davi/Scotia statement.

---

### Step 2 — Choose Your File

A file browser will open. Navigate to the folder where your bank export is saved.

- Use the **arrow keys** to move up and down.
- Press **Enter** or the **right arrow** to open a folder.
- Press the **left arrow** to close a folder and go up one level.
- When you see your file, press **Tab** to move to the "Select This File" button, then press **Enter**.

> Only files with the correct type are shown — CSV files for BAC, XLS files for Davi/Scotia — so you cannot accidentally pick the wrong kind of file.

Press **Escape** at any time to go back to the previous screen.

---

### Step 3 — Conversion in Progress

The tool will automatically convert your file. You will see a progress bar and a short message for each step. This usually takes just a few seconds.

```
Converting: BAC MCB Marzo-in.csv
████████████░░░░  Stage 3 of 4: Generating YNAB file (CRC)…
```

---

### Step 4 — Summary

When the conversion is done, you will see a summary:

```
✓ Conversion complete

  47 transactions processed
  Output files saved next to your original:
    • BAC MCB Marzo-out3-crc.csv
    • BAC MCB Marzo-out3-usd.csv

  [ Convert Another ]        [ Quit ]
```

Your YNAB-ready files are in the **same folder** as the file you selected. You do not need to move them — just open YNAB and import from there.

Press `c` to convert another file, or `q` to quit.

---

## If Something Goes Wrong

If the tool shows an error, it will explain what happened in plain language and offer two options:

- **Try Again** — go back to file selection and pick a different file
- **Start Over** — return to the main menu

Your original bank export file is **never changed or deleted**, so you can always try again safely.

---

## Common Questions

**What file do I export from BAC?**
Log in to BAC online banking, go to your credit card, and export your statement as CSV.

**What file do I export from Davi / Scotia?**
Log in to the bank's online portal, go to your credit card movements, and download the statement as XLS.

**Where do the output files go?**
They are saved in the exact same folder as the file you selected. Look for files ending in `-out3-crc.csv` and `-out3-usd.csv`.

**Do I need both CRC and USD files?**
Import whichever matches the currency account you track in YNAB. Most users import both.
