#!/usr/bin/env python3
import sys
from pathlib import Path

from loguru import logger

from src.common.exceptions import InvalidModException, InvalidModFolderException
from src.common.gui import start_gui
from src.common.mod_manager import UE4SSModManager


def find_mods_folder(base_path: Path | None = None) -> Path | None:
	"""
	Find the mods folder path.

	Args:
		base_path: The base path to start searching from. If None, it uses the application root.

	Returns:
		The path to the mods folder or None if not found.
	"""
	if base_path is None:
		base_path = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.parent

	current = base_path
	for _ in range(5):  # Check current and 4 parents
		# Check if current is the Mods folder
		if current.name.upper() == "MODS" and current.parent.name.upper() == "UE4SS":
			return current

		# Check if current/Mods is the Mods folder
		mods_path = current / "Mods"
		if mods_path.is_dir() and mods_path.parent.name.upper() == "UE4SS":
			return mods_path

		# Check if current/UE4SS/Mods is the Mods folder
		ue4ss_mods_path = current / "UE4SS" / "Mods"
		if ue4ss_mods_path.is_dir():
			return ue4ss_mods_path

		if current.parent == current:  # Root reached
			break
		current = current.parent

	return None


def find_assets(base_path: Path | None = None) -> tuple[Path, Path]:
	"""
	Find the paths to the logo and icon assets.

	Args:
		base_path: The base path to start searching from. If None, it uses the application root.

	Returns:
		A tuple containing the paths to the logo and icon assets.
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
	icon_path = None

	for location in possible_locations:
		if (location / "ue.svg").exists():
			logo_path = location / "ue.svg"

		if (location / "ue.ico").exists():
			icon_path = location / "ue.ico"

		if logo_path and icon_path:
			break

	return logo_path, icon_path


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
		mods_folder = find_mods_folder()
		if not mods_folder:
			show_startup_error(
				"Could not find the UE4SS Mods folder.\nPlease place this executable in the UE4SS/Mods folder.",
			)
			return

		logo_path, icon_path = find_assets()

		try:
			mod_manager = UE4SSModManager(mods_folder)
		except (InvalidModFolderException, InvalidModException) as e:
			show_startup_error(str(e))
			return

		start_gui(mod_manager, logo_path, icon_path)

	except Exception as e:
		logger.exception("An unexpected error occurred")
		show_startup_error(f"An unexpected error occurred:\n{e}")


if __name__ == "__main__":
	main()
