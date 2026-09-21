"""Prépare la page « Comprendre un texte » (docs/comprendre.md).

La page exécute le vrai moteur Python dans le navigateur, grâce à Pyodide : ce script
rassemble les modules nécessaires et les données dans docs/comprendre/bundle.json, que
la page recopie dans le système de fichiers de Pyodide. Il n'y a donc qu'une seule
implémentation de l'analyseur, celle qui est testée.

Il écrit aussi docs/comprendre/exemples.json : les phrases du corpus validé, proposées
comme exemples à analyser.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ["__init__.py", "conjugation.py", "french.py", "orthography.py", "understand.py"]
DATA = ["grammaire/soninke.yaml", "grammaire/objets.yaml",
        "references/verbes.yaml", "references/mots.yaml"]


def main() -> None:
    out = ROOT / "docs" / "comprendre"
    out.mkdir(parents=True, exist_ok=True)

    files = {}
    src = ROOT / "packages" / "snk-engine" / "src" / "snk_engine"
    for name in MODULES:
        files[f"packages/snk-engine/src/snk_engine/{name}"] = (src / name).read_text(encoding="utf-8")
    for name in DATA:
        files[f"data/{name}"] = (ROOT / "data" / name).read_text(encoding="utf-8")
    (out / "bundle.json").write_text(json.dumps(files, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    examples = []
    for path in sorted((ROOT / "corpus" / "valide").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry.get("niveau") == "phrase":
                examples.append({"id": entry["id"], "snk": entry["snk"], "fr": entry["fr"]})
    (out / "exemples.json").write_text(json.dumps(examples, ensure_ascii=False, indent=1), encoding="utf-8")

    old = out / "data.json"
    if old.exists():
        old.unlink()
    print(f"{out}/bundle.json : {len(files)} fichiers ; exemples.json : {len(examples)} phrases")


if __name__ == "__main__":
    main()
