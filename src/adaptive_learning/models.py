from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

"""
User Model

Assume one user exists. Information collected on the user is used to create an adaptive
learning environment by keeping track of wrong answers and making sure the user sees them
more often.

sessions: A session is everytime a user starts the adaptive learning CLI, and then 
          quits. That information is recorded in the session.

          {
           session: an integer that goes up. 
           date: the datetime of the session start.
           attempts: number of questions attempted.
           score: number of questions correct.
           incorrect: a list of ids of the questions that were incorrect.
          }

score: total number of questions correct by the user
attempts: total number of questions attempted by the user
incorrect_questions: incorrect questions need to be recorded, including its category
                     and schedule to see it.

"""
@dataclass()
class User:
    score: int
    attempts: int
    incorrect_questions: dict
    
    @classmethod
    def from_dict():
        pass

"""
Question Model

id: A unique question identifier.
prompt: This is the question that the CLI is gonna ask. It's found in the /problems folder.
answers: This is a list of all the WRONG answers.
correct_answer: ^ Answers doesn't contain the correct one. The correct answer is in it's own field.
rating: [1, 100] A numeric rating between 1 and 100, 1 being the easiest and 100 being the hardest.

"""
@dataclass(slots=True)
class Question:
    id: str
    prompt: str
    answers: list[str]
    correct_answer: str
    rating: int

    @classmethod
    def from_dict(cls, raw: object) -> "Question":
        if not isinstance(raw, dict):
            raise ValueError("Each question must be a JSON object.")

        question_id = raw.get("id")
        prompt = raw.get("prompt", raw.get("problem"))
        answers = raw.get("answers")
        correct_answer = raw.get("correct_answer")
        rating = raw.get("rating")

        if not isinstance(question_id, str) or not question_id.strip():
            raise ValueError("Question 'id' must be a non-empty string.")

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Question 'prompt' must be a non-empty string.")

        if not isinstance(answers, list) or len(answers) < 2:
            raise ValueError("Question 'answers' must be a list with at least two choices.")

        if not all(isinstance(option, str) and option.strip() for option in answers):
            raise ValueError("Each option must be a non-empty string.")

        if not isinstance(correct_answer, str) or not correct_answer.strip():
            raise ValueError("Question 'correct_answer' must be a non-empty string.")

        if not isinstance(rating, int) or rating < 1 or rating > 100:
            raise ValueError("Question 'rating' must be a value between 1 and 100 inclusive.")

        return cls(
            id=question_id.strip(),
            prompt=prompt.strip(),
            answers=answers,
            correct_answer=correct_answer,
            rating=rating,
        )

"""
Quiz State Model

This keeps track of which question has been selected in the quiz view. It's 
reponsible for keeping track the up an down arrows from the controller so that 
the view updates.

"""
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
