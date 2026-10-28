"""Safety-focused Flashpoint installation discovery and removal.

No user data outside the selected directory is modified by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import sys
from typing import Callable


LAUNCHERS = (
    Path('Launcher/Flashpoint.exe'),
    Path('Launcher/FlashpointLauncher.exe'),
)
SECONDARY = (
    Path('Manager/FlashpointManager.exe'),
    Path('Data'),
    Path('Legacy'),
    Path('FPSoftware'),
    Path('Components'),
)
BACKUP_LOCATIONS = (
    Path('Data/Playlists'),
    Path('Data/Games'),
    Path('Data/Images'),
    Path('Data/Saves'),
    Path('Data/Profiles'),
)


class SafetyError(ValueError):
    """The path is not an explicitly verified Flashpoint installation."""


@dataclass(frozen=True)
class Inspection:
    path: Path
    markers: tuple[str, ...]
    backup_candidates: tuple[str, ...]


def _normalized(path: os.PathLike[str] | str) -> Path:
    # Do not resolve symbolic links before checking them. Also never expand %vars
    # in user-supplied paths, avoiding surprising deletion targets.
    raw = os.fspath(path)
    if not raw or not raw.strip():
        raise SafetyError('未选择目录。')
    return Path(os.path.abspath(raw))


def _has_reparse(path: Path) -> bool:
    """Reject symlinks and Windows junctions/reparse points in path ancestry."""
    try:
        st = path.lstat()
    except OSError:
        return False
    # On Windows stat_result has st_file_attributes / st_reparse_tag.
    return path.is_symlink() or bool(getattr(st, 'st_file_attributes', 0) & 0x400)


def _ancestors(path: Path):
    yield path
    yield from path.parents


def _critical_roots() -> set[str]:
    roots = {Path.home(), Path.cwd().anchor and Path(Path.cwd().anchor)}
    for key in ('WINDIR', 'SystemRoot', 'ProgramFiles', 'ProgramFiles(x86)',
                'ProgramData', 'USERPROFILE', 'PUBLIC', 'APPDATA', 'LOCALAPPDATA',
                'TEMP', 'TMP'):
        if os.environ.get(key):
            roots.add(Path(os.environ[key]))
    roots.update(Path.home() / name for name in ('Desktop', 'Documents', 'Downloads', 'Pictures', 'Videos'))
    return {os.path.normcase(os.path.abspath(str(x))) for x in roots if x}


def _validate_boundary(path: Path, running_from: Path | None = None) -> None:
    if not path.is_dir():
        raise SafetyError('目标目录不存在。')
    if path == path.parent or os.path.normcase(str(path)) in _critical_roots():
        raise SafetyError('拒绝删除磁盘根目录或系统 / 用户的重要目录。')
    # The root and any parent must not be a junction or symlink.
    if any(_has_reparse(p) for p in _ancestors(path)):
        raise SafetyError('目录路径包含符号链接或联接点，出于安全考虑不允许删除。')
    if running_from is not None:
        runner = _normalized(running_from)
        try:
            common = os.path.commonpath((os.path.normcase(str(path)), os.path.normcase(str(runner))))
        except ValueError:
            common = None  # Different Windows drives.
        if common == os.path.normcase(str(path)):
            raise SafetyError('卸载器正在目标目录内运行，请先移至其他位置。')


def inspect_installation(path: os.PathLike[str] | str, *, running_from: Path | None = None) -> Inspection:
    root = _normalized(path)
    _validate_boundary(root, running_from)
    launchers = [str(name) for name in LAUNCHERS if (root / name).is_file() and not _has_reparse(root / name)]
    secondary = [str(name) for name in SECONDARY if (root / name).exists() and not _has_reparse(root / name)]
    if not launchers or not secondary:
        raise SafetyError('无法确认这是 Flashpoint 安装目录：缺少启动器与独立的目录特征。')
    # Avoid removing a directory where a marker itself traverses through a junction.
    for mark in (*launchers, *secondary):
        candidate = root / mark
        if any(_has_reparse(p) for p in _ancestors(candidate) if p != root and root in p.parents):
            raise SafetyError('安装标记路径包含联接点，无法安全验证目标。')
    backups = tuple(str(name) for name in BACKUP_LOCATIONS if (root / name).exists())
    return Inspection(root, tuple(launchers + secondary), backups)


def discover_installations() -> list[Path]:
    """Only check predictable locations, never scan the whole drive."""
    candidates = [Path('C:/Flashpoint'), Path('D:/Flashpoint'), Path('E:/Flashpoint')]
    home = Path.home()
    for base in (home / 'Downloads', home / 'Desktop'):
        if base.is_dir():
            try:
                candidates.extend(p for p in base.iterdir() if p.is_dir() and p.name.casefold().startswith('flashpoint'))
            except OSError:
                pass
    # Portable copy alongside the built executable (or source checkout).
    executable = Path(sys.executable if getattr(sys, 'frozen', False) else __file__)
    candidates.extend((executable.parent / 'Flashpoint', executable.parent.parent / 'Flashpoint'))
    seen: set[str] = set()
    valid = []
    for candidate in candidates:
        canonical = os.path.normcase(os.path.abspath(candidate))
        if canonical in seen:
            continue
        seen.add(canonical)
        try:
            inspect_installation(candidate, running_from=executable)
        except (SafetyError, OSError):
            continue
        valid.append(_normalized(candidate))
    return valid


def remove_installation(
    original: Inspection,
    *,
    running_from: Path | None = None,
    on_progress: Callable[[str], None] | None = None,
    remover: Callable[[Path], None] = shutil.rmtree,
) -> None:
    """Re-validate immediately before removal to avoid deleting unchecked targets.

    The caller must obtain explicit confirmation from the user. In tests,
    `remover` can be injected without modifying files.
    """
    current = inspect_installation(original.path, running_from=running_from)
    if current.path != original.path or current.markers != original.markers:
        raise SafetyError('目录内容在确认后发生变化，请重新检查。')
    if on_progress:
        on_progress('正在移除所选 Flashpoint 目录……')
    remover(current.path)
    if on_progress:
        on_progress('安装目录已移除。')
