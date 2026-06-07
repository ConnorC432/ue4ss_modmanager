from pathlib import Path

import pytest

from src.common.exceptions import InvalidModException
from src.common.mod import UE4SSMod


def test_mod_from_path_valid_lua(tmp_path):
    mod_dir = tmp_path / "MyMod"
    mod_dir.mkdir()
    scripts_dir = mod_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "main.lua").touch()

    mod = UE4SSMod.from_path(mod_dir)

    assert mod is not None, "UE4SSMod.from_path should return a mod object for valid path"
    assert mod.name == "MyMod", f"Expected mod name 'MyMod', got '{mod.name}'"
    assert mod.enabled is False, "Mod should be disabled by default (no enabled.txt)"
    assert "scripts/main.lua" in mod.scripts, "scripts/main.lua should be in mod.scripts"
    assert mod.lang == "lua", f"Expected language 'lua', got '{mod.lang}'"


def test_mod_from_path_valid_cpp(tmp_path):
    mod_dir = tmp_path / "MyCppMod"
    mod_dir.mkdir()
    dlls_dir = mod_dir / "dlls"
    dlls_dir.mkdir()
    (dlls_dir / "main.dll").touch()

    mod = UE4SSMod.from_path(mod_dir)

    assert mod is not None, "UE4SSMod.from_path should return a mod object for valid CPP path"
    assert mod.name == "MyCppMod", f"Expected mod name 'MyCppMod', got '{mod.name}'"
    assert "dlls/main.dll" in mod.scripts, "dlls/main.dll should be in mod.scripts"
    assert mod.lang == "cpp", f"Expected language 'cpp', got '{mod.lang}'"


def test_mod_from_path_invalid_no_scripts(tmp_path):
    mod_dir = tmp_path / "EmptyMod"
    mod_dir.mkdir()

    with pytest.raises(InvalidModException, match="has no scripts"):
        UE4SSMod.from_path(mod_dir)


def test_mod_from_path_invalid_no_main(tmp_path):
    mod_dir = tmp_path / "NoMainMod"
    mod_dir.mkdir()
    scripts_dir = mod_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "other.lua").touch()

    with pytest.raises(InvalidModException, match="does not have a main file"):
        UE4SSMod.from_path(mod_dir)


def test_mod_enable_disable(tmp_path):
    mod_dir = tmp_path / "ToggleMod"
    mod_dir.mkdir()
    scripts_dir = mod_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "main.lua").touch()

    mod = UE4SSMod.from_path(mod_dir)
    assert not (mod_dir / "enabled.txt").exists(), "enabled.txt should not exist initially"

    mod.enable()
    assert mod.enabled is True, "mod.enabled should be True after enable()"
    assert (mod_dir / "enabled.txt").exists(), "enabled.txt should exist after enable()"

    mod.disable()
    assert mod.enabled is False, "mod.enabled should be False after disable()"
    assert not (mod_dir / "enabled.txt").exists(), "enabled.txt should not exist after disable()"


def test_mod_disable_not_exists(tmp_path):
    mod_dir = tmp_path / "NoFileMod"
    mod_dir.mkdir()
    scripts_dir = mod_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "main.lua").touch()

    mod = UE4SSMod.from_path(mod_dir)
    mod.disable()
    assert mod.enabled is False


def test_mod_override_enabled(tmp_path):
    mod_dir = tmp_path / "OverrideMod"
    mod_dir.mkdir()
    scripts_dir = mod_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "main.lua").touch()

    mod = UE4SSMod.from_path(mod_dir, override_enabled=True)
    assert mod.enabled is True


def test_mod_from_path_not_directory(tmp_path):
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.touch()

    assert UE4SSMod.from_path(not_a_dir) is None


def test_mod_equality():
    path = Path("/tmp/mod")
    mod1 = UE4SSMod(name="Mod", path=path, enabled=True, scripts=[])
    mod2 = UE4SSMod(name="Mod", path=path, enabled=False, scripts=[])
    mod3 = UE4SSMod(name="Other", path=path, enabled=True, scripts=[])

    assert mod1 == mod2, "Mods with same name should be equal"
    assert mod1 != mod3, "Mods with different names should not be equal"
    assert mod1 != "not a mod", "Equality with non-mod object should be False"
    assert hash(mod1) == hash(mod2), "Equal mods should have same hash"
