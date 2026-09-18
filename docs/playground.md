# Playground

Choisis un verbe : le tableau donne sa conjugaison à tous les temps confirmés.
Les règles appliquées ici sont exactement celles du moteur, exportées depuis
`data/grammaire/` (`scripts/build_playground.py`).

<div id="snk-app">
  <div class="snk-controls">
    <label>Verbe <select id="snk-verb"></select></label>
    <label>Objet <select id="snk-obj"></select></label>
  </div>
  <p id="snk-about"></p>
  <div id="snk-out">Chargement…</div>
</div>

<style>
#snk-app .snk-controls { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: .5rem; }
#snk-app select { padding: .3rem .5rem; }
#snk-app h3 { margin: 1.2rem 0 .3rem; font-size: .95rem; text-transform: uppercase; letter-spacing: .04em; opacity: .75; }
#snk-app table { width: 100%; }
#snk-app td.snk-form { font-weight: 600; }
#snk-app td.snk-none { opacity: .45; font-style: italic; font-weight: 400; }
#snk-app .snk-note { font-size: .85rem; opacity: .7; }
</style>

<script>
(async function () {
  const D = await (await fetch('data.json')).json();
  const verbSel = document.getElementById('snk-verb');
  const objSel = document.getElementById('snk-obj');
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
    if (!persons.has(pronoun)) return null;
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
    return `${pronoun} ${words}`;
  };

  // --- affichage ----------------------------------------------------------
  const pronouns = D.pronoms.map(p => p.forme).filter((v, i, a) => a.indexOf(v) === i);

  Object.entries(D.verbes).forEach(([name, v]) =>
    verbSel.add(new Option(`${name} — ${v.fr}`, name)));
  objSel.add(new Option('(aucun)', ''));
  D.objets.forEach(o => objSel.add(new Option(`${o.snk} — ${o.fr}`, o.snk)));

  const render = () => {
    const verb = verbSel.value;
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
      const rows = pronouns.map(p => [p, conjugate(verb, p, tense, obj)]);
      if (!rows.some(r => r[1])) continue;
      html += `<h3>${t.nom}</h3><table><tbody>` + rows.map(([p, f]) =>
        `<tr><td>${p}</td><td class="${f ? 'snk-form' : 'snk-none'}">${f || 'non confirmé'}</td></tr>`
      ).join('') + '</tbody></table>';
    }
    out.innerHTML = html || '<p>Aucune forme confirmée pour ce verbe.</p>';
  };

  verbSel.onchange = render;
  objSel.onchange = render;
  render();
})();
</script>

!!! note "Pourquoi certaines cases disent « non confirmé »"
    Le moteur ne produit que ce que le locuteur a validé. Une case vide n'est pas un
    oubli : c'est une forme qu'on n'a pas encore recueillie, et qu'il serait faux
    d'inventer.
