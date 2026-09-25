"""Fait entrer dans le moteur les verbes de l'inventaire dont les formes sont sûres.

Côté soninké : le radical vient de la liste du locuteur, la forme en -ni de la règle
qu'il a validée (le suffixe reprend la dernière voyelle).

Côté français : seules les conjugaisons régulières sont dérivées — 1er groupe (-er)
et 2e groupe (-ir en -issons). Les verbes irréguliers restent dans l'inventaire :
le moteur ne produirait pas leur français sans risque d'erreur.

    uv run python scripts/promote_verbes.py            # montre ce qui serait fait
    uv run python scripts/promote_verbes.py --ecrire   # écrit dans data/grammaire/
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = ROOT / "data" / "grammaire" / "soninke.yaml"
VERBES = ROOT / "data" / "references" / "verbes.yaml"
VOWELS = "aeiou"

# verbes français qui se conjuguent avec « être »
ETRE = {"aller", "arriver", "descendre", "entrer", "monter", "mourir", "naître", "partir",
        "passer", "rentrer", "rester", "retourner", "revenir", "sortir", "tomber", "venir"}


def propose_gerund(radical: str) -> str:
    last = next((c for c in reversed(radical) if c in VOWELS), "i")
    return f"{radical}n{last}" if radical[-1] in VOWELS else f"{radical}ni"


def french_forms(infinitive: str, group: str) -> dict | None:
    """Conjugaison française des groupes réguliers ; None si le verbe est irrégulier."""
    aux = "etre" if infinitive in ETRE else "avoir"
    if group == "1er" and infinitive.endswith("er") and infinitive not in ("aller", "envoyer"):
        stem = infinitive[:-2]
        soft = stem + "e" if stem.endswith("g") else (stem[:-1] + "ç" if stem.endswith("c") else stem)
        return {
            "auxiliaire": aux, "infinitif": infinitive, "participe": stem + "é",
            "present": [stem + e for e in ("e", "es", "e")] + [soft + "ons", stem + "ez", stem + "ent"],
            "imparfait": [soft + e for e in ("ais", "ais", "ait")] + [stem + e for e in ("ions", "iez")]
                         + [soft + "aient"],
            "futur_radical": infinitive,
            "subjonctif": [stem + e for e in ("e", "es", "e", "ions", "iez", "ent")],
            "imperatif": [stem + "e", soft + "ons", stem + "ez"],
        }
    if group == "2e" and infinitive.endswith("ir"):
        stem, long = infinitive[:-2], infinitive[:-2] + "iss"
        return {
            "auxiliaire": aux, "infinitif": infinitive, "participe": stem + "i",
            "present": [stem + "is", stem + "is", stem + "it", long + "ons", long + "ez", long + "ent"],
            "imparfait": [long + e for e in ("ais", "ais", "ait", "ions", "iez", "aient")],
            "futur_radical": infinitive,
            "subjonctif": [long + e for e in ("e", "es", "e", "ions", "iez", "ent")],
            "imperatif": [stem + "is", long + "ons", long + "ez"],
        }
    return None


def main(write: bool = False) -> None:
    grammar_text = GRAMMAR.read_text(encoding="utf-8")
    grammar = yaml.safe_load(grammar_text)
    inventory = yaml.safe_load(VERBES.read_text(encoding="utf-8"))
    existing = {str(v.get("forme", "")).lower() for v in grammar["verbes"].values()}
    keys = set(grammar["verbes"])

    promoted, kept = {}, []
    for entry in inventory.get("liste") or []:
        radical, sens = entry.get("radical"), entry.get("fr")
        forms = french_forms(sens, entry.get("groupe_fr", ""))
        if not radical or radical.lower() in existing or not forms:
            kept.append(entry)
            continue
        key = radical if radical not in keys else f"{radical}2"
        keys.add(key)
        existing.add(radical.lower())
        promoted[key] = {
            "fr": sens, "forme": radical, "nom_action": entry.get("nom_action"),
            "gerondif": propose_gerund(radical), "classe": "regulier", "francais": forms,
        }

    print(f"{len(promoted)} verbes prêts à entrer dans le moteur")
    print(f"{len(kept)} restent dans l'inventaire (conjugaison française irrégulière)")
    for key, verb in list(promoted.items())[:6]:
        print(f"   {key:12} {verb['fr']:14} {verb['forme']} / {verb['gerondif']} · {verb['francais']['present'][0]}")
    if not write:
        print("\n(essai à blanc — relancer avec --ecrire pour appliquer)")
        return

    block = yaml.safe_dump({"verbes": promoted}, allow_unicode=True, sort_keys=False, width=200)
    block = "\n".join(line[2:] if line.startswith("  ") else line for line in block.splitlines()[1:])
    GRAMMAR.write_text(grammar_text.rstrip() + "\n\n  # --- verbes de la liste du locuteur (formes en -ni validées 2026-09-25) ---\n"
                       + "\n".join("  " + line for line in block.splitlines()) + "\n", encoding="utf-8")
    inventory["liste"] = kept
    header = VERBES.read_text(encoding="utf-8").split("locuteur:")[0]
    body = yaml.safe_dump({k: inventory[k] for k in ("locuteur", "liste", "sources") if k in inventory},
                          allow_unicode=True, sort_keys=False, width=200)
    VERBES.write_text(header + body, encoding="utf-8")
    print(f"\nécrit : {len(promoted)} verbes dans {GRAMMAR.name}")


if __name__ == "__main__":
    main("--ecrire" in sys.argv)
