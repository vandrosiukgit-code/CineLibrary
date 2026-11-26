from __future__ import annotations

import argparse
import json
import re
import stat
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v", ".ts", ".m2ts", ".webm", ".mpg", ".mpeg"}
OPTICAL_DIRECTORIES = {"video_ts": "dvd", "bdmv": "bluray"}
DOWNLOAD_SUFFIX = ".!qb"
CL_ID = re.compile(r"(?<![a-z0-9])CL-\d+(?!\d)", re.IGNORECASE)


@dataclass(frozen=True)
class MediaCopy:
    path: str
    name: str
    kind: str
    status: Literal["available", "downloading", "unknown"]
    cl_id: str | None


@dataclass
class ScanResult:
    copies: list[MediaCopy] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


def scan_media(root: Path, *, excluded: tuple[Path, ...] = (), recursive: bool = True) -> ScanResult:
    root = root.resolve()
    exclusions = {(root / path).resolve() for path in excluded}
    if any(path == root or not path.is_relative_to(root) for path in exclusions):
        raise ValueError("Исключения должны быть подпапками медиатеки")
    result = ScanResult()

    def entries(directory: Path) -> list[Path]:
        try:
            return sorted(directory.iterdir(), key=lambda path: (path.name.casefold(), path.name))
        except OSError as error:
            result.errors[str(directory)] = str(error)
            return []

    def add(path: Path, kind: str, status: Literal["available", "downloading", "unknown"]) -> None:
        ids = CL_ID.findall(path.name)
        if kind in {"video", "iso"} and path.parent.is_relative_to(root):
            ids.extend(CL_ID.findall(path.parent.name))
        unique_ids = {value.upper() for value in ids}
        result.copies.append(MediaCopy(
            str(path), path.name, kind, status,
            next(iter(unique_ids)) if len(unique_ids) == 1 else None,
        ))

    def visible(directory: Path) -> Iterator[tuple[Path, int]]:
        for path in entries(directory):
            if path in exclusions:
                continue
            try:
                mode = path.lstat().st_mode
                if not stat.S_ISLNK(mode) and not path.is_junction():
                    yield path, mode
            except OSError as error:
                result.errors[str(path)] = str(error)

    def scan_optical(directory: Path, kind: str) -> None:
        errors_before = len(result.errors)
        stack = [directory]
        files = set()
        while stack:
            current = stack.pop()
            for path, mode in visible(current):
                if stat.S_ISDIR(mode):
                    stack.append(path)
                elif stat.S_ISREG(mode):
                    files.add(path.relative_to(directory).as_posix().casefold())
        if any(name.endswith(DOWNLOAD_SUFFIX) for name in files):
            status = "downloading"
        elif len(result.errors) != errors_before:
            status = "unknown"
        elif kind == "dvd":
            status = "available" if "video_ts.ifo" in files and any(name.endswith(".vob") for name in files) else "unknown"
        else:
            has_stream = any(name.startswith("stream/") and name.endswith(".m2ts") for name in files)
            status = "available" if "index.bdmv" in files and has_stream else "unknown"
        add(directory.parent, kind, status)

    stack = [root]
    while stack:
        directory = stack.pop()
        for path, mode in visible(directory):
            if stat.S_ISDIR(mode):
                kind = OPTICAL_DIRECTORIES.get(path.name.casefold())
                if kind:
                    scan_optical(path, kind)
                elif recursive:
                    stack.append(path)
                continue
            if not stat.S_ISREG(mode):
                continue
            name = path.name.casefold()
            downloading = name.endswith(DOWNLOAD_SUFFIX)
            suffix = Path(name.removesuffix(DOWNLOAD_SUFFIX)).suffix
            if suffix == ".iso" or suffix in VIDEO_EXTENSIONS:
                add(path, "iso" if suffix == ".iso" else "video", "downloading" if downloading else "available")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверить папку CineLibrary и вывести найденные копии в JSON.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--exclude", type=Path, action="append", default=[])
    parser.add_argument("--no-recursion", action="store_true")
    args = parser.parse_args()
    try:
        result = scan_media(args.root, excluded=tuple(args.exclude), recursive=not args.no_recursion)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return int(bool(result.errors))


if __name__ == "__main__":
    raise SystemExit(main())
