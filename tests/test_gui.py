import sys
from unittest.mock import MagicMock

import pytest


# Mocking customtkinter and PIL before importing the GUI
class MockCTk:
    def __init__(self, *args, **kwargs) -> None:
        self.main_frame = MagicMock()
        self.search_var = MagicMock()
        self.search_var.get.return_value = ""
        self.toggle_all_var = MagicMock()
        self.toggle_all_var.get.return_value = False
        self.after_callbacks = []

    def title(self, *args) -> None:
        pass

    def winfo_screenwidth(self) -> int:
        return 1000

    def winfo_screenheight(self) -> int:
        return 1000

    def minsize(self, *args) -> None:
        pass

    def attributes(self, *args) -> None:
        pass

    def after(self, ms, callback, *args) -> None:
        if callback:
            self.after_callbacks.append(callback)

    def center_window(self) -> None:
        pass

    def iconbitmap(self, *args) -> None:
        pass

    def wm_iconphoto(self, *args, **kwargs) -> None:
        pass

    def pack(self, *args, **kwargs) -> None:
        pass

    def grid(self, *args, **kwargs) -> None:
        pass

    def configure(self, *args, **kwargs) -> None:
        pass

    def update_idletasks(self) -> None:
        pass

    def winfo_reqwidth(self) -> int:
        return 500

    def winfo_reqheight(self) -> int:
        return 500

    def geometry(self, *args) -> None:
        pass

    def mainloop(self) -> None:
        pass

    def winfo_width(self) -> int:
        return 500

    def winfo_height(self) -> int:
        return 500


mock_ctk = MagicMock()
mock_ctk.CTk = MockCTk
mock_ctk.CTkFrame = MagicMock()
mock_ctk.CTkLabel = MagicMock()
mock_ctk.CTkButton = MagicMock()
mock_ctk.CTkScrollableFrame = MagicMock()
mock_ctk.CTkCheckBox = MagicMock()
mock_ctk.CTkSwitch = MagicMock()
mock_ctk.CTkEntry = MagicMock()
mock_ctk.StringVar = MagicMock()
mock_ctk.BooleanVar = MagicMock()
mock_ctk.CTkFont = MagicMock()
mock_ctk.CTkImage = MagicMock()

sys.modules["customtkinter"] = mock_ctk
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()

from src.common.gui import UE4SSModManagerGUI, start_gui
from src.common.mod_manager import UE4SSModManager


@pytest.fixture
def mock_mod_manager():
    manager = MagicMock(spec=UE4SSModManager)
    mod1 = MagicMock()
    mod1.name = "Mod1"
    mod1.enabled = True
    mod1.is_native = False
    mod1.mod_type = "UE4SS"
    mod1.scripts = []
    manager.mods = [mod1]
    return manager


def test_gui_init(mock_mod_manager) -> None:
    # This might still fail if it calls more stuff in __init__
    # but let's see.
    gui = UE4SSModManagerGUI([mock_mod_manager])
    assert gui.mod_managers == [mock_mod_manager]
    assert (id(mock_mod_manager), "Mod1") in gui.initial_mod_states


def test_start_gui(mock_mod_manager, monkeypatch) -> None:
    mock_gui_instance = MagicMock()
    monkeypatch.setattr("src.common.gui.UE4SSModManagerGUI", lambda *args, **kwargs: mock_gui_instance)

    start_gui([mock_mod_manager])
    mock_gui_instance.mainloop.assert_called_once()


def test_gui_save_changes_pak(tmp_path, monkeypatch) -> None:
    from src.common.mod_manager import PakModManager

    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    pak_path = pak_dir / "Test.pak"
    pak_path.touch()

    manager = PakModManager(pak_dir)
    gui = UE4SSModManagerGUI([manager])

    # Simulate user unchecking the mod
    # The key is (id(manager), mod_name)
    checkbox_mock = MagicMock()
    checkbox_mock.get.return_value = False
    gui.mod_checkboxes[id(manager), "Test.pak"] = checkbox_mock

    # Save changes
    gui.save_changes()

    # Wait for the thread to finish
    import time

    timeout = 5
    start_time = time.time()
    while gui._is_saving and time.time() - start_time < timeout:
        if hasattr(gui, "tk"):
            gui.update()
        # Manually trigger the 'after' callbacks if they are stored in MockCTk
        elif hasattr(gui, "after_callbacks"):
            for cb in gui.after_callbacks:
                cb()
            gui.after_callbacks = []
        time.sleep(0.01)

    # Check if the file was renamed
    assert (pak_dir / "Test.pak.disabled").exists()
    assert not pak_path.exists()


def test_gui_import_routing(tmp_path, monkeypatch) -> None:
    import zipfile

    from src.common.mod_manager import PakModManager, UE4SSModManager

    ue4ss_dir = tmp_path / "UE4SS"
    ue4ss_dir.mkdir()
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()

    ue4ss_manager = UE4SSModManager(ue4ss_dir)
    pak_manager = PakModManager(pak_dir)

    # Mock manager imports
    ue4ss_manager.import_mod_archive = MagicMock(return_value="UE4SS_Mod")
    pak_manager.import_mod_archive = MagicMock(return_value="PAK_Mod")

    gui = UE4SSModManagerGUI([ue4ss_manager, pak_manager])

    # 1. Test UE4SS import
    ue4ss_zip = tmp_path / "ue4ss_mod.zip"
    with zipfile.ZipFile(ue4ss_zip, "w") as z:
        z.writestr("MyMod/scripts/main.lua", "-- test")

    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda **kwargs: str(ue4ss_zip))
    gui.import_mod()
    ue4ss_manager.import_mod_archive.assert_called_once()
    pak_manager.import_mod_archive.assert_not_called()

    # 2. Test PAK import
    ue4ss_manager.import_mod_archive.reset_mock()
    pak_manager.import_mod_archive.reset_mock()

    pak_zip = tmp_path / "pak_mod.zip"
    with zipfile.ZipFile(pak_zip, "w") as z:
        z.writestr("cool.pak", "data")

    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda **kwargs: str(pak_zip))
    gui.import_mod()
    pak_manager.import_mod_archive.assert_called_once()
    ue4ss_manager.import_mod_archive.assert_not_called()


def test_gui_import_no_suitable_manager(tmp_path, monkeypatch) -> None:
    import zipfile

    from src.common.mod_manager import PakModManager

    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    pak_manager = PakModManager(pak_dir)

    gui = UE4SSModManagerGUI([pak_manager])

    # Try to import a UE4SS mod when only PAK manager is available
    ue4ss_zip = tmp_path / "ue4ss_mod.zip"
    with zipfile.ZipFile(ue4ss_zip, "w") as z:
        z.writestr("MyMod/scripts/main.lua", "-- test")

    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda **kwargs: str(ue4ss_zip))
    mock_show_error = MagicMock()
    monkeypatch.setattr("src.common.gui.UE4SSModManagerGUI.show_error", mock_show_error)

    gui.import_mod()

    mock_show_error.assert_called_once()
    assert "no UE4SS mod manager is active" in mock_show_error.call_args[0][1]


def test_gui_import_unrecognized_archive(tmp_path, monkeypatch) -> None:
    import zipfile

    from src.common.mod_manager import UE4SSModManager

    ue4ss_dir = tmp_path / "UE4SS"
    ue4ss_dir.mkdir()
    manager = UE4SSModManager(ue4ss_dir)

    gui = UE4SSModManagerGUI([manager])

    # Unrecognized archive (no .pak, no scripts/dlls)
    random_zip = tmp_path / "random.zip"
    with zipfile.ZipFile(random_zip, "w") as z:
        z.writestr("random.txt", "nothing")

    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda **kwargs: str(random_zip))
    mock_show_error = MagicMock()
    monkeypatch.setattr("src.common.gui.UE4SSModManagerGUI.show_error", mock_show_error)

    gui.import_mod()

    mock_show_error.assert_called_once()
    assert "Could not determine mod type" in mock_show_error.call_args[0][1]
