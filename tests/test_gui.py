import sys
from unittest.mock import MagicMock

import pytest


# Mocking customtkinter and PIL before importing the GUI
class MockCTk:
    def __init__(self, *args, **kwargs):
        self.main_frame = MagicMock()
        self.search_var = MagicMock()

    def title(self, *args):
        pass

    def winfo_screenwidth(self):
        return 1000

    def winfo_screenheight(self):
        return 1000

    def minsize(self, *args):
        pass

    def attributes(self, *args):
        pass

    def after(self, *args):
        pass

    def center_window(self):
        pass

    def iconbitmap(self, *args):
        pass

    def pack(self, *args, **kwargs):
        pass

    def grid(self, *args, **kwargs):
        pass

    def configure(self, *args, **kwargs):
        pass

    def update_idletasks(self):
        pass

    def winfo_reqwidth(self):
        return 500

    def winfo_reqheight(self):
        return 500

    def geometry(self, *args):
        pass

    def mainloop(self):
        pass

    def winfo_width(self):
        return 500

    def winfo_height(self):
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
    manager.mods = [mod1]
    return manager


def test_gui_init(mock_mod_manager):
    # This might still fail if it calls more stuff in __init__
    # but let's see.
    gui = UE4SSModManagerGUI(mock_mod_manager)
    assert gui.mod_manager == mock_mod_manager
    assert "Mod1" in gui.initial_mod_states


def test_start_gui(mock_mod_manager, monkeypatch):
    mock_gui_instance = MagicMock()
    monkeypatch.setattr("src.common.gui.UE4SSModManagerGUI", lambda *args, **kwargs: mock_gui_instance)

    start_gui(mock_mod_manager)
    mock_gui_instance.mainloop.assert_called_once()
