from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from loguru import logger

from src.common.exceptions import InvalidModException


@dataclass(eq=False)
class Mod(ABC):
    """Base class for all mods."""

    name: str
    path: Path
    enabled: bool

    @abstractmethod
    def enable(self) -> None:
        """Enables the mod."""
        pass

    @property
    @abstractmethod
    def mod_type(self) -> str:
        """Returns the type of the mod."""
        pass

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mod):
            return False
        return self.name == other.name and self.__class__ == other.__class__

    def __hash__(self) -> int:
        return hash((self.name, self.__class__))


@dataclass(eq=False)
class UE4SSMod(Mod):
    """Represents a UE4SS mod."""

    scripts: list[str] = None
    is_native: bool = False
    lang: Literal["lua", "cpp"] = "lua"

    @property
    def mod_type(self) -> str:
        return "UE4SS"

    @classmethod
    def from_path(cls, path: Path, *, override_enabled: bool = False) -> "UE4SSMod":
        """
        Constructs a UE4SSMod object from a given path.

        Args:
            path: The path to the mod directory.
            override_enabled (optional): If True, the mod will be considered enabled even if
                there is no enabled.txt file. Defaults to False.

        Returns:
            An instance of the UE4SSMod class with the mod's name, enabled status, and list of scripts.

        Raises:
            InvalidModException: If the mod directory does not contain a main.lua file or if the directory
                is not a directory.
        """
        name = path.stem

        if not path.is_dir():
            logger.warning(f"Mod {name} is not a directory.")
            return None

        lua = [str(script.relative_to(path)) for script in path.glob("scripts/*.lua", case_sensitive=False)]
        dll = [str(script.relative_to(path)) for script in path.glob("dlls/*.dll", case_sensitive=False)]

        scripts = [s.replace("\\", "/") for s in lua + dll]

        if not scripts:
            raise InvalidModException(f"Mod {name} has no scripts.")

        if "scripts/main.lua" not in scripts and "dlls/main.dll" not in scripts:
            raise InvalidModException(f"Mod {name} does not have a main file: {scripts}")

        lang = "lua" if "scripts/main.lua" in scripts else "cpp"

        enabled = (path / "enabled.txt").exists() or override_enabled

        logger.debug(f"Mod {name} is {'enabled' if enabled else 'disabled'} with {len(scripts)} script(s)")

        return cls(name=name, enabled=enabled, scripts=scripts, path=path, lang=lang)

    def disable(self) -> None:
        """Disables the mod by removing the enabled.txt file."""
        enabled_file = self.path / "enabled.txt"

        if enabled_file.exists():
            enabled_file.unlink()
            logger.debug(f"Enabled file {enabled_file} removed.")

        else:
            logger.warning(f"Enabled file {enabled_file} does not exist.")

        self.enabled = False

        logger.debug(f"Mod {self.name} disabled.")

    def enable(self) -> None:
        """Enables the mod by creating an enabled.txt file."""
        enabled_file = self.path / "enabled.txt"
        enabled_file.touch()

        self.enabled = True

        logger.debug(f"Enabled file {enabled_file} created. Mod {self.name} enabled.")


@dataclass(eq=False)
class PakMod(Mod):
    """Represents a PAK mod."""

    @property
    def mod_type(self) -> str:
        return "PAK"

    @classmethod
    def from_path(cls, path: Path) -> "PakMod":
        """
        Constructs a PakMod object from a given path.

        Args:
            path: The path to the .pak file or .pak.disabled file.

        Returns:
            An instance of the PakMod class.
        """
        name = path.name
        enabled = not path.name.lower().endswith(".disabled")

        if not enabled:
            name = path.stem  # This will be "modname.pak" if path is "modname.pak.disabled"

        return cls(name=name, enabled=enabled, path=path)

    def enable(self) -> None:
        """Enables the mod by renaming .pak.disabled back to .pak."""
        if self.path.name.lower().endswith(".disabled"):
            new_path = self.path.parent / self.name
            self.path.rename(new_path)
            self.path = new_path
            self.enabled = True
            logger.debug(f"Mod {self.name} enabled by renaming to {new_path}")
        else:
            self.enabled = True
            logger.debug(f"Mod {self.name} is already enabled or has no .disabled suffix.")

    def disable(self) -> None:
        """Disables the mod by renaming .pak to .pak.disabled."""
        if not self.path.name.lower().endswith(".disabled"):
            new_path = self.path.with_name(f"{self.path.name}.disabled")
            self.path.rename(new_path)
            self.path = new_path
            self.enabled = False
            logger.debug(f"Mod {self.name} disabled by renaming to {new_path}")
        else:
            self.enabled = False
            logger.debug(f"Mod {self.name} is already disabled.")
