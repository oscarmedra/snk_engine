"""Gabarits de phrases.

Syntaxe d'un emplacement : {categorie[@tag][#n][.forme]}

  {nom}            une entrée de la catégorie « nom », forme par défaut
  {nom.pl}         forme « pl » de cette entrée
  {nom@anime}      entrée de « nom » portant le tag « anime »
  {nom#2}          un 2e nom, tiré indépendamment du 1er

Le même emplacement (même catégorie/tag/#n) réutilise la même entrée partout
dans le gabarit, en soninké comme en français : c'est ce qui aligne la traduction.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .lexicon import Lexicon, _yaml_files

SLOT_RE = re.compile(r"\{(?P<cat>\w+)(?:@(?P<tag>\w+))?(?:#(?P<idx>\d+))?(?:\.(?P<form>\w+))?\}")


@dataclass(frozen=True)
class Slot:
    category: str
    tag: str | None
    idx: str | None

    @property
    def key(self) -> str:
        return f"{self.category}@{self.tag or ''}#{self.idx or ''}"


@dataclass(frozen=True)
class Template:
    id: str
    snk: str
    fr: str | None = None
    weight: float = 1.0

    def slots(self) -> dict[str, Slot]:
        found: dict[str, Slot] = {}
        for text in (self.snk, self.fr or ""):
            for m in SLOT_RE.finditer(text):
                slot = Slot(m["cat"], m["tag"], m["idx"])
                found[slot.key] = slot
        return found

    def combinations(self, lexicon: Lexicon) -> int:
        return math.prod(len(lexicon.pool(s.category, s.tag)) for s in self.slots().values())


def load_templates(paths: list[Path]) -> list[Template]:
    templates: list[Template] = []
    for path in _yaml_files(paths):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for i, item in enumerate(data.get("templates") or []):
            templates.append(
                Template(
                    id=str(item.get("id", f"{path.stem}_{i}")),
                    snk=item["snk"],
                    fr=item.get("fr"),
                    weight=float(item.get("weight", 1.0)),
                )
            )
    return templates
