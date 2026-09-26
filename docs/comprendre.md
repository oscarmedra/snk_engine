---
description: "Traducteur soninké-français et français-soninké : écris une phrase, l'analyse grammaticale et la traduction s'affichent pendant la saisie."
---

# Traduire

Écris en soninké ou en français : la traduction apparaît pendant que tu tapes.
Le bouton ⇄ inverse le sens.

<div id="snk-comp">
  <div class="snk-langs">
    <span id="snk-from">Soninké</span>
    <button id="snk-swap" title="Inverser le sens" disabled>⇄</button>
    <span id="snk-to">Français</span>
  </div>
  <div class="snk-panes">
    <div class="snk-pane">
      <div class="snk-head" id="snk-head-in">Soninké</div>
      <textarea id="snk-input" rows="6" placeholder="Écris une phrase… par exemple : ake n'di maro ke n'yiga" disabled></textarea>
    </div>
    <div class="snk-pane">
      <div class="snk-head"><span id="snk-head-out">Français</span> <span id="snk-status">chargement du moteur…</span></div>
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
#snk-comp .snk-langs { display: flex; align-items: center; justify-content: center; gap: 1.2rem;
  margin-bottom: .8rem; font-weight: 600; }
#snk-comp .snk-langs span { min-width: 7rem; text-align: center; }
#snk-comp #snk-swap { border: 1px solid var(--md-default-fg-color--lighter); background: transparent;
  color: var(--md-default-fg-color); border-radius: 50%; width: 2.4rem; height: 2.4rem;
  font-size: 1.2rem; cursor: pointer; }
#snk-comp #snk-swap:hover { background: var(--md-default-fg-color--lightest); }
#snk-comp #snk-swap[disabled] { opacity: .4; cursor: wait; }
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

  const examples = await (await fetch('exemples.json', {cache: 'no-cache'})).json();
  examples.forEach((e, i) => exSel.add(new Option(`${e.id} — ${e.snk.slice(0, 50)}`, i)));

  // le vrai moteur Python, exécuté dans le navigateur
  const pyodide = await loadPyodide();
  await pyodide.loadPackage('pyyaml');
  const bundle = await (await fetch('bundle.json', {cache: 'no-cache'})).json();
  for (const [path, content] of Object.entries(bundle)) {
    const full = '/snk/' + path;
    pyodide.FS.mkdirTree(full.slice(0, full.lastIndexOf('/')));
    pyodide.FS.writeFile(full, content);
  }
  pyodide.runPython(`
import sys, json
sys.path.insert(0, "/snk/packages/snk-engine/src")
from snk_engine.understand import analyze_text, load_lexicon, render
from snk_engine.translate_fr import translate_text, render as render_snk
LEX = load_lexicon()

def traduire(texte):
    res = translate_text(texte, LEX)
    return json.dumps({"traduction": render_snk(res), "propositions": [{
        "snk": t.fr, "fr": t.snk, "confirme": t.confirme, "notes": list(t.notes),
        "frame": {k: v for k, v in t.frame.items() if v not in (None, [], False)},
        "mots": [],
    } for t in res]}, ensure_ascii=False)

def comprendre(texte):
    res = analyze_text(texte, LEX)
    return json.dumps({"traduction": render(res), "propositions": [{
        "snk": a.snk, "fr": a.fr, "confirme": a.confirme, "notes": list(a.notes),
        "frame": {k: v for k, v in a.frame.items() if v not in (None, [], False)},
        "mots": [{"mot": t.raw, "tags": list(t.tags)} for t in a.tokens],
    } for a in res]}, ensure_ascii=False)
`);
  const comprendre = pyodide.globals.get('comprendre');
  const traduire = pyodide.globals.get('traduire');
  const swap = document.getElementById('snk-swap');
  let fromSoninke = true;
  const labels = () => {
    const [a, b] = fromSoninke ? ['Soninké', 'Français'] : ['Français', 'Soninké'];
    document.getElementById('snk-from').textContent = a;
    document.getElementById('snk-to').textContent = b;
    document.getElementById('snk-head-in').textContent = a;
    document.getElementById('snk-head-out').textContent = b;
    input.placeholder = fromSoninke ? "Écris une phrase… par exemple : ake n'di maro ke n'yiga"
                                    : "Écris une phrase… par exemple : il a mangé le riz";
  };
  swap.onclick = () => {
    // comme un traducteur en ligne : la traduction devient le texte à traduire
    const translated = out.querySelector('p') ? out.querySelector('p').innerText : '';
    fromSoninke = !fromSoninke;
    labels();
    if (translated && !translated.includes('[unknown]')) input.value = translated;
    reference = null;
    run();
  };
  swap.disabled = false;
  input.disabled = false;
  status.textContent = '';
  input.focus();

  function run() {
    const text = input.value.trim();
    if (!text) { out.innerHTML = ''; detailOut.innerHTML = ''; status.textContent = ''; return; }
    const data = JSON.parse((fromSoninke ? comprendre : traduire)(text));
    const res = data.propositions;
    out.innerHTML = `<p>${esc(data.traduction).replace(/\[unknown\]/g, '<span class="snk-unknown">[unknown]</span>')}</p>`
      + (reference ? `<p class="snk-ref">locuteur : ${esc(reference)}</p>` : '');
    const all = res.every(a => a.confirme);
    status.innerHTML = all ? '<span class="snk-ok">✔ entièrement compris</span>'
                           : '<span class="snk-partial">◐ compréhension partielle</span>';
    detailOut.innerHTML = !detail.checked ? '' : res.map(a => {
      let h = `<div class="snk-block"><b>${esc(a.snk)}</b><br>`;
      h += (a.mots || []).map(m => `<b>${esc(m.mot)}</b> : ${esc(m.tags.join(', ') || 'non reconnu')}`).join(' · ');
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
    input.value = fromSoninke ? e.snk : e.fr;
    reference = fromSoninke ? e.fr : e.snk;
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

## Du soninké vers le français

1. **Segmentation** : la phrase est découpée en mots, et la particule collée
   (`n'`, `m'`, `l'`, `ŋ'`, `q'`) est détachée du mot qu'elle accentue.
2. **Tagage** : chaque mot reçoit **toutes** ses catégories possibles — pronom,
   déterminant, marqueur de temps, verbe, mot interrogatif, mot du lexique. Un mot
   ambigu comme `xa` (vous / où) garde ses deux étiquettes.
3. **Assemblage** : les catégories sont replacées dans l'ordre de la grammaire —
   sujet, marqueur, objet, verbe, compléments — et la position tranche les
   ambiguïtés. Quand un marqueur ouvre plusieurs temps, le moteur reconjugue chaque
   candidat et garde celui qui redonne la phrase.

**Le moteur tente toujours une traduction**, quel que soit le texte. Ce qu'aucune
donnée ne couvre devient `[unknown]` — jamais un mot français choisi au hasard —
et plusieurs mots incompris d'affilée ne donnent qu'une seule marque. Chaque
remplacement est expliqué dans le détail de l'analyse.

Le texte est découpé en phrases, puis en propositions sur les virgules, les
points-virgules et les deux-points : chaque proposition est analysée séparément.
Si aucune structure n'y est reconnue, elle est traduite mot à mot.

## Du français vers le soninké

Le moteur sait déjà produire le français de chaque verbe confirmé, à chaque
personne et à chaque temps. Il en construit l'index inverse — « il a mangé » →
manger, passé, 3ᵉ personne —, reconnaît ensuite l'objet et les compléments dans le
lexique, puis **produit le soninké avec le moteur de conjugaison lui-même**. Un
passage français qu'aucune donnée ne couvre devient `[unknown]`.

```bash
uv run snk-engine traduire "il a mangé le riz"          # ake n'di maro ke n'yiga
```

Les deux sens se vérifient l'un l'autre : une phrase traduite en français puis
retraduite en soninké redonne la phrase de départ.

## Ce qu'il ne sait pas encore faire

- **pas de subordonnée** : les propositions sont traduites l'une après l'autre ;
- **le vocabulaire limite tout** : un nom absent des données produit un `unknown` ;
- **les ambiguïtés** comme `xa` sont tranchées par la position, et signalées ;
- **en français → soninké**, seuls les verbes confirmés sont reconnus, et le
  pronom produit est celui de la série longue (`ake` plutôt que `a`).
