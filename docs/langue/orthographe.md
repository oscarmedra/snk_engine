# L'orthographe

Le projet suit l'orthographe employée dans la littérature linguistique (Creissels,
Mandenkan), telle que le locuteur l'a validée.

## Les lettres

| On écrit | Et non | Exemple |
|---|---|---|
| `x` | kh | `saxa` (marché), `xati` (lait) |
| `u` | ou | `oku` (nous), `wuru` (courir) |
| `e` | é | `sefe` (parler), `lemine` (enfant) |
| `g` | gu devant e, i | `yige` (manger) |
| `ŋ` | ng | `ŋ'wori` (voir, avec la particule) |
| `q` | — | `q'xobo` (acheter, avec la particule) |

Les voyelles s'écrivent **comme elles se prononcent** : `daga`, `gaaga`, `taaxu`. Une
voyelle double note une voyelle longue.

Les **tons ne sont pas notés**. La littérature les indique (`dàgá`), mais l'usage
courant ne les écrit pas, et le projet suit l'usage.

## L'apostrophe

L'apostrophe marque la particule qui se colle au mot suivant :

```
ake n'daga        il est parti
anke l'ri         tu es venu
ake m'mini        il a bu
ake ŋ'wori        il a vu
```

Voir [La particule](particule.md).

## Le trait d'union

Le trait d'union sépare le radical de son suffixe, comme dans la littérature :

```
daga-na     ri-ni     yige-ne     sefe-ne     wuru-nu
xara-kompe  yiga-moxo  waxi-ni
```

## Conversion de l'ancienne notation

Les premiers échanges du projet utilisaient une notation influencée par le français
(`nké`, `okou`, `khakou`, `yigué`). La fonction `snk_engine.orthography.modernize()`
convertit automatiquement : `kh` → `x`, `ou` → `u`, `é` → `e`, `gu` → `g`.

Elle ne devine ni les apostrophes ni les traits d'union, qui doivent être ajoutés à la main.
