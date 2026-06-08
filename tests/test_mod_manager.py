import json
import shutil
import tarfile
from pathlib import Path

import pytest

from src.common.exceptions import InvalidModFolderException
from src.common.mod_manager import PakModManager, UE4SSModManager


@pytest.fixture
def ue4ss_structure(tmp_path):
    ue4ss_dir = tmp_path / "UE4SS"
    ue4ss_dir.mkdir()
    mods_dir = ue4ss_dir / "Mods"
    mods_dir.mkdir()
    return mods_dir


def create_zip_mod(path: Path, mod_name: str, nested: bool = False):
    mod_dir = path / "temp_mod"
    mod_dir.mkdir()

    actual_mod_root = mod_dir
    if nested:
        actual_mod_root = mod_dir / "nested" / mod_name
        actual_mod_root.mkdir(parents=True)

    (actual_mod_root / "scripts").mkdir()
    (actual_mod_root / "scripts" / "main.lua").write_text("-- test mod")

    zip_path = path / f"{mod_name}.zip"
    shutil.make_archive(str(path / mod_name), "zip", str(mod_dir))
    shutil.rmtree(mod_dir)
    return zip_path


def create_tar_gz_mod(path: Path, mod_name: str):
    mod_dir = path / "temp_mod_tar"
    mod_dir.mkdir()
    (mod_dir / "scripts").mkdir()
    (mod_dir / "scripts" / "main.lua").write_text("-- test mod tar")

    tar_path = path / f"{mod_name}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(mod_dir, arcname=mod_name)
    shutil.rmtree(mod_dir)
    return tar_path


def test_mod_manager_init_valid(ue4ss_structure) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    assert manager.path == ue4ss_structure, f"Expected path {ue4ss_structure}, got {manager.path}"
    assert len(manager.mods) == 0, f"Expected 0 mods initially, got {len(manager.mods)}"


def test_mod_manager_init_invalid(tmp_path) -> None:
    invalid_path = tmp_path / "NotADir"
    # No directory created
    with pytest.raises(InvalidModFolderException):
        UE4SSModManager(invalid_path)


def test_load_mods(ue4ss_structure) -> None:
    # Create a mod
    mod1_dir = ue4ss_structure / "Mod1"
    mod1_dir.mkdir()
    (mod1_dir / "scripts").mkdir()
    (mod1_dir / "scripts" / "main.lua").touch()

    manager = UE4SSModManager(ue4ss_structure)
    assert len(manager.mods) == 1, f"Expected 1 mod to be loaded, got {len(manager.mods)}"
    assert manager.mods[0].name == "Mod1", f"Expected mod name 'Mod1', got '{manager.mods[0].name}'"


def test_get_enabled_overrides_txt(ue4ss_structure) -> None:
    mod1_dir = ue4ss_structure / "Mod1"
    mod1_dir.mkdir()
    (mod1_dir / "scripts").mkdir()
    (mod1_dir / "scripts" / "main.lua").touch()

    mods_txt = ue4ss_structure / "mods.txt"
    mods_txt.write_text("Mod1 : 1\nMod2 : 0", encoding="utf-8")

    manager = UE4SSModManager(ue4ss_structure)
    overrides = manager._get_enabled_overrides()
    assert "Mod1" in overrides, "Mod1 should be in enabled overrides from mods.txt"
    assert "Mod2" not in overrides, "Mod2 should NOT be in enabled overrides from mods.txt"


def test_get_enabled_overrides_txt_no_colon(ue4ss_structure) -> None:
    # Testing branch at line 54 of mod_manager.py
    mods_txt = ue4ss_structure / "mods.txt"
    mods_txt.write_text("Mod11", encoding="utf-8")  # "Mod1" + "1" (enabled)

    manager = UE4SSModManager(ue4ss_structure)
    overrides = manager._get_enabled_overrides()
    assert "Mod1" in overrides


def test_get_enabled_overrides_json(ue4ss_structure) -> None:
    mods_json = ue4ss_structure / "mods.json"
    data = [{"mod_name": "Mod1", "mod_enabled": True}, {"mod_name": "Mod2", "mod_enabled": False}]
    mods_json.write_text(json.dumps(data), encoding="utf-8")

    manager = UE4SSModManager(ue4ss_structure)
    overrides = manager._get_enabled_overrides()
    assert "Mod1" in overrides
    assert "Mod2" not in overrides


def test_parse_mods(ue4ss_structure) -> None:
    mod1_dir = ue4ss_structure / "Mod1"
    mod1_dir.mkdir()
    (mod1_dir / "scripts").mkdir()
    (mod1_dir / "scripts" / "main.lua").touch()

    manager = UE4SSModManager(ue4ss_structure)
    mod = manager.mods[0]
    mod.enabled = True

    manager.parse_mods([mod])

    assert (mod1_dir / "enabled.txt").exists()
    assert not (ue4ss_structure / "mods.json").exists()
    assert not (ue4ss_structure / "mods.txt").exists()


def test_load_mods_no_overrides(ue4ss_structure) -> None:
    # Testing line 86 of mod_manager.py
    mod1_dir = ue4ss_structure / "Mod1"
    mod1_dir.mkdir()
    (mod1_dir / "scripts").mkdir()
    (mod1_dir / "scripts" / "main.lua").touch()

    manager = UE4SSModManager(ue4ss_structure)
    # Call load_mods directly with None
    mods = manager.load_mods(None)
    assert len(mods) == 1


def test_parse_mods_with_existing_files(ue4ss_structure) -> None:
    mod1_dir = ue4ss_structure / "Mod1"
    mod1_dir.mkdir()
    (mod1_dir / "scripts").mkdir()
    (mod1_dir / "scripts" / "main.lua").touch()

    manager = UE4SSModManager(ue4ss_structure)
    mod = manager.mods[0]
    mod.enabled = True

    manager.parse_mods([mod])
    assert (mod1_dir / "enabled.txt").exists()
    assert not (ue4ss_structure / "mods.json").exists()
    assert not (ue4ss_structure / "mods.txt").exists()


def test_parse_mods_disabled_branch(ue4ss_structure) -> None:
    # Testing lines 180-181
    mod1_dir = ue4ss_structure / "Mod1"
    mod1_dir.mkdir()
    (mod1_dir / "scripts").mkdir()
    (mod1_dir / "scripts" / "main.lua").touch()
    (mod1_dir / "enabled.txt").touch()  # Start enabled

    manager = UE4SSModManager(ue4ss_structure)
    mod = manager.mods[0]
    mod.enabled = False  # Set to disabled

    manager.parse_mods([mod])
    assert not (mod1_dir / "enabled.txt").exists()


def test_load_mods_skips_shared(ue4ss_structure) -> None:
    shared_dir = ue4ss_structure / "shared"
    shared_dir.mkdir()
    (shared_dir / "scripts").mkdir()
    (shared_dir / "scripts" / "main.lua").touch()

    manager = UE4SSModManager(ue4ss_structure)
    assert len(manager.mods) == 0, "The 'shared' folder should be skipped during mod loading"


def test_load_mods_with_invalid_mod(ue4ss_structure) -> None:
    invalid_mod_dir = ue4ss_structure / "InvalidMod"
    invalid_mod_dir.mkdir()
    # No scripts folder or main file

    manager = UE4SSModManager(ue4ss_structure)
    assert len(manager.mods) == 0, "Invalid mods should be skipped without crashing the manager"


def test_enable_disable_mods(ue4ss_structure) -> None:
    mod_dir = ue4ss_structure / "Mod1"
    mod_dir.mkdir()
    (mod_dir / "scripts").mkdir()
    (mod_dir / "scripts" / "main.lua").touch()

    manager = UE4SSModManager(ue4ss_structure)
    manager.enable_mods(["Mod1"])
    assert (mod_dir / "enabled.txt").exists(), "Mod1 should have enabled.txt after enable_mods"

    manager.disable_mods(["Mod1"])
    assert not (mod_dir / "enabled.txt").exists(), "Mod1 should not have enabled.txt after disable_mods"


def test_properties(ue4ss_structure) -> None:
    mod1_dir = ue4ss_structure / "Mod1"
    mod1_dir.mkdir()
    (mod1_dir / "scripts").mkdir()
    (mod1_dir / "scripts" / "main.lua").touch()

    mod2_dir = ue4ss_structure / "Mod2"
    mod2_dir.mkdir()
    (mod2_dir / "scripts").mkdir()
    (mod2_dir / "scripts" / "main.lua").touch()
    (mod2_dir / "enabled.txt").touch()

    manager = UE4SSModManager(ue4ss_structure)
    assert "Mod1" in manager.all_mods
    assert "Mod2" in manager.all_mods
    assert "Mod2" in manager.enabled_mods
    assert "Mod1" in manager.disabled_mods


def test_import_zip_success(ue4ss_structure, tmp_path) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    zip_path = create_zip_mod(tmp_path, "NewMod")

    imported_name = manager.import_mod_archive(zip_path)

    assert imported_name == "NewMod"
    assert (ue4ss_structure / "NewMod").exists()
    assert (ue4ss_structure / "NewMod" / "scripts" / "main.lua").exists()
    assert "NewMod" in manager.all_mods


def test_import_nested_zip_success(ue4ss_structure, tmp_path) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    zip_path = create_zip_mod(tmp_path, "NestedMod", nested=True)

    imported_name = manager.import_mod_archive(zip_path)

    assert imported_name == "NestedMod"
    assert (ue4ss_structure / "NestedMod").exists()
    assert (ue4ss_structure / "NestedMod" / "scripts" / "main.lua").exists()
    assert not (ue4ss_structure / "NestedMod" / "nested").exists()  # Should have flattened


def test_import_tar_gz_success(ue4ss_structure, tmp_path) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    tar_path = create_tar_gz_mod(tmp_path, "TarMod")

    imported_name = manager.import_mod_archive(tar_path)

    assert imported_name == "TarMod"
    assert (ue4ss_structure / "TarMod").exists()
    assert (ue4ss_structure / "TarMod" / "scripts" / "main.lua").exists()


def test_import_overwrite_fails_if_false(ue4ss_structure, tmp_path) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    (ue4ss_structure / "ExistingMod").mkdir()
    zip_path = create_zip_mod(tmp_path, "ExistingMod")

    with pytest.raises(ValueError, match="already exists"):
        manager.import_mod_archive(zip_path, overwrite=False)


def test_import_overwrite_success_if_true(ue4ss_structure, tmp_path) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    existing_mod_dir = ue4ss_structure / "ExistingMod"
    existing_mod_dir.mkdir()
    (existing_mod_dir / "old_file.txt").touch()

    zip_path = create_zip_mod(tmp_path, "ExistingMod")

    imported_name = manager.import_mod_archive(zip_path, overwrite=True)

    assert imported_name == "ExistingMod"
    assert not (existing_mod_dir / "old_file.txt").exists()
    assert (existing_mod_dir / "scripts" / "main.lua").exists()


def test_import_invalid_format(ue4ss_structure, tmp_path) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("not an archive")

    with pytest.raises(ValueError, match="Unsupported archive format"):
        manager.import_mod_archive(invalid_file)


def test_pak_mod_manager_load(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    (pak_dir / "Mod1.pak").touch()
    (pak_dir / "Mod2.pak.disabled").touch()
    (pak_dir / "not_a_mod.txt").touch()

    expected_mod_count = 2
    manager = PakModManager(pak_dir)
    assert len(manager.mods) == expected_mod_count
    assert "Mod1.pak" in manager.all_mods
    assert "Mod2.pak" in manager.all_mods
    assert "Mod1.pak" in manager.enabled_mods
    assert "Mod2.pak" in manager.disabled_mods


def test_pak_mod_manager_enable_disable(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    pak_path = pak_dir / "Toggle.pak"
    pak_path.touch()

    manager = PakModManager(pak_dir)
    assert "Toggle.pak" in manager.enabled_mods

    manager.disable_mods(["Toggle.pak"])
    assert (pak_dir / "Toggle.pak.disabled").exists()
    assert not pak_path.exists()
    assert "Toggle.pak" in manager.disabled_mods

    manager.enable_mods(["Toggle.pak"])
    assert pak_path.exists()
    assert not (pak_dir / "Toggle.pak.disabled").exists()
    assert "Toggle.pak" in manager.enabled_mods


def test_pak_mod_manager_import(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    manager = PakModManager(pak_dir)

    import zipfile

    archive_path = tmp_path / "PakMod.zip"
    with zipfile.ZipFile(archive_path, "w") as z:
        z.writestr("MyCoolMod.pak", "fake pak content")

    imported_name = manager.import_mod_archive(archive_path)

    assert imported_name == "PakMod"
    assert (pak_dir / "MyCoolMod.pak").exists()
    assert "MyCoolMod.pak" in manager.all_mods


def test_pak_mod_manager_import_no_pak(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    manager = PakModManager(pak_dir)

    import zipfile

    archive_path = tmp_path / "NoPak.zip"
    with zipfile.ZipFile(archive_path, "w") as z:
        z.writestr("readme.txt", "no pak here")

    with pytest.raises(ValueError, match=r"No \.pak files found"):
        manager.import_mod_archive(archive_path)


def test_pak_mod_manager_import_overwrite(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    (pak_dir / "Overwrite.pak").write_text("old")
    manager = PakModManager(pak_dir)

    import zipfile

    archive_path = tmp_path / "New.zip"
    with zipfile.ZipFile(archive_path, "w") as z:
        z.writestr("Overwrite.pak", "new")

    # Should fail without overwrite
    with pytest.raises(ValueError, match="already exists"):
        manager.import_mod_archive(archive_path, overwrite=False)

    # Should succeed with overwrite
    manager.import_mod_archive(archive_path, overwrite=True)
    assert (pak_dir / "Overwrite.pak").read_text() == "new"


def test_import_multiple_paks_success(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    manager = PakModManager(pak_dir)

    import zipfile

    archive_path = tmp_path / "MultiPak.zip"
    with zipfile.ZipFile(archive_path, "w") as z:
        z.writestr("Mod1.pak", "data1")
        z.writestr("Mod2.pak", "data2")

    imported_name = manager.import_mod_archive(archive_path)
    assert imported_name == "MultiPak"
    assert (pak_dir / "Mod1.pak").exists()
    assert (pak_dir / "Mod2.pak").exists()


def test_import_nested_paks_success(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    manager = PakModManager(pak_dir)

    import zipfile

    archive_path = tmp_path / "NestedPak.zip"
    with zipfile.ZipFile(archive_path, "w") as z:
        z.writestr("Folder/Subfolder/Nested.pak", "data")

    imported_name = manager.import_mod_archive(archive_path)
    assert imported_name == "NestedPak"
    assert (pak_dir / "Nested.pak").exists()


def test_import_mixed_content_ue4ss(ue4ss_structure, tmp_path) -> None:
    # Testing that UE4SS manager ignores non-UE4SS files but imports the mod
    manager = UE4SSModManager(ue4ss_structure)

    import zipfile

    archive_path = tmp_path / "MixedMod.zip"
    with zipfile.ZipFile(archive_path, "w") as z:
        z.writestr("MyMod/scripts/main.lua", "-- lua")
        z.writestr("MyMod/random.txt", "random")
        z.writestr("readme.md", "info")

    imported_name = manager.import_mod_archive(archive_path)
    assert imported_name == "MixedMod"
    assert (ue4ss_structure / "MixedMod").exists()
    assert (ue4ss_structure / "MixedMod" / "scripts" / "main.lua").exists()
    assert (ue4ss_structure / "MixedMod" / "random.txt").exists()


def test_ue4ss_mod_manager_remove_mod(ue4ss_structure) -> None:
    manager = UE4SSModManager(ue4ss_structure)
    mod_name = "TestMod"
    mod_dir = ue4ss_structure / mod_name
    mod_dir.mkdir()
    (mod_dir / "scripts").mkdir()
    (mod_dir / "scripts" / "main.lua").touch()

    manager.mods = manager.load_mods()
    assert any(m.name == mod_name for m in manager.mods)
    assert mod_dir.exists()

    manager.remove_mod(mod_name)
    assert not any(m.name == mod_name for m in manager.mods)
    assert not mod_dir.exists()


def test_pak_mod_manager_remove_mod(tmp_path) -> None:
    pak_dir = tmp_path / "Paks"
    pak_dir.mkdir()
    pak_path = pak_dir / "Remove.pak"
    pak_path.touch()

    manager = PakModManager(pak_dir)
    assert "Remove.pak" in manager.all_mods
    assert pak_path.exists()

    manager.remove_mod("Remove.pak")
    assert "Remove.pak" not in manager.all_mods
    assert not pak_path.exists()
