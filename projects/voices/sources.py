"""USC and Yale recordings, joined to their Py-Feat sidecars."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PYFEAT_ROOT = Path("/data/VOICES/pyfeat-features")
EXCLUDED_VIDEO_IDS = {"321.3"}


@dataclass(frozen=True)
class Video:
    source: str
    video_id: str
    video_path: Path
    parquet_path: Path
    width: int
    height: int
    fps: float
    n_frames: int = 0


def list_videos(sources: list[str]) -> dict[str, list[Video]]:
    found: dict[str, list[Video]] = {}
    for source in sources:
        folder = PYFEAT_ROOT / source
        videos: list[Video] = []
        if folder.is_dir():
            for meta_path in sorted(folder.glob("*.meta.json")):
                meta = json.loads(meta_path.read_text())
                video_id = str(meta["video_id"])
                if video_id in EXCLUDED_VIDEO_IDS:
                    continue
                video_path = Path(meta["path"])
                if not video_path.is_file():
                    continue
                parquet_path = meta_path.with_name(meta_path.name.replace(".meta.json", ".parquet"))
                if not parquet_path.is_file():
                    continue
                videos.append(
                    Video(
                        source=source,
                        video_id=video_id,
                        video_path=video_path,
                        parquet_path=parquet_path,
                        width=int(meta["width"]),
                        height=int(meta["height"]),
                        fps=float(meta["fps"]),
                        n_frames=int(meta.get("decoded_frames") or meta.get("reported_frames") or 0),
                    )
                )
        found[source] = videos
    return found
