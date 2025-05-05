# src/logic/downloader_hooks.py
# -- ملف يحتوي على كلاسات معالجة الـ Hooks لعملية التحميل --
# -- Corrected FINAL_POSTPROCESSORS list for accurate move/rename trigger --

import os
import time
import humanize
import contextlib
import shutil  # لاستخدام shutil.move
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List, Union, TYPE_CHECKING
import threading

from yt_dlp.utils import DownloadCancelled as YtdlpDownloadCancelled

# --- Imports from current package ---
from .exceptions import DownloadCancelled
from .utils import clean_filename
from .downloader_constants import *
from .downloader_utils import check_cancel

if TYPE_CHECKING:
    from .downloader import Downloader


class ProgressHookHandler:
    """
    كلاس لمعالجة الـ progress_hooks من yt-dlp.
    يحاول حساب التقدم المجمع إذا كانت المعلومات متوفرة.
    """

    # --- كود ProgressHookHandler يبقى كما هو من الإصدار السابق (لا يحتاج تعديل هنا) ---
    def __init__(
        self,
        downloader: "Downloader",
        status_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
    ):
        self.downloader: "Downloader" = downloader
        self.status_callback: Callable[[str], None] = status_callback
        self.progress_callback: Callable[[float], None] = progress_callback
        self._total_size_estimate: Optional[float] = None
        self._last_artifact_filename_hook: Optional[str] = None

    def hook(self, d: Dict[str, Any]) -> None:
        try:
            check_cancel(self.downloader.cancel_event, "during progress hook")
        except DownloadCancelled as e:
            raise YtdlpDownloadCancelled(str(e)) from e

        status: Optional[str] = d.get("status")
        info_dict: Dict[str, Any] = d.get("info_dict", {})
        hook_playlist_index: Optional[int] = info_dict.get("playlist_index")
        current_hook_filename = d.get("filename")

        if (
            current_hook_filename
            and current_hook_filename != self._last_artifact_filename_hook
        ):
            self._last_artifact_filename_hook = current_hook_filename

        if (
            self.downloader.is_playlist
            and hook_playlist_index is not None
            and hook_playlist_index > self.downloader._last_hook_playlist_index
        ):
            self.downloader._current_processing_playlist_idx_display = (
                hook_playlist_index
            )
            self.downloader._last_hook_playlist_index = hook_playlist_index
            self._total_size_estimate = None
            self._last_artifact_filename_hook = None

        if status == "finished":
            if filepath := info_dict.get("filepath") or d.get("filename"):
                self.downloader._update_status_on_finish_or_process(
                    filepath, info_dict, is_final=False
                )
            else:
                self.status_callback(STATUS_PROCESSING_FILE)

        elif status == "downloading":
            downloaded_bytes: Optional[int] = d.get("downloaded_bytes")
            if downloaded_bytes is not None:
                current_total_estimate = d.get("_total_filesize_estimate")
                if current_total_estimate is not None and current_total_estimate > 0:
                    if (
                        self._total_size_estimate is None
                        or self._total_size_estimate != current_total_estimate
                    ):
                        print(
                            f"ProgressHook: Using total size estimate: {humanize.naturalsize(current_total_estimate, binary=True)}"
                        )
                        self._total_size_estimate = float(current_total_estimate)
                    progress = downloaded_bytes / self._total_size_estimate
                    progress = max(0.0, min(1.0, progress))
                    self.progress_callback(progress)
                else:
                    if self._total_size_estimate is not None:
                        print(
                            "ProgressHook: Total estimate N/A. Reverting to per-artifact progress."
                        )
                        self._total_size_estimate = None
                    total_artifact_bytes = d.get("total_bytes") or d.get(
                        "total_bytes_estimate"
                    )
                    if total_artifact_bytes and total_artifact_bytes > 0:
                        progress = downloaded_bytes / total_artifact_bytes
                        progress = max(0.0, min(1.0, progress))
                        self.progress_callback(progress)
                    else:
                        self.progress_callback(0.0)
                self._format_and_display_download_status(d, downloaded_bytes)
            else:
                self.status_callback(STATUS_CONNECTING)

        elif status == "error":
            self.status_callback(STATUS_ERROR_YT_DLP)
            print(
                f"yt-dlp hook reported error: {d.get('error', 'Unknown yt-dlp error')}"
            )

    def _format_and_display_download_status(
        self, d: Dict[str, Any], downloaded_bytes: int
    ) -> None:
        total_bytes_artifact: Optional[int] = d.get("total_bytes") or d.get(
            "total_bytes_estimate"
        )
        percentage_str_artifact: str = "0.0%"
        if total_bytes_artifact and total_bytes_artifact > 0:
            progress_artifact = max(
                0.0, min(1.0, downloaded_bytes / total_bytes_artifact)
            )
            percentage_str_artifact = f"{progress_artifact:.1%}"
        status_lines: List[str] = []
        if self.downloader.is_playlist:
            self._format_playlist_progress_status(status_lines, d.get("info_dict", {}))
        else:
            status_lines.append("Downloading Media")
        downloaded_size_str: str = humanize.naturalsize(downloaded_bytes, binary=True)
        total_size_str_artifact: str = (
            humanize.naturalsize(total_bytes_artifact, binary=True)
            if total_bytes_artifact
            else "Unknown size"
        )
        status_lines.append(
            f"Current File: {percentage_str_artifact} ({downloaded_size_str} / {total_size_str_artifact})"
        )
        speed: Optional[float] = d.get("speed")
        speed_str: str = (
            f"{humanize.naturalsize(speed, binary=True, gnu=True)}/s"
            if speed
            else "Calculating..."
        )
        eta: Optional[Union[int, float]] = d.get("eta")
        eta_str: str = "Calculating..."
        with contextlib.suppress(TypeError, ValueError):
            if eta is not None and isinstance(eta, (int, float)) and eta >= 0:
                td = time.gmtime(int(round(eta)))
                if td.tm_hour > 0:
                    eta_str = time.strftime("%H:%M:%S remaining", td)
                else:
                    eta_str = time.strftime("%M:%S remaining", td)
        status_lines.append(f"Speed: {speed_str} | ETA: {eta_str}")
        self.status_callback("\n".join(status_lines))

    def _format_playlist_progress_status(
        self, status_lines: List[str], info_dict: Dict[str, Any]
    ) -> None:
        current_absolute_index: int = (
            self.downloader._current_processing_playlist_idx_display
        )
        total_absolute_str: str = (
            f"of {self.downloader.total_playlist_count} total"
            if self.downloader.total_playlist_count > 0
            else ""
        )
        item_title = info_dict.get("title")
        if not item_title and self._last_artifact_filename_hook:
            item_title = Path(self._last_artifact_filename_hook).stem
        if item_title:
            item_title_cleaned = clean_filename(item_title)
            status_lines.append(
                f"Item {current_absolute_index} {total_absolute_str}: {item_title_cleaned[:45]}..."
            )
        else:
            status_lines.append(f"Item {current_absolute_index} {total_absolute_str}")
        index_in_selection: int = self.downloader._processed_selected_count + 1
        index_in_selection = min(
            index_in_selection, self.downloader.selected_items_count
        )
        remaining_in_selection: int = max(
            0,
            self.downloader.selected_items_count
            - self.downloader._processed_selected_count,
        )
        status_lines.append(
            f"Selected: {index_in_selection} of {self.downloader.selected_items_count} ({remaining_in_selection} remaining)"
        )


class PostprocessorHookHandler:
    """كلاس لمعالجة الـ postprocessor_hooks من yt-dlp. ينقل ويعيد تسمية الملف النهائي."""

    # <<< === التعديل هنا === >>>
    # استخدم الأسماء التي تظهر فعليًا في سجلات yt-dlp للخطاف
    FINAL_POSTPROCESSORS = ["Merger", "FFmpegExtractAudio", "MoveFiles"]
    # أضفنا MoveFiles احتياطيًا، مع أن النقل يجب أن يحدث بعد Merger/ExtractAudio
    # سنعتمد بشكل أساسي على انتهاء Merger أو ExtractAudio

    def __init__(self, downloader: "Downloader"):
        self.downloader: "Downloader" = downloader
        # <<< إضافة: تتبع ما إذا تم النقل لهذا الملف بالفعل >>>
        self._moved_files_for_current_item: set = set()

    def hook(self, d: Dict[str, Any]) -> None:
        """خطاف المعالج اللاحق لـ yt-dlp."""
        status: Optional[str] = d.get("status")
        postprocessor_name: Optional[str] = d.get("postprocessor")
        info_dict: Dict[str, Any] = d.get("info_dict", {})

        # <<< إضافة: إعادة تعيين حالة النقل عند بدء عنصر قائمة تشغيل جديد >>>
        # نعتمد على تغيير فهرس قائمة التشغيل في ProgressHook لتحديد بداية عنصر جديد
        # هذا ليس دقيقًا 100% ولكنه أفضل ما يمكن
        if self.downloader.is_playlist:
            current_display_index = (
                self.downloader._current_processing_playlist_idx_display
            )
            # إذا لم نسجل أي عملية نقل لهذا الفهرس بعد، قم بإعادة التعيين
            # هذا يحتاج طريقة أفضل، لنعتمد على playlist_index من info_dict هنا
            current_playlist_index = info_dict.get("playlist_index")
            if (
                current_playlist_index
                and current_playlist_index not in self._moved_files_for_current_item
            ):
                # print(f"Resetting moved flag for playlist index {current_playlist_index}")
                self._moved_files_for_current_item = set()  # Reset for new item

        if status == "started":
            print(f"Postprocessor Hook: '{postprocessor_name}' started.")
            # --- الكود الخاص بحالة started يبقى كما هو ---
            status_message: str = STATUS_FINAL_PROCESSING
            # Use short names for comparison here as well
            if postprocessor_name == "Merger":
                status_message = PP_STATUS_MERGING
            elif postprocessor_name == "FFmpegExtractAudio":
                target_codec: str = "audio"
                pp_args: Any = info_dict.get("postprocessor_args")
                with contextlib.suppress(Exception):
                    if isinstance(pp_args, list) and len(pp_args) >= 2:
                        target_codec = pp_args[1]
                    elif isinstance(pp_args, dict):
                        target_codec = pp_args.get("preferredcodec", target_codec)
                status_message = (
                    PP_STATUS_CONVERTING_MP3
                    if target_codec == "mp3"
                    else PP_STATUS_EXTRACTING_AUDIO.format(codec=target_codec)
                )
            elif postprocessor_name == "FFmpegVideoConvertor":
                status_message = PP_STATUS_CONVERTING_VIDEO
            # Remove MoveFiles from status updates shown to user
            # elif postprocessor_name == "MoveFiles": status_message = STATUS_ORGANIZE_FILES
            elif postprocessor_name:
                status_message = PP_STATUS_PROCESSING_GENERIC_PP.format(
                    pp_name=postprocessor_name
                )

            # Only update status if it's not MoveFiles (internal)
            if postprocessor_name != "MoveFiles":
                self.downloader.status_callback(status_message)

        elif status == "finished":
            temp_filepath_hook: Optional[str] = info_dict.get("filepath")
            print(
                f"Postprocessor Hook: Status='finished', PP='{postprocessor_name}', Hook Path='{temp_filepath_hook}'"
            )

            # --- <<< تعديل الشرط الرئيسي للنقل >>> ---
            # تحقق من اسم المعالج ومن وجود مسار الملف
            # وأضف تحققًا للتأكد من أننا لم ننقل هذا الملف بالفعل
            current_playlist_index = info_dict.get(
                "playlist_index"
            )  # Get index for tracking

            # We primarily care about Merger or FFmpegExtractAudio finishing
            trigger_move = postprocessor_name in ["Merger", "FFmpegExtractAudio"]

            # Check if already moved for this index (if playlist)
            already_moved = False
            if self.downloader.is_playlist and current_playlist_index and current_playlist_index in self._moved_files_for_current_item:
                already_moved = True
                print(
                    f"Postprocessor Hook: Already moved file for index {current_playlist_index}. Skipping."
                )

            if trigger_move and temp_filepath_hook and not already_moved:
                print(
                    f"Postprocessor Hook: Trigger processor '{postprocessor_name}' finished for '{temp_filepath_hook}'. Initiating move/rename."
                )

                temp_source_path = Path(temp_filepath_hook)

                if not temp_source_path.is_file():
                    print(
                        f"Postprocessor Error: Source file '{temp_source_path}' not found for move/rename."
                    )
                    return

                # --- بناء اسم الملف النهائي المستهدف ---
                target_basename = ""
                final_save_dir = Path(self.downloader.save_path)
                if info_dict:
                    target_basename = self._extracted_from_hook_98(
                        info_dict, temp_source_path, current_playlist_index
                    )
                else:
                    print(
                        "Postprocessor Warning: info_dict not found in hook. Using original temp filename."
                    )
                    target_basename = temp_source_path.name

                # --- بناء المسار النهائي وتنفيذ النقل ---
                final_dest_path = final_save_dir / target_basename
                print(
                    f"Postprocessor Hook: Moving '{temp_source_path}' -> '{final_dest_path}'"
                )
                try:
                    check_cancel(
                        self.downloader.cancel_event, "before final move in hook"
                    )
                    time.sleep(0.1)
                    final_save_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(temp_source_path), str(final_dest_path))
                    print(
                        f"Postprocessor Hook: Move successful for '{target_basename}'."
                    )

                    # --- تم النجاح النهائي لهذا الملف ---
                    self.downloader.status_callback(f"Completed: {target_basename}")
                    self.downloader._update_status_on_finish_or_process(
                        str(final_dest_path), info_dict, is_final=True
                    )

                    # <<< إضافة: تسجيل أن هذا الملف تم نقله >>>
                    if self.downloader.is_playlist and current_playlist_index:
                        # Store the index to prevent moving again if MoveFiles hook runs later
                        self._moved_files_for_current_item.add(current_playlist_index)
                        print(
                            f"Postprocessor Hook: Marked index {current_playlist_index} as moved."
                        )

                except OSError as move_err:
                    print(f"Postprocessor Error: Failed to move file: {move_err}")
                    self.downloader.status_callback(f"Error moving file: {move_err}")
                except DownloadCancelled:
                    print("Postprocessor Hook: Cancellation requested during move.")
                except Exception as final_err:
                    print(
                        f"Postprocessor Error: Unexpected error during move/rename: {final_err}"
                    )
                    self.downloader.status_callback(
                        f"Unexpected error finalizing file: {final_err}"
                    )
            else:
                # تجاهل معالجات أخرى أو ملفات تم نقلها بالفعل
                if not trigger_move:
                    print(
                        f"Postprocessor Hook: Ignoring 'finished' status for '{postprocessor_name}' (Not a trigger)."
                    )
                elif not already_moved:
                    print(
                        f"Postprocessor Warning: No filepath found in 'finished' hook for '{postprocessor_name}'."
                    )

    # TODO Rename this here and in `hook`
    def _extracted_from_hook_98(self, info_dict, temp_source_path, current_playlist_index):
        base_title: str = info_dict.get("title", "Untitled")
        base_ext: str = temp_source_path.suffix
        # Use playlist_index obtained earlier for consistency
        target_basename_no_ext: str
        target_basename_no_ext = (
            f"{current_playlist_index}. {base_title}"
            if (self.downloader.is_playlist and current_playlist_index is not None)
            else base_title
        )
        cleaned_target_basename_no_ext: str = clean_filename(
            target_basename_no_ext
        )
        return f"{cleaned_target_basename_no_ext}{base_ext}"
