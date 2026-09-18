"""Exporte les règles du moteur en JSON pour le playground web (docs/playground/)."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    grammaire = yaml.safe_load((ROOT / "data/grammaire/soninke.yaml").read_text(encoding="utf-8"))
    objets = yaml.safe_load((ROOT / "data/grammaire/objets.yaml").read_text(encoding="utf-8"))
    out = ROOT / "docs" / "playground"
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(
        json.dumps({
            "pronoms": grammaire["pronoms"],
            "temps": grammaire["temps"],
            "particules": grammaire["particules"],
            "classes": grammaire["classes"],
            "verbes": grammaire["verbes"],
            "objets": objets.get("objets", []),
        }, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{out/'data.json'} écrit ({len(grammaire['verbes'])} verbes, {len(grammaire['temps'])} temps)")


if __name__ == "__main__":
    main()
