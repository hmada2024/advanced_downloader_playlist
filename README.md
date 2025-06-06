# Advanced Spider Fetch

Advanced Spider Fetch is a user-friendly Windows desktop application built with Python. It provides a graphical interface (GUI) for the powerful command-line tool **yt-dlp**, making it easy to download videos and playlists from YouTube and many other websites supported by yt-dlp.

The main goal is to simplify the download process, manage multiple downloads effectively through a queue, and keep track of your download history.

## ✨ Key Features

- **Intuitive GUI:** A clean interface powered by CustomTkinter, eliminating the need for complex command-line arguments.
- **Versatile Downloading:** Download single videos or entire playlists.
- **Format Selection:** Choose your preferred video quality (e.g., up to 1080p, 720p) or download audio-only as MP3.
- **Playlist Control:** Select specific items from a playlist to download.
- **Download Queue:** Add multiple download tasks to a queue. Downloads run sequentially (one after another) to manage resources efficiently. Monitor the status and progress of each task.
- **Task Management:** Cancel individual tasks in the queue (pending or running). Clear finished tasks from the queue view.
- **History:** Keep track of your completed downloads and fetched info for easy reuse or reference.
- **Clean Output:** Downloads are processed in a temporary folder (`ASF_TEMP` in your user home directory), keeping your final save location tidy. Only the final file is moved.
- **Convenient Paste:** Quickly paste URLs from your clipboard using the "Paste" button.
- **Bundled FFmpeg:** Comes with the necessary FFmpeg components for media processing.

## 📸 Screenshots

![Main "Add Download" Tab](Screenshots/1.png)
![Download Queue Tab](Screenshots/2.png)
_(You can add a screenshot for the History tab here if you have one)_

<!-- ![History Tab](Screenshots/history.png) -->

## ⚙️ Requirements

- Windows Operating System (Tested on Windows 10/11, should work on 7/8)
- No external dependencies needed for the user (Python, yt-dlp, FFmpeg are handled internally or bundled).

## 🚀 Installation & Usage

1.  **Download the Application:**
    - **[Download ASF App v3.0.0 (Windows Executable)](https://github.com/hmada2024/advanced_spider_fetch/releases/download/v3.0.0/ASF.App.V3.0.0.exe)**
    - Alternatively, visit the [Releases page](https://github.com/hmada2024/advanced_spider_fetch/releases) for all versions.
2.  Run the downloaded `ASF.App.V3.0.0.exe` file. No installation is required.
3.  **Add Download Tab:**
    - Paste a video or playlist URL.
    - Click `Fetch Info`.
    - Select format, save location, and playlist items (if applicable).
    - Click `Add Video to Queue` or `Add Selection to Queue`.
4.  **Download Queue Tab:**
    - Monitor the progress of tasks (Pending, Running, Downloading %, Completed, Error, Cancelled).
    - Cancel tasks using the `Cancel` button next to each item.
    - Use `Clear Finished Tasks` to remove completed/errored/cancelled items from the view.
5.  **History Tab:**
    - View past successful operations.
    - Use `Use Again`, `Copy URL`, or `Delete` for individual entries.
    - `Clear History` removes all entries.

## 🛠️ Built With

- **Python:** Core programming language.
- **CustomTkinter:** Modern GUI toolkit for Python.
- **yt-dlp:** The powerful backend for fetching information and downloading media (used as a library and subprocess).
- **FFmpeg:** Bundled for media processing (merging, conversion).
- **SQLite:** For storing the download history locally.
- **PyInstaller:** Used for packaging the application into a standalone `.exe`.

---

_Note: This README provides a basic overview. You can expand it with more details, a license, contribution guidelines, etc., as needed._
