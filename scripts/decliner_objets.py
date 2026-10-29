"""Donne à chaque nom du moteur ses trois formes : nu, déterminé, démontré.

Le soninké marque la détermination par `ke`, et sa place décide du sens :

    alikati          un policier      (nom nu)
    alikati ke       le policier      (ke après le nom : article défini)
    ke alikati       ce policier      (ke avant le nom : démonstratif)

Les deux premières étaient déjà la convention du projet (maro / maro ke). La
troisième vient du locuteur, et son corpus la confirme : « Ké lélé » (ce soir),
« Ké suxuba » (ce matin), « ké siiné » (cette année).

Le genre français n'est pas deviné : il se lit dans l'article que la source donne
déjà (« le père » → masculin). Un nom sans article n'est pas touché.

    uv run python scripts/decliner_objets.py            # essai à blanc
    uv run python scripts/decliner_objets.py --ecrire
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OBJETS = ROOT / "data" / "grammaire" / "objets.yaml"

# article donné par la source → (genre, indéfini, défini, démonstratif)
# `du riz` est déjà un indéfini — le partitif d'une matière — et « un riz » serait
# du mauvais français : on le garde tel quel. Seul un article défini se ramène à
# l'indéfini, puisque c'est désormais `ke` qui porte la détermination.
GENRE = {
    "le": ("m", "un", "le", "ce"), "un": ("m", "un", "le", "ce"),
    "du": ("m", "du", "le", "ce"),
    "la": ("f", "une", "la", "cette"), "une": ("f", "une", "la", "cette"),
    "de la": ("f", "de la", "la", "cette"),
}
VOYELLE = re.compile(r"^[aeiouéèêâîôûh]", re.I)


def decoupe(fr: str) -> tuple[str, str] | None:
    """« le père » → (« le », « père ») ; rend None si l'article manque ou est ambigu."""
    bas = fr.strip()
    for article in ("de la ", "une ", "un ", "les ", "des ", "la ", "le ", "du ", "l'"):
        if bas.lower().startswith(article):
            reste = bas[len(article):].strip()
            cle = article.strip()
            if cle in ("les", "des"):          # un pluriel ne se décline pas ainsi
                return None
            if cle == "l'":                    # « l'enfant » ne dit pas le genre
                return None
            return cle, reste
    return None


def formes(snk: str, fr: str) -> list[tuple[str, str, str]] | None:
    """[(soninké, français, rôle)] pour un nom dont l'article est connu."""
    decoupage = decoupe(fr)
    if not decoupage:
        return None
    article, nom = decoupage
    _, indef, defi, demo = GENRE[article]
    defini = f"l'{nom}" if VOYELLE.match(nom) else f"{defi} {nom}"
    demonstratif = f"cet {nom}" if demo == "ce" and VOYELLE.match(nom) else f"{demo} {nom}"
    return [
        (snk, f"{indef} {nom}", "nu"),
        (f"{snk} ke", defini, "déterminé"),
        (f"ke {snk}", demonstratif, "démontré"),
    ]


def main(ecrire: bool = False) -> None:
    data = yaml.safe_load(OBJETS.read_text(encoding="utf-8")) or {}
    objets = data.get("objets") or []
    presents = {o["snk"] for o in objets}

    ajouts, intouches, corrections = [], [], []
    for o in objets:
        # on ne part que des noms nus : « maro ke » est déjà une forme déterminée,
        # la redécliner donnerait « maro ke ke »
        if o["snk"].lower().endswith((" ke", " ku")) or o["snk"].lower().startswith(("ke ", "ku ")):
            continue
        trois = formes(o["snk"], o["fr"])
        if not trois:
            intouches.append((o["snk"], o["fr"]))
            continue
        for snk, fr, role in trois:
            if snk in presents:
                # la forme nue existe déjà, mais souvent glosée au défini (« le père »)
                # alors que c'est `ke` qui détermine : on la ramène à l'indéfini
                if role == "nu" and o["fr"] != fr:
                    corrections.append((o["snk"], o["fr"], fr))
                continue
            presents.add(snk)
            ajouts.append({"snk": snk, "fr": fr, "verbes": o.get("verbes") or ["wori"],
                           "source": f'{o.get("source", "")} — forme {role}'.strip(" —")})

    print(f"{len(objets)} objets → {len(ajouts)} formes à ajouter, "
          f"{len(corrections)} gloses à ramener à l'indéfini")
    print(f"{len(intouches)} noms laissés tels quels (article absent ou ambigu)\n")
    for a in ajouts[:9]:
        print(f"   {a['snk']:20} {a['fr']}")
    if intouches:
        print("\n   laissés :", ", ".join(f"{s} ({f})" for s, f in intouches[:6]))
    for snk, avant, apres in corrections[:5]:
        print(f"   glose    {snk:18} {avant}  →  {apres}")

    if not ecrire:
        print("\n(essai à blanc — relancer avec --ecrire)")
        return

    lignes = []
    for a in ajouts:
        champs = [f'snk: "{a["snk"]}"', f"fr: {a['fr']}",
                  f"verbes: [{', '.join(a['verbes'])}]", f'source: "{a["source"]}"']
        lignes.append("  - {" + ", ".join(champs) + "}")
    texte = OBJETS.read_text(encoding="utf-8").rstrip()
    for snk, avant, apres in corrections:
        for guillemets in (f'snk: {snk}, fr: {avant},', f'snk: "{snk}", fr: {avant},'):
            texte = texte.replace(guillemets, guillemets.replace(f"fr: {avant},", f"fr: {apres},"))
    bloc = ("\n\n  # --- formes déterminée (nom + ke) et démonstrative (ke + nom) ---\n"
            + "\n".join(lignes))
    OBJETS.write_text(texte.replace("\ncomplements:", bloc + "\n\ncomplements:") + "\n",
                      encoding="utf-8")
    print(f"\nécrit : {len(ajouts)} formes dans {OBJETS.relative_to(ROOT)}")


if __name__ == "__main__":
    main("--ecrire" in sys.argv)
