# Conjuguer un verbe

Choisis un verbe : le tableau donne sa conjugaison à tous les temps.

Les formes **confirmées** par le locuteur sont en gras ; les **propositions**, que les
règles produisent mais que personne n'a encore validées, sont en orange. Elles n'entrent
pas dans le corpus tant qu'elles n'ont pas été relues.
Les règles appliquées ici sont exactement celles du moteur, exportées depuis
`data/grammaire/` (`scripts/build_conjugueur.py`).

<div id="snk-app">
  <div class="snk-controls">
    <label>Verbe <input id="snk-verb" list="snk-verbs" autocomplete="off"
      placeholder="manger, daga, écrire…" size="24"></label>
    <datalist id="snk-verbs"></datalist>
    <label>Objet <select id="snk-obj"></select></label>
    <label>Pronoms <select id="snk-serie">
      <option value="tous">les deux séries</option>
      <option value="longue">longs (nke, anke…)</option>
      <option value="diminutif">diminutifs (n, an…)</option>
    </select></label>
  </div>
  <p id="snk-about"></p>
  <div id="snk-out">Chargement…</div>
</div>

<style>
#snk-app .snk-controls { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: .5rem; }
#snk-app select, #snk-app input { padding: .3rem .5rem; font: inherit; }
#snk-app .snk-absent { color: #c62828; }
#snk-app .snk-inventaire { color: #b26a00; }
#snk-app h3 { margin: 1.2rem 0 .3rem; font-size: .95rem; text-transform: uppercase; letter-spacing: .04em; opacity: .75; }
#snk-app table { width: 100%; }
#snk-app td.snk-form { font-weight: 600; }
#snk-app td.snk-propose { color: #b26a00; font-weight: 400; }
#snk-app td.snk-none { opacity: .45; font-style: italic; font-weight: 400; }
#snk-app .snk-note { font-size: .85rem; opacity: .7; }
</style>

<script>
(async function () {
  const D = await (await fetch('data.json', {cache: 'no-cache'})).json();
  const verbSel = document.getElementById('snk-verb');
  const objSel = document.getElementById('snk-obj');
  const serieSel = document.getElementById('snk-serie');
  const out = document.getElementById('snk-out');
  const about = document.getElementById('snk-about');

  // --- mêmes règles que le moteur Python ---------------------------------
  const particleFor = (word) => {
    const i = (word || '').slice(0, 1).toLowerCase();
    const p = D.particules;
    if (p.par_initiale[i]) return p.par_initiale[i];
    if ((p.a_confirmer || []).includes(i)) return null;   // non confirmé
    return p.defaut;
  };

  const rulesFor = (verb, tense) => {
    const list = [];
    const own = (D.verbes[verb].conjugaison || {})[tense];
    if (own) list.push(own);
    const cls = D.classes[D.verbes[verb].classe];
    if (cls && cls.conjugaison[tense]) list.push(cls.conjugaison[tense]);
    return list;
  };

  const conjugate = (verb, pronoun, tense, obj) => {
    const v = D.verbes[verb], t = D.temps[tense];
    const rules = rulesFor(verb, tense);
    if (!rules.length) return null;
    const persons = new Set(rules.flatMap(r => (r.personnes || []).concat(Object.keys(r.formes || {}))));
    const confirmed = persons.has(pronoun);   // sinon : la règle propose, sans confirmation
    if (t.objet && !obj) return null;

    let form = null;
    for (const r of rules) {
      const bySubject = Object.assign({}, r.exceptions || {}, r.formes || {});
      if (bySubject[pronoun] !== undefined) { form = bySubject[pronoun]; break; }
    }
    if (form === null) {
      for (const r of rules) if (r.forme !== undefined && r.forme !== null) { form = r.forme; break; }
    }
    if (form === null) form = t.objet && v.forme_objet ? v.forme_objet : v.forme;
    if (t.objet && v.forme_objet) form = v.forme_objet;
    if (form === null || form === undefined) return null;
    if (form.includes('{forme}')) form = form.replace('{forme}', v.forme);
    if (form.includes('{gerondif}')) { if (!v.gerondif) return null; form = form.replace('{gerondif}', v.gerondif); }

    if (t.particule_verbe && form) {
      const p = particleFor(form);
      if (p === null) return null;
      form = p + form;
    }
    let words = [t.marqueur, t.objet ? obj : null, form, t.suffixe].filter(Boolean).join(' ');
    if (t.particule && (D.particules.personnes || []).includes(pronoun)) {
      const p = particleFor(words);
      if (p === null) return null;
      words = p + words;
    }
    return {forme: `${pronoun} ${words}`, confirme: confirmed};
  };

  // --- affichage ----------------------------------------------------------
  const pronounsOf = serie => D.pronoms
    .filter(p => serie === 'tous' || p.serie === serie)
    .map(p => p.forme).filter((v, i, a) => a.indexOf(v) === i);

  // la saisie accepte le français comme le soninké
  const list = document.getElementById('snk-verbs');
  const entries = Object.entries(D.verbes);
  entries.forEach(([name, v]) => {
    list.appendChild(Object.assign(document.createElement('option'),
      {value: v.fr, label: `${v.fr} — ${v.forme}`}));
    list.appendChild(Object.assign(document.createElement('option'), {value: v.forme, label: `${v.forme} — ${v.fr}`}));
  });
  const norm = t => (t || '').trim().toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const findVerb = text => {
    const q = norm(text);
    if (!q) return null;
    const exact = entries.find(([name, v]) => [name, v.forme, v.fr].some(x => norm(x) === q));
    if (exact) return exact[0];
    const partial = entries.find(([name, v]) => [name, v.forme, v.fr].some(x => norm(x).startsWith(q)));
    return partial ? partial[0] : null;
  };
  const inInventory = text => (D.inventaire || []).find(v =>
    [v.radical, v.fr].some(x => norm(x) === norm(text)));
  verbSel.value = entries[0][1].fr;
  objSel.add(new Option('(aucun)', ''));
  D.objets.forEach(o => objSel.add(new Option(`${o.snk} — ${o.fr}`, o.snk)));

  const render = () => {
    const verb = findVerb(verbSel.value);
    if (!verb) {
      const known = inInventory(verbSel.value);
      about.innerHTML = '';
      out.innerHTML = known
        ? `<p class="snk-inventaire"><b>${known.radical}</b> (${known.fr}) est connu du projet, mais pas encore
           conjugable : il manque ${known.manque || 'des formes'}. Il apparaît dans le lexique, pas dans le moteur.</p>`
        : `<p class="snk-absent">« ${verbSel.value} » est inconnu du moteur.</p>
           <p>Écris un verbe en français (manger) ou son radical soninké (yige). La liste déroulante
           propose les ${entries.length} verbes connus.</p>`;
      return;
    }
    const v = D.verbes[verb];
    const objOptions = D.objets.filter(o => !o.verbes || o.verbes.includes(verb));
    const current = objSel.value;
    objSel.innerHTML = '';
    objSel.add(new Option('(aucun)', ''));
    objOptions.forEach(o => objSel.add(new Option(`${o.snk} — ${o.fr}`, o.snk)));
    if (objOptions.some(o => o.snk === current)) objSel.value = current;
    objSel.disabled = !v.transitif;
    const obj = objSel.value || (v.transitif ? (objOptions[0] || {}).snk : null);

    about.innerHTML = `<span class="snk-note">radical <b>${v.forme}</b>` +
      (v.gerondif ? ` · forme en -ni <b>${v.gerondif}</b>` : '') +
      (v.forme_objet ? ` · avec objet <b>${v.forme_objet}</b>` : '') + '</span>';

    let html = '';
    for (const [tense, t] of Object.entries(D.temps)) {
      const rows = pronounsOf(serieSel.value).map(p => [p, conjugate(verb, p, tense, obj)]);
      if (!rows.some(r => r[1])) continue;
      html += `<h3>${t.nom}</h3><table><tbody>` + rows.map(([p, f]) =>
        `<tr><td>${p}</td><td class="${!f ? 'snk-none' : f.confirme ? 'snk-form' : 'snk-propose'}">` +
        `${f ? f.forme : 'forme inconnue'}${f && !f.confirme ? ' <small>(proposition)</small>' : ''}</td></tr>`
      ).join('') + '</tbody></table>';
    }
    out.innerHTML = html || '<p>Aucune forme confirmée pour ce verbe.</p>';
  };

  serieSel.onchange = render;
  verbSel.oninput = render;
  verbSel.onchange = render;
  objSel.onchange = render;
  render();
})();
</script>

!!! note "Confirmé, proposé, inconnu"
    **En gras** : la forme vient d'une phrase donnée par le locuteur, ou d'une règle
    qu'il a validée.

    **En orange** : la règle prévoit cette forme, mais personne ne l'a encore vérifiée.
    C'est une proposition à corriger, pas une affirmation — et elle reste hors du corpus.

    **Vide** : même les règles ne suffisent pas, faute d'une forme du verbe (par exemple
    sa forme en -ni) ou d'une particule confirmée pour cette initiale.
