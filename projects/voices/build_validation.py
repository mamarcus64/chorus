"""Build the validation partitions from Py-Feat tables.

The pilot preset writes 20 items for each question. Sampling stops once each
stratum has enough boxes, reading tapes in a seed-determined order.
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
from chorus.media import load_manifest, save_manifest  # noqa: E402
from chorus.tasks.frame_choice.task import FrameChoice  # noqa: E402
from projects.voices.build_head_present import render_still, still_relpath  # noqa: E402
from projects.voices.sources import Video, list_videos  # noqa: E402
from projects.voices.validation import (  # noqa: E402
    Drawn,
    FaceHit,
    SampleError,
    TapeSpan,
    absorb,
    hits_from_frames,
    make_features,
    make_locator,
    assemble,
    collection_need,
    need_by_source,
    partition_name,
    prepare_faces,
    questions,
    shortages,
    source_filled,
    still_id,
    interview_id,
)

TASK_TYPE = FrameChoice()
_COLUMNS = [
    "frame",
    "time_s",
    "FaceScore",
    "FaceRectX",
    "FaceRectY",
    "FaceRectWidth",
    "FaceRectHeight",
    "AU12",
    "AU25",
    "AU43",
    "gaze_yaw",
    "gaze_pitch",
    "Yaw",
]


def load_video_hits(video: Video) -> dict[str, list[FaceHit]]:
    import pyarrow.parquet as pq

    table = pq.read_table(video.parquet_path, columns=_COLUMNS)
    columns = {name: table.column(name).to_pylist() for name in _COLUMNS}
    grouped: dict[int, list[dict]] = {}
    order: list[int] = []
    for index, frame_value in enumerate(columns["frame"]):
        frame = int(frame_value)
        if frame not in grouped:
            grouped[frame] = []
            order.append(frame)
        grouped[frame].append(
            {
                "score": columns["FaceScore"][index],
                "bbox": (
                    columns["FaceRectX"][index],
                    columns["FaceRectY"][index],
                    columns["FaceRectWidth"][index],
                    columns["FaceRectHeight"][index],
                ),
                "au12": columns["AU12"][index],
                "au25": columns["AU25"][index],
                "au43": columns["AU43"][index],
                "gaze_yaw": columns["gaze_yaw"][index],
                "gaze_pitch": columns["gaze_pitch"][index],
                "head_yaw": columns["Yaw"][index],
                "time_s": columns["time_s"][index],
            }
        )
    frames: list[tuple[int, float, list[dict]]] = []
    for frame in order:
        rows = grouped[frame]
        time_s = next((row["time_s"] for row in rows if row["time_s"] is not None), None)
        if time_s is None:
            time_s = frame / video.fps if video.fps else 0.0
        frames.append((frame, float(time_s), rows))
    return hits_from_frames(
        video.source,
        video.video_id,
        interview_id(video.source, video.video_id),
        frames,
        video.width,
        video.height,
        keep=8,
    )


def collect_pools(
    videos_by_source: dict[str, list[Video]],
    load_hits,
    need: dict[str, dict[str, int]],
    seed: int,
    max_videos: int,
) -> dict[str, dict[str, list[FaceHit]]]:
    pools: dict[str, dict[str, list[FaceHit]]] = {
        stratum: {source: [] for source in videos_by_source} for stratum in need
    }
    for source, videos in videos_by_source.items():
        rng = random.Random(f"{seed}:{source}")
        order = list(videos)
        rng.shuffle(order)
        read = 0
        for video in order:
            if read >= max_videos or source_filled(pools, need, source):
                break
            found = load_hits(video)
            absorb(pools, found, source, need)
            read += 1
            print(f"{source} {read} {video.video_id}", flush=True)
        missing = shortages(pools, need, source)
        if missing:
            raise SystemExit(
                f"{source} is short after {read} tapes (limit {max_videos}): " + ", ".join(missing)
            )
    return pools


def tapes_for(videos_by_source: dict[str, list[Video]]) -> dict[tuple[str, str], list[TapeSpan]]:
    grouped: dict[tuple[str, str], list[TapeSpan]] = {}
    for source, videos in videos_by_source.items():
        for video in videos:
            key = (source, interview_id(source, video.video_id))
            grouped.setdefault(key, []).append(
                TapeSpan(source, video.video_id, video.n_frames, video.fps)
            )
    return grouped


def config_for(question) -> dict:
    return TASK_TYPE.validate_config(
        {
            "prompt": question.prompt,
            "choices": [
                {"value": value, "label": label, "key": key} for value, label, key in question.choices
            ],
            "overlays": list(question.overlays),
            "instructions": question.instructions,
        }
    )


def load_landmarks(video: Video, frame: int, face: int) -> list[list[float]]:
    import pyarrow.parquet as pq

    columns = ["FaceScore", "FaceRectX", "FaceRectY", "FaceRectWidth", "FaceRectHeight"]
    columns += [f"x_{i}" for i in range(68)] + [f"y_{i}" for i in range(68)]
    table = pq.read_table(video.parquet_path, columns=columns, filters=[("frame", "==", frame)])
    faces = []
    for index in range(table.num_rows):
        faces.append(
            {
                "score": table.column("FaceScore")[index].as_py(),
                "bbox": (
                    table.column("FaceRectX")[index].as_py(),
                    table.column("FaceRectY")[index].as_py(),
                    table.column("FaceRectWidth")[index].as_py(),
                    table.column("FaceRectHeight")[index].as_py(),
                ),
                "row": index,
            }
        )
    ranked = prepare_faces(faces)
    chosen = next((item for item in ranked if item["face"] == face), None)
    if chosen is None:
        raise SystemExit(f"No face {face} on {video.video_id} frame {frame}")
    row = chosen["row"]
    points: list[list[float]] = []
    for index in range(68):
        x = table.column(f"x_{index}")[row].as_py()
        y = table.column(f"y_{index}")[row].as_py()
        if x is None or y is None:
            raise SystemExit(f"Missing landmark {index} on {video.video_id} frame {frame}")
        points.append([float(x), float(y)])
    return points


def _remember_still(
    manifest: dict,
    sizes: dict[str, tuple[int, int]],
    data_dir: Path,
    video: Video,
    frame: int,
) -> None:
    file_id = still_id(video.source, video.video_id, frame)
    if file_id in sizes:
        return
    rel = still_relpath(video.source, video.video_id, frame)
    dest = data_dir / rel
    width, height = render_still(video.video_path, frame, dest)
    sizes[file_id] = (width, height)
    manifest["files"][file_id] = {
        "path": rel,
        "kind": "image",
        "bytes": dest.stat().st_size,
        "source": {"source": video.source, "video_id": video.video_id, "frame": frame},
    }


def render_items(
    project: str,
    assembled: list[tuple[object, list[Drawn]]],
    videos: dict[tuple[str, str], Video],
) -> dict[str, tuple[int, int]]:
    from chorus.config import settings

    data_dir = settings().data_dir(project)
    manifest = load_manifest(project)
    sizes: dict[str, tuple[int, int]] = {}
    for _question, drawn in assembled:
        for item in drawn:
            video = videos[(item.hit.source, item.hit.video_id)]
            _remember_still(manifest, sizes, data_dir, video, item.hit.frame)
            for video_id, frame in item.references:
                ref = videos[(item.hit.source, video_id)]
                _remember_still(manifest, sizes, data_dir, ref, frame)
    save_manifest(project, manifest)
    return sizes


def write_questions(
    project: str,
    preset: str,
    seed: int,
    sources: list[str],
    assembled: list[tuple[object, list[Drawn]]],
    videos: dict[tuple[str, str], Video],
    sizes: dict[str, tuple[int, int]],
) -> None:
    name = partition_name(preset)
    label = "Design pilot" if preset == "pilot" else "Confirmation set"
    conn = connect(project)
    try:
        for question, drawn in assembled:
            config = config_for(question)
            task = tasks.upsert_task(
                conn,
                name=question.name,
                code_key=TASK_TYPE.code_key,
                code_version=TASK_TYPE.code_version,
                config=config,
            )
            partition = partitions.upsert_partition(
                conn,
                task_id=task["id"],
                name=name,
                description=f"{label}, {len(drawn)} items, seed {seed}",
                config={"preset": preset, "seed": seed, "n": len(drawn), "sources": sources},
            )
            planned = []
            for ordinal, item in enumerate(drawn):
                video = videos[(item.hit.source, item.hit.video_id)]
                locator = make_locator(item)
                file_id = locator["still"]
                landmarks = None
                if question.landmarks:
                    landmarks = load_landmarks(video, item.hit.frame, item.hit.face)
                features = make_features(item, sizes[file_id], landmarks)
                TASK_TYPE.validate_item("frame", locator, features)
                planned.append((ordinal, locator, features))
            incoming_ids = {item_id(partition["id"], locator) for _, locator, _features in planned}
            existing_ids = items.item_ids(conn, partition["id"])
            if existing_ids and existing_ids != incoming_ids:
                raise SystemExit(
                    f"{question.name} / {name} already holds a different item set. "
                    "Choose a new partition name so the old labels stay attached."
                )
            if existing_ids:
                items.bump_ordinals(conn, partition["id"])
            for ordinal, locator, features in planned:
                items.upsert_item(
                    conn,
                    partition_id=partition["id"],
                    ordinal=ordinal,
                    kind="frame",
                    locator=locator,
                    features=features,
                )
            print(f"{question.name}: {len(planned)} items", flush=True)
    finally:
        conn.close()


def build(project: str, preset: str, seed: int, sources: list[str], max_videos: int, dry_run: bool) -> dict:
    if has_pending(project):
        migrate(project)
    videos_by_source = list_videos(sources)
    for source in sources:
        if not videos_by_source.get(source):
            raise SystemExit(f"No videos for source {source}")
    need = collection_need(need_by_source(preset, sources))
    pools = collect_pools(videos_by_source, load_video_hits, need, seed, max_videos)
    tapes = tapes_for(videos_by_source)
    bank = questions(preset)
    assembled = []
    try:
        for question in bank:
            assembled.append((question, assemble(question, pools, tapes, seed, sources)))
    except SampleError as exc:
        raise SystemExit(str(exc)) from exc
    if dry_run:
        for question, drawn in assembled:
            counts: dict[str, int] = {}
            for item in drawn:
                counts[item.stratum] = counts.get(item.stratum, 0) + 1
            print(f"{question.name}: {len(drawn)} {counts}", flush=True)
        return {"preset": preset, "questions": len(assembled), "dry_run": True}
    lookup = {
        (video.source, video.video_id): video
        for videos in videos_by_source.values()
        for video in videos
    }
    sizes = render_items(project, assembled, lookup)
    write_questions(project, preset, seed, sources, assembled, lookup, sizes)
    return {"preset": preset, "questions": len(assembled), "dry_run": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build validation partitions")
    parser.add_argument("--project", default="voices")
    parser.add_argument("--preset", choices=("pilot", "full"), default="pilot")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--sources", default="usc,yale")
    parser.add_argument("--max-videos", type=int, default=80)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    sources = [part.strip() for part in args.sources.split(",") if part.strip()]
    build(args.project, args.preset, args.seed, sources, args.max_videos, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
