"""Reject stale application code in a frozen build before packaging an installer.

Run with the release Python environment (which includes PyInstaller).
Comparisons ignore filename rewriting performed by the packager.
"""
from pathlib import Path
import marshal
import sys
import types

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "vid_trans_app", "vt_i18n", "vt_a11y", "vt_settings", "vt_setup",
    "vt_prefs", "vt_api", "vt_workers", "vt_batch", "vt_session", "help_menu",
)


def code_signature(value):
    if isinstance(value, types.CodeType):
        return (
            value.co_code,
            tuple(code_signature(item) for item in value.co_consts),
            value.co_names, value.co_varnames, value.co_argcount,
            value.co_kwonlyargcount, value.co_posonlyargcount, value.co_flags,
            value.co_freevars, value.co_cellvars,
        )
    return value


def verify(executable):
    archive = CArchiveReader(str(executable))
    pyz = archive.open_embedded_archive(
        next(name for name in archive.toc if name.lower().endswith(".pyz"))
    )
    stale = []
    for module in MODULES:
        packaged = (
            marshal.loads(archive.extract(module))
            if module == "vid_trans_app" else pyz.extract(module)
        )
        source = compile(
            (ROOT / (module + ".py")).read_text(encoding="utf-8"),
            module + ".py", "exec", optimize=0,
        )
        matches = code_signature(packaged) == code_signature(source)
        print(("MATCH " if matches else "STALE ") + module)
        if not matches:
            stale.append(module)
    return not stale


if __name__ == "__main__":
    executable = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else
        ROOT / "dist" / "AccessibleVideoTranscriber" / "AccessibleVideoTranscriber.exe"
    )
    raise SystemExit(0 if verify(executable) else 1)
