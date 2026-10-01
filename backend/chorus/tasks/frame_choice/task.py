"""A multiple-choice question about one frame, with optional overlays."""

from __future__ import annotations

from chorus.tasks.base import TaskError

_FRAME_KEYS = ("source", "video_id", "frame", "time_s", "still")
_VIDEO_KEYS = ("source", "video_id", "file", "start_s", "end_s")
_SPEECH_KEYS = ("source", "video_id", "start_s", "end_s")


_OVERLAYS = {"bbox", "landmarks"}
_REFERENCE_COUNT = 6


class FrameChoice:
    code_key = "frame_choice"
    code_version = 2
    item_kinds = {"frame"}

    def validate_config(self, config: dict) -> dict:
        prompt = config.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise TaskError("prompt is required")
        choices = config.get("choices")
        if not isinstance(choices, list) or not choices:
            raise TaskError("choices must be a non-empty list")
        seen: set[str] = set()
        clean_choices = []
        for choice in choices:
            if not isinstance(choice, dict):
                raise TaskError("each choice must be an object")
            value = choice.get("value")
            label = choice.get("label")
            key = choice.get("key")
            if not all(isinstance(part, str) and part for part in (value, label, key)):
                raise TaskError("each choice needs value, label, and key")
            if value in seen:
                raise TaskError(f"duplicate choice {value}")
            seen.add(value)
            clean_choices.append({"value": value, "label": label, "key": key})
        overlays = config.get("overlays", [])
        if not isinstance(overlays, list) or not all(isinstance(name, str) for name in overlays):
            raise TaskError("overlays must be a list of names")
        unknown = [name for name in overlays if name not in _OVERLAYS]
        if unknown:
            raise TaskError("unknown overlay " + ", ".join(unknown))
        instructions = config.get("instructions", "")
        if not isinstance(instructions, str):
            raise TaskError("instructions must be a string")
        return {
            "prompt": prompt.strip(),
            "choices": clean_choices,
            "overlays": list(overlays),
            "instructions": instructions,
        }

    def validate_item(self, kind: str, locator: dict, features: dict) -> None:
        if kind not in self.item_kinds:
            raise TaskError(f"{self.code_key} does not use item kind {kind}")
        missing = [key for key in _FRAME_KEYS if key not in locator]
        if missing:
            raise TaskError("frame locator missing " + ", ".join(missing))
        if not isinstance(locator["frame"], int):
            raise TaskError("frame must be an integer")
        if not isinstance(locator["still"], str) or not locator["still"]:
            raise TaskError("still file id is required")
        face = locator.get("face")
        if face is not None and not isinstance(face, int):
            raise TaskError("face must be an integer")
        references = locator.get("references")
        if references is not None:
            if (
                not isinstance(references, list)
                or len(references) != _REFERENCE_COUNT
                or not all(isinstance(item, str) and item for item in references)
                or len(set(references)) != _REFERENCE_COUNT
            ):
                raise TaskError("references must be six distinct file ids")
            if locator["still"] in references:
                raise TaskError("references must not include the judged still")
        bbox = features.get("bbox")
        if bbox is not None:
            if (
                not isinstance(bbox, list)
                or len(bbox) != 4
                or not all(isinstance(n, (int, float)) for n in bbox)
            ):
                raise TaskError("bbox must be [x, y, width, height]")
        image_size = features.get("image_size")
        if image_size is not None:
            if (
                not isinstance(image_size, list)
                or len(image_size) != 2
                or not all(isinstance(n, int) and n > 0 for n in image_size)
            ):
                raise TaskError("image_size must be [width, height]")
        landmarks = features.get("landmarks")
        if landmarks is not None:
            if not isinstance(landmarks, list) or len(landmarks) != 68:
                raise TaskError("landmarks must be 68 points")
            for point in landmarks:
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or not all(isinstance(number, (int, float)) for number in point)
                ):
                    raise TaskError("each landmark must be [x, y]")

    def validate_value(self, config: dict, value: dict) -> dict:
        clean = self.validate_config(config)
        choice = value.get("choice") if isinstance(value, dict) else None
        allowed = {item["value"] for item in clean["choices"]}
        if choice not in allowed:
            raise TaskError("choice must be one of " + ", ".join(sorted(allowed)))
        return {"choice": choice}

    def required_files(self, locator: dict) -> list[str]:
        files: list[str] = []
        still = locator.get("still")
        if isinstance(still, str) and still:
            files.append(still)
        references = locator.get("references")
        if isinstance(references, list):
            for item in references:
                if isinstance(item, str) and item and item not in files:
                    files.append(item)
        return files


def locator_keys(kind: str) -> tuple[str, ...]:
    """Required locator fields for the three item kinds. Used by later task types."""
    if kind == "frame":
        return _FRAME_KEYS
    if kind == "video":
        return _VIDEO_KEYS
    if kind == "speech":
        return _SPEECH_KEYS
    raise TaskError(f"unknown item kind {kind}")
