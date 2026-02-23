"""
Conversational guards / interceptors for the AI Finance Assistant.

This module provides middleware-style helpers that run *before* agent routing
to catch ambiguous or malformed inputs that would confuse downstream agents.

Public helpers
--------------
- ``wasLastMessageYesNoQuestion(history)``   → bool
- ``isAmbiguousYesNo(message, history)``     → bool
- ``check_ambiguous_yes_no_guard(message, history)`` → str | None

If ``check_ambiguous_yes_no_guard`` returns a non-``None`` string the caller
should short-circuit and return that string directly, skipping normal routing.

Design notes
------------
- Pure functions, no I/O, safe for async environments.
- All helpers accept the standard ``history`` list:
  ``[{"role": "user"|"assistant"|"summary", "content": str}, ...]``
- Modular: import individual helpers anywhere in the pipeline.
"""

from __future__ import annotations

import re
from typing import List, Dict, Optional

# ── Constants ──────────────────────────────────────────────────────────────────

# Words that signal a sentence starting a yes/no question in English.
# These are checked case-insensitively against the *first word* of the last
# assistant message (after optional leading whitespace).
_YES_NO_QUESTION_STARTERS: frozenset[str] = frozenset({
    "is", "are", "was", "were",
    "do", "does", "did",
    "should", "would", "could", "can",
    "will", "won't", "wouldn't", "shouldn't", "couldn't",
    "have", "has", "had",
    "may", "might", "must",
    "shall",
})

# Phrases anywhere in the last assistant message that strongly imply a
# yes/no answer is expected even if the sentence opener is not a canonical
# question starter (e.g. "Let me know if this makes sense?").
_YES_NO_EXPECTED_PHRASES: tuple[str, ...] = (
    "yes or no",
    "true or false",
    "let me know if",
    "does that",
    "does this",
    "is that",
    "is this",
    "do you want",
    "do you need",
    "would you like",
    "should i",
    "shall i",
    "are you",
    "can you confirm",
)

# Finance-domain topic keywords for the "last detected topic" extraction.
# Ordered loosely by specificity so the first match wins.
_TOPIC_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("stock",           "stocks"),
    ("portfolio",       "your portfolio"),
    ("market",          "the market"),
    ("crypto",          "cryptocurrency"),
    ("bitcoin",         "Bitcoin"),
    ("etf",             "ETFs"),
    ("bond",            "bonds"),
    ("dividend",        "dividends"),
    ("interest rate",   "interest rates"),
    ("inflation",       "inflation"),
    ("tax",             "taxes"),
    ("401k",            "your 401(k)"),
    ("ira",             "your IRA"),
    ("roth",            "Roth accounts"),
    ("invest",          "investing"),
    ("saving",          "saving"),
    ("budget",          "budgeting"),
    ("retire",          "retirement"),
    ("goal",            "your financial goals"),
    ("news",            "recent financial news"),
    ("trade",           "trading"),
    ("option",          "options trading"),
    ("fund",            "funds"),
    ("index",           "index funds"),
    ("real estate",     "real estate"),
    ("insurance",       "insurance"),
    ("debt",            "debt management"),
    ("credit",          "credit"),
)

# Default topic label used when no specific topic is detected.
_DEFAULT_TOPIC = "finance"


# ── Internal helpers ───────────────────────────────────────────────────────────

def _last_assistant_message(history: List[Dict[str, str]]) -> Optional[str]:
    """Return the content of the most recent assistant message, or None."""
    for entry in reversed(history):
        if entry.get("role") == "assistant":
            return entry.get("content", "").strip()
    return None


def _last_user_message(history: List[Dict[str, str]]) -> Optional[str]:
    """Return the content of the most recent user message (≥2 turns ago), or None."""
    user_msgs = [
        e.get("content", "").strip()
        for e in history
        if e.get("role") == "user"
    ]
    # We want the user message *before* the current one (context), i.e. last in list
    return user_msgs[-1] if user_msgs else None


def _extract_last_topic(history: List[Dict[str, str]]) -> str:
    """
    Scan recent history (assistant + user messages) for finance topic keywords
    and return a human-readable label for the last detected subject.

    Falls back to ``_DEFAULT_TOPIC`` when nothing matches.
    """
    # Build a combined text block from the most recent messages to search
    recent_content = " ".join(
        e.get("content", "")
        for e in history[-10:]
        if e.get("role") in ("user", "assistant")
    ).lower()

    for keyword, label in _TOPIC_KEYWORDS:
        if keyword in recent_content:
            return label

    return _DEFAULT_TOPIC


# ── Public API ─────────────────────────────────────────────────────────────────

def wasLastMessageYesNoQuestion(history: List[Dict[str, str]]) -> bool:  # noqa: N802
    """
    Return ``True`` when the most recent assistant message in *history* is
    clearly a yes/no question.

    Detection criteria (either is sufficient):
    1. The message ends with "?" AND the first word is a recognised
       yes/no question starter (e.g. "Is", "Do", "Should", …).
    2. The message ends with "?" AND contains a recognised expected-yes/no
       phrase (e.g. "does that make sense?").

    Parameters
    ----------
    history:
        Chronological list of ``{"role": str, "content": str}`` dicts.

    Returns
    -------
    bool
        ``True`` only when the last assistant turn is a yes/no question.
    """
    last_msg = _last_assistant_message(history)
    if not last_msg:
        return False

    # Must end with a question mark (possibly followed by whitespace)
    if not last_msg.rstrip().endswith("?"):
        return False

    lower = last_msg.lower()

    # Criterion 1: yes/no starter word
    first_word = re.split(r"\W+", lower.lstrip(), maxsplit=1)[0]
    if first_word in _YES_NO_QUESTION_STARTERS:
        return True

    # Criterion 2: embedded expected-yes/no phrase
    for phrase in _YES_NO_EXPECTED_PHRASES:
        if phrase in lower:
            return True

    return False


def isAmbiguousYesNo(  # noqa: N802
    message: str,
    history: List[Dict[str, str]],
) -> bool:
    """
    Return ``True`` when *message* is an ambiguous bare "yes" or "no" that the
    system cannot safely interpret.

    A yes/no is considered *ambiguous* when:
    - The current message is exactly "yes" or "no" (case-insensitive, stripped).
    - AND the previous assistant message was NOT a yes/no question.

    Parameters
    ----------
    message:
        The raw user input for the current turn.
    history:
        Conversation history (does *not* yet include the current user message).

    Returns
    -------
    bool
    """
    normalised = message.strip().lower()
    if normalised not in ("yes", "no"):
        return False

    return not wasLastMessageYesNoQuestion(history)


def _build_clarification_response(history: List[Dict[str, str]]) -> str:
    """
    Build the clarification prompt returned to the user when an ambiguous
    yes/no is detected.
    """
    topic = _extract_last_topic(history)
    return (
        f"Are you asking a yes/no question about {topic}?\n"
        "If so, please type the full question.\n\n"
        "Then I'll answer with just yes or no."
    )


def check_ambiguous_yes_no_guard(
    message: str,
    history: List[Dict[str, str]],
) -> Optional[str]:
    """
    Middleware / interceptor entry point for the ambiguous yes/no guard.

    Call this *before* agent routing.  If a non-``None`` value is returned,
    short-circuit the normal routing pipeline and use the returned string as
    the assistant response.

    Parameters
    ----------
    message:
        The raw user input for the current turn (not yet in *history*).
    history:
        Conversation history for the session — loaded from ConversationStore.

    Returns
    -------
    str | None
        Clarification message when the guard fires; ``None`` otherwise.

    Examples
    --------
    >>> guard_response = check_ambiguous_yes_no_guard(user_input, history)
    >>> if guard_response is not None:
    ...     return {"answer": guard_response, "agent": "guard", "session_id": sid}
    >>> # … normal routing …
    """
    if isAmbiguousYesNo(message, history):
        return _build_clarification_response(history)
    return None
