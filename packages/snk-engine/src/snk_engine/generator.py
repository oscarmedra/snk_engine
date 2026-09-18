"""Générateur de phrases : tirage pondéré des gabarits, remplissage, dédoublonnage."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Iterator
from dataclasses import dataclass

from .lexicon import Entry, Lexicon
from .orthography import Orthography, normalize
from .templates import SLOT_RE, Slot, Template


@dataclass
class Sample:
    snk: str
    fr: str | None
    template_id: str


class Generator:
    def __init__(
        self,
        lexicon: Lexicon,
        templates: list[Template],
        orthography: Orthography | None = None,
        seed: int = 42,
        distinct_slots: bool = True,
    ) -> None:
        if not templates:
            raise ValueError("Aucun gabarit chargé")
        self.lexicon = lexicon
        self.templates = templates
        self.weights = [t.weight for t in templates]
        self.orthography = orthography
        self.rng = random.Random(seed)
        self.distinct_slots = distinct_slots
        self._slots = {t.id: t.slots() for t in templates}
        self._pools = {
            (t.id, key): lexicon.pool(s.category, s.tag)
            for t in templates
            for key, s in self._slots[t.id].items()
        }
        self.rejected_orthography = 0

    def _bind(self, template: Template) -> dict[str, Entry] | None:
        bound: dict[str, Entry] = {}
        for key in self._slots[template.id]:
            pool = self._pools[(template.id, key)]
            if not pool:
                return None
            choices = pool
            if self.distinct_slots:
                used = {e.id for e in bound.values()}
                choices = [e for e in pool if e.id not in used] or pool
            bound[key] = self.rng.choice(choices)
        return bound

    @staticmethod
    def _render(text: str, bound: dict[str, Entry], lang: str) -> str:
        def repl(m):
            slot = Slot(m["cat"], m["tag"], m["idx"])
            return bound[slot.key].form(lang, m["form"])

        return SLOT_RE.sub(repl, text)

    def sample(self) -> Sample | None:
        template = self.rng.choices(self.templates, weights=self.weights, k=1)[0]
        bound = self._bind(template)
        if bound is None:
            return None
        snk = normalize(self._render(template.snk, bound, "snk"))
        if self.orthography and not self.orthography.is_valid(snk):
            self.rejected_orthography += 1
            return None
        fr = normalize(self._render(template.fr, bound, "fr")) if template.fr else None
        return Sample(snk=snk, fr=fr, template_id=template.id)

    def generate(self, n: int, max_misses: int = 100_000) -> Iterator[Sample]:
        """Produit jusqu'à `n` phrases uniques.

        S'arrête avant si `max_misses` tirages consécutifs sont des doublons
        (espace combinatoire épuisé : il faut enrichir le lexique/les gabarits).
        """
        seen: set[bytes] = set()
        produced = misses = 0
        while produced < n and misses < max_misses:
            s = self.sample()
            if s is None:
                misses += 1
                continue
            digest = hashlib.blake2b(s.snk.encode(), digest_size=8).digest()
            if digest in seen:
                misses += 1
                continue
            seen.add(digest)
            misses = 0
            produced += 1
            yield s

    def combinations(self) -> int:
        return sum(t.combinations(self.lexicon) for t in self.templates)
