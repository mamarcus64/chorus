"""Build the head-present frame task from Py-Feat face boxes.

Sampling is fixed by the seed: equal counts from each source, a video chosen
uniformly, then a frame chosen uniformly among frames with FaceScore above the
cutoff. Several faces in one frame: one of them, chosen with the same seed.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))

from chorus.db.connection import connect  # noqa: E402
from chorus.db.ids import item_id  # noqa: E402
from chorus.db.migrate import has_pending, migrate  # noqa: E402
from chorus.db.queries import items, partitions, tasks  # noqa: E402
from chorus.media import upsert_manifest_file  # noqa: E402
from chorus.tasks.frame_choice.task import FrameChoice  # noqa: E402
from projects.voices.sources import Video, list_videos  # noqa: E402

TASK_NAME = "Head present (face_score > 0.9)"
TASK_TYPE = FrameChoice()
INSTRUCTIONS = """\
You will see one video frame. A box shows where the face detector placed a face.

Decide whether a human head is inside that box.

- Yes: a human head is inside the box.
- No: the box is empty, or it is on something that is not a human head.
- Unsure: you cannot tell.

Keys: 1 Yes, 2 No, 3 Unsure.
"""


def split_counts(n: int, sources: list[str]) -> list[int]:
    if not sources:
        raise ValueError("at least one source is required")
    if n < 0:
        raise ValueError("n must be >= 0")
    base, remainder = divmod(n, len(sources))
    return [base + (1 if index < remainder else 0) for index in range(len(sources))]


def still_file_id(source: str, video_id: str, frame: int) -> str:
    return f"still:{source}:{video_id}:{frame}"


def still_relpath(source: str, video_id: str, frame: int) -> str:
    return f"stills/{source}/{video_id}/{frame:09d}.jpg"


def load_qualifying(video: Video, min_score: float) -> list[dict]:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    table = pq.read_table(
        video.parquet_path,
        columns=["frame", "time_s", "FaceScore", "FaceRectX", "FaceRectY", "FaceRectWidth", "FaceRectHeight"],
    )
    filtered = table.filter(pc.greater(table["FaceScore"], min_score))
    frames = filtered.column("frame").to_pylist()
    times = filtered.column("time_s").to_pylist()
    scores = filtered.column("FaceScore").to_pylist()
    xs = filtered.column("FaceRectX").to_pylist()
    ys = filtered.column("FaceRectY").to_pylist()
    widths = filtered.column("FaceRectWidth").to_pylist()
    heights = filtered.column("FaceRectHeight").to_pylist()
    grouped: dict[int, dict] = {}
    for index, frame in enumerate(frames):
        frame_i = int(frame)
        bucket = grouped.get(frame_i)
        if bucket is None:
            bucket = {"frame": frame_i, "time_s": round(float(times[index]), 6), "faces": []}
            grouped[frame_i] = bucket
        bucket["faces"].append(
            {
                "score": float(scores[index]),
                "bbox": [float(xs[index]), float(ys[index]), float(widths[index]), float(heights[index])],
            }
        )
    return [grouped[frame] for frame in sorted(grouped)]


def sample_faces(
    videos_by_source: dict[str, list[Video]],
    load_frames,
    n: int,
    seed: int,
    sources: list[str],
    min_score: float,
) -> list[dict]:
    rng = random.Random(seed)
    counts = split_counts(n, sources)
    chosen: list[dict] = []
    used: set[tuple[str, str, int]] = set()
    for source, count in zip(sources, counts):
        videos = videos_by_source[source]
        if count and not videos:
            raise SystemExit(f"No videos for source {source}")
        cache: dict[tuple[str, str], list[dict]] = {}
        for _ in range(count):
            video = None
            frame = None
            for _attempt in range(10000):
                video = videos[rng.randrange(len(videos))]
                key = (video.source, video.video_id)
                if key not in cache:
                    cache[key] = load_frames(video, min_score)
                available = [
                    candidate
                    for candidate in cache[key]
                    if (video.source, video.video_id, candidate["frame"]) not in used
                ]
                if not available:
                    continue
                frame = available[rng.randrange(len(available))]
                used.add((video.source, video.video_id, frame["frame"]))
                break
            else:
                raise SystemExit(f"Not enough frames with FaceScore > {min_score} in {source}")
            assert video is not None and frame is not None
            face = frame["faces"][rng.randrange(len(frame["faces"]))]
            chosen.append(
                {
                    "source": video.source,
                    "video_id": video.video_id,
                    "video_path": video.video_path,
                    "width": video.width,
                    "height": video.height,
                    "frame": frame["frame"],
                    "time_s": frame["time_s"],
                    "bbox": face["bbox"],
                    "face_score": face["score"],
                }
            )
    return chosen


def render_still(video_path: Path, frame_index: int, dest: Path) -> tuple[int, int]:
    import cv2

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 0:
        existing = cv2.imread(str(dest))
        if existing is not None:
            return int(existing.shape[1]), int(existing.shape[0])
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Could not open {video_path}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise SystemExit(f"Could not read frame {frame_index} of {video_path}")
    if not cv2.imwrite(str(dest), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90]):
        raise SystemExit(f"Could not write {dest}")
    return int(frame.shape[1]), int(frame.shape[0])


def task_config() -> dict:
    return TASK_TYPE.validate_config(
        {
            "prompt": "Is a human head inside the box?",
            "choices": [
                {"value": "yes", "label": "Yes", "key": "1"},
                {"value": "no", "label": "No", "key": "2"},
                {"value": "unsure", "label": "Unsure", "key": "3"},
            ],
            "overlays": ["bbox"],
            "instructions": INSTRUCTIONS,
        }
    )


def locator_for(spec: dict) -> dict:
    return {
        "source": spec["source"],
        "video_id": spec["video_id"],
        "frame": spec["frame"],
        "time_s": spec["time_s"],
        "still": still_file_id(spec["source"], spec["video_id"], spec["frame"]),
    }


def build(project: str, partition_name: str, n: int, seed: int, min_score: float, sources: list[str]) -> dict:
    from chorus.config import settings

    if has_pending(project):
        migrate(project)
    videos = list_videos(sources)
    sampled = sample_faces(videos, load_qualifying, n, seed, sources, min_score)
    data_dir = settings().data_dir(project)
    config = task_config()
    conn = connect(project)
    try:
        task = tasks.upsert_task(
            conn,
            name=TASK_NAME,
            code_key=TASK_TYPE.code_key,
            code_version=TASK_TYPE.code_version,
            config=config,
        )
        partition = partitions.upsert_partition(
            conn,
            task_id=task["id"],
            name=partition_name,
            description=f"{n} frames, seed {seed}, FaceScore > {min_score}",
            config={"seed": seed, "n": n, "min_score": min_score, "sources": sources},
        )
        planned = []
        for ordinal, spec in enumerate(sampled):
            rel = still_relpath(spec["source"], spec["video_id"], spec["frame"])
            dest = data_dir / rel
            width, height = render_still(spec["video_path"], spec["frame"], dest)
            locator = locator_for(spec)
            features = {
                "bbox": [round(float(value), 2) for value in spec["bbox"]],
                "face_score": round(float(spec["face_score"]), 6),
                "image_size": [width, height],
            }
            TASK_TYPE.validate_item("frame", locator, features)
            planned.append((ordinal, locator, features, rel, dest))
        incoming_ids = {item_id(partition["id"], locator) for _, locator, _, _, _ in planned}
        existing_ids = items.item_ids(conn, partition["id"])
        if existing_ids and existing_ids != incoming_ids:
            raise SystemExit(
                "This partition already holds a different item set. "
                "Choose a new --partition-name so the old labels stay attached."
            )
        if existing_ids:
            items.bump_ordinals(conn, partition["id"])
        for ordinal, locator, features, rel, dest in planned:
            items.upsert_item(
                conn,
                partition_id=partition["id"],
                ordinal=ordinal,
                kind="frame",
                locator=locator,
                features=features,
            )
            upsert_manifest_file(
                project,
                locator["still"],
                {
                    "path": rel,
                    "kind": "image",
                    "bytes": dest.stat().st_size,
                    "source": {
                        "source": locator["source"],
                        "video_id": locator["video_id"],
                        "frame": locator["frame"],
                    },
                },
            )
            print(f"{ordinal + 1}/{len(planned)} {locator['video_id']} frame {locator['frame']}", flush=True)
    finally:
        conn.close()
    return {"task_id": task["id"], "partition_id": partition["id"], "n": len(planned)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a head-present partition")
    parser.add_argument("--project", default="voices")
    parser.add_argument("--partition-name", required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--min-score", type=float, default=0.9)
    parser.add_argument("--sources", default="usc,yale")
    args = parser.parse_args(argv)
    sources = [part.strip() for part in args.sources.split(",") if part.strip()]
    result = build(args.project, args.partition_name, args.n, args.seed, args.min_score, sources)
    print(f"partition {result['partition_id']} ({result['n']} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
