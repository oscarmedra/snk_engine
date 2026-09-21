# Comprendre un texte

Le moteur sait maintenant lire dans l'autre sens : partir d'une phrase soninké et
dire ce qu'elle veut dire en français.

Il ne compare pas la phrase à une liste de phrases connues — cela ne serait pas
comprendre, seulement reconnaître. Il procède en trois étapes, comme un compilateur :

1. **Segmentation** : la phrase est découpée en mots, et la particule collée
   (`n'`, `m'`, `l'`, `ŋ'`, `q'`) est détachée du mot qu'elle accentue.
2. **Tagage** : chaque mot reçoit **toutes** ses catégories possibles — pronom,
   déterminant, marqueur de temps, verbe, mot interrogatif, mot du lexique. Un mot
   ambigu comme `xa` (vous / où) garde ses deux étiquettes.
3. **Assemblage** : les catégories sont replacées dans l'ordre que décrit la
   grammaire — sujet, marqueur, objet, verbe, compléments — et c'est la position qui
   tranche les ambiguïtés.

**Un mot qu'aucune donnée ne couvre devient le mot `unknown`** dans la traduction,
jamais un mot français choisi au hasard. Chaque remplacement est expliqué en note.

## Essayer

```bash
uv run snk-engine comprendre "ake n'di maro ke n'yiga"
```
```bash
uv run snk-engine comprendre "ake n'daga saxa daru" --detail
```

En Python :

```python
from snk_engine.understand import analyze

analyze("ake n'di maro ke n'yiga").fr      # il a mangé le riz
```

## Sur les phrases du corpus

Le tableau ci-dessous applique l'analyseur aux phrases traduites par le locuteur.
La colonne « moteur » est ce que l'analyseur comprend ; la colonne « locuteur » est
la traduction de référence. L'écart entre les deux montre exactement ce qui manque
encore.

<div id="snk-comp">
  <div class="snk-controls">
    <label>Phrase <select id="snk-sent"></select></label>
    <label><input type="checkbox" id="snk-only-ok"> seulement celles entièrement comprises</label>
  </div>
  <div id="snk-out">Chargement…</div>
</div>

<style>
#snk-comp .snk-controls { display: flex; gap: 1.5rem; align-items: center; flex-wrap: wrap; margin-bottom: .8rem; }
#snk-comp select { padding: .3rem .5rem; max-width: 30rem; }
#snk-comp .snk-line { font-size: 1.1rem; font-weight: 600; margin: .4rem 0; }
#snk-comp table { width: 100%; }
#snk-comp .snk-tags { opacity: .7; font-size: .85rem; }
#snk-comp .snk-note { font-size: .85rem; opacity: .75; }
#snk-comp .snk-unknown { color: #c62828; font-weight: 600; }
</style>

<script>
(async function () {
  const rows = await (await fetch('data.json')).json();
  const sel = document.getElementById('snk-sent');
  const onlyOk = document.getElementById('snk-only-ok');
  const out = document.getElementById('snk-out');

  const fill = () => {
    const list = rows.filter(r => !onlyOk.checked || r.confirme);
    sel.innerHTML = '';
    list.forEach((r, i) => sel.add(new Option(`${r.id} — ${r.snk.slice(0, 60)}`, rows.indexOf(r))));
    render();
  };

  const render = () => {
    const r = rows[sel.value];
    if (!r) { out.innerHTML = '<p>Aucune phrase.</p>'; return; }
    const mark = t => t.replace(/unknown/g, '<span class="snk-unknown">unknown</span>');
    let html = `<p class="snk-line">${r.snk}</p>`;
    html += `<table><tbody>
      <tr><td>moteur</td><td>${r.fr_moteur ? mark(r.fr_moteur) : '<em>' + (r.erreur || '—') + '</em>'}</td></tr>
      <tr><td>locuteur</td><td>${r.fr_locuteur}</td></tr></tbody></table>`;
    if (r.mots) {
      html += '<p class="snk-tags">' + r.mots.map(m =>
        `<b>${m.mot}</b> : ${(m.tags || []).join(', ') || 'non reconnu'}`).join(' · ') + '</p>';
    }
    if (r.frame && Object.keys(r.frame).length) {
      html += '<table><tbody>' + Object.entries(r.frame).map(([k, v]) =>
        `<tr><td>${k}</td><td>${Array.isArray(v) ? v.join(', ') : v}</td></tr>`).join('') + '</tbody></table>';
    }
    (r.notes || []).forEach(n => html += `<p class="snk-note">· ${n}</p>`);
    out.innerHTML = html;
  };

  sel.onchange = render;
  onlyOk.onchange = fill;
  fill();
})();
</script>

## Ce qu'il ne sait pas encore faire

- **une phrase simple à la fois** : pas de subordonnée, pas de phrase coordonnée ;
- **le sens français → soninké** n'est pas construit : le moteur produit des phrases
  à partir des règles ([le corpus](corpus.md)), mais ne traduit pas un texte français ;
- **les ambiguïtés** comme `xa` (vous / où) sont tranchées par la position, et
  signalées en note quand le doute subsiste ;
- **le vocabulaire limite tout** : la plupart des phrases du corpus contiennent
  encore des mots absent des données, donc beaucoup d'`unknown`.
