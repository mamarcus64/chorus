import pytest

from chorus.tasks.base import TaskError
from chorus.tasks.frame_choice.task import FrameChoice


def test_frame_choice_rejects_bad_answers():
    task = FrameChoice()
    config = task.validate_config(
        {
            "prompt": "Is a human head inside the box?",
            "choices": [
                {"value": "yes", "label": "Yes", "key": "1"},
                {"value": "no", "label": "No", "key": "2"},
            ],
            "overlays": ["bbox"],
            "instructions": "",
        }
    )
    assert task.validate_value(config, {"choice": "yes"}) == {"choice": "yes"}
    with pytest.raises(TaskError):
        task.validate_value(config, {"choice": "maybe"})
    with pytest.raises(TaskError):
        task.validate_value(config, {"head": True})
    with pytest.raises(TaskError):
        task.validate_item("video", {}, {})
    task.validate_item(
        "frame",
        {"source": "usc", "video_id": "10.1", "frame": 3, "time_s": 0.1, "still": "still:x"},
        {"bbox": [0, 0, 10, 10], "image_size": [320, 240]},
    )
    assert task.required_files(
        {"still": "still:x", "source": "usc", "video_id": "10.1", "frame": 3, "time_s": 0.1}
    ) == ["still:x"]
    refs = [f"still:ref:{index}" for index in range(6)]
    task.validate_item(
        "frame",
        {
            "source": "usc",
            "video_id": "10.1",
            "frame": 3,
            "time_s": 0.1,
            "still": "still:x",
            "face": 0,
            "references": refs,
        },
        {"bbox": [0, 0, 10, 10], "image_size": [320, 240], "landmarks": [[1, 2]] * 68},
    )
    assert task.required_files(
        {"still": "still:x", "references": refs, "source": "usc", "video_id": "10.1", "frame": 3, "time_s": 0.1}
    ) == ["still:x", *refs]
    with pytest.raises(TaskError):
        task.validate_item(
            "frame",
            {"source": "usc", "video_id": "10.1", "frame": 3, "time_s": 0.1, "still": "still:x", "references": refs[:5]},
            {},
        )
    with pytest.raises(TaskError):
        task.validate_config({**config, "overlays": ["arrow"]})
    task.validate_config({**config, "overlays": ["gaze", "pose"]})
    task.validate_item(
        "frame",
        {"source": "usc", "video_id": "10.1", "frame": 3, "time_s": 0.1, "still": "still:x"},
        {
            "bbox": [0, 0, 10, 10],
            "image_size": [320, 240],
            "eyes": [[1, 2], [3, 4]],
            "gaze_pitch": 0.1,
            "gaze_yaw": -0.2,
            "head_pitch": 0.0,
            "head_roll": 0.1,
            "head_yaw": -0.3,
        },
    )
