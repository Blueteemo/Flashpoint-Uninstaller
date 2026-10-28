"""Safety-focused Flashpoint installation discovery and removal.

No user data outside the selected directory is modified by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import sys
import uuid
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
    Path('Flash Save Backup'),
    Path('Launcher/config.json'),
    Path('preferences.json'),
    Path('Legacy/cgi-bin'),
    Path('FPSoftware/fpnavigator-portable/User'),
)


class SafetyError(ValueError):
    """The path is not an explicitly verified Flashpoint installation."""


@dataclass(frozen=True)
class Inspection:
    path: Path
    markers: tuple[str, ...]
    backup_candidates: tuple[str, ...]
    identity: tuple[int, int]


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
    except OSError as exc:
        raise SafetyError(f'无法确认路径是否为链接，已拒绝继续：{path} ({exc})') from exc
    # On Windows stat_result has st_file_attributes / st_reparse_tag.
    return path.is_symlink() or bool(getattr(st, 'st_file_attributes', 0) & 0x400)



class PartialRemovalError(SafetyError):
    """An already-started removal left files behind; re-verification is needed."""


@contextmanager
def _hold_directory(path: Path):
    """Prevent a Windows directory from being renamed while we erase its children.

    Share DELETE is intentionally omitted. Deleting the (eventually empty)
    directory itself happens only after the handle is closed; we never call a
    path-based recursive delete on an unlocked directory root.
    """
    if os.name != 'nt':
        yield
        return

    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    open_dir = kernel.CreateFileW
    open_dir.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                         ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    open_dir.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL

    # FILE_LIST_DIRECTORY is real data access. FILE_READ_ATTRIBUTES alone
    # does not enforce Windows sharing restrictions against rename.
    FILE_LIST_DIRECTORY_AND_ATTRIBUTES = 0x1 | 0x80
    FILE_SHARE_READ_WRITE = 0x1 | 0x2  # deliberately omit FILE_SHARE_DELETE
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    handle = open_dir(str(path), FILE_LIST_DIRECTORY_AND_ATTRIBUTES, FILE_SHARE_READ_WRITE,
                      None, OPEN_EXISTING,
                      FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, None)
    if not handle or handle == ctypes.c_void_p(-1).value:
        raise SafetyError(f'无法锁定待删除的目录，已拒绝继续：{path}')
    try:
        yield
    finally:
        kernel.CloseHandle(handle)


def _remove_tree_without_root_race(path: Path, expected: tuple[int, int] | None = None,
                                   on_deleted: Callable[[], None] | None = None) -> None:
    """Recursively remove a locked directory's CONTENTS, then its empty root.

    Every directory is held without FILE_SHARE_DELETE while visiting children,
    so another Windows process cannot swap a checked directory root for an
    unrelated nonempty tree just before path-based recursive deletion.
    Reparse points fail closed; only an already-empty root is ever rmdir'ed
    after the directory handle is released.
    """
    with _hold_directory(path):
        if _has_reparse(path):
            raise SafetyError('目录包含重解析点，已停止删除。')
        st = path.stat()
        if expected is not None and (st.st_dev, st.st_ino) != expected:
            raise SafetyError('暂存目录身份发生变化，已停止删除。')
        for child in path.iterdir():
            if _has_reparse(child):
                raise SafetyError('目标中包含链接或联接点，已停止删除。')
            if child.is_dir():
                _remove_tree_without_root_race(child, on_deleted=on_deleted)
            else:
                child.unlink()
                if on_deleted is not None:
                    on_deleted()
    # Only an empty directory can be removed here. Never rmtree an unlocked
    # pathname: it might have been replaced while the handle was being closed.
    path.rmdir()
    if on_deleted is not None:
        on_deleted()

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
    # A network share is too easy to mistake for a removable local installation.
    if os.name == 'nt' and str(path).startswith('\\\\'):
        raise SafetyError('不支持直接删除网络共享路径，请先在本地操作。')
    if path == path.parent:
        raise SafetyError('拒绝删除磁盘根目录。')
    target = os.path.normcase(str(path))
    for critical in _critical_roots():
        try:
            common = os.path.commonpath((target, critical))
        except ValueError:
            continue  # Different drives on Windows.
        # SafetyError subclasses ValueError, so don't raise inside the try.
        if common == target:
            raise SafetyError('拒绝删除系统 / 用户重要目录及其上层目录。')
    if os.name == 'nt':
        import ctypes
        # DRIVE_REMOTE includes mapped drive letters, not just UNC paths.
        try:
            drive_kind = ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor))
        except (AttributeError, OSError) as exc:
            raise SafetyError('无法确认磁盘类型，已拒绝删除。') from exc
        if drive_kind == 4:
            raise SafetyError('不支持从映射的网络磁盘删除 Flashpoint。')
        if drive_kind not in (2, 3, 6):
            raise SafetyError('无法验证当前磁盘类型，已拒绝删除。')
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
    # A generic Data/Legacy folder alone is not sufficient evidence.
    strong_markers = (str(Path('Manager/FlashpointManager.exe')) in secondary
                      or ('FPSoftware' in secondary and 'Data' in secondary))
    if not launchers or not strong_markers:
        raise SafetyError('无法充分确认 Flashpoint 安装身份：需要启动器和管理器，或 FPSoftware + Data。')
    # Avoid removing a directory where a marker itself traverses through a junction.
    for mark in (*launchers, *secondary):
        candidate = root / mark
        if any(_has_reparse(p) for p in _ancestors(candidate) if p != root and root in p.parents):
            raise SafetyError('安装标记路径包含联接点，无法安全验证目标。')
    backups = tuple(str(name) for name in BACKUP_LOCATIONS if (root / name).exists())
    st = root.stat()
    return Inspection(root, tuple(launchers + secondary), backups, (st.st_dev, st.st_ino))


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


def _remove_installation_locked(
    original: Inspection,
    *,
    running_from: Path | None = None,
    on_progress: Callable[[str], None] | None = None,
    remover: Callable[[Path], None] = shutil.rmtree,
    allow_partial: bool = False,
) -> None:
    """Re-validate immediately before removal to avoid deleting unchecked targets.

    The caller must obtain explicit confirmation from the user. In tests,
    `remover` can be injected without modifying files.
    """
    if running_from is None:
        raise SafetyError('必须传入正在运行的卸载器路径，以保护目标目录。')
    if allow_partial:
        # Only trusted snapshots from this process can resume after a failed
        # attempt. The original filesystem object must still be present.
        _validate_boundary(original.path, running_from=running_from)
        st = original.path.stat()
        if (st.st_dev, st.st_ino) != original.identity:
            raise SafetyError('未完成卸载的目录身份已改变，拒绝重试。')
        current = original
    else:
        current = inspect_installation(original.path, running_from=running_from)
        if (current.path != original.path or current.markers != original.markers
                or current.identity != original.identity):
            raise SafetyError('目录内容在确认后发生变化，请重新检查。')
    if on_progress:
        on_progress('正在移除所选 Flashpoint 目录……')

    # Production deletion first atomically moves the checked directory to a
    # private, unpredictable sibling. Re-verify the moved filesystem object
    # before recursively deleting: a replacement at the original path cannot
    # silently become the deletion target.
    if remover is shutil.rmtree:
        staging = current.path.parent / ('.Flashpoint-removing-' + uuid.uuid4().hex)
        if staging.exists() or staging.is_symlink():
            raise SafetyError('无法安全创建临时删除目录。')
        os.rename(current.path, staging)
        deletion_started = False
        def record_deletion() -> None:
            nonlocal deletion_started
            deletion_started = True

        try:
            _validate_boundary(staging, running_from=running_from)
            st = staging.stat()
            if (st.st_dev, st.st_ino) != current.identity:
                raise SafetyError('移动后的目标目录与确认时不符，拒绝删除。')
            # The per-directory handle closes the validation/delete race on
            # Windows. A hostile replacement can at most affect an empty
            # directory at rmdir time, never make us rmtree a foreign tree.
            _remove_tree_without_root_race(staging, expected=current.identity,
                                           on_deleted=record_deletion)
        except Exception as exc:
            # Keep the location of any remaining data in every error message,
            # including when a different installation recreated the old path.
            remaining = staging
            if staging.exists() and not current.path.exists():
                try:
                    os.rename(staging, current.path)
                    remaining = current.path
                except OSError:
                    pass
            if remaining.exists():
                detail = f'剩余文件位于 {remaining}。请勿盲目重新选择目录。'
            else:
                detail = '暂存目录已不存在；请检查安装数据是否已移除。'
            if deletion_started:
                raise PartialRemovalError(f'清理未完成：{exc}。{detail}') from exc
            raise SafetyError(f'{exc}。{detail}') from exc
    else:
        # Tests can inject a remover; never used by the packaged UI.
        remover(current.path)

    if on_progress:
        on_progress('安装目录已移除。')

@contextmanager
def _uninstall_mutex(path: Path):
    """Guard a canonical installation against concurrent uninstaller instances.

    On Windows this uses a non-blocking named kernel mutex. Fail closed when
    lock acquisition is not possible; never continue in an unlocked state.
    """
    if os.name != 'nt':
        yield
        return

    import ctypes
    kernel = ctypes.windll.kernel32
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.ReleaseMutex.argtypes = (ctypes.c_void_p,)
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    canonical = os.path.normcase(os.path.abspath(str(path)))
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]
    name = 'Local\\Flashpoint-Uninstaller-' + digest
    handle = kernel.CreateMutexW(None, False, name)
    if not handle:
        raise SafetyError('无法建立互斥保护，已拒绝卸载。')

    acquired = False
    try:
        result = kernel.WaitForSingleObject(handle, 0)
        if result == 0x102:  # WAIT_TIMEOUT
            raise SafetyError('此安装目录已有另一卸载任务在执行。')
        if result not in (0, 0x80):  # WAIT_OBJECT_0, WAIT_ABANDONED
            raise SafetyError('无法确认卸载互斥状态，已拒绝操作。')
        acquired = True
        yield
    finally:
        if acquired:
            kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)


def remove_installation(
    original: Inspection,
    *,
    running_from: Path | None = None,
    on_progress: Callable[[str], None] | None = None,
    remover: Callable[[Path], None] = shutil.rmtree,
    allow_partial: bool = False,
) -> None:
    """Serialize uninstalls before checking, staging, and removing the target."""
    with _uninstall_mutex(original.path):
        _remove_installation_locked(
            original, running_from=running_from, on_progress=on_progress,
            remover=remover, allow_partial=allow_partial)
