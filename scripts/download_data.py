"""Download the Kaggle competition files listed in data_manifest.csv.

Idempotent: a file is skipped when it already exists with the expected size,
so running `make data` again only downloads what is missing or incomplete.
"""

import argparse
import csv
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MANIFEST = Path(__file__).with_name("data_manifest.csv")


@dataclass(frozen=True)
class ManifestEntry:
    remote_path: str  # path inside the Kaggle competition
    local_path: str  # path relative to --dest
    size_bytes: int


def read_manifest(path: Path) -> list[ManifestEntry]:
    with path.open(newline="") as f:
        return [
            ManifestEntry(row["remote_path"], row["local_path"], int(row["size_bytes"]))
            for row in csv.DictReader(f)
        ]


def is_complete(path: Path, expected_size: int) -> bool:
    return path.is_file() and path.stat().st_size == expected_size


def download_file(competition: str, entry: ManifestEntry, target: Path) -> None:
    """Download one file from Kaggle and move it to `target`.

    The Kaggle CLI recreates the remote folders under -p (e.g. parquet_files/train/),
    so we download into a temporary folder next to `target` and then move the file.
    The move is atomic, so `target` never holds a half-downloaded file.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".download-") as tmp:
        cmd = ["kaggle", "competitions", "download", competition]
        cmd += ["-f", entry.remote_path, "-p", tmp, "--force"]
        subprocess.run(cmd, check=True)
        downloaded = Path(tmp) / entry.remote_path
        if not downloaded.is_file():
            raise FileNotFoundError(f"Kaggle CLI did not create {downloaded}")
        downloaded.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", required=True, help="Kaggle competition slug")
    parser.add_argument("--dest", type=Path, required=True, help="local data folder")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    if shutil.which("kaggle") is None:
        print(
            "error: kaggle CLI not found. Run: uv tool install kaggle --with six", file=sys.stderr
        )
        return 1

    entries = read_manifest(args.manifest)
    downloaded = skipped = 0
    for i, entry in enumerate(entries, start=1):
        target = args.dest / entry.local_path
        label = f"[{i:>2}/{len(entries)}] {entry.local_path}"

        if is_complete(target, entry.size_bytes):
            print(f"{label}: ok, skipping")
            skipped += 1
            continue

        print(f"{label}: downloading", flush=True)  # show before Kaggle's progress bar
        download_file(args.competition, entry, target)
        actual = target.stat().st_size
        if actual != entry.size_bytes:
            target.unlink()
            print(
                f"error: {label}: expected {entry.size_bytes} bytes, got {actual}", file=sys.stderr
            )
            return 1
        downloaded += 1

    print(f"Done: {downloaded} downloaded, {skipped} already present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
