# Getting Started

## Quick Start

Download the latest release from the [GitHub Releases page](../../releases) for your project. Extract the zip file, then follow the steps below for your operating system to install Python (if you haven't already) and run the application.

---

## Installing Python — Windows

1. Go to [https://python.org/downloads](https://python.org/downloads) in your browser.
2. Click the **Download Python** button (the big yellow button at the top).
3. Open the downloaded installer.
4. **Important**: On the first screen of the installer, check the box that says **"Add Python to PATH"** before clicking anything else. If you miss this step, the app will not be able to start.
5. Click **Install Now**.
6. Wait for the installation to finish, then click **Close**.

---

## Installing Python — Mac

> **Note**: Macs often come with Python 2 pre-installed, but this app requires Python 3. The steps below install Python 3 from the official source.

1. Go to [https://python.org/downloads](https://python.org/downloads) in your browser.
2. Click the **Download Python** button.
3. Open the downloaded `.pkg` installer and follow the on-screen steps.
4. When the installation finishes, click **Close**.

---

## Getting the Code

### Option A: Download the Release Zip (Recommended)

1. Go to the [GitHub Releases page](../../releases).
2. Click the most recent release.
3. Under **Assets**, click the `.zip` file to download it.
4. Extract (unzip) the downloaded file — on Windows, right-click it and choose **Extract All**; on Mac, double-click it.
5. Open the extracted folder.

### Option B: Clone with Git

If you have Git installed and prefer to keep the code up to date easily:

1. Open a terminal window.
2. Run the following command to download the code:
   ```
   git clone https://github.com/YOUR_USERNAME/credit-card-ynab-importer.git
   ```
3. Open the downloaded `credit-card-ynab-importer` folder.
4. Install the required dependencies by double-clicking the launcher for your platform (see **Running the Application** below) — the launcher handles this automatically on first run.

**To update the app later**: Open a terminal in the project folder and run `git pull`, then re-run the launcher to pick up any new dependencies.

---

## Running the Application

### Windows

Double-click **`run_windows.bat`** inside the extracted folder. A terminal window will open, install any required components, and launch the application.

### Mac

Double-click **`run_mac.command`** inside the extracted folder. A Terminal window will open, install any required components, and launch the application.

> **First time on Mac?** If macOS shows a warning saying the file is from an "Unidentified Developer", see the Troubleshooting section below.

---

## Troubleshooting

### Mac: "Unidentified Developer" or Gatekeeper Warning

When you double-click `run_mac.command` for the first time, macOS may show a dialog that says **"run_mac.command cannot be opened because it is from an unidentified developer"** or similar.

To allow the app to run:

1. **Right-click** (or Control-click) on `run_mac.command`.
2. Choose **Open** from the menu that appears.
3. A new dialog will appear — click **Open** again to confirm.

You only need to do this once. After the first time, double-clicking will work normally.

---

### Windows: SmartScreen Warning

When you double-click `run_windows.bat` for the first time, Windows may show a blue screen that says **"Windows protected your PC"**.

To allow the app to run:

1. Click **More info** (below the warning text).
2. Click **Run anyway**.

---

### Python Not Found

If a window appears saying **"Python not found"**:

- **Windows**: You may have forgotten to check "Add Python to PATH" during installation. Uninstall Python, then reinstall it and make sure to check that box on the first screen.
- **Mac**: Make sure you installed Python 3 from [python.org](https://python.org/downloads), not an older version.

After reinstalling Python, try double-clicking the launcher again.
