# Le soninké, décrit et calculable

Ce site documente la **structure du soninké** telle qu'elle est parlée par le locuteur
de référence du projet, et la rend exécutable : chaque règle décrite ici est appliquée
par un moteur de conjugaison, et vérifiée par des tests.

## Ce que contient ce dépôt

| Partie | Contenu |
|---|---|
| **Documentation** (`docs/`) | la description de la langue, section par section |
| **Moteur** (`packages/snk-engine/`) | le code qui applique ces règles |
| **Données** (`data/`) | les règles elles-mêmes, en YAML : rien n'est écrit en dur dans le code |
| **Corpus** (`corpus/`) | les phrases traduites par le locuteur, et celles produites par le moteur |

## Deux principes

**Rien n'est inventé.** Une forme n'entre dans le moteur que si le locuteur l'a
confirmée. Pour tout le reste, le moteur renvoie une erreur au lieu de produire une
phrase incertaine. Les hypothèses tirées de la littérature restent dans
[les notes de recherche](projet/recherche.md), séparées des données.

**Tout est vérifié.** Chaque forme confirmée a son test. Quand une nouvelle règle en
contredit une ancienne, les tests échouent, et la contradiction est soumise au locuteur.

## Essayer tout de suite

Le [**playground**](playground.md) conjugue n'importe quel verbe du moteur à tous les
temps confirmés, directement dans le navigateur.

## Par où commencer

- [L'orthographe](langue/orthographe.md) — comment on écrit
- [Les pronoms](langue/pronoms.md) — deux séries, longue et diminutive
- [La particule](langue/particule.md) — `n'`, `m'`, `l'`, `ŋ'` : la règle centrale
- [Les temps](langue/temps.md) — onze constructions, toutes bâties sur le même modèle
- [Le lexique](langue/lexique.md) — les verbes et les mots confirmés

## État d'avancement

- 8 verbes entièrement conjugables, 12 pronoms, 11 temps ;
- 134 tests ;
- un corpus parallèle soninké-français issu de textes traduits par le locuteur ;
- environ 1 800 phrases produites automatiquement, avec leur traduction.

Aucun corpus parallèle soninké-français public n'existe à ce jour : c'est le manque
que ce projet cherche à combler.
