# Comprendre un texte

Écris en soninké : la traduction française apparaît pendant que tu tapes.

<div id="snk-comp">
  <div class="snk-panes">
    <div class="snk-pane">
      <div class="snk-head">Soninké</div>
      <textarea id="snk-input" rows="6" placeholder="Écris une phrase… par exemple : ake n'di maro ke n'yiga" disabled></textarea>
    </div>
    <div class="snk-pane">
      <div class="snk-head">Français <span id="snk-status">chargement du moteur…</span></div>
      <div id="snk-out" class="snk-result"></div>
    </div>
  </div>
  <div class="snk-controls">
    <label>Exemple du corpus <select id="snk-ex"><option value="">—</option></select></label>
    <label><input type="checkbox" id="snk-detail"> voir le détail de l'analyse</label>
  </div>
  <div id="snk-detail-out"></div>
</div>

<style>
#snk-comp .snk-panes { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 700px) { #snk-comp .snk-panes { grid-template-columns: 1fr; } }
#snk-comp .snk-pane { border: 1px solid var(--md-default-fg-color--lightest); border-radius: 8px;
  overflow: hidden; display: flex; flex-direction: column; min-height: 11rem; }
#snk-comp .snk-head { padding: .45rem .8rem; font-size: .8rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .04em; border-bottom: 1px solid var(--md-default-fg-color--lightest);
  display: flex; justify-content: space-between; gap: 1rem; }
#snk-comp #snk-status { font-weight: 400; text-transform: none; letter-spacing: 0; opacity: .7; }
#snk-comp textarea { flex: 1; border: 0; resize: vertical; padding: .8rem; font-size: 1.15rem;
  font-family: inherit; background: transparent; color: var(--md-default-fg-color); outline: none; }
#snk-comp .snk-result { flex: 1; padding: .8rem; font-size: 1.15rem; background: var(--md-code-bg-color); }
#snk-comp .snk-result p { margin: 0 0 .5rem; }
#snk-comp .snk-controls { display: flex; gap: 1.5rem; align-items: center; flex-wrap: wrap; margin: .8rem 0; font-size: .85rem; }
#snk-comp select { max-width: 22rem; }
#snk-comp .snk-unknown { color: #c62828; }
#snk-comp .snk-ok { color: #2e7d32; }
#snk-comp .snk-partial { color: #b26a00; }
#snk-comp .snk-ref { font-size: .85rem; opacity: .75; }
#snk-comp .snk-block { margin-bottom: 1.2rem; font-size: .85rem; }
#snk-comp .snk-note { opacity: .8; margin: .1rem 0; }
</style>

<script src="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js"></script>
<script>
(async function () {
  const input = document.getElementById('snk-input');
  const exSel = document.getElementById('snk-ex');
  const detail = document.getElementById('snk-detail');
  const out = document.getElementById('snk-out');
  const detailOut = document.getElementById('snk-detail-out');
  const status = document.getElementById('snk-status');
  const esc = s => String(s).replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));
  let reference = null;

  const examples = await (await fetch('exemples.json')).json();
  examples.forEach((e, i) => exSel.add(new Option(`${e.id} — ${e.snk.slice(0, 50)}`, i)));

  // le vrai moteur Python, exécuté dans le navigateur
  const pyodide = await loadPyodide();
  await pyodide.loadPackage('pyyaml');
  const bundle = await (await fetch('bundle.json')).json();
  for (const [path, content] of Object.entries(bundle)) {
    const full = '/snk/' + path;
    pyodide.FS.mkdirTree(full.slice(0, full.lastIndexOf('/')));
    pyodide.FS.writeFile(full, content);
  }
  pyodide.runPython(`
import sys, json
sys.path.insert(0, "/snk/packages/snk-engine/src")
from snk_engine.understand import analyze_text, load_lexicon, AnalysisError
LEX = load_lexicon()

def comprendre(texte):
    try:
        res = analyze_text(texte, LEX)
    except AnalysisError as exc:
        return json.dumps({"erreur": str(exc)})
    return json.dumps([{
        "snk": a.snk, "fr": a.fr, "confirme": a.confirme, "notes": list(a.notes),
        "frame": {k: v for k, v in a.frame.items() if v not in (None, [], False)},
        "mots": [{"mot": t.raw, "tags": list(t.tags)} for t in a.tokens],
    } for a in res], ensure_ascii=False)
`);
  const comprendre = pyodide.globals.get('comprendre');
  input.disabled = false;
  status.textContent = '';
  input.focus();

  function run() {
    const text = input.value.trim();
    if (!text) { out.innerHTML = ''; detailOut.innerHTML = ''; status.textContent = ''; return; }
    const res = JSON.parse(comprendre(text));
    if (res.erreur) {
      out.innerHTML = '<p class="snk-unknown">…</p>';
      status.innerHTML = '<span class="snk-partial">rien de reconnu</span>';
      detailOut.innerHTML = detail.checked ? `<p class="snk-note">${esc(res.erreur)}</p>` : '';
      return;
    }
    out.innerHTML = res.map(a =>
      `<p>${esc(a.fr).replace(/unknown/g, '<span class="snk-unknown">unknown</span>')}</p>`).join('')
      + (reference && res.length === 1 ? `<p class="snk-ref">locuteur : ${esc(reference)}</p>` : '');
    const all = res.every(a => a.confirme);
    status.innerHTML = all ? '<span class="snk-ok">✔ entièrement compris</span>'
                           : '<span class="snk-partial">◐ compréhension partielle</span>';
    detailOut.innerHTML = !detail.checked ? '' : res.map(a => {
      let h = `<div class="snk-block"><b>${esc(a.snk)}</b><br>`;
      h += a.mots.map(m => `<b>${esc(m.mot)}</b> : ${esc(m.tags.join(', ') || 'non reconnu')}`).join(' · ');
      h += '<table><tbody>' + Object.entries(a.frame).map(([k, v]) =>
        `<tr><td>${esc(k)}</td><td>${esc(Array.isArray(v) ? v.join(', ') : v)}</td></tr>`).join('') + '</tbody></table>';
      a.notes.forEach(n => h += `<p class="snk-note">· ${esc(n)}</p>`);
      return h + '</div>';
    }).join('');
  }

  // comme un traducteur en ligne : on traduit pendant la frappe
  let timer = null;
  input.addEventListener('input', () => {
    reference = null;
    exSel.value = '';
    clearTimeout(timer);
    timer = setTimeout(run, 250);
  });
  exSel.onchange = () => {
    const e = examples[exSel.value];
    if (!e) return;
    input.value = e.snk;
    reference = e.fr;
    run();
  };
  detail.onchange = run;
})();
</script>

Le moteur met quelques secondes à se charger la première fois : c'est le moteur
Python lui-même qui tourne dans ton navigateur, pas une imitation. Ce que tu lis
ici est donc exactement ce que donnerait la commande :

```bash
uv run snk-engine comprendre "ake n'di maro ke n'yiga" --detail
```

## Comment il comprend

1. **Segmentation** : la phrase est découpée en mots, et la particule collée
   (`n'`, `m'`, `l'`, `ŋ'`, `q'`) est détachée du mot qu'elle accentue.
2. **Tagage** : chaque mot reçoit **toutes** ses catégories possibles — pronom,
   déterminant, marqueur de temps, verbe, mot interrogatif, mot du lexique. Un mot
   ambigu comme `xa` (vous / où) garde ses deux étiquettes.
3. **Assemblage** : les catégories sont replacées dans l'ordre de la grammaire —
   sujet, marqueur, objet, verbe, compléments — et la position tranche les
   ambiguïtés. Quand un marqueur ouvre plusieurs temps, le moteur reconjugue chaque
   candidat et garde celui qui redonne la phrase.

**Un mot qu'aucune donnée ne couvre devient `unknown`**, jamais un mot français
choisi au hasard. Chaque remplacement est expliqué dans le détail de l'analyse.

## Ce qu'il ne sait pas encore faire

- **une phrase simple à la fois** : pas de subordonnée, pas de phrase coordonnée ;
- **le vocabulaire limite tout** : un nom absent des données produit un `unknown` ;
- **les ambiguïtés** comme `xa` sont tranchées par la position, et signalées ;
- **le sens français → soninké** n'est pas construit.
