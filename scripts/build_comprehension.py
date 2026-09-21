"""Analyse les phrases du corpus validé et écrit docs/comprendre/data.json.

La page docs/comprendre.md se contente d'afficher ce résultat : l'analyse est faite
ici, par le moteur Python, jamais réimplémentée en JavaScript.
"""

import json
from pathlib import Path

from snk_engine.understand import AnalysisError, analyze, load_lexicon

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    lex = load_lexicon()
    rows = []
    for path in sorted((ROOT / "corpus" / "valide").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry.get("niveau") != "phrase":
                continue
            try:
                a = analyze(entry["snk"], lex)
            except AnalysisError as exc:
                rows.append({"id": entry["id"], "snk": entry["snk"], "fr_locuteur": entry["fr"],
                             "erreur": str(exc)})
                continue
            rows.append({
                "id": entry["id"], "snk": a.snk, "fr_locuteur": entry["fr"], "fr_moteur": a.fr,
                "confirme": a.confirme, "frame": {k: v for k, v in a.frame.items() if v not in (None, [], False)},
                "notes": list(a.notes),
                "mots": [{"mot": t.raw, "particule": t.particle,
                          "tags": list(t.tags)} for t in a.tokens],
            })
    out = ROOT / "docs" / "comprendre"
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for r in rows if r.get("confirme"))
    print(f"{out/'data.json'} : {len(rows)} phrases, {ok} entièrement comprises")


if __name__ == "__main__":
    main()
