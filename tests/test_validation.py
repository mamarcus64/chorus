"""Sampling rules for the validation pilot, without reading the corpus."""

import pytest

from projects.voices.validation import (
    FaceHit,
    SampleError,
    TapeSpan,
    absorb,
    assemble,
    collection_need,
    eye_centers,
    hits_from_frames,
    make_locator,
    need_by_source,
    questions,
    reference_frames,
    strata_for_faces,
    interview_id,
)


def _face(**overrides):
    face = {
        "score": 0.99,
        "bbox": (40, 30, 120, 140),
        "au12": 0.2,
        "au25": 0.5,
        "au43": 0.2,
        "gaze_yaw": 0.0,
        "gaze_pitch": 0.0,
        "head_yaw": 0.0,
    }
    face.update(overrides)
    return face


def _names(faces, width=320, height=240):
    return {name for name, _face in strata_for_faces(faces, width, height)}


def test_interview_ids_cover_both_archives():
    assert interview_id("usc", "15645.2") == "15645"
    assert interview_id("yale", "mssa_hvt_1728_p4of4.u") == "1728"
    assert interview_id("yale", "mssa_hvt_2865d_p1of2.u") == "2865d"
    assert interview_id("yale", "mssa_hvt_4466_P1of1.u") == "4466"
    assert interview_id("yale", "mssa_hvt_274rm_p2of2.u") == "274rm"


def test_strata_separate_the_survivor_cases_and_the_behavior_tails():
    usual = _names([_face()])
    assert "usual" in usual
    assert "landmarks" in usual
    assert "gaze_center" in usual
    assert "head_center" in usual

    assert "low" in _names([_face(score=0.7)])
    assert "usual" not in _names([_face(score=0.7)])

    small = _names([_face(bbox=(10, 10, 20, 24))])
    assert "small" in small
    assert "usual" not in small

    several = strata_for_faces([_face(score=0.99, bbox=(10, 10, 80, 80)), _face(score=0.8, bbox=(180, 20, 40, 40))], 320, 240)
    several_names = {name for name, _face in several}
    assert "several" in several_names
    assert "usual" not in several_names
    assert sum(1 for name, _face in several if name == "several") == 2

    smile = _names([_face(au12=0.91)])
    assert "smile_high" in smile
    assert "smile_low" not in smile
    assert "smile_low" in _names([_face(au12=0.05)])
    assert "mouth_high" in _names([_face(au25=0.97)])
    assert "mouth_low" in _names([_face(au25=0.1)])
    assert "eyes_high" in _names([_face(au43=0.8)])
    assert "gaze_yaw_neg" in _names([_face(gaze_yaw=-0.5, gaze_pitch=0.0)])
    assert "gaze_down" in _names([_face(gaze_yaw=0.0, gaze_pitch=0.4)])
    assert "gaze_down" not in _names([_face(gaze_yaw=-0.5, gaze_pitch=0.4)])
    assert "head_yaw_pos" in _names([_face(head_yaw=0.3)])


def test_fifth_face_is_left_out_of_the_several_stratum():
    faces = [_face(score=1 - index * 0.01, bbox=(index * 10, 10, 30, 40)) for index in range(5)]
    several = [face for name, face in strata_for_faces(faces, 320, 240) if name == "several"]
    assert len(several) == 4
    assert all(face["face"] < 4 for face in several)


def test_pilot_questions_use_the_answer_words():
    by_name = {question.name: question for question in questions("pilot")}
    assert [label for _value, label, _key in by_name["Survivor, present day"].choices] == [
        "Survivor in Present Day",
        "Picture/Other Person",
        "Not a Person",
        "Unsure",
    ]
    assert [label for _value, label, _key in by_name["Eyes closed"].choices] == ["Open", "Closed", "Unsure"]
    assert [label for _value, label, _key in by_name["Mouth open"].choices] == ["Open", "Closed", "Unsure"]
    assert [label for _value, label, _key in by_name["Smile"].choices] == ["Smiling", "Not Smiling", "Unsure"]
    assert by_name["Gaze direction"].overlays == ("gaze",)
    assert by_name["Head direction"].overlays == ("pose",)
    assert [label for _value, label, _key in by_name["Gaze direction"].choices] == [
        "Aligned",
        "Not aligned",
        "Unsure",
    ]


def test_eye_centers_average_each_eye():
    points = [[float(index), float(index)] for index in range(68)]
    right, left = eye_centers(points)
    assert right == [38.5, 38.5]
    assert left == [44.5, 44.5]


def test_pilot_and_confirmation_counts():
    for question in questions("pilot"):
        assert sum(count for _name, count in question.strata) == 20
    totals = {question.name: sum(count for _name, count in question.strata) for question in questions("full")}
    assert totals == {
        "Survivor, present day": 800,
        "Landmarks on the face": 200,
        "Smile": 120,
        "Mouth open": 80,
        "Eyes closed": 80,
        "Gaze direction": 150,
        "Head direction": 100,
    }


def test_collection_need_pads_overlapping_survivor_strata():
    draw = need_by_source("pilot", ["usc", "yale"])
    collect = collection_need(draw)
    assert collect["several"]["usc"] > draw["several"]["usc"]
    assert collect["usual"]["usc"] == draw["usual"]["usc"]
    assert collect["smile_high"]["yale"] == draw["smile_high"]["yale"]


def _hit(video_id, frame, face=0, source="usc"):
    return FaceHit(
        source=source,
        video_id=video_id,
        testimony_id=video_id.split(".")[0],
        frame=frame,
        time_s=frame / 30,
        face=face,
        score=0.99,
        bbox=(40, 30, 120, 140),
        au12=0.9,
        au25=0.99,
        au43=0.05,
        gaze_yaw=0.0,
        gaze_pitch=0.0,
        head_yaw=0.0,
    )


def test_absorb_spreads_a_stratum_across_tapes():
    pools = {"usual": {"usc": []}}
    need = {"usual": {"usc": 3}}
    for index, video_id in enumerate(("a.1", "b.1", "c.1")):
        found = {"usual": [_hit(video_id, frame) for frame in range(10)]}
        absorb(pools, found, "usc", need)
        assert len(pools["usual"]["usc"]) == min(3, (index + 1) * 2)
    assert len({hit.video_id for hit in pools["usual"]["usc"]}) == 2


def test_reference_frames_prefer_other_tapes_and_avoid_the_judged_moment():
    spans = [
        TapeSpan("usc", "10.1", 1800, 30.0),
        TapeSpan("usc", "10.2", 1800, 30.0),
    ]
    first = reference_frames(spans, "10.1", 100, seed="ref")
    assert first == reference_frames(spans, "10.1", 100, seed="ref")
    assert len(first) == 6
    assert all(video_id == "10.2" for video_id, _frame in first)
    alone = reference_frames([spans[0]], "10.1", 900, seed="alone")
    assert len(alone) == 6
    assert all(video_id == "10.1" for video_id, _frame in alone)
    assert all(abs(frame / 30 - 900 / 30) >= 2 for _video_id, frame in alone)


def test_assemble_builds_a_survivor_pilot_with_six_references():
    question = next(item for item in questions("pilot") if item.references)
    pools = {name: {"usc": [], "yale": []} for name, _count in question.strata}
    tapes = {}
    for source, prefix in (("usc", "10"), ("yale", "20")):
        for tape in range(8):
            video_id = f"{prefix}.{tape}"
            tapes.setdefault((source, prefix), []).append(TapeSpan(source, video_id, 3000, 30.0))
            for offset, name in enumerate(pools):
                pools[name][source].append(_hit(video_id, 200 + offset * 400 + tape, source=source))
    drawn = assemble(question, pools, tapes, seed=1, sources=["usc", "yale"])
    assert len(drawn) == 20
    counts = {}
    for item in drawn:
        counts[item.stratum] = counts.get(item.stratum, 0) + 1
        locator = make_locator(item)
        assert len(locator["references"]) == 6
        assert locator["still"] not in locator["references"]
        assert item.hit.video_id not in {ref.split(":")[2] for ref in locator["references"]}
    assert counts == {"several": 6, "small": 4, "low": 4, "usual": 6}
    with pytest.raises(SampleError):
        assemble(question, {"several": {"usc": [], "yale": []}}, {}, seed=1, sources=["usc", "yale"])


def test_hits_from_frames_keeps_a_spaced_subset():
    frames = [(index, index / 30, [_face()]) for index in range(30)]
    kept = hits_from_frames("usc", "10.1", "10", frames, 320, 240, keep=4)
    assert len(kept["usual"]) == 4
    assert kept["usual"][0].frame < kept["usual"][-1].frame
