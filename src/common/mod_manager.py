import os
import shutil
from abc import ABC, abstractmethod
from json import dumps, load
from pathlib import Path

from loguru import logger

from src.common.exceptions import InvalidModFolderException
from src.common.mod import Mod, PakMod, UE4SSMod


class ModManager(ABC):
    """Base class for mod managers."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.mods = self.load_mods()

    @abstractmethod
    def load_mods(self) -> list[Mod]:
        """Loads all mods from the specified path."""
        pass

    def enable_mods(self, mod_names: list[str]) -> None:
        """Enables the specified mods."""
        for mod in self.mods:
            if mod.name in mod_names:
                mod.enable()

    def disable_mods(self, mod_names: list[str]) -> None:
        """Disables the specified mods."""
        for mod in self.mods:
            if mod.name in mod_names:
                mod.disable()

    @abstractmethod
    def import_mod_archive(self, archive_path: Path, overwrite: bool = False) -> str:
        """
        Imports a mod from an archive file.

        Args:
            archive_path: The path to the mod archive.
            overwrite: Whether to overwrite an existing mod.

        Returns:
            The name of the imported mod.
        """
        pass

    @property
    def enabled_mods(self) -> list[str]:
        """Returns a list of enabled mod names."""
        return [mod.name for mod in self.mods if mod.enabled]

    @property
    def disabled_mods(self) -> list[str]:
        """Returns a list of disabled mod names."""
        return [mod.name for mod in self.mods if not mod.enabled]

    @property
    def all_mods(self) -> list[str]:
        """Returns a list of all mod names."""
        return [mod.name for mod in self.mods]


class UE4SSModManager(ModManager):
    """Manages the loading and enabling/disabling of UE4SS mods."""

    NATIVE_MODS = (
        "BPML_GenericFunctions",
        "BPModLoaderMod",
        "CheatManagerEnablerMod",
        "ConsoleCommandsMod",
        "ConsoleEnablerMod",
        "Keybinds",
        "ConsoleCommands",
    )

    def __init__(self, path: Path) -> None:
        """
        Initializes the UE4SSModManager with the given path.

        Args:
            path: The path to the mod folder.

        Raises:
            InvalidModFolderException: If the path is not a directory.
        """
        if not path.is_dir() or not path.exists():
            raise InvalidModFolderException(f"Path {path} is not a directory.")

        super().__init__(path)

    def _get_enabled_overrides(self) -> list[str]:
        output = []

        if (self.path / "mods.txt").exists():
            with Path.open(self.path / "mods.txt", encoding="utf-8") as f:
                for line in f.readlines():
                    stripped_line = line.strip()
                    if stripped_line.endswith("1"):
                        # Handle both "ModName : 1" and "ModName" (if it ends with 1)
                        if " : " in stripped_line:
                            output.append(stripped_line.split(" : ")[0].strip())
                        else:
                            output.append(stripped_line[:-1].strip())

        if (self.path / "mods.json").exists():
            with Path.open(self.path / "mods.json", encoding="utf-8-sig") as f:
                data = load(f)
                output += [mod["mod_name"] for mod in data if mod.get("mod_enabled", False)]

        return output

    def load_mods(self, enabled_overrides: list[str] | None = None) -> list[UE4SSMod]:
        """
        Loads all mods from the specified path.

        Returns:
            A list of UE4SSMod objects representing the mods in the directory.
        """
        if enabled_overrides is None:
            enabled_overrides = self._get_enabled_overrides()

        output = []
        for mod_path in self.path.iterdir():
            if mod_path.is_dir() and mod_path.stem.upper() != "SHARED":
                try:
                    override_enabled = mod_path.stem in enabled_overrides
                    mod = UE4SSMod.from_path(mod_path, override_enabled=override_enabled)
                    if mod:
                        mod.is_native = mod.name in self.NATIVE_MODS
                        output.append(mod)
                except Exception:
                    logger.exception(f"Failed to load mod from {mod_path}. This mod will be skipped.")
                    continue

        return output

    def _write_to_mods_json(self, mods: list[UE4SSMod]) -> None:
        """
        Writes the enabled mods to the mods.json file.

        Args:
            mods: A list of UE4SSMod objects to write to the mods.json file.
        """
        output = [{"mod_name": mod.name, "mod_enabled": mod.enabled} for mod in mods if mod.enabled]
        json_path = self.path / "mods.json"

        if json_path.exists():
            json_path.unlink()

        with Path.open(json_path, "w", encoding="utf-8") as f:
            f.write(dumps(output, indent=4, ensure_ascii=False))
            logger.debug(f"Enabled mods written to {json_path}")

    def _write_to_mods_txt(self, mods: list[UE4SSMod]) -> None:
        """
        Writes the enabled mods to the mods.txt file.

        Args:
            mods: A list of UE4SSMod objects to write to the mods.txt file.
        """
        output = [f"{mod.name} : 1\n" for mod in mods if mod.enabled]
        txt_path = self.path / "mods.txt"

        if txt_path.exists():
            txt_path.unlink()

        with Path.open(txt_path, "w", encoding="utf-8") as f:
            f.writelines(output)
            logger.debug(f"Enabled mods written to {txt_path}")

    def parse_mods(
        self,
        mods: list[UE4SSMod],
        *,
        save_enabled_txt: bool = True,
        save_mods_json: bool = True,
        save_mods_txt: bool = True,
    ) -> None:
        """
        Parses the mods and sets their enabled status.

        Args:
            mods: A list of UE4SSMod objects to parse.
            save_enabled_txt: Whether to save the enabled status to the enabled.txt files
            save_mods_json: Whether to save the enabled status to the mods.json file
            save_mods_txt: Whether to save the enabled status to the mods.txt file
        """
        enabled_mods = [mod for mod in mods if mod.enabled]
        disabled_mods = [mod for mod in mods if not mod.enabled]

        if save_mods_json:
            self._write_to_mods_json(enabled_mods)

        if save_mods_txt:
            self._write_to_mods_txt(enabled_mods)

        if save_enabled_txt:
            if enabled_mods:
                for mod in enabled_mods:
                    mod.enable()

            if disabled_mods:
                for mod in disabled_mods:
                    mod.disable()

        logger.debug(f"Parsed {len(mods)} mods.")

    def import_mod_archive(self, archive_path: Path, overwrite: bool = False) -> str:
        """
        Imports a mod from an archive file.

        Args:
            archive_path: The path to the mod archive.
            overwrite: Whether to overwrite an existing mod directory.

        Returns:
            The name of the imported mod.

        Raises:
            ValueError: If the archive is invalid, has an unsupported format, or already exists and overwrite is False.
        """
        # Use shutil to get supported formats
        supported_extensions = []
        for _, extensions, _ in shutil.get_unpack_formats():
            supported_extensions.extend(extensions)

        if not any(archive_path.name.lower().endswith(ext) for ext in supported_extensions):
            raise ValueError(
                f"Unsupported archive format: {archive_path.suffix}. Supported: {', '.join(supported_extensions)}"
            )

        mod_name = archive_path.stem
        # Handle cases like .tar.gz where stem would be .tar
        if archive_path.name.lower().endswith(".tar.gz"):
            mod_name = archive_path.name[:-7]
        elif archive_path.name.lower().endswith(".tar.bz2"):
            mod_name = archive_path.name[:-8]
        elif archive_path.name.lower().endswith(".tar.xz"):
            mod_name = archive_path.name[:-7]

        target_dir = self.path / mod_name

        if target_dir.exists() and not overwrite:
            raise ValueError(f"Mod '{mod_name}' already exists.")

        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            shutil.unpack_archive(str(archive_path), extract_dir=temp_dir)

            # Find the directory containing "scripts" or "dlls"
            root_in_extracted = None
            for root, dirs, _files in os.walk(temp_dir):
                root_path = Path(root)
                if "scripts" in [d.lower() for d in dirs] or "dlls" in [d.lower() for d in dirs]:
                    root_in_extracted = root_path
                    break

            if target_dir.exists() and overwrite:
                shutil.rmtree(target_dir)

            target_dir.mkdir(parents=True, exist_ok=True)

            if root_in_extracted is None:
                # If no scripts/dlls found, just copy everything from the top level
                for item in temp_path.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target_dir / item.name)
            else:
                # Copy everything from the discovered mod root
                for item in root_in_extracted.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target_dir / item.name)

        # Re-load mods after extraction
        self.mods = self.load_mods()
        return mod_name


class PakModManager(ModManager):
    """Manages the loading and enabling/disabling of PAK mods."""

    def load_mods(self) -> list[PakMod]:
        """Loads all PAK mods from the specified path."""
        output = []
        if not self.path.exists():
            return output

        for item in self.path.iterdir():
            if item.is_file() and (item.name.lower().endswith(".pak") or item.name.lower().endswith(".pak.disabled")):
                output.append(PakMod.from_path(item))

        return output

    def import_mod_archive(self, archive_path: Path, overwrite: bool = False) -> str:
        """Imports a PAK mod from an archive file."""
        import tempfile

        mod_name = archive_path.stem
        # Handle cases like .tar.gz where stem would be .tar
        if archive_path.name.lower().endswith(".tar.gz"):
            mod_name = archive_path.name[:-7]
        elif archive_path.name.lower().endswith(".tar.bz2"):
            mod_name = archive_path.name[:-8]
        elif archive_path.name.lower().endswith(".tar.xz"):
            mod_name = archive_path.name[:-7]

        with tempfile.TemporaryDirectory() as temp_dir:
            shutil.unpack_archive(str(archive_path), extract_dir=temp_dir)

            pak_files = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith(".pak"):
                        pak_files.append(Path(root) / file)

            if not pak_files:
                raise ValueError("No .pak files found in the archive.")

            for pak_file in pak_files:
                target_path = self.path / pak_file.name
                if target_path.exists() and not overwrite:
                    raise ValueError(f"Mod file '{pak_file.name}' already exists.")

            for pak_file in pak_files:
                target_path = self.path / pak_file.name
                if target_path.exists() and overwrite:
                    target_path.unlink()
                shutil.copy2(pak_file, target_path)

        self.mods = self.load_mods()
        return mod_name
