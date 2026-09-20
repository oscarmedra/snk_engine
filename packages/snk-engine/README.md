# snk-engine

Moteur linguistique soninké : conjugaison, génération de corpus, outils de collecte.

Le code ne contient **aucune règle de soninké en dur** : tout vient des fichiers YAML
de `data/grammaire/`, à la racine du dépôt. Le moteur refuse de produire une forme
qui n'y est pas confirmée, plutôt que de l'inventer.

## Modules

| Fichier | Rôle |
|---|---|
| `conjugation.py` | moteur : pronoms, temps, particules, classes, verbes |
| `french.py` | côté français des phrases (conjugaison minimale, pilotée par les données) |
| `sentences.py` | énumère toutes les phrases produisibles, avec leur traduction |
| `questionnaire.py` | questionnaires Excel de collecte et analyse des réponses |
| `verbs_excel.py` | export des conjugaisons vers Excel |
| `generator.py`, `templates.py`, `lexicon.py` | générateur par gabarits (première version) |
| `writer.py`, `hub.py` | écriture en fragments et publication Hugging Face |
| `orthography.py` | normalisation, conversion de l'ancienne notation |
| `cli.py` | commandes `snk-engine` |

## Utilisation

```python
from snk_engine.conjugation import conjugate

conjugate("dagaer", "anke", "future")      # anke n'yi rini daga
```

```bash
uv run pytest                 # depuis la racine du dépôt
uv run snk-engine --help
```
