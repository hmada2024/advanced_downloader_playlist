# Advanced Spider Fetch

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [//]: # (Replace with your chosen license badge if different)
[//]: # (Add other badges if desired: Build Status, Latest Release, etc.)

**A Powerful & User-Friendly GUI for yt-dlp and FFmpeg on Windows**

Advanced Spider Fetch is a feature-rich desktop application for Windows, built with Python and CustomTkinter. It provides an intuitive Graphical User Interface (GUI) for the powerful `yt-dlp` command-line tool, bridging the gap between its extensive capabilities and the ease-of-use desired by many users. Download videos and playlists effortlessly, fetch direct download links, and manage your media downloads with advanced controls, all without touching the command line.

![Application Screenshot](path/to/your/screenshot.png)
[//]: # (<<< IMPORTANT: Replace this with an actual screenshot or GIF of your application! >>>)

---

## Table of Contents

*   [Core Idea & Motivation](#core-idea--motivation)
*   [Key Features](#key-features)
    *   [Downloader Tab](#downloader-tab)
    *   [Get Playlist Links Tab](#get-playlist-links-tab)
*   [Tech Stack & Architecture](#tech-stack--architecture)
*   [Getting Started (Installation)](#getting-started-installation)
*   [Usage](#usage)
*   [Building from Source](#building-from-source)
*   [Contributing](#contributing)
*   [License](#license)
*   [Acknowledgements](#acknowledgements)

---

## Core Idea & Motivation

The primary goal of **Advanced Spider Fetch** is to harness the immense power of `yt-dlp` (a fork of youtube-dl) within a user-friendly graphical environment. While `yt-dlp` is incredibly versatile for downloading media from numerous websites, its command-line nature can be intimidating or cumbersome for some users.

This application was developed to:

1.  **Simplify Complexity:** Eliminate the need to memorize or construct complex `yt-dlp` commands.
2.  **Provide Visual Feedback:** Offer a visual interface to preview information (video titles, playlist items), select options easily (quality, format, path), and monitor download progress clearly (progress bar, status messages).
3.  **Integrate Essential Tools:** Seamlessly combine `yt-dlp` (for downloading & info fetching) and `FFmpeg` (for media processing like merging and conversion) into a single, cohesive workflow.
4.  **Ensure Portability & Ease of Distribution:** Create a standalone executable (`.exe`) for Windows that runs out-of-the-box without requiring users to manually install Python, `yt-dlp`, or `FFmpeg`.

---

## Key Features

Advanced Spider Fetch offers two main functional tabs:

### Downloader Tab

*   **Comprehensive Downloading:** Download single videos or entire playlists from YouTube and many other `yt-dlp` supported sites.
*   **Information Fetching:** Preview video titles or playlist contents *before* starting the download.
*   **Flexible Quality/Format Selection:** Choose desired video quality and audio/video formats from dynamically populated dropdown menus (e.g., 1080p MP4, 720p WebM, MP3 audio). The application constructs the appropriate `yt-dlp` format string automatically.
*   **Selective Playlist Downloading:** Easily select specific videos from a playlist to download.
*   **Custom Save Path:** Choose the destination folder for your downloads.
*   **One-Click MP3 Conversion:** Dedicated option to download only the audio track and automatically convert it to MP3 using FFmpeg.
*   **Automatic Merging:** Automatically merges separate video and audio streams (often downloaded for highest quality) into a single file using FFmpeg.
*   **Detailed Progress Monitoring:** Real-time feedback including a precise progress bar, download speed, estimated time remaining, current filename, and processing status (e.g., "Merging", "Converting"), thanks to leveraging `yt-dlp` as a library and using its progress hooks.
*   **Cancellation Support:** Cancel ongoing info fetching or download operations cleanly.

### Get Playlist Links Tab

*   **Direct Link Extraction:** A specialized feature to quickly extract direct, (often temporary) download links for all videos within a playlist.
*   **Targeted Use Case:** Primarily designed to facilitate importing playlists into external download managers like Internet Download Manager (IDM) that support batch importing from text files.
*   **Simple Workflow:** Enter the playlist URL, select the desired quality/format for the links.
*   **Convenient Output:** Displays the generated links in a large text area for easy viewing and copying.
*   **Export Options:** Buttons to "Copy All Links" to the clipboard or "Save Links to File" (.txt).
*   **Efficient Implementation:** Uses `yt-dlp` as a subprocess with the `-g` flag for optimized link fetching.

---

## Tech Stack & Architecture

The application is built with a clear separation between the UI and backend logic:

*   **Language:** **Python 3**
*   **GUI Framework:** **CustomTkinter** - Chosen for its modern look and feel, built upon Tkinter, with easy support for themes (light/dark) matching modern Windows aesthetics.
*   **Core Downloader:** **`yt-dlp`**
    *   Used as a **Python library** (`import yt_dlp`) in the main Downloader module for fine-grained control, option configuration, and access to progress/postprocessor hooks.
    *   Used as a **subprocess** (`subprocess.run`) in the "Get Playlist Links" module for efficient direct link fetching (`-g` flag).
*   **Media Processing:** **FFmpeg** & **ffprobe** - Bundled with the application (in `ffmpeg_bin/`). Automatically detected and its path passed to `yt-dlp` for merging and conversion tasks.
*   **Concurrency:** **Python's `threading` module** - All potentially long-running operations (info fetching, downloading, link fetching) are executed in separate threads to keep the GUI responsive. Callbacks (`widget.after`) are used to safely update the UI from background threads. `threading.Event` is used for managing cancellation requests.
*   **Code Structure:**
    *   **UI:** Modularized using CustomTkinter widgets and frames (`src/ui/components/`). Uses Mixins (`UIStateManagerMixin`, `UICallbackHandlerMixin`, `UIActionHandlerMixin`) for better organization within the main UI class (`src/ui/app_ui.py`).
    *   **Logic:** Separated into handlers and utility classes (`src/logic/`) like `LogicHandler`, `InfoFetcher`, `Downloader`, `LinkFetcher`, `utils.py`, etc. Custom exceptions (`src/logic/exceptions.py`) are defined.
*   **Packaging:** **PyInstaller** (or similar tool) - Used to bundle the Python code, dependencies (CustomTkinter, yt-dlp), and the bundled FFmpeg binaries into a single standalone executable or folder for easy distribution on Windows.

---

## Getting Started (Installation)

Advanced Spider Fetch is designed to be portable. No complex installation is required.

1.  **Download:** Go to the [**Releases Page**]([Your Repository Link]/releases) of this repository. [//]: # (<<< Update this link!)
2.  **Extract:** Download the latest release `.zip` file and extract its contents to a folder of your choice.
3.  **Run:** Double-click the `Advanced Spider Fetch.exe` (or the name you chose for the executable) inside the extracted folder.

That's it! The application includes bundled versions of `yt-dlp` and `FFmpeg`, so you don't need to install them separately.

**Requirements:**
*   Windows Operating System (Tested primarily on Windows 10/11).

---

## Usage

1.  Launch the application executable.
2.  **For Downloading:**
    *   Navigate to the **"Downloader"** tab.
    *   Paste a video or playlist URL into the input field.
    *   Click "Fetch Info". Wait for the title/playlist items to appear.
    *   Select desired quality/format, choose specific playlist items (if applicable), and select a save path.
    *   Check the "Download as MP3" option if you only want audio.
    *   Click "Download". Monitor the progress bar and status messages.
3.  **For Getting Direct Links:**
    *   Navigate to the **"Get Playlist Links"** tab.
    *   Paste a playlist URL into the input field.
    *   Select the desired quality/format for the links.
    *   Click "Get Links". Wait for the links to appear in the text area.
    *   Use the "Copy All" or "Save to File" buttons as needed.

---

## Building from Source

If you want to build the application yourself:

**Prerequisites:**

*   Python 3.8+ ([Download Python](https://www.python.org/downloads/))
*   Git ([Download Git](https://git-scm.com/downloads/))
*   FFmpeg binaries (`ffmpeg.exe`, `ffprobe.exe`) ([Download FFmpeg](https://ffmpeg.org/download.html) - e.g., the gyan.dev builds for Windows)

**Steps:**

1.  **Clone the repository:**
    ```bash
    git clone [Your Repository Link] [//]: # (<<< Update this link!)
    cd advanced-spider-fetch [//]: # (Or your repository directory name)
    ```

2.  **Create and activate a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # On Windows
    # source venv/bin/activate # On Linux/macOS (if adapting)
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Place FFmpeg Binaries:**
    *   Download `ffmpeg.exe` and `ffprobe.exe`.
    *   Create a folder named `ffmpeg_bin` in the root directory of the project.
    *   Place the downloaded `ffmpeg.exe` and `ffprobe.exe` inside the `ffmpeg_bin` folder. (The `find_ffmpeg` utility in `src/logic/utils.py` expects them here).

5.  **Run the application (for testing):**
    ```bash
    python main.py [//]: # (<<< Verify 'main.py' is your main script name)
    ```

6.  **Build the executable using PyInstaller:**
    ```bash
    # Example PyInstaller command (adjust as needed):
    pyinstaller --name AdvancedSpiderFetch --windowed --onefile --add-data "ffmpeg_bin;ffmpeg_bin" --add-data "[path_to_customtkinter];customtkinter" main.py
    # OR for a folder distribution (often more reliable):
    # pyinstaller --name AdvancedSpiderFetch --windowed --add-data "ffmpeg_bin;ffmpeg_bin" --add-data "[path_to_customtkinter];customtkinter" main.py

    # Notes on PyInstaller command:
    # --name: Sets the executable name.
    # --windowed: Prevents a console window from appearing.
    # --onefile: Creates a single .exe (can sometimes have issues, folder distribution might be better).
    # --add-data "source;destination": Bundles FFmpeg and CustomTkinter assets.
    #   - Replace [path_to_customtkinter] with the actual path to the customtkinter library in your venv (e.g., venv\Lib\site-packages\customtkinter).
    # main.py: Your main application script. [//]: # (<<< Verify!)
    ```
    The executable/folder will be located in the `dist` directory.

---

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1.  **Fork** the repository on GitHub.
2.  **Clone** your forked repository locally (`git clone https://github.com/YourUsername/advanced-spider-fetch.git`).
3.  Create a new **branch** for your feature or bug fix (`git checkout -b feature/your-feature-name` or `bugfix/issue-description`).
4.  Make your changes and **commit** them with clear messages.
5.  **Push** your changes to your fork on GitHub (`git push origin feature/your-feature-name`).
6.  Open a **Pull Request** from your fork's branch to the main repository's `main` branch.

Please also feel free to open **Issues** for bug reports or feature requests.

---

## License

This project is licensed under the **[Your Chosen License Name]**. See the [LICENSE](LICENSE) file for details.

[//]: # (<<< IMPORTANT: Create a LICENSE file in your repo root and choose a license like MIT, GPLv3, Apache 2.0, etc. Update this section accordingly. >>>)
[//]: # (Example for MIT: This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.)

---

## Acknowledgements

*   **yt-dlp team:** For creating and maintaining the incredibly powerful download tool that forms the core of this application. ([yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp))
*   **FFmpeg team:** For the essential multimedia framework used for merging and conversion. ([FFmpeg Website](https://ffmpeg.org/))
*   **Tom Schimansky:** For the wonderful CustomTkinter library that makes modern GUI development in Python much easier. ([CustomTkinter GitHub](https://github.com/TomSchimansky/CustomTkinter))
*   The **Python** community.
