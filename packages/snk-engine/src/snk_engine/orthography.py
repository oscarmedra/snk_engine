"""Normalisation et validation orthographique.

L'alphabet est configurable (configs/default.yaml → orthographe.alphabet)
pour s'adapter à la norme retenue (Mali, Sénégal, Mauritanie, Gambie).
"""

from __future__ import annotations

import re
import unicodedata

_SPACES = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,;:!?])")


def normalize(text: str, capitalize: bool = True, final_punct: str | None = ".") -> str:
    text = unicodedata.normalize("NFC", text)
    text = _SPACES.sub(" ", text).strip()
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    if not text:
        return text
    if capitalize:
        text = text[0].upper() + text[1:]
    if final_punct and text[-1] not in ".!?":
        text += final_punct
    return text


_GU = re.compile(r"(?<=[gG])u(?=[eéèiíì])")


def modernize(text: str) -> str:
    """Ancienne notation du projet → orthographe confirmée (x, u, e, g).

    kh → x, ou → u, é → e, gu devant e/i → g. Ne touche ni aux apostrophes
    ni aux traits d'union du gérondif, qui ne se déduisent pas.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace("kh", "x").replace("Kh", "X")
    text = _GU.sub("", text)
    text = text.replace("ou", "u").replace("Ou", "U")
    return text.replace("é", "e").replace("É", "E")


class Orthography:
    def __init__(self, alphabet: str, extra: str = " '-.,;:!?") -> None:
        letters = unicodedata.normalize("NFC", alphabet)
        self.allowed = set(letters.lower()) | set(letters.upper()) | set(extra)

    def invalid_chars(self, text: str) -> set[str]:
        return {c for c in unicodedata.normalize("NFC", text) if c not in self.allowed}

    def is_valid(self, text: str) -> bool:
        return not self.invalid_chars(text)
