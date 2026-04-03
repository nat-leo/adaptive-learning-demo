from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

"""
Question Model

prompt: This is the question that the CLI is gonna ask. It's found in the /problems folder.
answers: This is a list of all the WRONG answers.
correct_answer: ^ Answers doesn't contain the correct one. The correct answer is in it's own field.
rating: [1, 100] A numeric rating between 1 and 100, 1 being the easiest and 100 being the hardest.

"""
@dataclass(slots=True)
class Question:
    prompt: str
    answers: list[str]
    correct_answer: str
    rating: int

    @classmethod
    def from_dict(cls, raw: object) -> "Question":
        if not isinstance(raw, dict):
            raise ValueError("Each question must be a JSON object.")

        prompt = raw.get("prompt", raw.get("problem"))
        answers = raw.get("answers", raw.get("answers"))
        correct_answer = raw.get("correct_answer")
        rating = raw.get("rating")

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Question 'prompt' must be a non-empty string.")

        if not isinstance(answers, list) or len(answers) < 2:
            raise ValueError("Question 'answers' must be a list with at least two choices.")

        if not all(isinstance(option, str) and option.strip() for option in answers):
            raise ValueError("Each option must be a non-empty string.")

        if correct_answer is None:
            if not isinstance(correct_answer, str) or not correct_answer.strip():
                raise ValueError(
                    "Question must include either 'correct_answer' or a non-empty 'correct_answer'."
                )
            
            if correct_answer in answers:
                raise ValueError(
                    "Question 'correct_answer' cannot also be in (the wrong) answers."
                )
        elif not isinstance(correct_answer, str):
            raise ValueError("Question 'correct_answer' must be a string.")
        
        if rating < 0 or rating > 100:
            raise ValueError("Question 'rating' must be a value between 1 and 100 inclusive.")

        return cls(prompt=prompt.strip(), answers=answers, correct_answer=correct_answer, rating=rating)


@dataclass(slots=True)
class QuizState:
    question: Question
    selected_index: int = 0

    def move_up(self) -> None:
        self.selected_index = (self.selected_index - 1) % len(self.question.answers)

    def move_down(self) -> None:
        self.selected_index = (self.selected_index + 1) % len(self.question.answers)

    def is_correct(self) -> bool:
        selected_answer = self.question.answers[self.selected_index]
        return selected_answer == self.question.correct_answer

Command = Literal["up", "down", "submit", "quit", "noop"]
