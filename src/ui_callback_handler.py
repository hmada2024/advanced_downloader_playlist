# src/ui_callback_handler.py
# -- Mixin class for handling callbacks from the logic layer --

import customtkinter as ctk
from tkinter import messagebox
import logging  # <-- إضافة استيراد logging


class UICallbackHandlerMixin:
    """Mixin class containing methods for handling callbacks from LogicHandler."""

    def update_status(self, message):
        """Updates the status label text and color (thread-safe)."""

        # تجنب تسجيل كل تحديث صغير Avoid logging every minor update
        # logging.debug(f"UICallbackHandler: Received status update: {message}")
        def _update():
            color = "gray"
            justify_val = "left" if "\n" in message else "center"
            msg_lower = message.lower()
            if "error" in msg_lower:
                color = "red"
            elif "warning" in msg_lower:
                color = "orange"
            elif "cancel" in msg_lower:
                color = "orange"
            elif (
                "complete" in msg_lower
                or "finished" in msg_lower
                or "success" in msg_lower
            ):
                color = "green"
            elif (
                "downloading" in msg_lower
                or "processing" in msg_lower
                or "fetching" in msg_lower
                or "starting" in msg_lower
            ):
                color = "blue"
            self.status_label.configure(
                text=message, text_color=color, justify=justify_val
            )

        self.after(1, _update)  # استخدام after مهم جداً Thread-safe update

    def update_progress(self, value):
        """Updates the progress bar value (thread-safe)."""
        # تجنب تسجيل كل تحديث صغير Avoid logging every minor update
        # logging.debug(f"UICallbackHandler: Received progress update: {value:.2f}")
        value = max(0.0, min(1.0, value))
        self.after(1, lambda: self.progress_bar.set(value))  # Thread-safe update

    def on_info_success(self, info_dict):
        """Callback executed when info fetch succeeds (thread-safe)."""
        logging.info("UICallbackHandler: on_info_success callback received.")

        def _update():
            self.fetched_info = info_dict
            if not info_dict:
                logging.error(
                    "UICallbackHandler: on_info_success received empty or invalid info_dict."
                )
                self.on_info_error("Received empty or invalid info.")
                return

            is_actually_playlist = isinstance(info_dict.get("entries"), list)
            logging.debug(
                f"UICallbackHandler: Info success - Is Playlist: {is_actually_playlist}, Restoring switch state to: {self._last_toggled_playlist_mode}"
            )

            if is_actually_playlist:
                self.options_frame_widget.set_playlist_mode(
                    self._last_toggled_playlist_mode
                )
            else:
                logging.debug(
                    "UICallbackHandler: Info success - Not a playlist, ensuring switch is OFF and disabled."
                )
                self.options_frame_widget.set_playlist_mode(False)
                self.options_frame_widget.playlist_switch.configure(state="disabled")

            # الدالة ستسجل بنفسها Function will log itself
            self._enter_info_fetched_state()

            status_msg = "Info fetched successfully. Ready to download."
            if self.options_frame_widget.get_playlist_mode() and is_actually_playlist:
                status_msg = "Playlist info fetched. Select items and download."
            self.update_status(status_msg)  # التحديث للواجهة Update UI

        self.after(0, _update)  # Thread-safe update

    def on_info_error(self, error_message):
        """Callback executed when info fetch fails (thread-safe)."""
        logging.error(
            f"UICallbackHandler: on_info_error callback received: {error_message}"
        )

        def _update():
            messagebox.showerror(
                "Information Fetch Error",
                f"Could not fetch information:\n{error_message}",
            )
            # الدالة ستسجل بنفسها Function will log itself
            self._enter_idle_state()

        self.after(0, _update)  # Thread-safe update

    def on_task_finished(self):
        """Callback executed when any background task finishes (thread-safe)."""
        logging.debug("UICallbackHandler: on_task_finished callback received.")

        def _process_finish():
            operation_type = self.current_operation
            final_status_text = self.status_label.cget("text")
            # قد لا يكون اللون مؤشراً موثوقاً دائماً Color might not be reliable, rely on text/state
            was_cancelled = "cancel" in final_status_text.lower()
            # التحقق من وجود كلمة خطأ في الحالة النهائية Check for error word in final status
            was_error = "error" in final_status_text.lower()

            logging.info(
                f"UICallbackHandler: Processing task finish.\n"
                f"  Operation Type: '{operation_type}'\n"
                f"  Final Status Text: '{final_status_text}'\n"
                f"  Was Cancelled: {was_cancelled}\n"
                f"  Was Error: {was_error}"
            )

            # Reset the current operation tracker *before* changing state
            self.current_operation = None

            # Logic to transition UI state based on outcome
            if was_cancelled:
                logging.info("UICallbackHandler: Operation was cancelled.")
                if self.fetched_info:
                    self._enter_info_fetched_state()  # العودة لعرض المعلومات Go back to showing info
                    self.update_status("Operation Cancelled.")
                else:
                    self._enter_idle_state()  # العودة للخمول Go back to idle
                    self.update_status("Info Fetch Cancelled.")
            elif was_error:
                logging.info("UICallbackHandler: Operation failed with error.")
                # لا تعرض رسالة خطأ أخرى، تم عرضها بواسطة on_info_error أو تم تحديث الحالة
                # Don't show another error box, already shown or status updated
                if self.fetched_info:
                    self._enter_info_fetched_state()  # اذهب لعرض المعلومات حتى لو كان هناك خطأ Show info even if error occurred
                else:
                    self._enter_idle_state()  # اذهب للخمول إذا فشل الجلب Go idle if fetch failed
            elif operation_type == "fetch":
                # النجاح تم التعامل معه بـ on_info_success
                # Success handled by on_info_success
                logging.info(
                    "UICallbackHandler: Info fetch finished successfully (state already updated)."
                )
            elif operation_type == "download":
                # نجاح التحميل Successfull download
                logging.info("UICallbackHandler: Download finished successfully.")
                save_path = self.path_frame_widget.get_path()
                messagebox.showinfo(
                    "Download Complete",
                    f"Download finished successfully!\nFile(s) saved in:\n{save_path}",
                )
                self._enter_idle_state()  # العودة للخمول بعد التحميل الناجح Back to idle after success
            else:
                # حالة غير متوقعة أو غير معروفة Unexpected state
                logging.warning(
                    f"UICallbackHandler: Task finished with unknown state or type. Resetting. (Op: {operation_type}, Status: {final_status_text})"
                )
                self._enter_idle_state()

            # self.current_operation = None # تم نقله للأعلى Moved up

        # تأخير بسيط لضمان تحديث الحالة النهائية قبل المعالجة Small delay for final status update
        self.after(50, _process_finish)
