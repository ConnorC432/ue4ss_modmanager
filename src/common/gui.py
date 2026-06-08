import os
import sys
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from loguru import logger
from PIL import Image, ImageTk

from src.common.mod import UE4SSMod
from src.common.mod_manager import ModManager, PakModManager, UE4SSModManager


class UE4SSModManagerGUI(ctk.CTk):
    """A GUI for managing UE4SS and PAK mods."""

    def __init__(
        self,
        mod_managers: list[ModManager],
        logo_path: Path | None = None,
        icon_path: Path | None = None,
        dark_logo_path: Path | None = None,
    ) -> None:
        """Initialize the UE4SSModManagerGUI."""
        super().__init__()

        self.mod_managers = mod_managers
        self.initial_mod_states = {}
        for manager in mod_managers:
            for mod in manager.mods:
                self.initial_mod_states[id(manager), mod.name] = mod.enabled

        self.mod_checkboxes = {}  # (manager_id, mod_name) -> checkbox

        self._setup_window(icon_path)
        self._setup_theme()

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self._create_header(logo_path, dark_logo_path)
        self._create_search_filter()
        self._create_controls()
        self._create_mod_list()
        self._create_save_section()
        self._create_status_bar()

        self.populate_mod_list()
        self.update_save_button_state()

    def _setup_window(self, icon_path: Path | None = None) -> None:
        """Configure the window properties."""
        self.title("UE4SS Mod Manager")

        # Make window size dynamic based on screen size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = int(screen_width * 0.6)
        window_height = int(screen_height * 0.6)
        self.minsize(window_width, window_height)

        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.center_window()

        if icon_path and icon_path.exists():
            try:
                if icon_path.suffix.lower() == ".ico" and sys.platform.startswith("win"):
                    self.iconbitmap(icon_path)
                else:
                    self.icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                    self.wm_iconphoto(True, self.icon_img)
            except (OSError, RuntimeError, AttributeError) as e:
                logger.error(f"Failed to set window icon: {e}")
            else:
                logger.debug(f"Set window icon: {icon_path}")

    @staticmethod
    def _setup_theme() -> None:
        """Set up the application theme."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def _create_header(self, logo_path: Path | None = None, dark_logo_path: Path | None = None) -> None:
        """Create the header with logo or title."""
        if not logo_path or not logo_path.exists():
            self._create_title_label()
        else:
            self._setup_logo(logo_path, dark_logo_path)

        self.header_frame = ctk.CTkFrame(self.main_frame)
        self.header_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.separator1 = ctk.CTkFrame(self.main_frame, height=1, fg_color="gray30")
        self.separator1.pack(fill="x", padx=10, pady=3)

    def _setup_logo(self, logo_path: Path, dark_logo_path: Path | None) -> None:
        """Set up the logo image."""
        try:
            pil_image = Image.open(logo_path)
            target_width, target_height = self._calculate_logo_size(pil_image)
            dark_pil_image = self._load_dark_logo(dark_logo_path, pil_image)
            self._display_logo(pil_image, dark_pil_image, target_width, target_height)
        except (OSError, RuntimeError) as e:
            logger.error(f"Failed to load logo image: {e}")
            self._create_title_label()
        else:
            logger.debug(f"Set logo image: {logo_path} (size: {target_width}x{target_height})")

    def _display_logo(
        self,
        pil_image: Image.Image,
        dark_pil_image: Image.Image,
        target_width: int,
        target_height: int,
    ) -> None:
        """Display the logo image in the GUI."""
        self.logo_image = ctk.CTkImage(
            light_image=pil_image,
            dark_image=dark_pil_image,
            size=(target_width, target_height),
        )
        self.logo_label = ctk.CTkLabel(self.main_frame, image=self.logo_image, text="")
        self.logo_label.pack(pady=(0, 15))

    @staticmethod
    def _calculate_logo_size(pil_image: Image.Image) -> tuple[int, int]:
        """Calculate the target size for the logo image.

        Args:
            pil_image: The PIL image object.

        Returns:
            A tuple of (width, height) for the target size.
        """
        max_logo_width = 300
        original_width, original_height = pil_image.size
        aspect_ratio = original_width / original_height

        target_height = 54
        target_width = int(target_height * aspect_ratio)

        if target_width > max_logo_width:
            target_width = max_logo_width
            target_height = int(target_width / aspect_ratio)

        return target_width, target_height

    def _load_dark_logo(self, dark_logo_path: Path | None, default_image: Image.Image) -> Image.Image:
        """Load the dark logo image if available.

        Args:
            dark_logo_path: Path to the dark logo image.
            default_image: Default image to return if dark logo loading fails.

        Returns:
            The loaded dark logo image or the default image.
        """
        if dark_logo_path and dark_logo_path.exists():
            try:
                return Image.open(dark_logo_path)
            except (OSError, RuntimeError) as e:
                logger.warning(f"Failed to load dark logo image: {e}")
        return default_image

    def _create_title_label(self) -> None:
        """Create the title label if no logo is available."""
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="UE4SS Mod Manager",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.pack(pady=(0, 15))

    def _create_search_filter(self) -> None:
        """Create the search filter components."""
        self.list_label = ctk.CTkLabel(
            self.header_frame,
            text="Available Mods:",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.list_label.pack(side="left", padx=10, pady=5)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.filter_mods())
        self.search_entry = ctk.CTkEntry(
            self.header_frame,
            placeholder_text="Search mods...",
            textvariable=self.search_var,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=10, pady=5)

    def _create_controls(self) -> None:
        """Create the control buttons section."""
        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.toggle_all_var = ctk.BooleanVar(value=False)
        self.toggle_all_checkbox = ctk.CTkCheckBox(
            self.controls_frame,
            text="Toggle All",
            variable=self.toggle_all_var,
            onvalue=True,
            offvalue=False,
            command=self.toggle_all_mods,
            width=24,
        )
        self.toggle_all_checkbox.pack(side="left", padx=10, pady=5)

        self.import_button = ctk.CTkButton(
            self.controls_frame,
            text="Import Mod",
            command=self.import_mod,
            width=100,
        )
        self.import_button.pack(side="left", padx=5, pady=5)

        self.refresh_button = ctk.CTkButton(
            self.controls_frame,
            text="Refresh",
            command=self.refresh_mods,
            width=80,
        )
        self.refresh_button.pack(side="right", padx=5, pady=5)

        self.reset_button = ctk.CTkButton(
            self.controls_frame,
            text="Reset",
            command=self.reset_mods,
            width=80,
        )
        self.reset_button.pack(side="right", padx=5, pady=5)

    def _create_mod_list(self) -> None:
        """Create the scrollable mod list area."""
        self.mod_list_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.mod_list_frame.pack(fill="both", expand=True, padx=10, pady=8)

    def _create_save_section(self) -> None:
        """Create the save section."""
        self.save_button = ctk.CTkButton(
            self.main_frame,
            text="Save Changes",
            command=self.save_changes,
            width=200,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.save_button.pack(pady=(10, 5), anchor="center")

    def _create_status_bar(self) -> None:
        """Create the status bar at the bottom."""
        total_mods = sum(len(m.mods) for m in self.mod_managers)
        self.status_bar = ctk.CTkLabel(
            self.main_frame,
            text=f"Loaded {total_mods} mods",
            font=ctk.CTkFont(size=12),
        )
        self.status_bar.pack(pady=(8, 0), anchor="w")

    def update_save_button_state(self) -> None:
        """Update the save button state."""
        if self.initial_mod_states == self.get_mod_status():
            self.save_button.configure(state="disabled")
        else:
            self.save_button.configure(state="normal")

    def refresh_mods(self) -> None:
        """Reload mods from disk."""
        self.initial_mod_states = {}
        for manager in self.mod_managers:
            manager.mods = manager.load_mods()
            for mod in manager.mods:
                self.initial_mod_states[id(manager), mod.name] = mod.enabled

        self.populate_mod_list()

        total_mods = sum(len(m.mods) for m in self.mod_managers)
        self.status_bar.configure(text=f"Refreshed {total_mods} mods")

    def populate_mod_list(self) -> None:
        """Populate the mod list with checkboxes for each mod."""
        for widget in self.mod_list_frame.winfo_children():
            widget.destroy()

        self.mod_checkboxes = {}

        # Flatten mods from all managers
        all_mods_with_managers = []
        for manager in self.mod_managers:
            all_mods_with_managers.extend((manager, mod) for mod in manager.mods)

        # Sort mods by name
        all_mods_with_managers.sort(key=lambda x: x[1].name.lower())

        for manager, mod in all_mods_with_managers:
            is_ue4ss = isinstance(mod, UE4SSMod)

            # Filter based on search text
            search_text = str(self.search_var.get()).lower()
            if search_text and search_text not in str(mod.name).lower():
                continue

            frame = ctk.CTkFrame(self.mod_list_frame)
            frame.pack(fill="x", padx=5, pady=2)

            # Mod type tag
            type_tag = ctk.CTkLabel(
                frame,
                text=f"[{mod.mod_type}]",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="gray",
                width=50,
            )
            type_tag.pack(side="left", padx=(5, 0))

            checkbox = ctk.CTkCheckBox(
                frame,
                text=f"{mod.name}",
                variable=ctk.BooleanVar(value=mod.enabled),
                command=self.update_save_button_state,
                onvalue=True,
                offvalue=False,
                width=24,
            )
            checkbox.pack(side="left", padx=10, pady=5)

            if is_ue4ss:
                script_count = ctk.CTkLabel(
                    frame,
                    text=f"{len(mod.scripts)} script(s)",
                    font=ctk.CTkFont(size=12),
                    text_color="gray",
                )
                script_count.pack(side="right", padx=10, pady=5)

            self.mod_checkboxes[id(manager), mod.name] = checkbox

        visible_count = len(self.mod_checkboxes)
        enabled_count = sum(1 for cb in self.mod_checkboxes.values() if cb.get())
        self.status_bar.configure(text=f"Showing {visible_count} mods ({enabled_count} enabled)")

    def reset_mods(self) -> None:
        """Reset mods to their initial states when the app was launched."""
        for (manager_id, mod_name), checkbox in self.mod_checkboxes.items():
            initial_state = self.initial_mod_states.get((manager_id, mod_name), False)
            if initial_state:
                checkbox.select()
            else:
                checkbox.deselect()

        self.status_bar.configure(text="Mods reset to initial state. Click Save to apply.")
        self.update_save_button_state()

    def show_warning(self, title: str, message: str, on_ok: callable, on_cancel: callable) -> None:
        """Show a warning popup with OK and Cancel buttons."""
        warning_window = ctk.CTkToplevel(self)
        warning_window.title(title)
        warning_window.geometry("450x200")
        warning_window.transient(self)
        warning_window.grab_set()
        warning_window.attributes("-topmost", True)
        warning_window.after(100, lambda: warning_window.attributes("-topmost", False))
        warning_window.update_idletasks()
        width = warning_window.winfo_width()
        height = warning_window.winfo_height()
        x = (warning_window.winfo_screenwidth() // 2) - (width // 2)
        y = (warning_window.winfo_screenheight() // 2) - (height // 2)
        warning_window.geometry(f"{width}x{height}+{x}+{y}")

        frame = ctk.CTkFrame(warning_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        warning_label = ctk.CTkLabel(frame, text=message, wraplength=410, justify="left")
        warning_label.pack(padx=10, pady=(10, 20))

        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=lambda: (on_cancel(), warning_window.destroy()),
            width=100,
        )
        cancel_button.pack(side="left", padx=10, pady=10)

        ok_button = ctk.CTkButton(
            button_frame,
            text="OK",
            command=lambda: (on_ok(), warning_window.destroy()),
            width=100,
        )
        ok_button.pack(side="right", padx=10, pady=10)

    def get_mod_status(self) -> dict[tuple[int, str], bool]:
        """
        Get the current status of all mods from the checkboxes.

        Returns:
            A mapping with (manager_id, mod_name) as keys and their enabled status as values.
        """
        mod_status = {}
        for (manager_id, mod_name), checkbox in self.mod_checkboxes.items():
            mod_status[manager_id, mod_name] = checkbox.get()

        return mod_status

    def save_changes(self) -> None:
        """Save the changes to the mods."""
        for manager in self.mod_managers:
            updated_mods = []
            for mod in manager.mods:
                checkbox = self.mod_checkboxes.get((id(manager), mod.name))
                if checkbox:
                    mod.enabled = checkbox.get()
                    updated_mods.append(mod)

            if isinstance(manager, UE4SSModManager):
                manager.parse_mods(mods=updated_mods)
            else:
                for mod in updated_mods:
                    if mod.enabled:
                        mod.enable()
                    else:
                        mod.disable()

        self.status_bar.configure(text="Changes saved.")
        self.populate_mod_list()
        self.initial_mod_states = self.get_mod_status()
        self.update_save_button_state()

    def toggle_all_mods(self) -> None:
        """Toggle all mods on or off based on the Toggle All checkbox."""
        new_state = self.toggle_all_var.get()

        for checkbox in self.mod_checkboxes.values():
            if new_state:
                checkbox.select()
            else:
                checkbox.deselect()

        self.status_bar.configure(text=f"All mods {'enabled' if new_state else 'disabled'}. Click Save to apply.")

    def filter_mods(self) -> None:
        """Filter mods based on search text."""
        self.populate_mod_list()

    def _detect_mod_type(self, archive_path: Path) -> ModManager:
        """Detect mod type by looking into the archive and return the appropriate manager.

        Args:
            archive_path: Path to the mod archive.

        Returns:
            The mod manager that can handle this mod type.

        Raises:
            ValueError: If the mod type cannot be determined or no manager is available.
        """
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.unpack_archive(str(archive_path), extract_dir=temp_dir)

            is_ue4ss = False
            is_pak = False

            for _root, dirs, files in os.walk(temp_dir):
                if "scripts" in [d.lower() for d in dirs] or "dlls" in [d.lower() for d in dirs]:
                    is_ue4ss = True
                    break
                if any(f.lower().endswith(".pak") for f in files):
                    is_pak = True

            manager = None
            if is_ue4ss:
                manager = next((m for m in self.mod_managers if isinstance(m, UE4SSModManager)), None)
            elif is_pak:
                manager = next((m for m in self.mod_managers if isinstance(m, PakModManager)), None)

            if not manager:
                if is_ue4ss:
                    msg = "UE4SS mod detected, but no UE4SS mod manager is active."
                    raise ValueError(msg)
                if is_pak:
                    msg = "PAK mod detected, but no PAK mod manager is active."
                    raise ValueError(msg)
                msg = "Could not determine mod type from archive (no scripts, dlls, or .pak files found)."
                raise ValueError(msg)

            return manager

    def import_mod(self) -> None:
        """Open a file dialog to import a mod archive."""
        import shutil

        supported_extensions = []
        for _, extensions, _ in shutil.get_unpack_formats():
            supported_extensions.extend(extensions)

        extensions_str = " ".join(f"*{ext}" for ext in supported_extensions)

        file_path = filedialog.askopenfilename(
            title="Select Mod Archive",
            filetypes=[("Mod Archives", extensions_str), ("All files", "*.*")],
        )

        if not file_path:
            return

        archive_path = Path(file_path)
        try:
            manager = self._detect_mod_type(archive_path)
        except (ValueError, OSError) as e:
            logger.exception(f"Error initiating import: {e}")
            self.show_error("Import Error", str(e))
            return

        mod_name = archive_path.stem
        if archive_path.name.lower().endswith(".tar.gz"):
            mod_name = archive_path.name[:-7]
        elif archive_path.name.lower().endswith(".tar.bz2"):
            mod_name = archive_path.name[:-8]
        elif archive_path.name.lower().endswith(".tar.xz"):
            mod_name = archive_path.name[:-7]

        def do_import(overwrite: bool = False) -> None:
            try:
                imported_mod_name = manager.import_mod_archive(archive_path, overwrite=overwrite)
                self.refresh_mods()
                self.status_bar.configure(text=f"Successfully imported mod: {imported_mod_name}")
            except (ValueError, OSError) as e:
                logger.exception(f"Error importing mod: {e}")
                self.show_error("Import Error", str(e))

        already_exists = False
        if isinstance(manager, UE4SSModManager) and (manager.path / mod_name).exists():
            already_exists = True

        if isinstance(manager, UE4SSModManager) and already_exists:
            self.show_warning(
                "Overwrite Mod",
                f"Mod '{mod_name}' already exists. Do you want to overwrite it?",
                on_ok=lambda: do_import(overwrite=True),
                on_cancel=lambda: None,
            )
        else:
            do_import(overwrite=False)

    def center_window(self) -> None:
        """Center the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def show_error(self, title: str, message: str) -> None:
        """Show an error popup with the given title and message."""
        error_window = ctk.CTkToplevel(self)
        error_window.title(title)
        error_window.geometry("450x250")
        error_window.transient(self)
        error_window.grab_set()
        error_window.attributes("-topmost", True)

        frame = ctk.CTkFrame(error_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        error_label = ctk.CTkLabel(frame, text=message, wraplength=400, justify="left")
        error_label.pack(padx=10, pady=(10, 20), fill="both", expand=True)

        ok_button = ctk.CTkButton(frame, text="OK", command=error_window.destroy, width=100)
        ok_button.pack(pady=(0, 10))

        error_window.update_idletasks()
        width = error_window.winfo_width()
        height = error_window.winfo_height()
        x = (error_window.winfo_screenwidth() // 2) - (width // 2)
        y = (error_window.winfo_screenheight() // 2) - (height // 2)
        error_window.geometry(f"{width}x{height}+{x}+{y}")


def start_gui(
    mod_managers: list[ModManager],
    logo_path: Path | None = None,
    icon_path: Path | None = None,
    dark_logo_path: Path | None = None,
) -> None:
    """
    Start the GUI with the given mod managers.

    Args:
        mod_managers: A list of ModManager instances
        logo_path: Path to the logo image file
        icon_path: Path to the icon file (.ico)
        dark_logo_path: Path to the dark mode logo image file
    """
    app = UE4SSModManagerGUI(mod_managers, logo_path, icon_path, dark_logo_path)
    app.mainloop()
