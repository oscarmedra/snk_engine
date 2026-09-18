"""Carte de dataset et publication sur Hugging Face Hub."""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import HfApi

CARD = """---
language:
- snk
{fr_lang}license: {license}
task_categories:
- text-generation
{translation_task}pretty_name: {pretty_name}
size_categories:
- {size_category}
tags:
- soninke
- synthetic
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
---

# {pretty_name}

Corpus **synthétique** en soninké (code ISO 639-3 : `snk`), généré à partir d'un
lexique et de gabarits grammaticaux.

- Nombre de phrases : **{count:,}**
- Gabarits : {n_templates}
- Entrées lexicales : {n_entries}

## Colonnes

| colonne | description |
|---|---|
| `id` | identifiant |
| `snk` | phrase en soninké |
| `fr` | traduction française alignée (si disponible) |
| `template_id` | gabarit ayant produit la phrase |
| `source` | toujours `synthetic` |

## Limites

Les phrases sont produites par combinaison de gabarits : elles sont
grammaticalement contrôlées mais peu variées et peuvent être sémantiquement
étranges. À utiliser en complément de textes authentiques, pas à leur place.
"""


def _size_category(n: int) -> str:
    for limit, label in [(1_000, "n<1K"), (10_000, "1K<n<10K"), (100_000, "10K<n<100K"),
                         (1_000_000, "100K<n<1M"), (10_000_000, "1M<n<10M"), (100_000_000, "10M<n<100M")]:
        if n < limit:
            return label
    return "100M<n<1B"


def write_card(out_dir: Path, count: int, n_templates: int, n_entries: int, has_fr: bool,
               pretty_name: str = "Soninke Synthetic Corpus", license: str = "cc-by-4.0") -> Path:
    text = CARD.format(
        fr_lang="- fr\n" if has_fr else "",
        translation_task="- translation\n" if has_fr else "",
        license=license, pretty_name=pretty_name, size_category=_size_category(count),
        count=count, n_templates=n_templates, n_entries=n_entries,
    )
    path = out_dir / "README.md"
    path.write_text(text, encoding="utf-8")
    return path


def push(out_dir: Path, repo_id: str, private: bool = True) -> str:
    api = HfApi()
    api.create_repo(repo_id, repo_type="dataset", private=private, exist_ok=True)
    api.upload_large_folder(repo_id=repo_id, folder_path=str(out_dir), repo_type="dataset")
    return f"https://huggingface.co/datasets/{repo_id}"
