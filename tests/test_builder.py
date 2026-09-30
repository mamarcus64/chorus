"""The same seed yields the same item ids, without reading the corpus."""

from chorus.db.ids import item_id, partition_id, task_id
from projects.voices.build_head_present import locator_for, sample_faces, split_counts
from projects.voices.sources import Video


class _Video(Video):
    pass


def _videos():
    def make(source, video_id):
        return Video(source, video_id, __import__("pathlib").Path("/tmp/v"), __import__("pathlib").Path("/tmp/v.parquet"), 320, 240, 30.0)

    return {
        "usc": [make("usc", "a"), make("usc", "b")],
        "yale": [make("yale", "c")],
    }


def _frames(video, min_score):
    del min_score
    return [
        {
            "frame": 10,
            "time_s": 0.3,
            "faces": [{"score": 0.95, "bbox": [1, 2, 3, 4]}, {"score": 0.99, "bbox": [5, 6, 7, 8]}],
        },
        {
            "frame": 20,
            "time_s": 0.6,
            "faces": [{"score": 0.91, "bbox": [9, 9, 9, 9]}],
        },
    ]


def test_split_counts_spreads_the_remainder():
    assert split_counts(5, ["usc", "yale"]) == [3, 2]


def test_same_seed_same_item_ids():
    kwargs = dict(
        videos_by_source=_videos(),
        load_frames=_frames,
        n=5,
        seed=7,
        sources=["usc", "yale"],
        min_score=0.9,
    )
    first = sample_faces(**kwargs)
    second = sample_faces(**kwargs)
    assert first == second
    tid = task_id("Head present (face_score > 0.9)")
    pid = partition_id(tid, "pilot")
    ids = [item_id(pid, locator_for(spec)) for spec in first]
    assert ids == [item_id(pid, locator_for(spec)) for spec in second]
    assert len(set(ids)) == len(ids)
