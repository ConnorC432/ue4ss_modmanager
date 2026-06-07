import json
import shutil
import tarfile
from pathlib import Path

import pytest

from src.common.exceptions import InvalidModFolderException
from src.common.mod_manager import UE4SSModManager


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


def test_mod_manager_init_valid(ue4ss_structure):
	manager = UE4SSModManager(ue4ss_structure)
	assert manager.path == ue4ss_structure, f"Expected path {ue4ss_structure}, got {manager.path}"
	assert len(manager.mods) == 0, f"Expected 0 mods initially, got {len(manager.mods)}"


def test_mod_manager_init_invalid(tmp_path):
	invalid_path = tmp_path / "NotMods"
	invalid_path.mkdir()
	with pytest.raises(InvalidModFolderException):
		UE4SSModManager(invalid_path)


def test_load_mods(ue4ss_structure):
	# Create a mod
	mod1_dir = ue4ss_structure / "Mod1"
	mod1_dir.mkdir()
	(mod1_dir / "scripts").mkdir()
	(mod1_dir / "scripts" / "main.lua").touch()

	manager = UE4SSModManager(ue4ss_structure)
	assert len(manager.mods) == 1, f"Expected 1 mod to be loaded, got {len(manager.mods)}"
	assert manager.mods[0].name == "Mod1", f"Expected mod name 'Mod1', got '{manager.mods[0].name}'"


def test_get_enabled_overrides_txt(ue4ss_structure):
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


def test_get_enabled_overrides_txt_no_colon(ue4ss_structure):
	# Testing branch at line 54 of mod_manager.py
	mods_txt = ue4ss_structure / "mods.txt"
	mods_txt.write_text("Mod11", encoding="utf-8")  # "Mod1" + "1" (enabled)

	manager = UE4SSModManager(ue4ss_structure)
	overrides = manager._get_enabled_overrides()
	assert "Mod1" in overrides


def test_get_enabled_overrides_json(ue4ss_structure):
	mods_json = ue4ss_structure / "mods.json"
	data = [{"mod_name": "Mod1", "mod_enabled": True}, {"mod_name": "Mod2", "mod_enabled": False}]
	mods_json.write_text(json.dumps(data), encoding="utf-8")

	manager = UE4SSModManager(ue4ss_structure)
	overrides = manager._get_enabled_overrides()
	assert "Mod1" in overrides
	assert "Mod2" not in overrides


def test_parse_mods(ue4ss_structure):
	mod1_dir = ue4ss_structure / "Mod1"
	mod1_dir.mkdir()
	(mod1_dir / "scripts").mkdir()
	(mod1_dir / "scripts" / "main.lua").touch()

	manager = UE4SSModManager(ue4ss_structure)
	mod = manager.mods[0]
	mod.enabled = True

	manager.parse_mods([mod], save_enabled_txt=True, save_mods_json=True, save_mods_txt=True)

	assert (mod1_dir / "enabled.txt").exists()
	assert (ue4ss_structure / "mods.json").exists()
	assert (ue4ss_structure / "mods.txt").exists()

	# Check mods.txt content
	assert "Mod1 : 1" in (ue4ss_structure / "mods.txt").read_text(), "Mod1 should be enabled in mods.txt"


def test_load_mods_no_overrides(ue4ss_structure):
	# Testing line 86 of mod_manager.py
	mod1_dir = ue4ss_structure / "Mod1"
	mod1_dir.mkdir()
	(mod1_dir / "scripts").mkdir()
	(mod1_dir / "scripts" / "main.lua").touch()

	manager = UE4SSModManager(ue4ss_structure)
	# Call load_mods directly with None
	mods = manager.load_mods(None)
	assert len(mods) == 1


def test_parse_mods_with_existing_files(ue4ss_structure):
	mod1_dir = ue4ss_structure / "Mod1"
	mod1_dir.mkdir()
	(mod1_dir / "scripts").mkdir()
	(mod1_dir / "scripts" / "main.lua").touch()

	# Pre-create files to test unlinking (lines 125, 142)
	(ue4ss_structure / "mods.json").write_text("[]", encoding="utf-8")
	(ue4ss_structure / "mods.txt").touch()

	manager = UE4SSModManager(ue4ss_structure)
	mod = manager.mods[0]
	mod.enabled = True

	manager.parse_mods([mod])
	assert (ue4ss_structure / "mods.json").exists()
	assert (ue4ss_structure / "mods.txt").exists()


def test_parse_mods_disabled_branch(ue4ss_structure):
	# Testing lines 180-181
	mod1_dir = ue4ss_structure / "Mod1"
	mod1_dir.mkdir()
	(mod1_dir / "scripts").mkdir()
	(mod1_dir / "scripts" / "main.lua").touch()
	(mod1_dir / "enabled.txt").touch()  # Start enabled

	manager = UE4SSModManager(ue4ss_structure)
	mod = manager.mods[0]
	mod.enabled = False  # Set to disabled

	manager.parse_mods([mod], save_enabled_txt=True)
	assert not (mod1_dir / "enabled.txt").exists()


def test_load_mods_skips_shared(ue4ss_structure):
	shared_dir = ue4ss_structure / "shared"
	shared_dir.mkdir()
	(shared_dir / "scripts").mkdir()
	(shared_dir / "scripts" / "main.lua").touch()

	manager = UE4SSModManager(ue4ss_structure)
	assert len(manager.mods) == 0, "The 'shared' folder should be skipped during mod loading"


def test_load_mods_with_invalid_mod(ue4ss_structure):
	invalid_mod_dir = ue4ss_structure / "InvalidMod"
	invalid_mod_dir.mkdir()
	# No scripts folder or main file

	manager = UE4SSModManager(ue4ss_structure)
	assert len(manager.mods) == 0, "Invalid mods should be skipped without crashing the manager"


def test_enable_disable_mods(ue4ss_structure):
	mod_dir = ue4ss_structure / "Mod1"
	mod_dir.mkdir()
	(mod_dir / "scripts").mkdir()
	(mod_dir / "scripts" / "main.lua").touch()

	manager = UE4SSModManager(ue4ss_structure)
	manager.enable_mods(["Mod1"])
	assert (mod_dir / "enabled.txt").exists(), "Mod1 should have enabled.txt after enable_mods"

	manager.disable_mods(["Mod1"])
	assert not (mod_dir / "enabled.txt").exists(), "Mod1 should not have enabled.txt after disable_mods"


def test_properties(ue4ss_structure):
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


def test_import_zip_success(ue4ss_structure, tmp_path):
	manager = UE4SSModManager(ue4ss_structure)
	zip_path = create_zip_mod(tmp_path, "NewMod")

	imported_name = manager.import_mod_archive(zip_path)

	assert imported_name == "NewMod"
	assert (ue4ss_structure / "NewMod").exists()
	assert (ue4ss_structure / "NewMod" / "scripts" / "main.lua").exists()
	assert "NewMod" in manager.all_mods


def test_import_nested_zip_success(ue4ss_structure, tmp_path):
	manager = UE4SSModManager(ue4ss_structure)
	zip_path = create_zip_mod(tmp_path, "NestedMod", nested=True)

	imported_name = manager.import_mod_archive(zip_path)

	assert imported_name == "NestedMod"
	assert (ue4ss_structure / "NestedMod").exists()
	assert (ue4ss_structure / "NestedMod" / "scripts" / "main.lua").exists()
	assert not (ue4ss_structure / "NestedMod" / "nested").exists()  # Should have flattened


def test_import_tar_gz_success(ue4ss_structure, tmp_path):
	manager = UE4SSModManager(ue4ss_structure)
	tar_path = create_tar_gz_mod(tmp_path, "TarMod")

	imported_name = manager.import_mod_archive(tar_path)

	assert imported_name == "TarMod"
	assert (ue4ss_structure / "TarMod").exists()
	assert (ue4ss_structure / "TarMod" / "scripts" / "main.lua").exists()


def test_import_overwrite_fails_if_false(ue4ss_structure, tmp_path):
	manager = UE4SSModManager(ue4ss_structure)
	(ue4ss_structure / "ExistingMod").mkdir()
	zip_path = create_zip_mod(tmp_path, "ExistingMod")

	with pytest.raises(ValueError, match="already exists"):
		manager.import_mod_archive(zip_path, overwrite=False)


def test_import_overwrite_success_if_true(ue4ss_structure, tmp_path):
	manager = UE4SSModManager(ue4ss_structure)
	existing_mod_dir = ue4ss_structure / "ExistingMod"
	existing_mod_dir.mkdir()
	(existing_mod_dir / "old_file.txt").touch()

	zip_path = create_zip_mod(tmp_path, "ExistingMod")

	imported_name = manager.import_mod_archive(zip_path, overwrite=True)

	assert imported_name == "ExistingMod"
	assert not (existing_mod_dir / "old_file.txt").exists()
	assert (existing_mod_dir / "scripts" / "main.lua").exists()


def test_import_invalid_format(ue4ss_structure, tmp_path):
	manager = UE4SSModManager(ue4ss_structure)
	invalid_file = tmp_path / "test.txt"
	invalid_file.write_text("not an archive")

	with pytest.raises(ValueError, match="Unsupported archive format"):
		manager.import_mod_archive(invalid_file)
