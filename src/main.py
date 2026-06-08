#!/usr/bin/env python3
import sys
from pathlib import Path

from loguru import logger

from src.common.exceptions import InvalidModException, InvalidModFolderException
from src.common.gui import start_gui
from src.common.mod_manager import UE4SSModManager, PakModManager


def find_game_root(base_path: Path | None = None) -> Path | None:
    """
    Find the game root folder path.

    Args:
        base_path: The base path to start searching from. If None, it uses the application root.

    Returns:
        The path to the game root folder or None if not found.
    """
    if base_path is None:
        base_path = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent

    current = base_path
    for _ in range(5):  # Check current and 4 parents
        # Game root usually contains "Binaries" and "Content"
        if (current / "Binaries").is_dir() and (current / "Content").is_dir():
            return current

        # Check if we are inside Binaries/Win64/UE4SS/Mods or Binaries/Win64/ue4ss/Mods
        if current.name.upper() == "MODS" and current.parent.name.upper() in ("UE4SS", "UE4SS"):
            if current.parent.parent.name.upper() == "WIN64" and current.parent.parent.parent.name.upper() == "BINARIES":
                potential_root = current.parent.parent.parent.parent
                if (potential_root / "Binaries").is_dir() and (potential_root / "Content").is_dir():
                    return potential_root

        if current.parent == current:  # Root reached
            break
        current = current.parent

    # Fallback to current directory if it looks like a game root
    if (base_path / "Binaries").is_dir() and (base_path / "Content").is_dir():
        return base_path

    return None


def find_mods_folder(base_path: Path | None = None) -> Path | None:
    """
    Find the UE4SS mods folder.

    Args:
        base_path: The base path to start searching from.

    Returns:
        The path to the UE4SS mods folder or None if not found.
    """
    game_root = find_game_root(base_path)
    if not game_root:
        return None

    ue4ss_mods_path = game_root / "Binaries" / "Win64" / "UE4SS" / "Mods"
    if not ue4ss_mods_path.exists():
        ue4ss_mods_path = game_root / "Binaries" / "Win64" / "ue4ss" / "Mods"

    return ue4ss_mods_path if ue4ss_mods_path.exists() else None


def find_assets(base_path: Path | None = None) -> tuple[Path | None, Path | None, Path | None]:
    """
    Find the paths to the logo and icon assets.

    Args:
        base_path: The base path to start searching from. If None, it uses the application root.

    Returns:
        A tuple containing the paths to the logo, dark logo, and icon assets.
    """
    if base_path is None:
        base_path = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent

    possible_locations = [
        base_path / "assets" / "img",
        base_path.parent / "assets" / "img",
        base_path / "img",
        base_path.parent / "img",
    ]

    logo_path = None
    dark_logo_path = None
    icon_path = None

    for location in possible_locations:
        if not logo_path:
            # Prefer PNG for better cross-platform compatibility
            for ext in [".png", ".svg"]:
                if (location / f"logo{ext}").exists():
                    logo_path = location / f"logo{ext}"
                    break
                if (location / f"ue{ext}").exists():
                    logo_path = location / f"ue{ext}"
                    break

        if not dark_logo_path:
            for ext in [".png", ".svg"]:
                if (location / f"logo_white{ext}").exists():
                    dark_logo_path = location / f"logo_white{ext}"
                    break

        if not icon_path:
            # On Linux, .png works better for window icons than .ico
            for ext in [".png", ".ico"]:
                if (location / f"ue{ext}").exists():
                    icon_path = location / f"ue{ext}"
                    break

        if logo_path and dark_logo_path and icon_path:
            break

    return logo_path, dark_logo_path, icon_path


def main() -> None:
    """Main entry point for the application."""
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")

    def show_startup_error(message: str) -> None:
        app = ctk.CTk()
        app.withdraw()

        dialog = ctk.CTkToplevel(app)
        dialog.title("Error")
        dialog.attributes("-topmost", True)

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        error_label = ctk.CTkLabel(frame, text=message, wraplength=360)
        error_label.pack(padx=10, pady=(10, 20))

        ok_button = ctk.CTkButton(
            frame,
            text="OK",
            command=lambda: (dialog.destroy(), app.destroy(), sys.exit(1)),
            width=100,
        )
        ok_button.pack(pady=(0, 10))

        dialog.protocol("WM_DELETE_WINDOW", lambda: (dialog.destroy(), app.destroy(), sys.exit(1)))

        dialog.update_idletasks()
        width = dialog.winfo_reqwidth()
        height = dialog.winfo_reqheight()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        app.mainloop()

    try:
        game_root = find_game_root()
        if not game_root:
            show_startup_error(
                "Could not find the game root folder.\nPlease place this executable in the game's root folder or UE4SS/Mods folder.",
            )
            return

        logo_path, dark_logo_path, icon_path = find_assets()

        try:
            ue4ss_mods_path = find_mods_folder(game_root)
            pak_mods_path = game_root / "Content" / "Paks"

            managers = []
            if ue4ss_mods_path and ue4ss_mods_path.exists():
                managers.append(UE4SSModManager(ue4ss_mods_path))
            if pak_mods_path.exists():
                managers.append(PakModManager(pak_mods_path))

            if not managers:
                show_startup_error("No mod folders found.")
                return

        except (InvalidModFolderException, InvalidModException) as e:
            show_startup_error(str(e))
            return

        start_gui(managers, logo_path, icon_path, dark_logo_path)

    except Exception as e:
        logger.exception("An unexpected error occurred")
        show_startup_error(f"An unexpected error occurred:\n{e}")


if __name__ == "__main__":
    main()
