"""Sampling rules for the facial-behavior validation questions.

A question is one prompt. The pilot preset draws 20 items for each question.
The confirmation preset draws 200. Most of those are the difficult frames.
A smaller group in each question is a high-confidence case, kept so the
common frames are checked as well. Within a question, a box is drawn for the
first matching stratum only.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

_YALE_TESTIMONY = re.compile(r"^mssa_hvt_(\d+[A-Za-z]*)_[pP]\d+of\d+")
_YALE_PART = re.compile(r"[pP](\d+)of\d+")

LARGE_AREA = 0.08
SMALL_AREA = 0.03
LOW_SCORE_MAX = 0.9
USUAL_SCORE = 0.95
DETECTOR_MIN = 0.5
BEHAVIOR_SCORE = 0.9
MULTI_CAP = 4

AU12_HIGH = 0.8
AU12_LOW = 0.1
AU12_MID_LO = 0.35
AU12_MID_HI = 0.65
AU25_HIGH = 0.95
AU25_LOW = 0.2
AU25_MID_LO = 0.4
AU25_MID_HI = 0.7
AU43_HIGH = 0.7
AU43_LOW = 0.1

GAZE_CENTER = 0.15
GAZE_SIDE = 0.40
GAZE_DOWN = 0.30
HEAD_CENTER = 0.08
HEAD_TURN = 0.25

REFERENCE_COUNT = 6
REFERENCE_WINDOW_S = 2.0


class SampleError(RuntimeError):
    """A question could not be filled under its sampling rules."""


@dataclass(frozen=True)
class FaceHit:
    source: str
    video_id: str
    testimony_id: str
    frame: int
    time_s: float
    face: int
    score: float
    bbox: tuple[float, float, float, float]
    au12: float | None = None
    au25: float | None = None
    au43: float | None = None
    gaze_yaw: float | None = None
    gaze_pitch: float | None = None
    head_pitch: float | None = None
    head_roll: float | None = None
    head_yaw: float | None = None


@dataclass(frozen=True)
class TapeSpan:
    source: str
    video_id: str
    n_frames: int
    fps: float

    @property
    def duration(self) -> float:
        if self.fps <= 0 or self.n_frames <= 0:
            return 0.0
        return self.n_frames / self.fps


@dataclass(frozen=True)
class Drawn:
    hit: FaceHit
    stratum: str
    references: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Question:
    name: str
    prompt: str
    choices: tuple[tuple[str, str, str], ...]
    overlays: tuple[str, ...]
    instructions: str
    strata: tuple[tuple[str, int], ...]
    references: bool
    landmarks: bool


_SURVIVOR = (
    ("present", "Survivor in Present Day", "1"),
    ("other", "Picture/Other Person", "2"),
    ("not_person", "Not a Person", "3"),
    ("unsure", "Unsure", "4"),
)

_SMILE = (
    ("smiling", "Smiling", "1"),
    ("not_smiling", "Not Smiling", "2"),
    ("unsure", "Unsure", "3"),
)

_OPEN = (
    ("open", "Open", "1"),
    ("closed", "Closed", "2"),
    ("unsure", "Unsure", "3"),
)

_ALIGNED = (
    ("aligned", "Aligned", "1"),
    ("not_aligned", "Not aligned", "2"),
    ("unsure", "Unsure", "3"),
)


def _keys(text: str) -> str:
    return text.rstrip() + "\n"


SURVIVOR_INSTRUCTIONS = _keys(
    """\
A box marks one detected region in the main frame.

Six smaller frames show other moments from the same interview. Use them to see who is being interviewed. Judge only the boxed region.

Survivor in Present Day: the box is on the survivor's face as they look during this interview, in the room, on this day.
Picture/Other Person: the box is on someone else, or on a photograph or a screen. A picture of the survivor, including one from years earlier, counts here.
Not a Person: the box is not on a face.
Unsure: you cannot tell.

Press 1 for Survivor in Present Day, 2 for Picture/Other Person, 3 for Not a Person, 4 for Unsure.
"""
)

LANDMARK_INSTRUCTIONS = _keys(
    """\
White points mark the detected eyes, brows, nose, mouth, and jaw of the boxed face.

On the face: the points sit on those features.
Slipped off the features: the points belong to this face but have drifted off the features.
On the wrong thing: the points sit on a different person, a photograph, or something that is not a face.
Unsure: you cannot tell.

Press 1 for On the face, 2 for Slipped off the features, 3 for On the wrong thing, 4 for Unsure.
"""
)

SMILE_INSTRUCTIONS = _keys(
    """\
Decide whether the person in the box is smiling.

Smiling: the mouth is clearly smiling.
Not Smiling: the person is not smiling.
Unsure: you cannot tell.

Press 1 for Smiling, 2 for Not Smiling, 3 for Unsure.
"""
)

MOUTH_INSTRUCTIONS = _keys(
    """\
Decide whether the mouth in the box is open.

Open: the lips are parted.
Closed: the lips meet.
Unsure: you cannot tell.

Press 1 for Open, 2 for Closed, 3 for Unsure.
"""
)

EYES_INSTRUCTIONS = _keys(
    """\
Decide whether the eyes in the box are open or closed.

Open: at least one eye is open.
Closed: both eyes are shut, including a blink.
Unsure: you cannot tell.

Press 1 for Open, 2 for Closed, 3 for Unsure.
"""
)

GAZE_INSTRUCTIONS = _keys(
    """\
Two copies of the same frame are shown. The photograph has no drawing. The estimate draws the predicted direction of the eyes.

An arrow starts at each eye. A circle at the eye means the estimate points toward the camera.

Aligned: the drawing matches where the eyes are looking.
Not aligned: the drawing points somewhere else, or a circle is drawn when the eyes are clearly averted.
Unsure: the eyes are hidden, or you cannot tell.

Press 1 for Aligned, 2 for Not aligned, 3 for Unsure.
"""
)

HEAD_INSTRUCTIONS = _keys(
    """\
Two copies of the same frame are shown. The photograph has no drawing. The estimate draws three axes on the face.

Red is the left-right axis of the head. Green is the up-down axis. Blue is the direction the face is estimated to point. When that direction is toward the camera, blue shrinks to a dot at the center.

Aligned: the axes sit with the head. Blue points the way the face is turned, and red and green follow the tilt of the head.
Not aligned: an axis is clearly wrong.
Unsure: you cannot tell.

Press 1 for Aligned, 2 for Not aligned, 3 for Unsure.
"""
)

_LANDMARK_CHOICES = (
    ("on_face", "On the face", "1"),
    ("slipped", "Slipped off the features", "2"),
    ("wrong", "On the wrong thing", "3"),
    ("unsure", "Unsure", "4"),
)

_PRESET_COUNTS: dict[str, dict[str, tuple[tuple[str, int], ...]]] = {
    "pilot": {
        "survivor": (("several", 6), ("small", 4), ("low", 4), ("usual", 6)),
        "landmarks": (("landmarks", 20),),
        "smile": (("smile_high", 10), ("smile_low", 10)),
        "mouth": (("mouth_high", 10), ("mouth_low", 10)),
        "eyes": (("eyes_high", 10), ("eyes_low", 10)),
        "gaze": (("gaze_yaw_neg", 4), ("gaze_yaw_pos", 4), ("gaze_down", 4), ("gaze_center", 8)),
        "head": (("head_yaw_neg", 6), ("head_yaw_pos", 6), ("head_center", 8)),
    },
    "full": {
        "survivor": (("several", 100), ("small", 50), ("low", 20), ("usual", 30)),
        "landmarks": (
            ("landmarks_turn", 70),
            ("landmarks_small", 40),
            ("landmarks_several", 40),
            ("landmarks_frontal", 50),
        ),
        "smile": (("smile_mid", 120), ("smile_high", 40), ("smile_low", 40)),
        "mouth": (("mouth_mid", 120), ("mouth_high", 40), ("mouth_low", 40)),
        "eyes": (("eyes_high", 160), ("eyes_low", 40)),
        "gaze": (("gaze_yaw_neg", 70), ("gaze_yaw_pos", 70), ("gaze_down", 30), ("gaze_center", 30)),
        "head": (("head_yaw_neg", 85), ("head_yaw_pos", 85), ("head_center", 30)),
    },
}


def questions(preset: str) -> list[Question]:
    if preset not in _PRESET_COUNTS:
        raise SampleError(f"unknown preset {preset}")
    counts = _PRESET_COUNTS[preset]
    return [
        Question(
            "Survivor, present day",
            "What is inside the box?",
            _SURVIVOR,
            ("bbox",),
            SURVIVOR_INSTRUCTIONS,
            counts["survivor"],
            True,
            False,
        ),
        Question(
            "Landmarks on the face",
            "Do these points lie on this person's eyes, mouth, and jaw?",
            _LANDMARK_CHOICES,
            ("bbox", "landmarks"),
            LANDMARK_INSTRUCTIONS,
            counts["landmarks"],
            False,
            True,
        ),
        Question(
            "Smile",
            "Is this person smiling?",
            _SMILE,
            ("bbox",),
            SMILE_INSTRUCTIONS,
            counts["smile"],
            False,
            False,
        ),
        Question(
            "Mouth open",
            "Is the mouth open or closed?",
            _OPEN,
            ("bbox",),
            MOUTH_INSTRUCTIONS,
            counts["mouth"],
            False,
            False,
        ),
        Question(
            "Eyes closed",
            "Are the eyes open or closed?",
            _OPEN,
            ("bbox",),
            EYES_INSTRUCTIONS,
            counts["eyes"],
            False,
            False,
        ),
        Question(
            "Gaze direction",
            "Does the drawing match where the eyes are looking?",
            _ALIGNED,
            ("gaze",),
            GAZE_INSTRUCTIONS,
            counts["gaze"],
            False,
            False,
        ),
        Question(
            "Head direction",
            "Does the drawing match the way the head is turned?",
            _ALIGNED,
            ("pose",),
            HEAD_INSTRUCTIONS,
            counts["head"],
            False,
            False,
        ),
    ]


def partition_name(preset: str) -> str:
    if preset == "pilot":
        return "pilot-20"
    if preset == "full":
        return "confirmation"
    raise SampleError(f"unknown preset {preset}")


def interview_id(source: str, video_id: str) -> str:
    if source == "usc":
        interview, _, _rest = video_id.partition(".")
        return interview or video_id
    match = _YALE_TESTIMONY.match(video_id)
    if match:
        return match.group(1)
    return video_id


def tape_index(source: str, video_id: str) -> int:
    if source == "usc":
        _interview, sep, part = video_id.partition(".")
        if sep and part.isdigit():
            return int(part)
        return 0
    match = _YALE_PART.search(video_id)
    if match:
        return int(match.group(1))
    return 0


def split_counts(n: int, sources: list[str]) -> list[int]:
    if not sources:
        raise SampleError("at least one source is required")
    if n < 0:
        raise SampleError("n must be >= 0")
    base, remainder = divmod(n, len(sources))
    return [base + (1 if index < remainder else 0) for index in range(len(sources))]


def per_video_limit(stratum: str) -> int:
    if stratum in {"several", "landmarks_several"}:
        return 4
    return 2


def need_by_source(preset: str, sources: list[str]) -> dict[str, dict[str, int]]:
    need: dict[str, dict[str, int]] = {}
    for question in questions(preset):
        for stratum, count in question.strata:
            parts = split_counts(count, sources)
            bucket = need.setdefault(stratum, {source: 0 for source in sources})
            for source, part in zip(sources, parts):
                bucket[source] = bucket.get(source, 0) + part
    return need


_OVERLAP = ("several", "small", "low")


def collection_need(draw: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    """Read extra boxes for strata that can describe the same face.

    The survivor question uses each box once, so a face that is both small
    and low-scoring has to be replaceable in the stratum it is not drawn for.
    """
    collect = {stratum: dict(counts) for stratum, counts in draw.items()}
    sources = list(next(iter(draw.values())).keys()) if draw else []
    for source in sources:
        total = sum(draw[name][source] for name in _OVERLAP if name in draw)
        padded = total + 4
        for name in _OVERLAP:
            if name in collect:
                collect[name][source] = max(collect[name][source], padded)
    return collect


def _area(bbox: tuple[float, float, float, float], width: int, height: int) -> float:
    if width <= 0 or height <= 0:
        return 0.0
    return (bbox[2] * bbox[3]) / (width * height)


def prepare_faces(faces: list[dict]) -> list[dict]:
    """Keep usable boxes and rank them by score, then by position."""
    valid: list[dict] = []
    for face in faces:
        score = face.get("score")
        bbox = face.get("bbox")
        if score is None or not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
            continue
        if any(value is None for value in bbox):
            continue
        x, y, w, h = (float(value) for value in bbox)
        if w <= 0 or h <= 0:
            continue
        item = dict(face)
        item["score"] = float(score)
        item["bbox"] = (x, y, w, h)
        valid.append(item)
    valid.sort(key=lambda item: (-item["score"], item["bbox"][0], item["bbox"][1]))
    for index, item in enumerate(valid):
        item["face"] = index
    return valid


def _optional(face: dict, key: str) -> float | None:
    value = face.get(key)
    if value is None:
        return None
    return float(value)


def strata_for_faces(faces: list[dict], width: int, height: int) -> list[tuple[str, dict]]:
    """Strata a frame's boxes can fill. One box may match several questions."""
    ranked = prepare_faces(faces)
    n_faces = len(ranked)
    found: list[tuple[str, dict]] = []
    for face in ranked:
        score = face["score"]
        area = _area(face["bbox"], width, height)
        rank = face["face"]
        if DETECTOR_MIN < score <= LOW_SCORE_MAX:
            found.append(("low", face))
        if n_faces >= 2 and score > DETECTOR_MIN and rank < MULTI_CAP:
            found.append(("several", face))
        if area < SMALL_AREA and score > DETECTOR_MIN:
            found.append(("small", face))
        if n_faces == 1 and score > USUAL_SCORE and area >= LARGE_AREA:
            found.append(("usual", face))
        if n_faces == 1 and area < SMALL_AREA and score > BEHAVIOR_SCORE:
            found.append(("landmarks_small", face))
        if n_faces >= 2 and score > BEHAVIOR_SCORE and rank < MULTI_CAP:
            found.append(("landmarks_several", face))
        if not (n_faces == 1 and score > BEHAVIOR_SCORE and area >= LARGE_AREA):
            continue
        found.append(("landmarks", face))
        au12 = _optional(face, "au12")
        au25 = _optional(face, "au25")
        au43 = _optional(face, "au43")
        gaze_yaw = _optional(face, "gaze_yaw")
        gaze_pitch = _optional(face, "gaze_pitch")
        head_yaw = _optional(face, "head_yaw")
        if head_yaw is not None and abs(head_yaw) > HEAD_TURN:
            found.append(("landmarks_turn", face))
        elif head_yaw is not None and abs(head_yaw) < HEAD_CENTER and score > USUAL_SCORE:
            found.append(("landmarks_frontal", face))
        if au12 is not None and au12 >= AU12_HIGH:
            found.append(("smile_high", face))
        elif au12 is not None and au12 <= AU12_LOW:
            found.append(("smile_low", face))
        elif au12 is not None and AU12_MID_LO <= au12 <= AU12_MID_HI:
            found.append(("smile_mid", face))
        if au25 is not None and au25 >= AU25_HIGH:
            found.append(("mouth_high", face))
        elif au25 is not None and au25 <= AU25_LOW:
            found.append(("mouth_low", face))
        elif au25 is not None and AU25_MID_LO <= au25 <= AU25_MID_HI:
            found.append(("mouth_mid", face))
        if au43 is not None and au43 >= AU43_HIGH:
            found.append(("eyes_high", face))
        elif au43 is not None and au43 <= AU43_LOW:
            found.append(("eyes_low", face))
        if gaze_yaw is not None and gaze_pitch is not None:
            if abs(gaze_yaw) > GAZE_SIDE:
                found.append(("gaze_yaw_pos" if gaze_yaw > 0 else "gaze_yaw_neg", face))
            elif gaze_pitch > GAZE_DOWN:
                found.append(("gaze_down", face))
            elif abs(gaze_yaw) < GAZE_CENTER and abs(gaze_pitch) < GAZE_CENTER:
                found.append(("gaze_center", face))
        if head_yaw is not None and abs(head_yaw) > HEAD_TURN:
            found.append(("head_yaw_pos" if head_yaw > 0 else "head_yaw_neg", face))
        elif head_yaw is not None and abs(head_yaw) < HEAD_CENTER:
            found.append(("head_center", face))
    return found


def space_evenly(items: list, count: int) -> list:
    if count <= 0 or not items:
        return []
    if len(items) <= count:
        return list(items)
    if count == 1:
        return [items[len(items) // 2]]
    step = (len(items) - 1) / (count - 1)
    return [items[round(index * step)] for index in range(count)]


def _hit_from(source: str, video_id: str, testimony: str, frame: int, time_s: float, face: dict) -> FaceHit:
    return FaceHit(
        source=source,
        video_id=video_id,
        testimony_id=testimony,
        frame=int(frame),
        time_s=float(time_s),
        face=int(face["face"]),
        score=float(face["score"]),
        bbox=tuple(face["bbox"]),
        au12=_optional(face, "au12"),
        au25=_optional(face, "au25"),
        au43=_optional(face, "au43"),
        gaze_yaw=_optional(face, "gaze_yaw"),
        gaze_pitch=_optional(face, "gaze_pitch"),
        head_pitch=_optional(face, "head_pitch"),
        head_roll=_optional(face, "head_roll"),
        head_yaw=_optional(face, "head_yaw"),
    )


def hits_from_frames(
    source: str,
    video_id: str,
    testimony: str,
    frames: list[tuple[int, float, list[dict]]],
    width: int,
    height: int,
    keep: int | None = None,
) -> dict[str, list[FaceHit]]:
    pending: dict[str, list[tuple[int, float, dict]]] = {}
    for frame, time_s, faces in frames:
        for stratum, face in strata_for_faces(faces, width, height):
            pending.setdefault(stratum, []).append((int(frame), float(time_s), face))
    buckets: dict[str, list[FaceHit]] = {}
    for stratum, rows in pending.items():
        rows.sort(key=lambda row: (row[0], row[2]["face"]))
        chosen = space_evenly(rows, keep) if keep is not None else rows
        buckets[stratum] = [
            _hit_from(source, video_id, testimony, frame, time_s, face) for frame, time_s, face in chosen
        ]
    return buckets


def absorb(
    pools: dict[str, dict[str, list[FaceHit]]],
    found: dict[str, list[FaceHit]],
    source: str,
    need: dict[str, dict[str, int]],
) -> None:
    """Add a spaced handful from one tape, stopping at the stratum quota."""
    for stratum, hits in found.items():
        quota = need.get(stratum, {}).get(source, 0)
        if quota <= 0:
            continue
        have = pools.setdefault(stratum, {}).setdefault(source, [])
        room = quota - len(have)
        if room <= 0:
            continue
        have.extend(space_evenly(hits, min(room, per_video_limit(stratum))))


def source_filled(pools: dict[str, dict[str, list[FaceHit]]], need: dict[str, dict[str, int]], source: str) -> bool:
    for stratum, counts in need.items():
        if len(pools.get(stratum, {}).get(source, [])) < counts.get(source, 0):
            return False
    return True


def shortages(pools: dict[str, dict[str, list[FaceHit]]], need: dict[str, dict[str, int]], source: str) -> list[str]:
    missing = []
    for stratum, counts in sorted(need.items()):
        want = counts.get(source, 0)
        have = len(pools.get(stratum, {}).get(source, []))
        if have < want:
            missing.append(f"{stratum} {have}/{want}")
    return missing


def draw_spread(
    by_source: dict[str, list[FaceHit]],
    count: int,
    seed: str,
    sources: list[str],
) -> list[FaceHit]:
    """Draw `count` hits, split across sources, spreading across tapes."""
    chosen: list[FaceHit] = []
    for source, quota in zip(sources, split_counts(count, sources)):
        if quota == 0:
            continue
        pool = list(by_source.get(source, []))
        rng = random.Random(f"{seed}:{source}")
        rng.shuffle(pool)
        by_video: dict[str, list[FaceHit]] = {}
        order: list[str] = []
        for hit in pool:
            if hit.video_id not in by_video:
                order.append(hit.video_id)
                by_video[hit.video_id] = []
            by_video[hit.video_id].append(hit)
        rng.shuffle(order)
        picked: list[FaceHit] = []
        round_index = 0
        while len(picked) < quota:
            progressed = False
            for video_id in order:
                group = by_video[video_id]
                if round_index < len(group):
                    picked.append(group[round_index])
                    progressed = True
                    if len(picked) == quota:
                        break
            if not progressed:
                break
            round_index += 1
        if len(picked) < quota:
            raise SampleError(f"{source} has {len(picked)} of {quota}")
        chosen.extend(picked)
    return chosen


def _locate(spans: list[TapeSpan], moment: float, total: float) -> tuple[str, int, float]:
    if moment >= total:
        moment = max(0.0, total - 1e-6)
    if moment < 0:
        moment = 0.0
    acc = 0.0
    for span in spans:
        dur = span.duration
        if moment < acc + dur or span is spans[-1]:
            local = min(max(moment - acc, 0.0), max(dur - 1e-6, 0.0))
            frame = int(local * span.fps)
            if frame >= span.n_frames:
                frame = span.n_frames - 1
            if frame < 0:
                frame = 0
            return span.video_id, frame, span.fps
        acc += dur
    raise SampleError("empty timeline")


def reference_frames(
    spans: list[TapeSpan],
    target_video_id: str,
    target_frame: int,
    seed: str,
    n: int = REFERENCE_COUNT,
    window_s: float = REFERENCE_WINDOW_S,
) -> tuple[tuple[str, int], ...]:
    """Six frames spread across the testimony, off the judged frame's tape when possible."""
    usable = [span for span in spans if span.duration > 0]
    usable.sort(key=lambda span: (tape_index(span.source, span.video_id), span.video_id))
    others = [span for span in usable if span.video_id != target_video_id]
    same = [span for span in usable if span.video_id == target_video_id]
    use = others if others else same
    if not use:
        raise SampleError(f"no timeline for {target_video_id}")
    target = same[0] if same else use[0]
    total = sum(span.duration for span in use)
    if total <= 0:
        raise SampleError(f"timeline for {target_video_id} has no duration")
    rng = random.Random(seed)
    edges = [total * index / n for index in range(n + 1)]
    used: set[tuple[str, int]] = set()
    picks: list[tuple[str, int]] = []

    def eligible(video_id: str, frame: int, fps: float) -> bool:
        if video_id != target_video_id:
            return True
        return abs(frame / fps - target_frame / target.fps) >= window_s

    for index in range(n):
        lo, hi = edges[index], edges[index + 1]
        if hi <= lo:
            hi = lo + 1e-3
        found: tuple[str, int] | None = None
        for _attempt in range(40):
            video_id, frame, fps = _locate(use, rng.uniform(lo, hi), total)
            key = (video_id, frame)
            if key in used or not eligible(video_id, frame, fps):
                continue
            found = key
            break
        if found is None:
            steps = 24
            for step in range(steps):
                moment = lo + (hi - lo) * (step + 0.5) / steps
                video_id, frame, fps = _locate(use, moment, total)
                key = (video_id, frame)
                if key in used or not eligible(video_id, frame, fps):
                    continue
                found = key
                break
        if found is None:
            raise SampleError(f"could not place reference {index + 1} for {target_video_id} frame {target_frame}")
        used.add(found)
        picks.append(found)
    return tuple(picks)


def _order(items: list[Drawn], seed: str) -> list[Drawn]:
    rng = random.Random(seed)
    groups: dict[tuple[str, str], list[Drawn]] = {}
    keys: list[tuple[str, str]] = []
    for item in items:
        key = (item.hit.source, item.hit.testimony_id)
        if key not in groups:
            keys.append(key)
            groups[key] = []
        groups[key].append(item)
    rng.shuffle(keys)
    ordered: list[Drawn] = []
    for key in keys:
        group = groups[key]
        rng.shuffle(group)
        ordered.extend(group)
    return ordered


def assemble(
    question: Question,
    pools: dict[str, dict[str, list[FaceHit]]],
    tapes: dict[tuple[str, str], list[TapeSpan]],
    seed: int,
    sources: list[str],
) -> list[Drawn]:
    used: set[tuple[str, str, int, int]] = set()
    drawn: list[Drawn] = []
    for stratum, count in question.strata:
        by_source: dict[str, list[FaceHit]] = {}
        for source in sources:
            by_source[source] = [
                hit
                for hit in pools.get(stratum, {}).get(source, [])
                if (hit.source, hit.video_id, hit.frame, hit.face) not in used
            ]
        try:
            picked = draw_spread(by_source, count, f"{seed}:{question.name}:{stratum}", sources)
        except SampleError as exc:
            raise SampleError(f"{question.name} / {stratum}: {exc}") from exc
        for hit in picked:
            used.add((hit.source, hit.video_id, hit.frame, hit.face))
            references: tuple[tuple[str, int], ...] = ()
            if question.references:
                references = reference_frames(
                    tapes.get((hit.source, hit.testimony_id), []),
                    hit.video_id,
                    hit.frame,
                    seed=f"{seed}:{hit.source}:{hit.video_id}:{hit.frame}",
                )
            drawn.append(Drawn(hit, stratum, references))
    return _order(drawn, f"{seed}:{question.name}")


def still_id(source: str, video_id: str, frame: int) -> str:
    return f"still:{source}:{video_id}:{frame}"


def make_locator(item: Drawn) -> dict:
    locator = {
        "source": item.hit.source,
        "video_id": item.hit.video_id,
        "frame": item.hit.frame,
        "time_s": round(float(item.hit.time_s), 6),
        "still": still_id(item.hit.source, item.hit.video_id, item.hit.frame),
        "face": item.hit.face,
    }
    if item.references:
        locator["references"] = [
            still_id(item.hit.source, video_id, frame) for video_id, frame in item.references
        ]
    return locator


def _round_or_drop(value: float | None, places: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), places)


def make_features(
    item: Drawn,
    image_size: tuple[int, int],
    landmarks: list[list[float]] | None = None,
    eyes: list[list[float]] | None = None,
) -> dict:
    features: dict = {
        "bbox": [round(float(value), 2) for value in item.hit.bbox],
        "image_size": [int(image_size[0]), int(image_size[1])],
        "stratum": item.stratum,
        "face_score": round(float(item.hit.score), 6),
    }
    for key, value in (
        ("au12", item.hit.au12),
        ("au25", item.hit.au25),
        ("au43", item.hit.au43),
        ("gaze_yaw", item.hit.gaze_yaw),
        ("gaze_pitch", item.hit.gaze_pitch),
        ("head_pitch", item.hit.head_pitch),
        ("head_roll", item.hit.head_roll),
        ("head_yaw", item.hit.head_yaw),
    ):
        rounded = _round_or_drop(value)
        if rounded is not None:
            features[key] = rounded
    if landmarks is not None:
        features["landmarks"] = [[round(float(x), 2), round(float(y), 2)] for x, y in landmarks]
    if eyes is not None:
        features["eyes"] = [[round(float(x), 2), round(float(y), 2)] for x, y in eyes]
    return features


def eye_centers(points: list[list[float]]) -> list[list[float]]:
    """Mean of the 68-point right-eye and left-eye landmarks, in that order."""

    def center(start: int, stop: int) -> list[float]:
        group = points[start:stop]
        return [
            sum(point[0] for point in group) / len(group),
            sum(point[1] for point in group) / len(group),
        ]

    return [center(36, 42), center(42, 48)]
