"""Lit le glossaire soninké-français (PDF) et le range en données exploitables.

Le PDF se laisse extraire par `pdftotext -layout`, à un détail près : la lettre ŋ
est posée dans une fonte que l'extracteur ne sait pas lire et disparaît, laissant
une espace au milieu du mot (banŋe → « ban e »). Vérifié page 2 : le cas est rare
et se répare sans deviner, puisqu'une espace au milieu d'un mot soninké n'a pas
d'autre cause.

Le glossaire note `nn` là où la norme malienne écrit `nŋ` (fanne / fanŋe) et `ñ`
là où elle écrit `ɲ` : c'est une graphie du Sénégal, de Gambie ou de Mauritanie.
Rien n'en sort pour le moteur sans arbitrage du locuteur.

    pdftotext -layout glossaire.pdf glossaire.txt
    uv run python scripts/importer_glossaire.py glossaire.txt --yaml data/references/glossaire.yaml
"""

import argparse
import re
from pathlib import Path

import yaml

REJET = re.compile(r"^\s*(A B C D|Mot Soninké|LA LANGUE|\( Singulier|Pluriel\s*\)|[A-Z]\s*$|\s*$)")
MARQUEURS = re.compile(r"^\(\s*[a-zà-ÿ]{0,4}\s*[,;]\s*[a-zà-ÿ]{0,4}\s*\)$")   # (i, nu)
SONINKE = re.compile(r"^[A-Za-zÀ-ÿŋɲñ'/\-\.! ]+$")
TETE = 15        # largeur de la colonne soninké : au-delà, la ligne est une suite


def repare_eng(mot: str) -> str:
    """Rend le ŋ perdu à l'extraction : « ban e » → « banŋe »."""
    return re.sub(r"(?<=[a-zà-ÿ]) (?=[a-zà-ÿ])", "ŋ", mot) if " " in mot.strip() else mot


def parse(lignes: list[str]) -> list[dict]:
    """Une entrée peut tenir sur trois lignes : le mot, sa seconde forme, le sens.

        Banbu
        (Banbunu)
                      Porter sur le dos (enfant), Bercer

    D'où la petite machine à états : on tient une entrée ouverte et on lui ajoute
    ce qui arrive, jusqu'à ce qu'un nouveau mot commence dans la colonne de gauche.
    """
    entrees: list[dict] = []
    courante: dict | None = None
    # Une ligne haute du tableau fait parfois commencer sa traduction AU-DESSUS de son
    # mot. Un débordement qui ouvre par une majuscule alors que l'entrée courante a
    # déjà un sens appartient donc à l'entrée suivante, pas à celle-ci.
    en_attente = ""

    def ferme():
        nonlocal courante
        if courante and courante.get("fr"):
            courante["fr"] = re.sub(r"\s+", " ", courante["fr"]).strip(" ,;")
            entrees.append(courante)
        courante = None

    for ligne in lignes:
        if REJET.match(ligne):
            continue
        champs = [c.strip() for c in re.split(r"\s{2,}", ligne.strip()) if c.strip()]
        if not champs:
            continue
        tete = ligne[:TETE].strip()

        if not tete:                                   # suite : du français qui déborde
            suite = " ".join(champs)
            if courante and courante.get("fr") and suite[:1].isupper():
                en_attente = (en_attente + " " + suite).strip()
            elif courante:
                courante["fr"] = (courante.get("fr", "") + " " + suite).strip()
            continue
        if tete.startswith("(") and courante:          # la seconde forme, sur sa propre ligne
            courante["forme2"] = champs[0].strip("() ")
            if len(champs) > 1:
                courante["fr"] = (courante.get("fr", "") + " " + " ".join(champs[1:])).strip()
            continue

        # La 2e colonne porte soit les marques de nombre — « (i, nu) », reconnaissables
        # à leur virgule — soit la seconde forme du verbe, « (betunu) », qui n'en a pas.
        mot, marqueurs, forme_col, sens = champs[0], "", "", ""
        if len(champs) >= 2 and champs[1].startswith("("):
            if MARQUEURS.match(champs[1].replace(" ", "")):
                marqueurs = champs[1]
            else:
                forme_col = champs[1].strip("() ")
            sens = " ".join(champs[2:])
        elif len(champs) >= 2:
            sens = " ".join(champs[1:])
        if not SONINKE.match(mot.split("(")[0]):
            continue

        ferme()
        forme2 = ""
        if "(" in mot:
            mot, _, reste = mot.partition("(")
            forme2 = reste.strip(") ")
        if not sens and en_attente:
            sens, en_attente = en_attente, ""
        courante = {"snk": repare_eng(mot.strip()), "fr": sens}
        if forme2 or forme_col:
            courante["forme2"] = forme2 or forme_col
        if marqueurs:
            courante["nombre"] = marqueurs.strip("() ")
    ferme()
    return entrees


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("texte", type=Path, help="sortie de pdftotext -layout")
    parser.add_argument("--yaml", type=Path)
    args = parser.parse_args()

    entrees = parse(args.texte.read_text(encoding="utf-8").splitlines())
    verbes = [e for e in entrees if e.get("forme2") and not e.get("nombre")]
    noms = [e for e in entrees if e.get("nombre")]
    print(f"{len(entrees)} entrées")
    print(f"   dont {len(noms)} avec marques singulier/pluriel (des noms)")
    print(f"   dont {len(verbes)} avec une seconde forme (verbes : radical + forme en -ni)")
    repares = [e["snk"] for e in entrees if "ŋ" in e["snk"] ]
    print(f"   ŋ rendus à l'extraction : {', '.join(repares) or 'aucun'}")

    if args.yaml:
        entete = (
            "# Glossaire soninké-français, importé d'un PDF fourni par le locuteur\n"
            "# (2026-10-29) et converti par scripts/importer_glossaire.py.\n"
            "#\n"
            "# Graphie du glossaire : `nn` là où la norme malienne écrit `nŋ`, et `ñ`\n"
            "# pour `ɲ` — usage du Sénégal, de Gambie ou de Mauritanie. Ce n'est donc\n"
            "# pas forcément la variété du locuteur : SOURCE EXTERNE, rien n'entre dans\n"
            "# le moteur sans son arbitrage.\n#\n"
            "# `forme2` : la seconde forme donnée entre parenthèses — pour un verbe, sa\n"
            "# forme en -ni ; `nombre` : les marques de singulier et de pluriel.\n\n"
        )
        args.yaml.write_text(
            entete + yaml.safe_dump({"entrees": entrees}, allow_unicode=True,
                                    sort_keys=False, width=200), encoding="utf-8")
        print(f"\nécrit : {args.yaml}")


if __name__ == "__main__":
    main()
