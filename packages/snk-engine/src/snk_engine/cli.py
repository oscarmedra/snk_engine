"""Interface en ligne de commande : snk-engine stats | validate | generate | push."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from tqdm import tqdm

from .generator import Generator
from .hub import push as hub_push
from .hub import write_card
from .lexicon import Lexicon
from .orthography import Orthography
from .templates import SLOT_RE, load_templates
from .writer import ShardWriter

app = typer.Typer(help="Génération de corpus soninké", no_args_is_help=True)

ConfigOpt = typer.Option(Path("configs/default.yaml"), "--config", "-c", help="Fichier de configuration")


def _load(config: Path):
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    lexicon = Lexicon.from_paths([Path(p) for p in cfg["lexique"]])
    templates = load_templates([Path(p) for p in cfg["gabarits"]])
    ortho_cfg = cfg.get("orthographe") or {}
    ortho = Orthography(ortho_cfg["alphabet"]) if ortho_cfg.get("alphabet") else None
    return cfg, lexicon, templates, ortho


@app.command()
def stats(config: Path = ConfigOpt):
    """Taille du lexique et nombre de phrases distinctes possibles."""
    _, lexicon, templates, _ = _load(config)
    typer.echo(f"Entrées lexicales : {len(lexicon)}")
    for cat, entries in sorted(lexicon.categories.items()):
        typer.echo(f"  {cat:<20} {len(entries)}")
    typer.echo(f"Gabarits : {len(templates)}")
    total = 0
    for t in templates:
        n = t.combinations(lexicon)
        total += n
        typer.echo(f"  {t.id:<30} {n:,}")
    typer.echo(f"Combinaisons max (borne haute) : {total:,}")


@app.command()
def validate(config: Path = ConfigOpt):
    """Vérifie l'orthographe du lexique et la cohérence des gabarits."""
    _, lexicon, templates, ortho = _load(config)
    errors = 0
    if ortho:
        for entries in lexicon.categories.values():
            for e in entries:
                for form, text in e.snk.items():
                    if bad := ortho.invalid_chars(text):
                        errors += 1
                        typer.echo(f"[orthographe] {e.id}.{form} = {text!r} : caractères {sorted(bad)}")
    for t in templates:
        for text, lang in ((t.snk, "snk"), (t.fr, "fr")):
            for m in SLOT_RE.finditer(text or ""):
                try:
                    pool = lexicon.pool(m["cat"], m["tag"])
                    if not pool:
                        raise KeyError(f"aucune entrée pour {m.group(0)}")
                    for e in pool:
                        e.form(lang, m["form"])
                except KeyError as exc:
                    errors += 1
                    typer.echo(f"[gabarit] {t.id} ({lang}) : {exc}")
                    break
    typer.echo("OK" if not errors else f"{errors} erreur(s)")
    raise typer.Exit(code=1 if errors else 0)


@app.command()
def generate(
    n: int = typer.Option(..., "--n", "-n", help="Nombre de phrases à générer"),
    out: Path = typer.Option(Path("output/soninke-corpus"), "--out", "-o"),
    fmt: str = typer.Option("parquet", "--format", "-f", help="parquet ou jsonl"),
    shard_size: int = typer.Option(1_000_000, help="Phrases par fichier"),
    seed: int = typer.Option(42),
    config: Path = ConfigOpt,
):
    """Génère le corpus en fragments + carte de dataset."""
    _, lexicon, templates, ortho = _load(config)
    gen = Generator(lexicon, templates, ortho, seed=seed)
    has_fr = any(t.fr for t in templates)
    with ShardWriter(out, shard_size=shard_size, fmt=fmt) as writer:
        for sample in tqdm(gen.generate(n), total=n, unit="phr"):
            writer.write(sample)
    write_card(out, writer.count, len(templates), len(lexicon), has_fr)
    typer.echo(f"{writer.count:,} phrases → {out} ({len(writer.files)} fichier(s))")
    if gen.rejected_orthography:
        typer.echo(f"Rejetées (orthographe) : {gen.rejected_orthography:,}")
    if writer.count < n:
        typer.echo("⚠ Espace combinatoire épuisé : enrichir le lexique ou les gabarits.")


@app.command()
def push(
    repo_id: str = typer.Argument(..., help="ex. mon-compte/soninke-corpus"),
    out: Path = typer.Option(Path("output/soninke-corpus"), "--out", "-o"),
    public: bool = typer.Option(False, "--public", help="Rendre le dataset public"),
):
    """Publie le dossier généré sur Hugging Face (nécessite `hf auth login`)."""
    url = hub_push(out, repo_id, private=not public)
    typer.echo(url)


@app.command("exporter-verbes")
def exporter_verbes(out: Path = typer.Argument(Path("data/grammaire/verbes.xlsx"))):
    """Écrit les verbes actuels du moteur dans un fichier Excel."""
    from .conjugation import default_engine
    from .verbs_excel import export_verbs

    typer.echo(export_verbs(default_engine(), out))


@app.command("questionnaire-creer")
def questionnaire_creer(
    serie: Path = typer.Argument(..., help="ex. data/questionnaires/serie_02.yaml"),
    out: Path = typer.Option(None, "--out", "-o", help="Excel à produire (défaut : à côté du YAML)"),
):
    """Génère l'Excel de questions à traduire."""
    from .conjugation import default_engine
    from .questionnaire import load_series, write_questionnaire

    from .questionnaire import QuestionnaireError

    series, questions = load_series(serie)
    try:
        path = write_questionnaire(questions, default_engine(), out or serie.with_suffix(".xlsx"))
    except QuestionnaireError as exc:
        typer.echo(f"Refusé : {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Série {series} : {len(questions)} question(s) → {path}")


@app.command("questionnaire-analyser")
def questionnaire_analyser(
    fichier: Path = typer.Argument(..., help="Excel rempli"),
    corpus: Path = typer.Option(Path("data/corpus_valide"), help="Dossier du corpus validé"),
):
    """Compare les traductions au moteur et enregistre les paires validées."""
    from .conjugation import default_engine
    from .questionnaire import analyse, read_answers, save_validated

    engine = default_engine()
    answers = read_answers(fichier, engine)
    results = analyse(answers, engine)
    order = ["à vérifier", "nouveau", "conforme", "sans réponse"]
    for status in order:
        group = [r for r in results if r.status == status]
        if not group:
            continue
        typer.echo(f"\n== {status.upper()} ({len(group)})")
        for r in group:
            q, a = r.answer.question, r.answer
            typer.echo(f"[{q.id}] {q.french}")
            if a.soninke:
                typer.echo(f"    réponse : {a.soninke}")
            if status == "à vérifier":
                typer.echo(f"    moteur  : {' / '.join(r.expected)}")
            if a.description:
                typer.echo(f"    note    : {a.description}")
    series = answers[0].question.id.split("-")[0] if answers else "inconnue"
    path = save_validated(series, answers, corpus)
    typer.echo(f"\nPaires enregistrées → {path}")


@app.command("termes-creer")
def termes_creer(
    serie: Path = typer.Argument(..., help="ex. data/questionnaires/serie_04_termes.yaml"),
    out: Path = typer.Option(None, "--out", "-o"),
):
    """Génère l'Excel des termes à expliquer."""
    from .questionnaire import QuestionnaireError, load_terms, write_terms

    series, terms = load_terms(serie)
    try:
        path = write_terms(series, terms, out or serie.with_suffix(".xlsx"))
    except QuestionnaireError as exc:
        typer.echo(f"Refusé : {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Série {series} : {len(terms)} terme(s) → {path}")


@app.command("generer")
def generer(
    out: Path = typer.Option(Path("output/soninke-corpus"), "--out", "-o"),
    fmt: str = typer.Option("parquet", "--format", "-f", help="parquet ou jsonl"),
    shard_size: int = typer.Option(1_000_000, help="Phrases par fichier"),
    apercu: int = typer.Option(0, "--apercu", help="N'écrit rien : montre N phrases"),
):
    """Génère le corpus à partir du moteur de conjugaison (phrases + traduction)."""
    from .conjugation import default_engine
    from .sentences import generate as generate_sentences
    from .writer import ShardWriter

    engine = default_engine()
    rows = generate_sentences(engine)
    if apercu:
        for i, s in enumerate(rows):
            if i >= apercu:
                break
            typer.echo(f"{s.snk:38} | {s.fr}")
        raise typer.Exit()

    from .generator import Sample

    with ShardWriter(out, shard_size=shard_size, fmt=fmt) as writer:
        for s in rows:
            writer.write(Sample(snk=s.snk, fr=s.fr, template_id=f"{s.verb}:{s.tense}"))
    write_card(out, writer.count, len(engine.tenses), len(engine.verbs), True)
    typer.echo(f"{writer.count:,} phrases → {out} ({len(writer.files)} fichier(s))")


@app.command("conjuguer")
def conjuguer(
    verbe: str = typer.Argument(..., help="ex. dagaer"),
    objet: str = typer.Option(None, "--objet", "-o", help="objet pour les temps qui en prennent"),
):
    """Affiche la conjugaison complète d'un verbe."""
    from .conjugation import ConjugationError, default_engine

    engine = default_engine()
    if verbe not in engine.verbs:
        typer.echo(f"Verbe inconnu. Verbes disponibles : {', '.join(engine.verbs)}", err=True)
        raise typer.Exit(code=1)
    v = engine.verbs[verbe]
    typer.echo(f"{verbe} — {v.french} (radical {v.form}" + (f", forme en -ni {v.gerund}" if v.gerund else "") + ")")
    pronouns = list(engine.pronouns)
    for tense, t in engine.tenses.items():
        obj = objet or ("maro" if t.object else None)
        formes = []
        for p in pronouns:
            try:
                formes.append(engine.conjugate(verbe, p, tense, obj))
            except ConjugationError:
                continue
        if not formes:
            continue
        typer.echo(f"\n{t.label}" + (f" (objet : {obj})" if obj else ""))
        for f in formes:
            typer.echo(f"  {f}")


@app.command("comprendre")
def comprendre(
    texte: str = typer.Argument(..., help="phrase ou texte soninké"),
    detail: bool = typer.Option(False, "--detail", help="montre le tagage et l'assemblage"),
):
    """Traduit un texte soninké en français, en n'affirmant que ce qui est reconnu."""
    from .understand import analyze_text, load_lexicon, render

    analyses = analyze_text(texte, load_lexicon())
    typer.echo(render(analyses))
    if not detail:
        return
    typer.echo("")
    for a in analyses:
        typer.echo(f"{a.snk}\n→ {a.fr}")
        if detail:
            typer.echo("  mots :")
            for t in a.tokens:
                tags = ", ".join(t.tags) or "non reconnu"
                particule = f" (particule {t.particle})" if t.particle else ""
                typer.echo(f"    {t.raw:<16} {tags}{particule}")
            f = a.frame
            typer.echo("  phrase :")
            if f:
                typer.echo(f"    sujet       {f['sujet'] or '—'}" + (f" ({f['personne']})" if f['personne'] else ""))
                typer.echo(f"    temps       {f['temps'] or '—'}")
                typer.echo(f"    objet       {f['objet'] or '—'}")
                typer.echo(f"    verbe       {f['verbe'] or '—'}" + ("" if f["verbe_confirme"] else " (non confirmé)"))
                typer.echo(f"    compléments {', '.join(f['complements']) or '—'}")
            for note in a.notes:
                typer.echo(f"  · {note}")
        typer.echo("")


if __name__ == "__main__":
    app()
