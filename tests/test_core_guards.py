"""Unit tests for src/core/guards.py"""
from __future__ import annotations
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _history(*messages):
    """Build a history list from (role, content) tuples."""
    return [{"role": role, "content": content} for role, content in messages]


# ── wasLastMessageYesNoQuestion ───────────────────────────────────────────────

class TestWasLastMessageYesNoQuestion:

    def test_true_for_is_question(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Is this a good investment?"))
        assert wasLastMessageYesNoQuestion(h) is True

    def test_true_for_should_question(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Should you invest in index funds?"))
        assert wasLastMessageYesNoQuestion(h) is True

    def test_true_for_do_question(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Do you want to learn more about ETFs?"))
        assert wasLastMessageYesNoQuestion(h) is True

    def test_true_for_would_you_like(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Would you like to explore more options?"))
        assert wasLastMessageYesNoQuestion(h) is True

    def test_true_for_does_that_phrase(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "ETFs are diversified funds. Does that make sense?"))
        assert wasLastMessageYesNoQuestion(h) is True

    def test_false_for_statement(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "The S&P 500 returned 20% this year."))
        assert wasLastMessageYesNoQuestion(h) is False

    def test_false_for_no_history(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        assert wasLastMessageYesNoQuestion([]) is False

    def test_false_for_no_question_mark(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Is this a good investment"))
        assert wasLastMessageYesNoQuestion(h) is False

    def test_skips_user_messages(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(
            ("assistant", "The market looks volatile."),
            ("user", "Is that right?"),   # user message — should be ignored
        )
        # last assistant message is a statement, not yes/no question
        assert wasLastMessageYesNoQuestion(h) is False

    def test_true_for_can_you_confirm(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Can you confirm your investment horizon?"))
        assert wasLastMessageYesNoQuestion(h) is True

    def test_are_question(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Are you interested in dividend stocks?"))
        assert wasLastMessageYesNoQuestion(h) is True

    def test_will_question(self):
        from src.core.guards import wasLastMessageYesNoQuestion
        h = _history(("assistant", "Will you be investing for the long term?"))
        assert wasLastMessageYesNoQuestion(h) is True


# ── isAmbiguousYesNo ──────────────────────────────────────────────────────────

class TestIsAmbiguousYesNo:

    def test_yes_after_statement_is_ambiguous(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "The S&P returned 20%."))
        assert isAmbiguousYesNo("yes", h) is True

    def test_no_after_statement_is_ambiguous(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "The S&P returned 20%."))
        assert isAmbiguousYesNo("no", h) is True

    def test_yes_after_yes_no_question_is_not_ambiguous(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "Should you invest in index funds?"))
        assert isAmbiguousYesNo("yes", h) is False

    def test_no_after_yes_no_question_is_not_ambiguous(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "Do you want more info?"))
        assert isAmbiguousYesNo("no", h) is False

    def test_non_yes_no_not_ambiguous(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "The market is down."))
        assert isAmbiguousYesNo("what is an ETF?", h) is False

    def test_case_insensitive_yes(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "Markets closed today."))
        assert isAmbiguousYesNo("YES", h) is True

    def test_case_insensitive_no(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "Markets closed today."))
        assert isAmbiguousYesNo("NO", h) is True

    def test_yes_with_extra_whitespace(self):
        from src.core.guards import isAmbiguousYesNo
        h = _history(("assistant", "Markets closed today."))
        assert isAmbiguousYesNo("  yes  ", h) is True

    def test_empty_history_bare_yes_is_ambiguous(self):
        from src.core.guards import isAmbiguousYesNo
        assert isAmbiguousYesNo("yes", []) is True


# ── check_ambiguous_yes_no_guard ──────────────────────────────────────────────

class TestCheckAmbiguousYesNoGuard:

    def test_returns_none_for_normal_question(self):
        from src.core.guards import check_ambiguous_yes_no_guard
        h = _history(("assistant", "The market is down today."))
        result = check_ambiguous_yes_no_guard("What is inflation?", h)
        assert result is None

    def test_returns_string_for_ambiguous_yes(self):
        from src.core.guards import check_ambiguous_yes_no_guard
        h = _history(("assistant", "Markets look volatile."))
        result = check_ambiguous_yes_no_guard("yes", h)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_none_for_yes_after_yn_question(self):
        from src.core.guards import check_ambiguous_yes_no_guard
        h = _history(("assistant", "Should you invest in bonds?"))
        result = check_ambiguous_yes_no_guard("yes", h)
        assert result is None

    def test_clarification_mentions_topic(self):
        from src.core.guards import check_ambiguous_yes_no_guard
        h = _history(
            ("user", "I want to learn about stocks"),
            ("assistant", "Here is what you need to know about stock investing."),
        )
        result = check_ambiguous_yes_no_guard("yes", h)
        assert result is not None
        assert "stock" in result.lower() or "finance" in result.lower()

    def test_returns_string_for_ambiguous_no(self):
        from src.core.guards import check_ambiguous_yes_no_guard
        h = _history(("assistant", "Portfolio diversification is important."))
        result = check_ambiguous_yes_no_guard("no", h)
        assert isinstance(result, str)
