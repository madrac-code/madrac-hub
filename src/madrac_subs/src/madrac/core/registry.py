"""Windows Shell integration: context menu, SendTo, native COM drop handler.

Usage:
    from madrac.core.registry import registrar_drop_handler, desregistrar_drop_handler
    registrar_drop_handler()  # register all three layers
    desregistrar_drop_handler()  # remove all three layers
"""

import sys
import os
import shutil
import winreg
import subprocess
from pathlib import Path

from .io_utils import write_text, read_text
from .paths import get_user_config_dir

VIDEO_EXTS = [".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv"]
SRT_EXTS = [".srt", ".ass", ".vtt"]
CLSID_DROP_HANDLER = "{B1C9A5E0-8F4D-4E7A-9C3D-2A1B6F8E0D4C}"


def _get_fast_mux_cmd() -> str:
    """Returns the full command line for the shell verb (handles frozen vs dev)."""
    fast_mux = '--fast-mux --no-trash "%1" "%*"'
    if getattr(sys, "frozen", False):
        exe = str(Path(sys.executable).resolve())
        return f'"{exe}" {fast_mux}'
    python = str(Path(sys.executable).resolve())
    launcher = str(Path(__file__).resolve().parent.parent.parent.parent / "launcher_fast_mux.py")
    return f'"{python}" "{launcher}" {fast_mux}'


def _get_exe_path() -> str:
    """Returns the executable path for icon/defaults (frozen or dev)."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    return str(Path(sys.executable).resolve())


def _get_prog_id() -> str:
    exe_name = Path(_get_exe_path()).name.replace(".", "_")
    return f"MADRACSubs.{exe_name}"


# ─── Context Menu Verb ────────────────────────────────────────────────


def registrar_shell_verb() -> bool:
    """Register 'Muxear con Madrac-subs' in the right-click menu of video files."""
    try:
        prog_id = _get_prog_id()
        verb_cmd = _get_fast_mux_cmd()
        base = rf"Software\Classes\{prog_id}"

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "MADRAC-SUBS Video")
            with winreg.CreateKey(k, r"DefaultIcon") as ik:
                icon_path = _get_exe_path()
                winreg.SetValue(ik, "", winreg.REG_SZ, f'"{icon_path}",0')

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\muxear\command") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, verb_cmd)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\muxear") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "Muxear con Madrac-subs")
            icon_path = _get_exe_path()
            winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, f'"{icon_path}",0')

        for ext in VIDEO_EXTS + SRT_EXTS:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}\OpenWithProgids") as k:
                winreg.SetValueEx(k, prog_id, 0, winreg.REG_SZ, "")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}\shell\muxear\command") as k:
                winreg.SetValue(k, "", winreg.REG_SZ, verb_cmd)
        return True
    except Exception:
        return False


def desregistrar_shell_verb() -> bool:
    """Remove context menu entries."""
    try:
        prog_id = _get_prog_id()
        for ext in VIDEO_EXTS + SRT_EXTS:
            for subkey in [rf"Software\Classes\{ext}\shell\muxear", rf"Software\Classes\{ext}\OpenWithProgids"]:
                try:
                    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
                except OSError:
                    pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}")
        except OSError:
            pass
        return True
    except Exception:
        return False


# ─── SendTo integration ───────────────────────────────────────────────


def _get_sendto_folder() -> Path:
    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "SendTo"


def registrar_sendto() -> bool:
    """Add MADRAC-SUBS to the 'Send To' menu for quick SRT muxing."""
    try:
        sendto = _get_sendto_folder()
        sendto.mkdir(parents=True, exist_ok=True)
        target = sys.executable if getattr(sys, "frozen", False) else sys.executable
        if not getattr(sys, "frozen", False):
            args = "-m madrac --fast-mux --no-trash"
        else:
            args = "--fast-mux --no-trash"
        shortcut_path = sendto / "MADRAC-SUBS (muxear SRT).lnk"
        _crear_acceso_directo(
            target, args, str(shortcut_path),
            "Arrastra/Envia .srt a un video para muxear",
        )
        return True
    except Exception:
        return False


def _crear_acceso_directo(target: str, args: str, path: str, desc: str = "") -> None:
    """Create a .lnk shortcut using win32com (falls back to PowerShell)."""
    try:
        from win32com.client import Dispatch
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(path)
        shortcut.TargetPath = target
        shortcut.Arguments = args
        shortcut.Description = desc
        shortcut.WorkingDirectory = str(Path(target).parent)
        shortcut.Save()
        return
    except ImportError:
        pass

    def _ps_escape(s: str) -> str:
        return s.replace("'", "''")

    ps_code = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{_ps_escape(path)}')
$s.TargetPath = '{_ps_escape(target)}'
$s.Arguments = '{_ps_escape(args)}'
$s.Description = '{_ps_escape(desc)}'
$s.Save()
"""
    ps_file = Path(path).with_suffix(".ps1")
    write_text(ps_file, ps_code)
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps_file)],
        check=False, capture_output=True,
    )
    ps_file.unlink(missing_ok=True)


def desregistrar_sendto() -> bool:
    """Remove SendTo shortcut."""
    try:
        shortcut = _get_sendto_folder() / "MADRAC-SUBS (muxear SRT).lnk"
        if shortcut.exists():
            shortcut.unlink()
        return True
    except Exception:
        return False


# ─── COM DLL (drag-and-drop nativo, .NET Framework 4.x) ──────────────


def _get_mscoree_path() -> str:
    """Return the path to mscoree.dll (CLR shim)."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for candidate in [
        Path(windir) / "System32" / "mscoree.dll",
        Path(windir) / "SysWOW64" / "mscoree.dll",
    ]:
        if candidate.exists():
            return str(candidate)
    for arch in ["Framework64", "Framework"]:
        candidate = Path(windir) / "Microsoft.NET" / arch / "v4.0.30319" / "mscoree.dll"
        if candidate.exists():
            return str(candidate)
    return ""


def _copiar_dll_al_usuario() -> bool:
    """Copy pre-compiled MadracDropHandler.dll to user config dir."""
    try:
        if getattr(sys, "frozen", False):
            src = Path(sys._MEIPASS) / "madrac" / "core" / "MadracDropHandler.dll"
        else:
            src = Path(__file__).parent / "MadracDropHandler.dll"
        if not src.exists():
            return False
        destino = get_user_config_dir() / "MadracDropHandler.dll"
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(destino))
        return True
    except Exception:
        return False


def _registrar_clsid(dll_path: Path) -> bool:
    """Write COM CLSID registry entries for the .NET COM assembly."""
    try:
        clsid_base = rf"Software\Classes\CLSID\{CLSID_DROP_HANDLER}"
        mscoree = _get_mscoree_path()
        dll_uri = dll_path.resolve().as_uri()

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, clsid_base) as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "MadracDropHandler")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{clsid_base}\\InprocServer32") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, mscoree)
            winreg.SetValueEx(k, "ThreadingModel", 0, winreg.REG_SZ, "Both")
            winreg.SetValueEx(k, "Assembly", 0, winreg.REG_SZ,
                "MadracDropHandler, Version=0.0.0.0, "
                "Culture=neutral, PublicKeyToken=null")
            winreg.SetValueEx(k, "Class", 0, winreg.REG_SZ, "MadracDropHandler")
            winreg.SetValueEx(k, "CodeBase", 0, winreg.REG_SZ, dll_uri)
            winreg.SetValueEx(k, "RuntimeVersion", 0, winreg.REG_SZ, "v4.0.30319")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{clsid_base}\\ProgId") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "MadracSubs.DropHandler")
        return True
    except Exception:
        return False


def _escribir_shellex_drophandler() -> None:
    """Register shellex DropHandler CLSID for each video extension."""
    for ext in VIDEO_EXTS:
        try:
            key = rf"Software\Classes\{ext}\shellex\DropHandler"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
                winreg.SetValue(k, "", winreg.REG_SZ, CLSID_DROP_HANDLER)
        except Exception:
            pass


def _guardar_config_app() -> None:
    """Save exe/script paths for the DLL to read at drop time."""
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\MadracSubs") as k:
            exe = str(Path(sys.executable).resolve())
            winreg.SetValueEx(k, "AppExe", 0, winreg.REG_SZ, exe)
            if getattr(sys, "frozen", False):
                winreg.SetValueEx(k, "ScriptPath", 0, winreg.REG_SZ, "")
            else:
                script = str(Path(__file__).resolve().parent.parent.parent.parent / "launcher_fast_mux.py")
                winreg.SetValueEx(k, "ScriptPath", 0, winreg.REG_SZ, script)
            workdir = str(Path(sys.executable).resolve().parent)
            winreg.SetValueEx(k, "WorkDir", 0, winreg.REG_SZ, workdir)
    except Exception:
        pass


def _limpiar_config_app() -> None:
    """Remove MadracSubs config key from registry."""
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\MadracSubs")
    except OSError:
        pass


def compilar_y_registrar_dll() -> bool:
    """Copy pre-compiled DLL and register it as a COM drop handler."""
    if not _copiar_dll_al_usuario():
        return False
    dll = get_user_config_dir() / "MadracDropHandler.dll"
    if not _registrar_clsid(dll):
        _limpiar_dll()
        return False
    _escribir_shellex_drophandler()
    _guardar_config_app()
    return True


def _desregistrar_clsid() -> None:
    """Remove COM CLSID and shellex DropHandler entries."""
    for ext in VIDEO_EXTS:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{ext}\shellex\DropHandler")
        except OSError:
            pass
    clsid = rf"Software\Classes\CLSID\{CLSID_DROP_HANDLER}"
    for sub in ["ProgId", "InprocServer32", ""]:
        try:
            key = f"{clsid}\\{sub}" if sub else clsid
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
        except OSError:
            pass
    _limpiar_config_app()


def _limpiar_dll() -> None:
    """Delete the compiled DLL from user config dir."""
    dll = get_user_config_dir() / "MadracDropHandler.dll"
    if dll.exists():
        dll.unlink()


# ─── Combined functions ──────────────────────────────────────────────


def registrar_drop_handler() -> bool:
    """Register shell verb + sendto + COM DLL for full integration."""
    ok = registrar_shell_verb()
    if sys.platform == "win32":
        registrar_sendto()
        ok = compilar_y_registrar_dll() and ok
    if ok:
        try:
            from ..config import set_config, get_config_manager
            set_config("file_handlers.registered", True)
            get_config_manager()._save()
        except Exception:
            pass
    return ok


def desregistrar_drop_handler() -> bool:
    """Remove all integration (shell verb, sendto, COM DLL)."""
    ok = desregistrar_shell_verb()
    if sys.platform == "win32":
        desregistrar_sendto()
        _desregistrar_clsid()
        _limpiar_dll()
    try:
        from ..config import set_config, get_config_manager
        set_config("file_handlers.registered", False)
        get_config_manager()._save()
    except Exception:
        pass
    return ok
