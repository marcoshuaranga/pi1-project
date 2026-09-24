"""Repository policy checks for raw and processed privacy artifacts."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_raw_xlsx_exports_are_not_tracked_by_git():
    tracked = subprocess.run(
        ["git", "ls-files", "data/raw"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert not [path for path in tracked if path.lower().endswith((".xlsx", ".xls"))]


def test_raw_data_directory_has_no_generated_commit_candidates():
    raw_dir = ROOT / "data" / "raw"
    assert raw_dir.is_dir()
    for path in raw_dir.iterdir():
        if path.suffix.lower() in {".xlsx", ".xls"}:
            ignored = subprocess.run(
                ["git", "check-ignore", "--no-index", str(path.relative_to(ROOT))],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert ignored.returncode == 0, f"Raw export is not ignored: {path}"
