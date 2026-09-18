"""Côté français des phrases : conjugaison minimale, pilotée par les données.

Chaque verbe porte dans data/grammaire/soninke.yaml une section `francais` :
auxiliaire (avoir/etre), participe, present[6], imparfait[6], futur_radical.
Les six formes sont dans l'ordre : je, tu, il, nous, vous, ils.
"""

from __future__ import annotations

from dataclasses import dataclass

PERSONS = ["1sg", "2sg", "3sg", "1pl", "2pl", "3pl"]
SUBJECTS = {"1sg": "je", "2sg": "tu", "3sg": "il", "1pl": "nous", "2pl": "vous", "3pl": "ils"}
AUX = {
    "avoir": ["ai", "as", "a", "avons", "avez", "ont"],
    "etre": ["suis", "es", "est", "sommes", "êtes", "sont"],
}
FUTURE_ENDINGS = ["ai", "as", "a", "ons", "ez", "ont"]
PLURAL = {"1pl", "2pl", "3pl"}


class FrenchError(ValueError):
    pass


@dataclass(frozen=True)
class FrenchVerb:
    infinitive: str
    aux: str
    participle: str
    present: list[str]
    imperfect: list[str]
    future_stem: str

    @classmethod
    def from_data(cls, infinitive: str, data: dict) -> "FrenchVerb":
        try:
            return cls(infinitive, data["auxiliaire"], data["participe"],
                       list(data["present"]), list(data["imparfait"]), data["futur_radical"])
        except KeyError as exc:
            raise FrenchError(f"Formes françaises incomplètes pour '{infinitive}' : {exc}") from exc


def _elide(subject: str, word: str) -> str:
    """je + ai → j'ai."""
    if subject == "je" and word[:1].lower() in "aeiouéèêh":
        return f"j'{word}"
    return f"{subject} {word}"


def _negate(subject: str, first: str, rest: str) -> str:
    ne = "n'" if first[:1].lower() in "aeiouéèêh" else "ne "
    head = "j'" + first if subject == "je" and ne == "n'" else f"{subject} {ne}{first}"
    if subject == "je" and ne == "n'":
        head = f"je n'{first}"
    return f"{head} pas {rest}".strip()


def conjugate_fr(verb: FrenchVerb, person: str, tense: str, obj: str | None = None) -> str:
    """Phrase française correspondant au temps soninké `tense`."""
    if person not in PERSONS:
        raise FrenchError(f"Personne inconnue : {person}")
    i = PERSONS.index(person)
    subject = SUBJECTS[person]
    participle = verb.participle
    if verb.aux == "etre" and person in PLURAL:
        participle += "s"
    compose = f"{AUX[verb.aux][i]} {participle}"
    future = verb.future_stem + FUTURE_ENDINGS[i]
    tail = f" {obj}" if obj else ""

    if tense in ("past", "past_object"):
        return _elide(subject, compose) + tail
    if tense in ("present", "present_object"):
        return _elide(subject, verb.present[i]) + tail
    if tense == "imperfect":
        return _elide(subject, verb.imperfect[i]) + tail
    if tense in ("progressive", "progressive_watia"):
        return _elide(subject, verb.present[i]) + tail + " en ce moment"
    if tense == "future":
        return _elide(subject, future) + tail
    if tense == "past_negative":
        return _negate(subject, AUX[verb.aux][i], f"{participle}{tail}")
    if tense in ("future_negative", "future_negative_ntaxa"):
        return _negate(subject, future, tail.strip())
    raise FrenchError(f"Temps sans traduction française : '{tense}'")
