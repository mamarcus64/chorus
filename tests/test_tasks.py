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
