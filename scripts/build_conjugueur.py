"""Exporte les règles du moteur en JSON pour le conjuguer web (docs/conjuguer/)."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    grammaire = yaml.safe_load((ROOT / "data/grammaire/soninke.yaml").read_text(encoding="utf-8"))
    objets = yaml.safe_load((ROOT / "data/grammaire/objets.yaml").read_text(encoding="utf-8"))
    out = ROOT / "docs" / "conjuguer"
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(
        json.dumps({
            "pronoms": grammaire["pronoms"],
            "temps": grammaire["temps"],
            "particules": grammaire["particules"],
            "classes": grammaire["classes"],
            "verbes": grammaire["verbes"],
            "objets": objets.get("objets", []),
            # verbes connus mais pas encore conjugables : pour que la saisie sache les nommer
            "inventaire": [
                {"radical": v.get("radical"), "fr": v.get("fr"), "manque": v.get("manque", "")}
                for section in ("locuteur", "liste", "variantes")
                for v in (yaml.safe_load((ROOT / "data/references/verbes.yaml").read_text(encoding="utf-8"))
                          .get(section) or [])
                if v.get("radical") and v.get("radical") != "?"
            ],
        }, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{out/'data.json'} écrit ({len(grammaire['verbes'])} verbes, {len(grammaire['temps'])} temps)")


if __name__ == "__main__":
    main()
