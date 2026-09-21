import pytest

from snk_engine.translate_fr import UNKNOWN, build_index, render, translate_text
from snk_engine.understand import analyze_text, load_lexicon
from snk_engine.understand import render as render_fr


@pytest.fixture(scope="module")
def lex():
    return load_lexicon()


def fr2snk(text, lex):
    return render(translate_text(text, lex))


@pytest.mark.parametrize(
    "fr, snk",
    [
        ("il est parti au marché hier", "ake n'daga saxa daru"),
        ("il a mangé le riz", "ake n'di maro ke n'yiga"),
        ("elle a bu le lait", "ake n'di xati ke m'mini"),
        ("je mange du riz tous les jours", "nke yi maro yigane koota su"),
        ("tu partiras demain", "anke n'yi rini daga kumbene"),
        ("nous ne sommes pas partis", "oku maxa daga"),
        ("mange le riz", "maro ke yiga"),          # l'impératif, pas la demande
        ("ne pars pas", "maxa daga"),
        ("venez", "xa yeli"),                      # impératif irrégulier de venir
    ],
)
def test_french_to_soninke(lex, fr, snk):
    assert fr2snk(fr, lex) == snk


def test_every_form_comes_from_the_engine(lex):
    # l'index ne contient que du français produit par conjugate_fr, pour des verbes confirmés
    index = build_index(lex)
    assert "il a mangé" in index and "je mange" in index
    assert all(verb in lex.engine.verbs for entries in index.values() for verb, _, _ in entries)


def test_unknown_parts_are_marked(lex):
    assert fr2snk("il est parti à Paris", lex) == f"ake n'daga {UNKNOWN}"
    assert fr2snk("Le moteur met quelques secondes : c'est Python.", lex) == f"{UNKNOWN}: {UNKNOWN}."


def test_round_trip(lex):
    # soninké → français → soninké redonne la phrase de départ
    for snk in ["ake n'daga saxa daru", "ake n'di maro ke n'yiga", "anke n'yi rini daga kumbene",
                "nke yi maro yigane koota su"]:
        fr = render_fr(analyze_text(snk, lex))
        assert fr2snk(fr, lex) == snk, (snk, fr)
