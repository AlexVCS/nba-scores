import pytest

from server.services.ask_scope import unsupported_scope_message


@pytest.mark.parametrize(
    ("question", "message_fragment"),
    [
        ("How many wins did the Thunder have in the 2023-24 regular season?", "win totals"),
        ("How many losses did the Celtics have in the 2023–24 regular-season?", "win totals"),
        ("What was the Lakers' win-loss record in the 2022‑23 regular season?", "win totals"),
        ("Which was the Thunder's biggest win of the 2023-24 regular season?", "biggest win"),
        ("how many points Shai score in the Thunder’s largest win of the 2023–24 regular season?", "biggest win"),
        ("what team won the most games in the 1949-50 regular season?", "standings"),
    ],
)
def test_regular_season_record_and_season_wide_result_queries_are_guarded(question, message_fragment):
    message = unsupported_scope_message(question)

    assert message is not None
    assert message_fragment in message


@pytest.mark.parametrize(
    "question",
    [
        "How many points did Shai score on 2024-03-10?",
        "Show the Thunder games during the 2023-24 regular season.",
        "What was the Thunder's record in the 2023-24 playoffs?",
        "How many wins did the Thunder have in the 2023-24 season?",
        "Who scored the most points in the Thunder's largest win on 2024-02-01?",
        "What is Shai's regular-season scoring average?",
    ],
)
def test_other_questions_remain_supported_or_parser_bound(question):
    assert unsupported_scope_message(question) is None
