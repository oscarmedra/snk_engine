import pytest

from snk_engine.conjugation import default_engine
from snk_engine.french import FrenchVerb, conjugate_fr
from snk_engine.sentences import french_verbs, generate

VERB = FrenchVerb("yigeyer", "manger", "avoir", "mangé",
                  ["mange", "manges", "mange", "mangeons", "mangez", "mangent"],
                  ["mangeais", "mangeais", "mangeait", "mangions", "mangiez", "mangeaient"], "manger",
                  ["mange", "manges", "mange", "mangions", "mangiez", "mangent"],
                  ["mange", "mangeons", "mangez"])


@pytest.mark.parametrize(
    "person, tense, obj, expected",
    [
        ("1sg", "past", None, "j'ai mangé"),
        ("3sg", "past", None, "il a mangé"),
        ("1pl", "past_object", "le riz", "nous avons mangé le riz"),
        ("2sg", "demande", None, "mange"),
        ("3sg", "demande", "le riz", "qu'il mange le riz"),
        ("1sg", "demande", None, "que je mange"),
        ("1sg", "imperfect", None, "je mangeais"),
        ("1sg", "en_cours", None, "je mange en ce moment"),
        ("3pl", "future", None, "ils mangeront"),
        ("1sg", "past_negative", None, "je n'ai pas mangé"),
        ("2sg", "future_negative", None, "tu ne mangeras pas"),
        ("3sg", "progressive_watia", None, "il mange en ce moment"),
        ("1sg", "imminent", None, "je suis sur le point de manger"),
    ],
)
def test_french_conjugation(person, tense, obj, expected):
    assert conjugate_fr(VERB, person, tense, obj) == expected


def test_etre_agreement():
    partir = FrenchVerb("dagaer", "partir", "etre", "parti", ["pars"] * 6, ["partais"] * 6, "partir")
    assert conjugate_fr(partir, "1sg", "past") == "je suis parti"
    assert conjugate_fr(partir, "1pl", "past") == "nous sommes partis"


def test_generation_pairs_are_consistent():
    engine = default_engine()
    rows = list(generate(engine))
    assert len(rows) > 1000
    assert len(french_verbs(engine)) == len(engine.verbs)
    snk = {r.snk for r in rows}
    assert len({(r.snk, r.fr) for r in rows}) == len(rows)   # aucune paire en double
    # « nke yi ri-ni » vaut pour le futur et pour l'action en cours : ambiguïté réelle
    assert {r.fr for r in rows if r.snk == "nke yi ri-ni"} == {"je viendrai", "je viens en ce moment"}
    assert "nke daga saxa" in snk
    assert "ake n'di maro ke n'yiga" in snk
    assert all(r.fr and r.snk for r in rows)


def test_no_object_for_intransitive_verbs():
    rows = list(generate(default_engine()))
    assert not [r for r in rows if r.verb == "dagaer" and r.obj]      # on ne « part » pas un objet
    assert not [r for r in rows if r.verb == "yigeyer" and r.obj and "xati" in r.obj]  # ni ne mange du lait
    assert [r for r in rows if r.verb == "mini" and r.obj and "xati" in r.obj]


def test_complements_match_the_tense():
    rows = list(generate(default_engine()))
    assert not [r for r in rows if r.complement == "daru" and r.tense.startswith("future")]
    assert not [r for r in rows if r.complement == "kumbene" and r.tense == "past"]
    assert [r for r in rows if r.complement == "kumbene" and r.tense == "future"]
