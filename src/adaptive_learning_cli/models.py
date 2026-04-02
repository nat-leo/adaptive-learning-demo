from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Question:
    prompt: str
    options: list[str]
    answer_index: int

    @classmethod
    def from_dict(cls, raw: object) -> "Question":
        if not isinstance(raw, dict):
            raise ValueError("Each question must be a JSON object.")

        prompt = raw.get("prompt")
        options = raw.get("options")
        answer_index = raw.get("answer_index")

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Question 'prompt' must be a non-empty string.")

        if not isinstance(options, list) or len(options) < 2:
            raise ValueError("Question 'options' must be a list with at least two choices.")

        if not all(isinstance(option, str) and option.strip() for option in options):
            raise ValueError("Each option must be a non-empty string.")

        if not isinstance(answer_index, int):
            raise ValueError("Question 'answer_index' must be an integer.")

        if answer_index < 0 or answer_index >= len(options):
            raise ValueError("Question 'answer_index' must point to a valid option.")

        return cls(prompt=prompt.strip(), options=options, answer_index=answer_index)
