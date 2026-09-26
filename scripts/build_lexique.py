"""Régénère docs/langue/lexique.md à partir des données (à relancer après toute ajout)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(path):
    return yaml.safe_load((DATA / path).read_text(encoding="utf-8")) or {}


def main() -> None:
    grammaire = load("grammaire/soninke.yaml")
    verbes_ref = load("references/verbes.yaml")
    mots = load("references/mots.yaml")

    out = ["---",
           'description: "Lexique soninké-français : verbes avec leur radical et leur forme en -ni, noms et mots courants, tirés des données du moteur."',
           "---", "",
           "# Le lexique", "",
           "Cette page est **générée** à partir des données (`scripts/build_lexique.py`).", "",
           "## Verbes du moteur", "",
           "Entièrement conjugables : toutes les formes sont confirmées par le locuteur.", "",
           "| verbe | sens | radical | forme en -ni | avec objet |", "|---|---|---|---|---|"]
    for name, v in grammaire["verbes"].items():
        out.append(f"| `{name}` | {v['fr']} | {v.get('forme','')} | {v.get('gerondif','—')} | "
                   f"{v.get('forme_objet') or ('oui' if v.get('transitif') else '—')} |")

    out += ["", "## Verbes donnés par le locuteur, pas encore dans le moteur", "",
            "| radical | sens | ce qui manque |", "|---|---|---|"]
    for v in verbes_ref.get("locuteur", []):
        out.append(f"| {v['radical']} | {v['fr']} | {v.get('manque', v.get('note',''))} |")

    out += ["", "## Verbes relevés dans les textes", "",
            "Sens compris d'après le contexte, confirmés par le locuteur.", "",
            "| radical | sens |", "|---|---|"]
    for v in verbes_ref.get("locuteur", []):
        pass
    textes = [v for v in verbes_ref.get("locuteur", []) if v.get("source") == "texte_journee"]
    for v in textes:
        out.append(f"| {v['radical']} | {v['fr']} |")

    out += ["", "## Mots et expressions", ""]
    sections = {
        "noms": "Noms", "temps": "Moments", "grammaire": "Mots grammaticaux",
        "adverbes": "Adverbes", "serie_04": "Précisions du locuteur",
    }
    for key, title in sections.items():
        rows = mots.get(key) or []
        if not rows:
            continue
        out += [f"### {title}", "", "| mot | sens |", "|---|---|"]
        out += [f"| `{r['snk']}` | {r['fr']} |" for r in rows if r.get("snk")]
        out.append("")
    for group, title in (("texte_journee", "Relevés du texte « une journée »"),
                         ("texte_marche", "Relevés du texte « au marché »"),
                         ("texte_village", "Relevés du texte « le village »")):
        data = mots.get(group) or {}
        if not isinstance(data, dict):
            continue
        out += [f"### {title}", ""]
        for sub, rows in data.items():
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                continue
            out += [f"**{sub.replace('_', ' ')}**", "", "| mot | sens |", "|---|---|"]
            out += [f"| `{r['snk']}` | {r.get('fr','')} |" for r in rows if r.get("snk")]
            out.append("")

    total = sum(len(v) if isinstance(v, list) else sum(len(x) for x in v.values() if isinstance(x, list))
                for v in mots.values())
    out += ["---", "",
            f"{len(grammaire['verbes'])} verbes conjugables · "
            f"{len(verbes_ref.get('locuteur', []))} verbes du locuteur en attente · "
            f"{len(verbes_ref.get('sources', []))} verbes relevés dans la littérature · "
            f"environ {total} mots enregistrés."]
    (ROOT / "docs" / "langue" / "lexique.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("docs/langue/lexique.md régénéré")


if __name__ == "__main__":
    main()
