from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class SessionData:
    """Per-session counters for one quiz run.

    session_id: Stable ID for the session.
    started_at: Session start timestamp.
    questions_seen: Number of questions attempted in this session.
    questions_correct: Number of correct answers in this session.
    """

    session_id: str
    started_at: datetime
    questions_seen: int = 0
    questions_correct: int = 0


@dataclass
class IncorrectQuestion:
    """Tracking state for a question that has been answered incorrectly.

    question_id: Unique ID of the question.
    category: Topic label used for reporting/selection.
    last_seen: Timestamp for the last presentation or answer event.
    due_in: Number of attempts before this question is eligible again.
    times_wrong: Total incorrect answers for this question.
    times_seen_since_wrong: Number of re-shows since first entering retry flow.
    reintroduciton_streak: Consecutive reintroduction count used by backoff.
    """

    question_id: str
    category: str
    last_seen: datetime | None = None
    due_in: int = 0 
    times_wrong: int = 0
    times_seen_since_wrong: int = 0
    reintroduciton_streak: int = 0

    def mark_wrong(self) -> None:
        """Call when user answers this question incorrectly."""
        self.times_wrong += 1
        self.last_seen = datetime.now()

    def mark_reintroduced(self) -> None:
        """Call when a previously-missed question is shown again."""
        self.reintroduciton_streak += 1
        self.times_seen_since_wrong += 1
        self.last_seen = datetime.now()

    def schedule_next(self, backoff_fn: Callable[[int, int], datetime]) -> None:
        """
        Delegate spacing computation to the caller.
        backoff_fn receives (reintroduciton_streak) and returns due_in.
        """
        self.due_in = backoff_fn(self.reintroduciton_streak)


    @classmethod
    def from_dict(cls, data: dict) -> IncorrectQuestion:
        return cls(
            question_id=data["question_id"],
            category=data["category"],
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            due_in=data["due_in"] if data.get("due_in") else None,
            times_wrong=data.get("times_wrong", 0),
            times_seen_since_wrong=data.get("times_seen_since_wrong", 0),
            reintroduciton_streak=data.get("reintroduciton_streak", 0),
        )


@dataclass
class User:
    """Aggregate user-level learning state.

    score: Total number of correct answers across sessions.
    attempts: Total number of attempted questions across sessions.
    sessions: Session history keyed by session_id.
    incorrect_questions: Retry-pool questions keyed by question_id.
    """

    score: int = 0
    attempts: int = 0
    sessions: dict[str, SessionData] = field(default_factory=dict)
    incorrect_questions: dict[str, IncorrectQuestion] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            score=data.get("score", 0),
            attempts=data.get("attempts", 0),
            sessions={
                sid: SessionData(
                    session_id=sdata["session_id"],
                    started_at=datetime.fromisoformat(sdata["started_at"]),
                    questions_seen=sdata.get("questions_seen", 0),
                    questions_correct=sdata.get("questions_correct", 0),
                )
                for sid, sdata in data.get("sessions", {}).items()
            },
            incorrect_questions={
                qid: IncorrectQuestion.from_dict(qdata)
                for qid, qdata in data.get("incorrect_questions", {}).items()
            },
        )


@dataclass(slots=True)
class Question:
    """
    Question Model

    id: A unique question identifier.
    prompt: This is the question that the CLI is gonna ask. It's found in the /problems folder.
    answers: This is a list of all the WRONG answers.
    correct_answer: ^ Answers doesn't contain the correct one. The correct answer is in it's own field.
    rating: [1, 100] A numeric rating between 1 and 100, 1 being the easiest and 100 being the hardest.

    """
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


@dataclass(slots=True)
class QuizState:
    """
    Quiz State Model

    This keeps track of which question has been selected in the quiz view. It's 
    reponsible for keeping track the up an down arrows from the controller so that 
    the view updates.

    """
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
