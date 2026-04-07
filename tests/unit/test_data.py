from __future__ import annotations

import json
from pathlib import Path

import pytest

from adaptive_learning import data


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_question(question_id: str) -> dict[str, object]:
    return {
        "id": question_id,
        "prompt": f"Prompt for {question_id}",
        "answers": ["A", "B"],
        "correct_answer": "A",
        "rating": 10,
    }


def test_load_questions_returns_defaults_for_none_or_blank_file(tmp_path: Path) -> None:
    blank = tmp_path / "blank.json"
    blank.write_text("   ", encoding="utf-8")

    none_loaded = data.load_questions(None)
    blank_loaded = data.load_questions(blank)

    assert len(none_loaded) == 1
    assert none_loaded[0].id == "default-1"
    assert [q.id for q in blank_loaded] == ["default-1"]


def test_load_questions_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(FileNotFoundError, match="Question file not found"):
        data.load_questions(missing)


@pytest.mark.parametrize(
    "payload,error",
    [
        ({"id": "not-a-list"}, "JSON array"),
        ([], "at least one question"),
    ],
)
def test_load_questions_rejects_invalid_top_level_payload(tmp_path: Path, payload: object, error: str) -> None:
    path = tmp_path / "questions.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match=error):
        data.load_questions(path)


def test_load_questions_rejects_duplicate_ids_within_one_file(tmp_path: Path) -> None:
    path = tmp_path / "dup.json"
    _write_json(path, [_valid_question("dup"), _valid_question("dup")])

    with pytest.raises(ValueError, match="duplicate id 'dup'"):
        data.load_questions(path)


def test_load_from_many_combines_multiple_files_and_rejects_cross_file_duplicates(tmp_path: Path) -> None:
    one = tmp_path / "one.json"
    two = tmp_path / "two.json"
    three = tmp_path / "three.json"

    _write_json(one, [_valid_question("a")])
    _write_json(two, [_valid_question("b")])
    _write_json(three, [_valid_question("a")])

    combined = data.load_from_many([one, two])
    assert [q.id for q in combined] == ["a", "b"]

    with pytest.raises(ValueError, match="Duplicate question id 'a'"):
        data.load_from_many([one, three])


def test_load_from_many_none_returns_defaults() -> None:
    loaded = data.load_from_many(None)
    assert [q.id for q in loaded] == ["default-1"]
