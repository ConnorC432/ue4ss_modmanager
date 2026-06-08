import sys
from typing import Never
from unittest.mock import MagicMock

from src.common.mod_manager import UE4SSModManager
from src.main import find_assets, find_mods_folder


def test_find_mods_folder_direct(tmp_path) -> None:
    # Setup game root
    bin_dir = tmp_path / "Binaries"
    bin_dir.mkdir()
    (tmp_path / "Content").mkdir()

    ue4ss_dir = bin_dir / "Win64" / "UE4SS"
    ue4ss_dir.mkdir(parents=True)
    mods_dir = ue4ss_dir / "Mods"
    mods_dir.mkdir()

    assert find_mods_folder(tmp_path) == mods_dir
    assert find_mods_folder(mods_dir) == mods_dir
    assert find_mods_folder(ue4ss_dir) == mods_dir


def test_find_mods_folder_not_found(tmp_path) -> None:
    assert find_mods_folder(tmp_path) is None


def test_find_assets(tmp_path) -> None:
    assets_dir = tmp_path / "assets" / "img"
    assets_dir.mkdir(parents=True)
    logo = assets_dir / "ue.svg"
    logo.touch()
    icon = assets_dir / "ue.ico"
    icon.touch()

    found_logo, found_dark_logo, found_icon = find_assets(tmp_path)
    assert found_logo == logo
    assert found_dark_logo is None
    assert found_icon == icon


def test_find_assets_with_dark_logo(tmp_path) -> None:
    assets_dir = tmp_path / "assets" / "img"
    assets_dir.mkdir(parents=True)
    logo = assets_dir / "logo.png"
    logo.touch()
    dark_logo = assets_dir / "logo_white.png"
    dark_logo.touch()
    icon = assets_dir / "ue.png"
    icon.touch()

    found_logo, found_dark_logo, found_icon = find_assets(tmp_path)
    assert found_logo == logo
    assert found_dark_logo == dark_logo
    assert found_icon == icon


def test_find_assets_partial(tmp_path) -> None:
    assets_dir = tmp_path / "assets" / "img"
    assets_dir.mkdir(parents=True)
    logo = assets_dir / "ue.svg"
    logo.touch()

    found_logo, found_dark_logo, found_icon = find_assets(tmp_path)
    assert found_logo == logo
    assert found_dark_logo is None
    assert found_icon is None


def test_find_assets_other_locations(tmp_path) -> None:
    # Test base_path / "img"
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    logo = img_dir / "ue.svg"
    logo.touch()
    icon = img_dir / "ue.ico"
    icon.touch()

    found_logo, found_dark_logo, found_icon = find_assets(tmp_path)
    assert found_logo == logo
    assert found_dark_logo is None
    assert found_icon == icon


def test_find_mods_folder_parent_search(tmp_path) -> None:
    # Create structure: tmp_path / UE4SS / Mods / Sub / SubSub
    mods_dir = tmp_path / "UE4SS" / "Mods"
    mods_dir.mkdir(parents=True)
    deep_dir = mods_dir / "Sub" / "SubSub"
    deep_dir.mkdir(parents=True)


def test_find_mods_folder_frozen(tmp_path, monkeypatch) -> None:
    # Mock sys.frozen and sys.executable
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    # Create a dummy executable path
    exe_dir = tmp_path / "bin"
    exe_dir.mkdir()
    # Mock game root structure
    (exe_dir / "Binaries").mkdir()
    (exe_dir / "Content").mkdir()

    exe_path = exe_dir / "app.exe"
    monkeypatch.setattr(sys, "executable", str(exe_path))

    # Create Mods folder relative to "executable"
    mods_dir = exe_dir / "Binaries" / "Win64" / "UE4SS" / "Mods"
    mods_dir.mkdir(parents=True)

    assert find_mods_folder() == mods_dir


def test_find_assets_frozen(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    exe_dir = tmp_path / "bin"
    exe_dir.mkdir()
    exe_path = exe_dir / "app.exe"
    monkeypatch.setattr(sys, "executable", str(exe_path))

    assets_dir = exe_dir / "assets" / "img"
    assets_dir.mkdir(parents=True)
    logo = assets_dir / "ue.svg"
    logo.touch()

    found_logo, _, _ = find_assets()
    assert found_logo == logo


def test_main_startup_no_mods_folder(monkeypatch, tmp_path) -> None:
    # Mock find_mods_folder to return None
    monkeypatch.setattr("src.main.find_mods_folder", lambda *args, **kwargs: None)

    # Mock ctk and show_startup_error to avoid GUI
    monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

    # We want to catch the sys.exit(1) or the return
    # Since show_startup_error is defined inside main(), we might need to mock it differently
    # or mock the things it calls.

    # Actually, it's easier to mock the whole show_startup_error if we can,
    # but it's nested. Let's mock CTk instead.

    class MockApp:
        def withdraw(self) -> None:
            pass

        def destroy(self) -> None:
            pass

        def mainloop(self) -> None:
            pass

        def update_idletasks(self) -> None:
            pass

        def winfo_reqwidth(self) -> int:
            return 100

        def winfo_reqheight(self) -> int:
            return 100

        def winfo_screenwidth(self) -> int:
            return 1000

        def winfo_screenheight(self) -> int:
            return 1000

        def wm_iconphoto(self, *args, **kwargs) -> None:
            pass

        def iconbitmap(self, *args, **kwargs) -> None:
            pass

        def geometry(self, geo) -> None:
            pass

        def protocol(self, name, cmd) -> None:
            pass

        def title(self, title) -> None:
            pass

        def attributes(self, *args, **kwargs) -> None:
            pass

        def pack(self, *args, **kwargs) -> None:
            pass

    monkeypatch.setattr("customtkinter.CTk", MockApp)
    monkeypatch.setattr("customtkinter.CTkFrame", lambda *args, **kwargs: MockApp())
    monkeypatch.setattr("customtkinter.CTkLabel", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr("customtkinter.CTkButton", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr("customtkinter.CTkToplevel", lambda *args, **kwargs: MockApp())

    # Mock sys.exit to avoid exiting the test runner
    exit_calls = []
    monkeypatch.setattr(sys, "exit", exit_calls.append)

    from src.main import main

    main()

    # The show_startup_error calls app.mainloop() which we mocked.


def test_main_startup_full(monkeypatch, tmp_path) -> None:
    # Mock find_game_root and find_assets to return valid paths
    game_root = tmp_path
    (game_root / "Binaries").mkdir()
    (game_root / "Content").mkdir()

    ue4ss_dir = game_root / "Binaries" / "Win64" / "UE4SS"
    mods_dir = ue4ss_dir / "Mods"
    mods_dir.mkdir(parents=True)
    (mods_dir / "Mod1").mkdir()
    (mods_dir / "Mod1" / "scripts").mkdir()
    (mods_dir / "Mod1" / "scripts" / "main.lua").touch()

    monkeypatch.setattr("src.main.find_game_root", lambda *args, **kwargs: game_root)
    monkeypatch.setattr("src.main.find_assets", lambda *args, **kwargs: (None, None, None))

    # Mock start_gui to avoid GUI
    gui_calls = []
    monkeypatch.setattr("src.main.start_gui", lambda manager, logo, icon, dark_logo: gui_calls.append(manager))

    # Mock ctk
    monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

    from src.main import main

    main()

    assert len(gui_calls) == 1
    assert isinstance(gui_calls[0], list)
    assert any(isinstance(m, UE4SSModManager) for m in gui_calls[0])


def test_main_invalid_mod_folder_exception(monkeypatch, tmp_path) -> None:
    # Mock find_mods_folder to return a path
    ue4ss_dir = tmp_path / "UE4SS"
    mods_dir = ue4ss_dir / "Mods"
    mods_dir.mkdir(parents=True)

    monkeypatch.setattr("src.main.find_mods_folder", lambda *args, **kwargs: mods_dir)
    monkeypatch.setattr("src.main.find_assets", lambda *args, **kwargs: (None, None, None))

    # Mock UE4SSModManager to raise InvalidModFolderException
    from src.common.exceptions import InvalidModFolderException

    def mock_init(*args, **kwargs) -> Never:
        msg = "Invalid folder"
        raise InvalidModFolderException(msg)

    monkeypatch.setattr("src.main.UE4SSModManager", mock_init)

    # Mock ctk and show_startup_error parts
    monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

    class MockApp:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def withdraw(self) -> None:
            pass

        def destroy(self) -> None:
            pass

        def mainloop(self) -> None:
            pass

        def update_idletasks(self) -> None:
            pass

        def winfo_reqwidth(self) -> int:
            return 100

        def winfo_reqheight(self) -> int:
            return 100

        def winfo_screenwidth(self) -> int:
            return 1000

        def winfo_screenheight(self) -> int:
            return 1000

        def wm_iconphoto(self, *args, **kwargs) -> None:
            pass

        def iconbitmap(self, *args, **kwargs) -> None:
            pass

        def geometry(self, geo) -> None:
            pass

        def protocol(self, name, cmd) -> None:
            pass

        def title(self, title) -> None:
            pass

        def attributes(self, *args, **kwargs) -> None:
            pass

        def pack(self, *args, **kwargs) -> None:
            pass

    monkeypatch.setattr("customtkinter.CTk", MockApp)
    monkeypatch.setattr("customtkinter.CTkFrame", lambda *args, **kwargs: MockApp())
    monkeypatch.setattr("customtkinter.CTkLabel", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr("customtkinter.CTkButton", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr("customtkinter.CTkToplevel", lambda *args, **kwargs: MockApp())

    from src.main import main

    main()
    # Should handle the exception and return


def test_main_unexpected_exception(monkeypatch, tmp_path) -> None:
    def mock_find_game_root(*args, **kwargs):
        msg = "Unexpected"
        raise ValueError(msg)
    monkeypatch.setattr("src.main.find_game_root", mock_find_game_root)
    monkeypatch.setattr("src.main.find_assets", lambda *args, **kwargs: (None, None, None))

    # Mock ctk
    monkeypatch.setattr("customtkinter.set_appearance_mode", lambda mode: None)

    # Since CTk might be called in show_startup_error
    class MockApp:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def withdraw(self) -> None:
            pass

        def destroy(self) -> None:
            pass

        def mainloop(self) -> None:
            pass

        def update_idletasks(self) -> None:
            pass

        def winfo_reqwidth(self) -> int:
            return 100

        def winfo_reqheight(self) -> int:
            return 100

        def winfo_screenwidth(self) -> int:
            return 1000

        def winfo_screenheight(self) -> int:
            return 1000

        def wm_iconphoto(self, *args, **kwargs) -> None:
            pass

        def iconbitmap(self, *args, **kwargs) -> None:
            pass

        def geometry(self, geo) -> None:
            pass

        def protocol(self, name, cmd) -> None:
            pass

        def title(self, title) -> None:
            pass

        def attributes(self, *args, **kwargs) -> None:
            pass

        def pack(self, *args, **kwargs) -> None:
            pass

    monkeypatch.setattr("customtkinter.CTk", MockApp)
    monkeypatch.setattr("customtkinter.CTkFrame", lambda *args, **kwargs: MockApp())
    monkeypatch.setattr("customtkinter.CTkLabel", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr("customtkinter.CTkButton", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr("customtkinter.CTkToplevel", lambda *args, **kwargs: MockApp())

    from src.main import main

    main()
    # Should handle the exception and return
