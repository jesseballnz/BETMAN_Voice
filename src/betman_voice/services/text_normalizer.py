from __future__ import annotations

import re


ONES = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
}
TENS = {
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}
ORDINALS = {
    "1": "first",
    "2": "second",
    "3": "third",
    "4": "fourth",
    "5": "fifth",
    "6": "sixth",
    "7": "seventh",
    "8": "eighth",
    "9": "ninth",
    "10": "tenth",
}
FORM_TOKENS = {
    "x": "spell",
    "p": "pulled up",
    "f": "fell",
    "l": "lost rider",
}


def normalize_racing_text(text: str, max_sentence_words: int = 28) -> str:
    """Make BETMAN racing copy safer for local TTS engines.

    The normaliser is deliberately deterministic. It does not try to be clever
    with model prompts; it rewrites the handful of racing notations that Piper
    routinely reads badly.
    """

    value = str(text or "").strip()
    if not value:
        return ""

    value = re.sub(r"https?://\S+", "", value)
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    value = re.sub(r"[‐‑‒–—]+", " - ", value)
    value = re.sub(r"\s*[·•|]\s*", ". ", value)
    value = re.sub(r"\s*/\s*", ", ", value)
    value = _normalize_market_move_phrases(value)
    value = _normalize_money(value)
    value = _normalize_spoken_price_digits(value)
    value = _normalize_contextual_decimal_odds(value)
    value = _normalize_races(value)
    value = _normalize_ordinals(value)
    value = _normalize_form_phrases(value)
    value = _normalize_standalone_form_tokens(value)
    value = _spell_acronyms(value)
    value = _protect_horse_name_punctuation(value)
    value = re.sub(r"[#*_`>\[\]{}]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = _shorten_long_sentences(value, max_sentence_words=max_sentence_words)
    return value


def _normalize_money(value: str) -> str:
    return re.sub(
        r"\$(\d{1,4})(?:\.(\d{1,2}))?\b",
        lambda match: _format_price_words(match.group(1), match.group(2)),
        value,
    )


def _normalize_contextual_decimal_odds(value: str) -> str:
    context = r"(?:odds?|price|quote|trading|trade|from|into|out to|at|around|opened|open)"
    pattern = re.compile(rf"\b({context})(\s+)(\d{{1,4}}\.\d{{1,2}})\b", re.IGNORECASE)
    return pattern.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{_format_price_words(*_split_decimal(match.group(3)))}",
        value,
    )


def _normalize_spoken_price_digits(value: str) -> str:
    return re.sub(
        r"\b(\d{1,4})\s+dollars(?:\s+(\d{1,2}))?\b",
        lambda match: _format_price_words(match.group(1), match.group(2)),
        value,
        flags=re.IGNORECASE,
    )


def _normalize_market_move_phrases(value: str) -> str:
    arrow = re.compile(r"\b(\d{1,4}(?:\.\d{1,2})?)\s*(?:->|→|to)\s*(\d{1,4}(?:\.\d{1,2})?)\b")

    def replace_arrow(match: re.Match[str]) -> str:
        left = float(match.group(1))
        right = float(match.group(2))
        direction = "out to" if right > left else "into"
        return f"from {_format_price_words(*_split_decimal(match.group(1)))} {direction} {_format_price_words(*_split_decimal(match.group(2)))}"

    value = arrow.sub(replace_arrow, value)
    value = re.sub(r"\bfirm(?:ed|ing)?\b", "firmed", value, flags=re.IGNORECASE)
    value = re.sub(r"\bdrift(?:ed|ing)?\b", "drifted", value, flags=re.IGNORECASE)
    return value


def _normalize_races(value: str) -> str:
    value = re.sub(
        r"\bR(\d{1,2})\b",
        lambda match: f"Race {_number_to_words(int(match.group(1)))}",
        value,
    )
    return re.sub(
        r"\bRace\s+(\d{1,2})\b",
        lambda match: f"Race {_number_to_words(int(match.group(1)))}",
        value,
        flags=re.IGNORECASE,
    )


def _normalize_ordinals(value: str) -> str:
    return re.sub(
        r"\b(\d{1,2})(?:st|nd|rd|th)\b",
        lambda match: ORDINALS.get(match.group(1), f"{_number_to_words(int(match.group(1)))}th"),
        value,
        flags=re.IGNORECASE,
    )


def _normalize_form_phrases(value: str) -> str:
    pattern = re.compile(r"\b(form|last\s*(?:start|starts)?|recent\s*form)\s*[:=]?\s*([0-9xXpPfFlL-]{2,12})\b", re.IGNORECASE)

    def replace_form(match: re.Match[str]) -> str:
        spoken = _speak_form_sequence(match.group(2))
        return f"{match.group(1)} reads {spoken}" if spoken else match.group(0)

    return pattern.sub(replace_form, value)


def _normalize_standalone_form_tokens(value: str) -> str:
    value = re.sub(r"\b[Pp]\b(?!\s+[A-Z]\b)", "pulled up", value)
    value = re.sub(r"\b[xX]\b", "spell", value)
    return value


def _speak_form_sequence(value: str) -> str:
    parts: list[str] = []
    for char in str(value or ""):
        lower = char.lower()
        if lower in FORM_TOKENS:
            parts.append(FORM_TOKENS[lower])
        elif char.isdigit():
            parts.append(ORDINALS.get(char, _number_to_words(int(char))))
        elif char == "-":
            continue
    return ", ".join(parts)


def _spell_acronyms(value: str) -> str:
    known = {
        "AI",
        "API",
        "BETMAN",
        "HK",
        "NZ",
        "NZB",
        "TAB",
        "TTS",
        "URL",
        "VIP",
    }

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token == "BETMAN":
            return token
        if token in known or (len(token) <= 4 and token.isupper()):
            return " ".join(token)
        return token

    return re.sub(r"\b[A-Z]{2,6}\b", replace, value)


def _protect_horse_name_punctuation(value: str) -> str:
    # Keep possessives and hyphenated horse names readable instead of leaving
    # punctuation that Piper can over-emphasise.
    value = re.sub(r"\b([A-Za-z])'([A-Za-z])", r"\1 \2", value)
    value = re.sub(r"\b([A-Za-z]+)-([A-Za-z]+)\b", r"\1 \2", value)
    return value


def _shorten_long_sentences(value: str, max_sentence_words: int) -> str:
    if max_sentence_words <= 0:
        return value
    pieces = re.split(r"(?<=[.!?])\s+", value)
    out: list[str] = []
    for piece in pieces:
        words = piece.split()
        if len(words) <= max_sentence_words:
            out.append(piece)
            continue
        chunks = [
            " ".join(words[index : index + max_sentence_words])
            for index in range(0, len(words), max_sentence_words)
        ]
        out.append(". ".join(chunk.rstrip(".,;:") for chunk in chunks if chunk))
    return " ".join(out)


def _split_decimal(value: str) -> tuple[str, str | None]:
    left, _, right = str(value).partition(".")
    return left, right or None


def _format_price_words(whole: str, cents: str | None = None) -> str:
    whole_num = int(whole)
    result = f"{_number_to_words(whole_num)} dollars"
    if cents is None:
        return result
    cents_num = int(str(cents).ljust(2, "0")[:2])
    if cents_num:
        result += f" {_number_to_words(cents_num)}"
    return result


def _number_to_words(value: int) -> str:
    if value < 0:
        return f"minus {_number_to_words(abs(value))}"
    if value < 20:
        return ONES[value]
    if value < 100:
        tens = (value // 10) * 10
        remainder = value % 10
        return TENS[tens] if remainder == 0 else f"{TENS[tens]} {_number_to_words(remainder)}"
    if value < 1000:
        hundreds = value // 100
        remainder = value % 100
        return (
            f"{_number_to_words(hundreds)} hundred"
            if remainder == 0
            else f"{_number_to_words(hundreds)} hundred {_number_to_words(remainder)}"
        )
    if value < 10000:
        thousands = value // 1000
        remainder = value % 1000
        return (
            f"{_number_to_words(thousands)} thousand"
            if remainder == 0
            else f"{_number_to_words(thousands)} thousand {_number_to_words(remainder)}"
        )
    return str(value)
