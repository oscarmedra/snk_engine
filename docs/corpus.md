# Le corpus

Le corpus a deux parties, de nature très différente.

## 1. Les phrases traduites par le locuteur

C'est la partie la plus précieuse : du soninké naturel, avec sa traduction française.
Elle vit dans `corpus/valide/` (une ligne JSON par phrase).

| Fichier | Contenu |
|---|---|
| `texte_journee.jsonl` | une journée ordinaire, 8 paragraphes |
| `texte_marche.jsonl` | dialogue au marché, 26 phrases |
| `texte_village.jsonl` | récit d'un voyage au village, 27 phrases |
| `serie_02.jsonl`, `serie_03.jsonl` | réponses aux questionnaires |

Les textes d'origine sont dans `data/sources/`, avec les deux langues en regard.

Chaque ligne conserve la saisie d'origine du locuteur à côté de la version convertie
dans l'orthographe du projet.

## 2. Les phrases produites par le moteur

Le moteur combine verbes, pronoms, temps, objets et compléments, et n'écrit que ce
qu'il sait justifier. Aujourd'hui, cela donne environ **1 800 phrases** avec leur
traduction.

```bash
uv run snk-engine generer --apercu 30
uv run snk-engine generer -f jsonl -o output/corpus-moteur
```

Exemples :

```
nke daga saxa                  je suis parti au marché
anke n'yi wurunu              tu courais
ake n'di maro ke n'yiga        il a mangé le riz
i na xati m'mini               ils boivent du lait
xaku n'yi rini daga kumbene   vous partirez demain
```

### Comment les phrases absurdes sont évitées

- un verbe intransitif ne reçoit pas d'objet : on ne « part » pas un objet ;
- chaque objet est lié aux verbes qui l'acceptent : on boit le lait, on ne le mange pas ;
- les compléments de temps s'accordent au temps du verbe : « hier » ne va pas au futur.

## Publier sur Hugging Face

```bash
uv run hf auth login
uv run snk-engine push mon-compte/soninke-corpus
```

La fiche du dataset est écrite automatiquement. Elle indique que les phrases produites
par le moteur sont **synthétiques**, ce qui est une information indispensable pour qui
réutilise le corpus.
