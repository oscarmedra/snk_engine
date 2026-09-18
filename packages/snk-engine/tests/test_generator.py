from pathlib import Path

import pyarrow.parquet as pq

from snk_engine.generator import Generator
from snk_engine.lexicon import Entry, Lexicon
from snk_engine.orthography import Orthography, normalize
from snk_engine.templates import Template
from snk_engine.writer import ShardWriter


def make_lexicon() -> Lexicon:
    lex = Lexicon()
    lex.add(Entry("s1", "sujet", {"base": "aa"}, {"base": "je"}))
    lex.add(Entry("s2", "sujet", {"base": "bb"}, {"base": "tu"}))
    lex.add(Entry("o1", "obj", {"base": "cc", "pl": "ccn"}, {"base": "x", "pl": "xs"}))
    lex.add(Entry("o2", "obj", {"base": "dd", "pl": "ddn"}, {"base": "y", "pl": "ys"}))
    return lex


def test_alignment_and_forms():
    t = Template("t", "{sujet} {obj.pl} {obj#2}", "{sujet} {obj.pl}")
    gen = Generator(make_lexicon(), [t], seed=0)
    s = gen.sample()
    words = s.snk.rstrip(".").lower().split()
    assert words[1] in {"ccn", "ddn"}
    assert words[1][:2] != words[2]  # emplacements distincts -> entrées distinctes
    assert s.fr.lower().startswith({"aa": "je", "bb": "tu"}[words[0]])


def test_dedup_stops_when_exhausted():
    t = Template("t", "{sujet} {obj}")
    gen = Generator(make_lexicon(), [t], seed=0)
    assert gen.combinations() == 4
    out = list(gen.generate(100, max_misses=500))
    assert len(out) == 4
    assert len({s.snk for s in out}) == 4


def test_orthography_rejects():
    ortho = Orthography("abcd")
    assert ortho.is_valid(normalize("aa  bb"))
    assert not ortho.is_valid("zz")


def test_writer_shards(tmp_path: Path):
    t = Template("t", "{sujet} {obj}", "{sujet} {obj}")
    gen = Generator(make_lexicon(), [t], seed=1)
    with ShardWriter(tmp_path, shard_size=3) as w:
        for s in gen.generate(4):
            w.write(s)
    assert len(w.files) == 2
    assert sum(pq.read_table(f).num_rows for f in w.files) == 4
