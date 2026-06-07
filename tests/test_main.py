import sys

from src.common.mod_manager import UE4SSModManager
from src.main import find_assets, find_mods_folder


def test_find_mods_folder_direct(tmp_path):
	ue4ss_dir = tmp_path / "UE4SS"
	ue4ss_dir.mkdir()
	mods_dir = ue4ss_dir / "Mods"
	mods_dir.mkdir()

	assert find_mods_folder(mods_dir) == mods_dir
	assert find_mods_folder(ue4ss_dir) == mods_dir
	assert find_mods_folder(tmp_path) == mods_dir


def test_find_mods_folder_not_found(tmp_path):
	assert find_mods_folder(tmp_path) is None


def test_find_assets(tmp_path):
	assets_dir = tmp_path / "assets" / "img"
	assets_dir.mkdir(parents=True)
	logo = assets_dir / "ue.svg"
	logo.touch()
	icon = assets_dir / "ue.ico"
	icon.touch()

	found_logo, found_icon = find_assets(tmp_path)
	assert found_logo == logo
	assert found_icon == icon


def test_find_assets_partial(tmp_path):
	assets_dir = tmp_path / "assets" / "img"
	assets_dir.mkdir(parents=True)
	logo = assets_dir / "ue.svg"
	logo.touch()

	found_logo, found_icon = find_assets(tmp_path)
	assert found_logo == logo
	assert found_icon is None


def test_find_assets_other_locations(tmp_path):
	# Test base_path / "img"
	img_dir = tmp_path / "img"
	img_dir.mkdir()
	logo = img_dir / "ue.svg"
	logo.touch()
	icon = img_dir / "ue.ico"
	icon.touch()

	found_logo, found_icon = find_assets(tmp_path)
	assert found_logo == logo
	assert found_icon == icon


def test_find_mods_folder_parent_search(tmp_path):
	# Create structure: tmp_path / UE4SS / Mods / Sub / SubSub
	mods_dir = tmp_path / "UE4SS" / "Mods"
	mods_dir.mkdir(parents=True)
	deep_dir = mods_dir / "Sub" / "SubSub"
	deep_dir.mkdir(parents=True)


def test_find_mods_folder_frozen(tmp_path, monkeypatch):
	# Mock sys.frozen and sys.executable
	monkeypatch.setattr(sys, "frozen", True, raising=False)

	# Create a dummy executable path
	exe_dir = tmp_path / "bin"
	exe_dir.mkdir()
	exe_path = exe_dir / "app.exe"
	monkeypatch.setattr(sys, "executable", str(exe_path))

	# Create Mods folder relative to "executable"
	mods_dir = exe_dir / "UE4SS" / "Mods"
	mods_dir.mkdir(parents=True)

	assert find_mods_folder() == mods_dir


def test_find_assets_frozen(tmp_path, monkeypatch):
	monkeypatch.setattr(sys, "frozen", True, raising=False)
	exe_dir = tmp_path / "bin"
	exe_dir.mkdir()
	exe_path = exe_dir / "app.exe"
	monkeypatch.setattr(sys, "executable", str(exe_path))

	assets_dir = exe_dir / "assets" / "img"
	assets_dir.mkdir(parents=True)
	logo = assets_dir / "ue.svg"
	logo.touch()

	found_logo, _ = find_assets()
	assert found_logo == logo


def test_main_startup_no_mods_folder(monkeypatch, tmp_path):
	# Mock find_mods_folder to return None
	monkeypatch.setattr("src.main.find_mods_folder", lambda: None)

	# Mock ctk and show_startup_error to avoid GUI
	monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

	# We want to catch the sys.exit(1) or the return
	# Since show_startup_error is defined inside main(), we might need to mock it differently
	# or mock the things it calls.

	# Actually, it's easier to mock the whole show_startup_error if we can,
	# but it's nested. Let's mock CTk instead.

	class MockApp:
		def withdraw(self):
			pass

		def destroy(self):
			pass

		def mainloop(self):
			pass

		def update_idletasks(self):
			pass

		def winfo_reqwidth(self):
			return 100

		def winfo_reqheight(self):
			return 100

		def winfo_screenwidth(self):
			return 1000

		def winfo_screenheight(self):
			return 1000

		def geometry(self, geo):
			pass

		def protocol(self, name, cmd):
			pass

		def title(self, title):
			pass

		def attributes(self, *args, **kwargs):
			pass

		def pack(self, *args, **kwargs):
			pass

	monkeypatch.setattr("customtkinter.CTk", MockApp)
	monkeypatch.setattr("customtkinter.CTkFrame", lambda master: MockApp())
	monkeypatch.setattr("customtkinter.CTkLabel", lambda master, text, wraplength: MockApp())
	monkeypatch.setattr("customtkinter.CTkButton", lambda master, text, command, width: MockApp())
	monkeypatch.setattr("customtkinter.CTkToplevel", lambda master: MockApp())

	# Mock sys.exit to avoid exiting the test runner
	exit_calls = []
	monkeypatch.setattr(sys, "exit", exit_calls.append)

	from src.main import main

	main()

	# The show_startup_error calls app.mainloop() which we mocked.


def test_main_startup_full(monkeypatch, tmp_path):
	# Mock find_mods_folder and find_assets to return valid paths
	ue4ss_dir = tmp_path / "UE4SS"
	mods_dir = ue4ss_dir / "Mods"
	mods_dir.mkdir(parents=True)
	(mods_dir / "Mod1").mkdir()
	(mods_dir / "Mod1" / "scripts").mkdir()
	(mods_dir / "Mod1" / "scripts" / "main.lua").touch()

	monkeypatch.setattr("src.main.find_mods_folder", lambda: mods_dir)
	monkeypatch.setattr("src.main.find_assets", lambda: (None, None))

	# Mock start_gui to avoid GUI
	gui_calls = []
	monkeypatch.setattr("src.main.start_gui", lambda manager, logo, icon: gui_calls.append(manager))

	# Mock ctk
	monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

	from src.main import main

	main()

	assert len(gui_calls) == 1
	assert isinstance(gui_calls[0], UE4SSModManager)


def test_main_invalid_mod_folder_exception(monkeypatch, tmp_path):
	# Mock find_mods_folder to return a path
	ue4ss_dir = tmp_path / "UE4SS"
	mods_dir = ue4ss_dir / "Mods"
	mods_dir.mkdir(parents=True)

	monkeypatch.setattr("src.main.find_mods_folder", lambda: mods_dir)
	monkeypatch.setattr("src.main.find_assets", lambda: (None, None))

	# Mock UE4SSModManager to raise InvalidModFolderException
	from src.common.exceptions import InvalidModFolderException

	def mock_init(*args, **kwargs):
		raise InvalidModFolderException("Invalid folder")

	monkeypatch.setattr("src.main.UE4SSModManager", mock_init)

	# Mock ctk and show_startup_error parts
	monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

	class MockApp:
		def __init__(self, *args, **kwargs):
			pass

		def withdraw(self):
			pass

		def destroy(self):
			pass

		def mainloop(self):
			pass

		def update_idletasks(self):
			pass

		def winfo_reqwidth(self):
			return 100

		def winfo_reqheight(self):
			return 100

		def winfo_screenwidth(self):
			return 1000

		def winfo_screenheight(self):
			return 1000

		def geometry(self, geo):
			pass

		def protocol(self, name, cmd):
			pass

		def title(self, title):
			pass

		def attributes(self, *args, **kwargs):
			pass

		def pack(self, *args, **kwargs):
			pass

	monkeypatch.setattr("customtkinter.CTk", MockApp)
	monkeypatch.setattr("customtkinter.CTkFrame", lambda master: MockApp())
	monkeypatch.setattr("customtkinter.CTkLabel", lambda master, text, wraplength: MockApp())
	monkeypatch.setattr("customtkinter.CTkButton", lambda master, text, command, width: MockApp())
	monkeypatch.setattr("customtkinter.CTkToplevel", lambda master: MockApp())

	from src.main import main

	main()
	# Should handle the exception and return


def test_main_unexpected_exception(monkeypatch, tmp_path):
	monkeypatch.setattr("src.main.find_mods_folder", lambda: Exception("Unexpected"))

	# Mock ctk
	monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

	# Since CTk might be called in show_startup_error
	class MockApp:
		def __init__(self, *args, **kwargs):
			pass

		def withdraw(self):
			pass

		def destroy(self):
			pass

		def mainloop(self):
			pass

		def update_idletasks(self):
			pass

		def winfo_reqwidth(self):
			return 100

		def winfo_reqheight(self):
			return 100

		def winfo_screenwidth(self):
			return 1000

		def winfo_screenheight(self):
			return 1000

		def geometry(self, geo):
			pass

		def protocol(self, name, cmd):
			pass

		def title(self, title):
			pass

		def attributes(self, *args, **kwargs):
			pass

		def pack(self, *args, **kwargs):
			pass

	monkeypatch.setattr("customtkinter.CTk", MockApp)
	monkeypatch.setattr("customtkinter.CTkFrame", lambda master: MockApp())
	monkeypatch.setattr("customtkinter.CTkLabel", lambda master, text, wraplength: MockApp())
	monkeypatch.setattr("customtkinter.CTkButton", lambda master, text, command, width: MockApp())
	monkeypatch.setattr("customtkinter.CTkToplevel", lambda master: MockApp())

	from src.main import main

	main()
	# Should handle the exception and return
