import json

import pytest

from snk_engine.conjugation import DATA_DIR
from snk_engine.understand import (
    UNKNOWN,
    AnalysisError,
    analyze,
    analyze_text,
    load_lexicon,
    tag,
    tokenize,
)

CORPUS = DATA_DIR.parent / "corpus" / "valide"


@pytest.fixture(scope="module")
def lex():
    return load_lexicon()


# --- Segmentation ------------------------------------------------------------

def test_particle_is_detached():
    tokens = tokenize("ake n'daga saxa")
    assert [t.word for t in tokens] == ["ake", "daga", "saxa"]
    assert [t.particle for t in tokens] == [None, "n'", None]


def test_compound_words_are_kept_whole():
    assert [t.word for t in tokenize("xara-kompe ma-ma")] == ["xara-kompe", "ma-ma"]


def test_text_is_split_into_sentences(lex):
    assert len(analyze_text("ake n'daga. anke l'ri !", lex)) == 2


# --- Phrases du corpus validé -------------------------------------------------

def test_past_without_object(lex):
    a = analyze("ake n'daga saxa daru", lex)
    assert a.frame["sujet"] == "ake" and a.frame["temps"] == "past"
    assert a.frame["verbe"] == "dagaer" and a.confirme
    assert a.fr == "il est parti au marché hier"


def test_object_is_isolated_between_marker_and_verb(lex):
    a = analyze("ake n'di maro ke n'yiga", lex)
    assert a.frame["temps"] == "past_object"          # et non « past »
    assert a.frame["objet"] == "maro ke"
    assert a.fr == "il a mangé le riz"


def test_shared_marker_is_disambiguated_by_the_object(lex):
    # « yi » sert à en_cours et en_cours_objet : c'est l'objet qui tranche
    assert analyze("nke yi wurunu", lex).frame["temps"] == "en_cours"
    with_object = analyze("nke yi maro yigane", lex)
    assert with_object.frame["temps"] == "en_cours_objet"
    assert with_object.frame["objet"] == "maro"


def test_tense_is_checked_by_regenerating(lex):
    # « fayi » ouvre plusieurs temps : le moteur reconjugue chaque candidat
    assert analyze("nke fayi dagana saxa", lex).frame["temps"] == "en_cours_fayi"
    watia = analyze("nke fayi dagana watia", lex)
    assert watia.frame["temps"] == "progressive_watia"
    assert watia.frame["complements"] == []          # « watia » appartient au temps
    assert watia.fr == "je suis en train de partir"
    assert analyze("nke fayi rini daga", lex).frame["temps"] == "imminent"


def test_multiword_suffix_belongs_to_the_verb(lex):
    a = analyze("nke do yigaye ni ya me", lex)
    assert a.frame["temps"] == "en_cours_do" and a.frame["complements"] == []
    assert a.fr == "je suis en train de manger"


def test_multiword_complement(lex):
    a = analyze("nke yi maro yigane koota su", lex)
    assert a.frame["complements"] == ["koota su"]
    assert a.fr == "je mange du riz tous les jours"


def test_corpus_sentences_are_understood(lex):
    rows = [json.loads(line) for line in (CORPUS / "texte_marche.jsonl").read_text(encoding="utf-8").splitlines()]
    snk = {r["id"]: r["snk"] for r in rows}

    # « An l'rini kan dimma ? » — forme en -ni sans marqueur : le verbe est reconnu,
    # le temps ne se déduit pas, et le mot interrogatif est repéré
    quand = analyze(snk["marche-09"], lex)
    assert quand.frame["verbe"] == "rier" and quand.frame["temps"] is None
    assert quand.frame["question"] == "quand"
    assert any("forme en -ni" in n for n in quand.notes)

    # l'orthographe d'origine du corpus (é, ou, kh) est ramenée à celle du projet
    marche = analyze(snk["marche-02"], lex)      # « nké fayi dagana saxa. »
    assert marche.frame["sujet"] == "nke" and marche.frame["verbe"] == "dagaer"


# --- Rien n'est inventé --------------------------------------------------------

def test_reference_verb_is_marked_unconfirmed(lex):
    a = analyze("a guiri", lex)                 # guiri : donné par le locuteur, non confirmé
    assert a.frame["verbe"] == "se lever" and not a.frame["verbe_confirme"]
    assert not a.confirme and "non confirmé" in a.fr
    assert any("non confirmé" in n for n in a.notes)


def test_literature_verbs_are_not_used(lex):
    # « taaxu » (s'asseoir) n'existe que dans la section `sources` de verbes.yaml
    assert "taaxu" not in lex.verbs and "taaxu" not in lex.reference_verbs
    a = analyze("ake n'taaxu", lex)
    assert a.frame["verbe"] is None and UNKNOWN in a.fr


def test_unknown_word_becomes_unknown(lex):
    a = analyze("ake n'daga zzzz", lex)
    assert a.fr == "il est parti unknown"
    assert any("zzzz" in n for n in a.notes)
    assert not a.confirme


def test_nothing_recognised_raises(lex):
    with pytest.raises(AnalysisError):
        analyze("zzzz qqqq", lex)


# --- Ambiguïtés ----------------------------------------------------------------

def test_xa_is_a_pronoun_at_the_start_and_a_question_at_the_end(lex):
    subject = analyze("xa daga saxa", lex)
    assert subject.frame["sujet"] == "xa" and subject.frame["personne"] == "2pl"
    assert any("xa" in n for n in subject.notes)          # l'ambiguïté est signalée

    question = analyze("an guida xa", lex)
    assert question.frame["question"] == "où" and question.fr.endswith("?")


def test_tagger_lists_every_candidate(lex):
    tags = {t.word: t.tags for t in tag(tokenize("xa maro ke yi"), lex)}
    assert {"pronom", "interrogatif"} <= set(tags["xa"])   # deux candidats, pas de choix hâtif
    assert "marqueur" in tags["yi"] and "determinant" in tags["ke"]


def test_particle_mismatch_is_reported(lex):
    a = analyze("ake n'mini", lex)        # attendu : m'mini
    assert any("particule inattendue" in n for n in a.notes)
