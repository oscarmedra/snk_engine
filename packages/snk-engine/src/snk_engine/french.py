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
IMPERATIVE_SLOTS = {"2sg": 0, "1pl": 1, "2pl": 2}


class FrenchError(ValueError):
    pass


@dataclass(frozen=True)
class FrenchVerb:
    infinitive: str          # clé du verbe soninké
    french_infinitive: str
    aux: str
    participle: str
    present: list[str]
    imperfect: list[str]
    future_stem: str
    subjunctive: list[str] | None = None
    imperative: list[str] | None = None   # tu, nous, vous

    @classmethod
    def from_data(cls, infinitive: str, data: dict) -> "FrenchVerb":
        try:
            return cls(infinitive, data.get("infinitif", ""), data["auxiliaire"], data["participe"],
                       list(data["present"]), list(data["imparfait"]), data["futur_radical"],
                       list(data["subjonctif"]) if data.get("subjonctif") else None,
                       list(data["imperatif"]) if data.get("imperatif") else None)
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
    if tense in ("demande", "demande_objet"):
        # « na » exprime une demande : l'impératif quand le français l'a, sinon « que… »
        if person in IMPERATIVE_SLOTS and verb.imperative:
            return verb.imperative[IMPERATIVE_SLOTS[person]] + tail
        if not verb.subjunctive:
            raise FrenchError(f"Pas de subjonctif français pour '{verb.infinitive}'")
        que = "qu'" if subject.startswith(("il", "el")) else "que "
        return f"{que}{subject} {verb.subjunctive[i]}{tail}"
    if tense in ("en_cours_objet", "en_cours_objet_fayi"):
        return _elide(subject, verb.present[i]) + tail
    if tense in ("en_cours", "en_cours_fayi"):
        # présent simple : « en ce moment » entrerait en conflit avec « koota su »
        return _elide(subject, verb.present[i]) + tail
    if tense == "imperfect":
        return _elide(subject, verb.imperfect[i]) + tail
    if tense == "imminent":
        return _elide(subject, f"{AUX['etre'][i]} sur le point de {verb.french_infinitive}") + tail
    if tense == "progressive_watia":
        return _elide(subject, f"{AUX['etre'][i]} en train de {verb.french_infinitive}") + tail
    if tense == "future":
        return _elide(subject, future) + tail
    if tense == "past_negative":
        return _negate(subject, AUX[verb.aux][i], f"{participle}{tail}")
    if tense in ("future_negative", "future_negative_ntaxa"):
        return _negate(subject, future, tail.strip())
    raise FrenchError(f"Temps sans traduction française : '{tense}'")
