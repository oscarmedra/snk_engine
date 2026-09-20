# Le moteur

Le moteur applique les règles décrites sur ce site. Il ne contient aucune forme
soninké en dur : tout vient de `data/grammaire/soninke.yaml`.

## Installer et vérifier

```bash
uv sync
```

```bash
uv run pytest -q
```

Chaque forme confirmée par le locuteur a son test. Si une règle nouvelle en contredit
une ancienne, les tests échouent : c'est le signal qu'il faut retourner poser la question.

## Conjuguer

```python
from snk_engine.conjugation import conjugate, default_engine

conjugate("dagaer", "anke", "future")              # anke n'yi rini daga
conjugate("yigeyer", "ake", "past_object", "maro") # ake n'di maro n'yiga

engine = default_engine()
list(engine.verbs)     # les verbes connus
list(engine.tenses)    # les temps connus
```

Une forme non confirmée lève une erreur explicite :

```python
conjugate("sefeer", "nke", "progressive")
# ConjugationNotDefinedError: Form not confirmed for verb 'sefeer', subject 'nke', tense 'progressive'
```

## Ajouter un verbe

Dans `data/grammaire/soninke.yaml` :

```yaml
  wurier:
    fr: courir
    forme: wuru
    gerondif: wurunu
    classe: regulier
    francais:
      auxiliaire: avoir
      participe: couru
      present: [cours, cours, court, courons, courez, courent]
      imparfait: [courais, courais, courait, courions, couriez, couraient]
      futur_radical: courr
```

Puis relancer les tests. Un temps inconnu, un pronom inexistant ou une classe absente
empêchent le moteur de démarrer, avec un message qui dit où est l'erreur.

## Les commandes

```bash
uv run snk-engine --help
```

| Commande | Rôle |
|---|---|
| `generer` | produit le corpus depuis le moteur (`--apercu N` pour regarder sans écrire) |
| `exporter-verbes` | sort les conjugaisons actuelles en Excel |
| `questionnaire-creer` / `questionnaire-analyser` | prépare et dépouille un questionnaire |
| `termes-creer` | liste les termes d'un texte à faire expliquer |
| `push` | publie le corpus sur Hugging Face |
| `stats`, `validate`, `generate` | générateur par gabarits (première version du projet) |

## L'organisation du dépôt

```
packages/snk-engine/   le code et ses tests
data/grammaire/        les règles confirmées (lues par le moteur)
data/references/       ce qui est connu mais pas encore confirmé
data/sources/          les textes d'origine du locuteur
data/questionnaires/   les séries de questions
corpus/valide/         les phrases traduites, alignées
docs/                  ce site
scripts/               régénération du lexique
```
