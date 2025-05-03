# src/ui_components/playlist_selector.py
# -- ملف لمكون الواجهة الخاص بعرض واختيار عناصر قائمة التشغيل --

import customtkinter as ctk
import logging  # <-- إضافة استيراد logging


class PlaylistSelector(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, label_text="Playlist Items", **kwargs)
        logging.debug("PlaylistSelector initialized.")
        self.checkboxes_data = []

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=5, padx=5)

        self.select_all_button = ctk.CTkButton(
            self.button_frame, text="Select All", command=self.select_all
        )
        self.select_all_button.pack(side="left", padx=(0, 5))
        self.deselect_all_button = ctk.CTkButton(
            self.button_frame, text="Deselect All", command=self.deselect_all
        )
        self.deselect_all_button.pack(side="left", padx=5)

        self.disable()

    def clear_items(self):
        """Destroys old checkboxes and clears the internal list."""
        logging.debug("PlaylistSelector: Clearing items.")
        for cb, var, index in self.checkboxes_data:
            if cb and isinstance(cb, (ctk.CTkCheckBox, ctk.CTkLabel)):
                try:
                    cb.destroy()
                except Exception as e:
                    # استخدام logging.error لتسجيل خطأ التدمير
                    logging.error(
                        f"PlaylistSelector: Error destroying playlist item widget: {e}"
                    )
        self.checkboxes_data = []
        self.disable()

    def populate_items(self, entries):
        """Populates the frame with checkboxes for playlist items."""
        logging.debug(
            f"PlaylistSelector: Populating with {len(entries) if entries else 0} items."
        )
        self.clear_items()

        if not entries:
            no_items_label = ctk.CTkLabel(self, text="No videos found in playlist.")
            no_items_label.pack(pady=5, padx=5, anchor="w")
            self.checkboxes_data.append((no_items_label, None, -1))
            self.disable()
            return

        self.enable()

        for index, entry in enumerate(entries):
            if not entry:
                logging.warning(
                    f"PlaylistSelector: Found null entry at index {index}, skipping."
                )
                continue

            video_index = entry.get("playlist_index") or (index + 1)
            title = entry.get("title") or f"Video {video_index} (Untitled)"
            max_len = 70
            display_title = f"{title[:max_len]}..." if len(title) > max_len else title

            var = ctk.StringVar(value="on")
            cb = ctk.CTkCheckBox(
                self,
                text=f"{video_index}. {display_title}",
                variable=var,
                onvalue="on",
                offvalue="off",
            )
            cb.pack(anchor="w", padx=10, pady=(2, 2), fill="x")
            self.checkboxes_data.append((cb, var, video_index))
        logging.debug("PlaylistSelector: Finished packing checkboxes.")

    def select_all(self):
        """Selects all checkboxes."""
        logging.debug("PlaylistSelector: Select All clicked.")
        for cb, var, index in self.checkboxes_data:
            if var and isinstance(var, ctk.StringVar):
                var.set("on")

    def deselect_all(self):
        """Deselects all checkboxes."""
        logging.debug("PlaylistSelector: Deselect All clicked.")
        for cb, var, index in self.checkboxes_data:
            if var and isinstance(var, ctk.StringVar):
                var.set("off")

    def get_selected_items_string(self):
        """Returns a comma-separated string of selected item indices."""
        selected_indices = [
            index
            for cb, var, index in self.checkboxes_data
            if cb and isinstance(cb, ctk.CTkCheckBox) and var and var.get() == "on"
        ]
        if not selected_indices:
            logging.debug(
                "PlaylistSelector: get_selected_items_string - No items selected."
            )
            return None
        result = ",".join(map(str, sorted(selected_indices)))
        logging.debug(
            f"PlaylistSelector: get_selected_items_string - Selected: {result}"
        )
        return result

    def reset(self):
        """Resets the component."""
        logging.debug("PlaylistSelector: Resetting.")
        self.clear_items()

    def enable(self):
        """Enables control buttons and checkboxes."""
        logging.debug("PlaylistSelector: Enabling controls.")
        self.select_all_button.configure(state="normal")
        self.deselect_all_button.configure(state="normal")
        for cb, var, index in self.checkboxes_data:
            if cb and isinstance(cb, ctk.CTkCheckBox):
                cb.configure(state="normal")

    def disable(self):
        """Disables control buttons and checkboxes."""
        logging.debug("PlaylistSelector: Disabling controls.")
        self.select_all_button.configure(state="disabled")
        self.deselect_all_button.configure(state="disabled")
        for cb, var, index in self.checkboxes_data:
            if cb and isinstance(cb, ctk.CTkCheckBox):
                cb.configure(state="disabled")
