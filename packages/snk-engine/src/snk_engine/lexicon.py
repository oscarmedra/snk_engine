"""Chargement du lexique soninké depuis des fichiers YAML.

Format d'un fichier de lexique :

    categories:
      nom:
        - id: n_maison
          snk: {sg: "...", pl: "..."}   # ou simplement snk: "..."
          fr:  {sg: "...", pl: "..."}
          tags: [lieu]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_FORM = "base"


@dataclass(frozen=True)
class Entry:
    id: str
    category: str
    snk: dict[str, str]
    fr: dict[str, str] = field(default_factory=dict)
    tags: frozenset[str] = frozenset()

    def form(self, lang: str, name: str | None) -> str:
        forms = self.snk if lang == "snk" else self.fr
        if not forms:
            raise KeyError(f"'{self.id}' n'a pas de forme en '{lang}'")
        if name is None:
            return forms.get(DEFAULT_FORM, next(iter(forms.values())))
        if name not in forms:
            raise KeyError(f"'{self.id}' n'a pas de forme '{name}' en '{lang}'")
        return forms[name]


def _as_forms(value: str | dict | None) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, str):
        return {DEFAULT_FORM: value}
    return {str(k): str(v) for k, v in value.items()}


class Lexicon:
    def __init__(self) -> None:
        self.categories: dict[str, list[Entry]] = {}

    def add(self, entry: Entry) -> None:
        self.categories.setdefault(entry.category, []).append(entry)

    def pool(self, category: str, tag: str | None = None) -> list[Entry]:
        if category not in self.categories:
            raise KeyError(f"Catégorie inconnue dans le lexique : '{category}'")
        entries = self.categories[category]
        if tag:
            entries = [e for e in entries if tag in e.tags]
        return entries

    def __len__(self) -> int:
        return sum(len(v) for v in self.categories.values())

    @classmethod
    def from_paths(cls, paths: list[Path]) -> "Lexicon":
        lex = cls()
        for path in _yaml_files(paths):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for category, items in (data.get("categories") or {}).items():
                for i, item in enumerate(items or []):
                    lex.add(
                        Entry(
                            id=str(item.get("id", f"{category}_{path.stem}_{i}")),
                            category=category,
                            snk=_as_forms(item["snk"]),
                            fr=_as_forms(item.get("fr")),
                            tags=frozenset(item.get("tags", [])),
                        )
                    )
        return lex


def _yaml_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.y*ml")))
        else:
            files.append(p)
    return files
