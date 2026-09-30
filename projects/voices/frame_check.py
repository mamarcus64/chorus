"""Compare an OpenCV seek against a sequential read, and check the box against landmarks.

Py-Feat decoded with OpenCV, so the stills are made the same way. This check
asks whether that seek lands on the same pixels as reading frames in order,
and whether the stored 68-point landmarks sit on the detected box.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from projects.voices.sources import list_videos  # noqa: E402


def read_sequential(video_path: Path, indexes: list[int]) -> dict[int, object]:
    import cv2

    wanted = set(indexes)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {video_path}")
    found: dict[int, object] = {}
    limit = max(indexes)
    index = 0
    while index <= limit:
        ok, frame = cap.read()
        if not ok:
            break
        if index in wanted:
            found[index] = frame.copy()
        index += 1
    cap.release()
    return found


def read_seek(video_path: Path, index: int):
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None
    return frame


def frames_equal(left, right) -> bool:
    import numpy as np

    if left is None or right is None:
        return False
    return bool(np.array_equal(left, right))


def seek_matches(video_path: Path, indexes: list[int]) -> list[dict]:
    sequential = read_sequential(video_path, indexes)
    results = []
    for index in indexes:
        sought = read_seek(video_path, index)
        results.append(
            {
                "frame": index,
                "match": frames_equal(sequential.get(index), sought),
                "sequential": index in sequential,
            }
        )
    return results


def landmarks_for_frame(parquet_path: Path, frame: int) -> tuple[list[float], list[float], list[float]] | None:
    """Return x, y, and the box of the highest-scoring face on this frame."""
    import pyarrow.parquet as pq

    columns = ["frame", "FaceScore", "FaceRectX", "FaceRectY", "FaceRectWidth", "FaceRectHeight"]
    columns += [f"x_{i}" for i in range(68)] + [f"y_{i}" for i in range(68)]
    table = pq.read_table(parquet_path, columns=columns, filters=[("frame", "==", frame)])
    if table.num_rows == 0:
        return None
    scores = table.column("FaceScore").to_pylist()
    best = max(range(len(scores)), key=lambda i: scores[i] if scores[i] is not None else -1)
    xs = [float(table.column(f"x_{i}")[best].as_py()) for i in range(68)]
    ys = [float(table.column(f"y_{i}")[best].as_py()) for i in range(68)]
    box = [
        float(table.column("FaceRectX")[best].as_py()),
        float(table.column("FaceRectY")[best].as_py()),
        float(table.column("FaceRectWidth")[best].as_py()),
        float(table.column("FaceRectHeight")[best].as_py()),
    ]
    return xs, ys, box


def landmark_fraction_inside(xs: list[float], ys: list[float], box: list[float], slack: float = 0.15) -> float:
    x, y, w, h = box
    pad = slack * max(w, h)
    inside = 0
    for px, py in zip(xs, ys):
        if x - pad <= px <= x + w + pad and y - pad <= py <= y + h + pad:
            inside += 1
    return inside / len(xs)


def sample_early_frames(video, limit: int = 2500, n: int = 20) -> list[int]:
    import pyarrow.parquet as pq

    table = pq.read_table(
        video.parquet_path,
        columns=["frame", "FaceScore"],
        filters=[("FaceScore", ">", 0.9), ("frame", "<", limit)],
    )
    frames = sorted({int(value) for value in table.column("frame").to_pylist()})
    if len(frames) <= n:
        return frames
    step = max(1, len(frames) // n)
    return frames[: n * step : step][:n]


def run_check(n: int = 20) -> dict:
    videos = list_videos(["usc"])["usc"]
    if not videos:
        raise RuntimeError("No USC videos are available")
    video = videos[0]
    indexes = sample_early_frames(video, n=n)
    if len(indexes) < n:
        raise RuntimeError(f"Only found {len(indexes)} early frames in {video.video_id}")
    matches = seek_matches(video.video_path, indexes)
    landmark_hits = []
    for index in indexes:
        loaded = landmarks_for_frame(video.parquet_path, index)
        if loaded is None:
            landmark_hits.append({"frame": index, "fraction": 0.0})
            continue
        xs, ys, box = loaded
        landmark_hits.append(
            {"frame": index, "fraction": landmark_fraction_inside(xs, ys, box)}
        )
    return {
        "video_id": video.video_id,
        "seek": matches,
        "landmarks": landmark_hits,
        "seek_ok": all(item["match"] for item in matches),
        "landmarks_ok": all(item["fraction"] >= 0.5 for item in landmark_hits),
    }


def main() -> int:
    report = run_check(20)
    print(report["video_id"], "seek_ok", report["seek_ok"], "landmarks_ok", report["landmarks_ok"])
    for item in report["seek"]:
        if not item["match"]:
            print(" seek mismatch", item["frame"])
    for item in report["landmarks"]:
        if item["fraction"] < 0.5:
            print(" landmarks outside box", item)
    return 0 if report["seek_ok"] and report["landmarks_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
