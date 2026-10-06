"""Length-preserving text folding and tokenization shared by every matcher."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_CHAR_MAP = {
    "‘": "'", "’": "'", "ʼ": "'", "`": "'",
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
}
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)*'?")
NAME_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv"})


def fold(text: str) -> str:
    """Casefold and strip accents while keeping every character at its index."""
    out: list[str] = []
    for char in text:
        char = _CHAR_MAP.get(char, char)
        base = "".join(c for c in unicodedata.normalize("NFKD", char) if not unicodedata.combining(c))
        folded = base.casefold() if base else " "
        out.append(folded[:1] or " ")
    return "".join(out)


@dataclass(frozen=True)
class Token:
    norm: str
    start: int
    end: int
    capitalized: bool


def _clean_token(raw: str) -> str:
    if raw.endswith("'s") and len(raw) > 2:
        raw = raw[:-2]
    return raw.replace("'", "")


def tokenize(folded: str, original: str | None = None) -> list[Token]:
    """Tokens of a folded string; ``original`` supplies capitalization."""
    tokens = []
    for match in _TOKEN_RE.finditer(folded):
        norm = _clean_token(match.group())
        if not norm:
            continue
        first = original[match.start()] if original is not None else ""
        tokens.append(Token(norm, match.start(), match.end(), first.isupper() or first.isdigit()))
    return tokens


def name_key(text: str) -> str:
    """Normalized lookup key for a name or phrase (``"Shaquille O'Neal"`` -> ``"shaquille oneal"``)."""
    return " ".join(t.norm for t in tokenize(fold(text)))


def strip_suffix(key: str) -> str:
    parts = key.split()
    while len(parts) > 1 and parts[-1] in NAME_SUFFIXES:
        parts.pop()
    return " ".join(parts)


def mask(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]


# Words that are never a single-token player or team mention on their own.
STOPWORDS = frozenset("""
a about after against ago all also am an and any are around as at averaged away be been before beat beaten best
between block blocks board boards box boxscore but by can champion champions championship champs christmas could
day days did do does double during each east eastern either every field fg final finals first for foul fouls free
from game games get give go goals got had has have he her high him his home how i if in into is it its last lead
leader leaders led let list lose lost many me minutes more most much my nba need next night no not number of off on
one or other our out over past per percentage play played player players playoff playoffs plays please point points
postseason put rebound rebounds record result results round score scored scores scoring season seasons second see
series she should show shooting shot shots stat stats steal steals than that the their them then there these they
this those three threes throw throws tied title to today tomorrow tonight top total totals triple turnover turnovers
under up versus vs was we week weekend were west western what whats when where which who whos why win winner
winners with won would year years yesterday you your will just only ever mvp team teams matchup conference conf semis semifinal semifinals ecf wcf quarterfinals opening
january february march april may june july august september october november december
jan feb mar apr jun jul aug sep sept oct nov dec
monday tuesday wednesday thursday friday saturday sunday standings regular average averages losses loss wins percentage pct ppg rpg apg mpg
rank ranks ranked ranking rankings
""".split())
# Everyday words that are also first names: a one-word mention only when capitalized
# ("Mark's points", never "regular-season mark").
CAPITALIZED_ONLY = frozenset({"mark"})
