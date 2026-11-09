(() => {
  // UI audit: how hard is this page for a text-based element picker? Read-only, sends nothing anywhere.
  const SEL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=checkbox],[role=tab],[role=menuitem],[role=option],[role=switch],[contenteditable=""],[contenteditable=true],[onclick],[tabindex]:not([tabindex="-1"])';
  const r = {url: location.href, iframes: 0, iframesCrossOrigin: 0, openShadowRoots: 0, canvas: 0, interactive: 0, withName: 0, iconOnly: 0, withTestId: 0, grids: [], names: {}};
  const clean = t => (t || '').replace(/\s+/g, ' ').trim();
  const visible = el => { const b = el.getBoundingClientRect(), s = getComputedStyle(el); return b.width > 2 && b.height > 2 && s.visibility !== 'hidden' && s.display !== 'none'; };
  function scan(root) {
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) { r.openShadowRoots++; scan(el.shadowRoot); }
      const tag = el.tagName.toLowerCase();
      if (tag === 'canvas' && visible(el)) r.canvas++;
      if (tag === 'iframe') { r.iframes++; try { if (el.contentDocument) scan(el.contentDocument); else r.iframesCrossOrigin++; } catch (e) { r.iframesCrossOrigin++; } }
      const role = el.getAttribute('role');
      if (tag === 'table' || role === 'grid' || role === 'treegrid' || role === 'table') {
        const cells = el.querySelectorAll('td,th,[role=gridcell],[role=cell]').length;
        r.grids.push({cells, ariaRows: el.getAttribute('aria-rowcount') || null, rendered: el.querySelectorAll('tr,[role=row]').length});
      }
      if (el.matches && el.matches(SEL) && visible(el)) {
        r.interactive++;
        const name = clean(el.getAttribute('aria-label') || (el.labels && [...el.labels].map(l => l.innerText).join(' ')) || el.innerText || el.value || el.title || el.placeholder || el.alt);
        if (name) { r.withName++; r.names[name] = (r.names[name] || 0) + 1; } else r.iconOnly++;
        if (el.hasAttribute('data-testid') || el.hasAttribute('data-test') || el.hasAttribute('data-cy') || el.hasAttribute('data-qa')) r.withTestId++;
      }
    }
  }
  scan(document);
  r.maxGridCells = Math.max(0, ...r.grids.map(g => g.cells));
  r.virtualizedGrids = r.grids.filter(g => g.ariaRows && +g.ariaRows > g.rendered).length;
  r.duplicateNames = Object.entries(r.names).filter(([, n]) => n >= 5).sort((a, b) => b[1] - a[1]).slice(0, 8);
  delete r.names; r.grids = r.grids.length;
  r.verdict = [
    r.interactive > 40 ? 'many interactive elements (' + r.interactive + '): pre-filter needed (Laya weak above ~40 candidates)' : 'candidate count is in Laya\'s comfortable range',
    r.iconOnly / Math.max(1, r.interactive) > 0.2 ? 'many unlabeled/icon-only controls: add aria-labels' : 'most controls have a text name',
    r.canvas ? 'canvas present: not visible to DOM-based pickers' : 'no canvas', r.iframesCrossOrigin ? 'cross-origin iframes: need frame-aware tooling' : 'no cross-origin iframes',
    r.withTestId ? 'data-testid present on ' + r.withTestId + ' elements' : 'no data-testid attributes'];
  console.table({...r, duplicateNames: JSON.stringify(r.duplicateNames), verdict: r.verdict.join(' | ')});
  return r;
})();
