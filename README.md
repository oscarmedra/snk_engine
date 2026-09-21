# Soninké — structure de la langue, moteur et corpus

Ce dépôt décrit la **structure du soninké** et la rend exécutable : chaque règle
documentée est appliquée par un moteur de conjugaison et vérifiée par des tests.
Il produit aussi un **corpus parallèle soninké-français**, destiné à Hugging Face.

Le soninké (`snk`) est parlé au Mali, en Mauritanie, au Sénégal et en Gambie. Aucun
corpus parallèle soninké-français public n'existait au moment où ce projet a commencé.

## En ligne

| | |
|---|---|
| 📖 **Documentation** | <https://oscarmedra.github.io/snk_engine/> |
| 🔎 **Comprendre un texte** — soninké → français | <https://oscarmedra.github.io/snk_engine/comprendre/> |
| 🎛️ **Playground** — conjuguer un verbe dans le navigateur | <https://oscarmedra.github.io/snk_engine/playground/> |
| 📚 **Le lexique** | <https://oscarmedra.github.io/snk_engine/langue/lexique/> |
| 🧩 **La particule**, la règle centrale de la langue | <https://oscarmedra.github.io/snk_engine/langue/particule/> |

Le site est publié automatiquement à chaque push sur `main`.
Pour le consulter en local : `uv run mkdocs serve`, puis <http://127.0.0.1:8000>.

## Deux principes

1. **Rien n'est inventé.** Une forme n'entre dans le moteur que si le locuteur de
   référence l'a confirmée. Sinon, le moteur renvoie une erreur plutôt qu'une phrase
   incertaine. Les hypothèses tirées de la littérature restent à part, dans
   `docs/projet/recherche.md`.
2. **Tout est vérifié.** Chaque forme confirmée a son test : une règle nouvelle qui en
   contredit une ancienne fait échouer les tests, et la contradiction est soumise au
   locuteur.

## Organisation

```
docs/                  la documentation de la langue (site MkDocs)
packages/snk-engine/   le moteur : conjugaison, génération, outils de collecte
data/grammaire/        les règles confirmées, en YAML (lues par le moteur)
data/references/       le connu mais non confirmé : verbes, mots, dérivations
data/sources/          les textes d'origine, soninké et français en regard
data/questionnaires/   les séries de questions posées au locuteur
corpus/valide/         les phrases traduites, alignées, une par ligne JSON
scripts/               régénération du lexique documenté
```

## Comprendre un texte soninké

Le moteur lit aussi dans l'autre sens : il analyse une phrase soninké et la traduit
en français.

```bash
uv run snk-engine comprendre "ake n'di maro ke n'yiga"          # il a mangé le riz
uv run snk-engine comprendre "ake n'daga saxa daru" --detail    # + le détail de l'analyse
```

L'analyse se fait en trois étapes — segmentation, tagage de chaque mot par catégorie,
puis assemblage dans l'ordre de la grammaire — et non par comparaison avec des phrases
déjà connues. **Un mot absent des données devient `[unknown]`** dans la traduction,
jamais un mot français deviné ; chaque remplacement est expliqué. Le moteur tente
toujours une traduction : tout ce qu'il ne comprend pas est marqué `[unknown]`.

Ses limites aujourd'hui : une phrase simple à la fois, pas de subordonnée ; les
ambiguïtés comme `xa` (vous / où) sont tranchées par la position et signalées en note ;
le vocabulaire confirmé reste petit, donc beaucoup de phrases contiennent des `unknown`.
Le sens inverse — traduire un texte français en soninké — n'est pas construit : le
moteur produit des phrases à partir des règles, mais ne traduit pas du français.

## Démarrer

```bash
uv sync
```

```bash
uv run pytest -q
```

```bash
uv run snk-engine generer --apercu 30
```

Le site de documentation se construit et se consulte en local :

```bash
uv run mkdocs serve
```

## Où en est le projet

| | |
|---|---|
| verbes entièrement conjugables | 8 |
| pronoms | 12 (série longue et série diminutive) |
| temps et constructions | 11 |
| tests | 134 |
| phrases traduites par le locuteur | une centaine, issues de trois textes suivis |
| phrases produites par le moteur | environ 1 800, avec leur traduction |
| verbes et mots en attente de validation | plus de 250 |

## Méthode

Le locuteur traduit un texte français ; le moteur compare chaque phrase à ce qu'il
sait produire et signale les écarts ; ce qui est confirmé devient une règle, avec son
test ; ce qui reste douteux redevient une question. La littérature linguistique
(Creissels, Diagne, Grégoire, Diagana) sert à comprendre la structure et à poser de
meilleures questions, jamais à compléter les données.

## Crédits

La description de la langue, les textes et les traductions sont l'œuvre de
**noah-medra** ([ORCID 0009-0003-6018-9802](https://orcid.org/0009-0003-6018-9802)),
locuteur de référence du projet. Le moteur ne fait qu'appliquer les règles qu'il a
confirmées, forme par forme.

## Licences

| Partie | Licence |
|---|---|
| le code (`packages/`, `scripts/`) | [MIT](LICENSE) |
| les données, le corpus et la documentation (`data/`, `corpus/`, `docs/`) | [CC BY 4.0](LICENSE-DATA) |

La licence CC BY autorise la réutilisation, y compris pour entraîner des modèles de
langue, à condition de citer l'auteur :

> noah-medra (ORCID 0009-0003-6018-9802), « snk_engine — soninké : structure de la
> langue, moteur de conjugaison et corpus parallèle », 2026.
> https://github.com/oscarmedra/snk_engine — CC BY 4.0

Le fichier [`CITATION.cff`](CITATION.cff) donne la citation au format reconnu par GitHub
(bouton « Cite this repository »).
