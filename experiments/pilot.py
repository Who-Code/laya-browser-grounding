"""Pilot: frame- and shadow-DOM-aware page snapshot, interchangeable 'grounders' that pick the element for an
instruction (Laya-MLX, lexical, embedding, local LLM), and an executor that acts through real Playwright handles."""
from __future__ import annotations
import asyncio, math, os, re, sys, time, json, urllib.request
from dataclasses import dataclass, asdict, field
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))

SNAP_JS = r"""() => {
 window.__lp = []; const out = [];
 const clean = t => (t || '').replace(/\s+/g, ' ').trim();
 const vis = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
   return r.width > 2 && r.height > 2 && s.visibility !== 'hidden' && s.display !== 'none' && (s.opacity !== '0' || el.tagName === 'INPUT'); };   // CSS-hidden native inputs are still operable
 const SEL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=checkbox],[role=tab],[role=menuitem],[role=option],[role=switch],[contenteditable=""],[contenteditable=true],[onclick],[tabindex]:not([tabindex="-1"])';
 function* walk(root) { for (const el of root.querySelectorAll('*')) { if (el.matches(SEL)) yield el; if (el.shadowRoot) yield* walk(el.shadowRoot); } }
 const roleOf = el => { const r = el.getAttribute('role'); if (r) return r; const t = el.tagName.toLowerCase();
   if (t === 'a') return 'link'; if (t === 'button' || t === 'summary') return 'button'; if (t === 'select') return 'combobox';
   if (t === 'textarea') return 'textbox'; if (t === 'input') { const ty = (el.type || 'text');
     return ty === 'checkbox' ? 'checkbox' : ty === 'radio' ? 'radio' : (ty === 'submit' || ty === 'button') ? 'button' : 'textbox'; }
   if (el.isContentEditable) return 'textbox'; return 'generic'; };
 const ROW = 'li,tr,[role=row],[role=listitem],article,fieldset,label,[data-card],.card,.example';
 let i = 0;
 for (const el of walk(document)) {
   if (el.disabled || !vis(el)) continue;
   const t = el.tagName.toLowerCase();
   let name = clean(el.getAttribute('aria-label')) || '';
   if (!name && el.getAttribute('aria-labelledby')) name = clean(el.getAttribute('aria-labelledby').split(' ').map(id => document.getElementById(id)?.innerText).join(' '));
   if (!name && el.labels && el.labels.length && t !== 'button') name = clean([...el.labels].map(l => l.innerText.replace(el.value || '', '')).join(' '));
   if (!name && (t === 'input') && (el.type === 'submit' || el.type === 'button')) name = clean(el.value);
   if (!name && t !== 'input' && t !== 'select' && t !== 'textarea') name = clean(el.innerText || el.textContent);
   if (!name) name = clean(el.title || el.placeholder || el.alt || el.querySelector('img')?.alt || '');
   const row = el.closest(ROW) || (el.getRootNode().host && el.getRootNode().host.closest(ROW));
   let ctx = '';
   if (row) { const cl = row.cloneNode(true); cl.querySelectorAll('button,select,input,textarea,script,style').forEach(n => n.remove());
     ctx = clean(cl.textContent); }
   if (!name && ctx && ['checkbox', 'radio', 'switch'].includes(roleOf(el))) name = ctx;   // unlabeled checkbox -> its row text
   if (ctx === name) ctx = '';
   const gt = el.getAttribute('data-gt') || '';
   const info = {i, tag: t, role: roleOf(el), type: el.type || '', name: name.slice(0, 80), ctx: ctx.slice(0, 80),
     ph: el.placeholder || '', gt, id: el.id || '', href: el.getAttribute('href') || '', checked: !!el.checked,
     editable: !!el.isContentEditable, nopts: t === 'select' ? el.options.length : 0};
   window.__lp.push(el); out.push(info); i++;
   if (out.length >= 600) break;
 }
 return out;
}"""

@dataclass
class Cand:
    i: int; frame: int; tag: str; role: str; type: str; name: str; ctx: str; ph: str; gt: str; id: str; href: str
    checked: bool; editable: bool; nopts: int
    depth: int = 0
    @property
    def text(self) -> str:            # what every grounder is allowed to see
        n = self.name or self.ph or ("(unlabeled)")
        return f"{self.role} '{n}'" + (f" in '{self.ctx}'" if self.ctx else "")
    @property
    def label(self) -> str:
        return (self.name or self.ph or f"unlabeled {self.role}")[:60]


class Pilot:
    def __init__(self, page): self.page = page; self.cands: list[Cand] = []

    async def snapshot(self, main_only: bool = False) -> list[Cand]:
        t = time.perf_counter(); out: list[Cand] = []
        for fi, fr in enumerate(self.page.frames):
            if main_only and fi > 0: break
            try:
                items = await fr.evaluate(SNAP_JS)
            except Exception:
                continue
            d, p = 0, fr
            while p.parent_frame: d += 1; p = p.parent_frame
            out += [Cand(frame=fi, depth=d, **it) for it in items]
        self.cands = out; self.snap_ms = (time.perf_counter() - t) * 1000
        return out

    async def handle(self, c: Cand):
        fr = self.page.frames[c.frame]
        return (await fr.evaluate_handle("i => window.__lp[i]", c.i)).as_element()

    async def act(self, c: Cand, instruction: str, option_picker=None):
        t = time.perf_counter(); h = await self.handle(c)
        m = re.search(r"['\"“‘]([^'\"”’]+)['\"”’]", instruction)
        if c.tag == "select":
            opts = await h.evaluate("e => [...e.options].map(o => o.text)")
            pick = await option_picker(instruction, opts) if option_picker else opts[0]
            await h.select_option(label=pick)
        elif c.role == "textbox" and m:
            await h.fill(m.group(1), timeout=2500)
            if re.search(r"press enter|and submit", instruction, re.I): await h.press("Enter")
        else:
            await h.click(timeout=2500)
        self.act_ms = (time.perf_counter() - t) * 1000


# ------------------------------------------------------------------------------------------------ grounders
Q = "Which interface element should be used to carry out this instruction?"

def uniq_labels(cands: list[Cand]) -> dict[str, str]:
    """label -> description, labels made unique by row context (then by ordinal)."""
    labels: dict[str, str] = {}; counts: dict[str, int] = {}
    for c in cands: counts[c.label] = counts.get(c.label, 0) + 1
    for c in cands:
        lab = c.label if counts[c.label] == 1 else f"{c.label} ({c.ctx[:40]})" if c.ctx else c.label
        k = 2
        if lab in labels:
            first = lab; n = counts[c.label]
            labels[f"{first} (1 of {n})"] = labels.pop(first) if first in labels else ""
            lab = f"{c.label} ({k} of {n})"
            while lab in labels: k += 1; lab = f"{c.label} ({k} of {n})"
        labels[lab] = c.text
    return labels

class LayaGrounder:
    name = "laya"
    def __init__(self, brain, tag="laya"): self.brain = brain; self.name = tag
    async def pick(self, instruction, cands):
        if not cands: return {"idx": None, "p": 0.0, "ms": 0.0}
        labels = uniq_labels(cands)
        (o,), ms = await self.brain.choose([instruction], labels, Q)
        idx = list(labels).index(o["choice"])
        return {"idx": idx, "p": o["p"], "ms": ms}

STOP = set("the a an to of on in into for and or with that this is it as at by from click press tap type enter then please".split())
def toks(s): return [w[:6] for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]

class LexicalGrounder:
    name = "lexical"
    async def pick(self, instruction, cands):
        t = time.perf_counter(); q = toks(instruction)
        docs = [toks(c.text) + toks(c.ph) for c in cands]
        df = {}
        for d in docs:
            for w in set(d): df[w] = df.get(w, 0) + 1
        n = max(1, len(docs)); scores = []
        for d, c in zip(docs, cands):
            s = sum(math.log(1 + n / df[w]) for w in set(q) if w in d)
            s += 0.4 * sum(math.log(1 + n / df[w]) for w in set(q) if w in toks(c.name))   # name match counts extra
            scores.append(s)
        if not scores or max(scores) == 0: idx = 0 if cands else None; p = 0.0
        else:
            idx = max(range(len(scores)), key=scores.__getitem__); srt = sorted(scores, reverse=True)
            p = srt[0] / (srt[0] + (srt[1] if len(srt) > 1 else 0) + 1e-9)
        return {"idx": idx, "p": p, "ms": (time.perf_counter() - t) * 1000}

def _ollama(path, body, timeout=120):
    req = urllib.request.Request("http://127.0.0.1:11434" + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

class EmbedGrounder:
    name = "embed(bge-m3)"
    async def pick(self, instruction, cands):
        if not cands: return {"idx": None, "p": 0.0, "ms": 0.0}
        t = time.perf_counter()
        r = await asyncio.to_thread(_ollama, "/api/embed", {"model": "bge-m3", "input": [instruction] + [c.text for c in cands], "keep_alive": "60s"})
        E = r["embeddings"]; dot = lambda a, b: sum(x * y for x, y in zip(a, b))
        nrm = lambda a: math.sqrt(dot(a, a)); q = E[0]
        sims = [dot(q, e) / (nrm(q) * nrm(e) + 1e-9) for e in E[1:]]
        idx = max(range(len(sims)), key=sims.__getitem__); srt = sorted(sims, reverse=True)
        return {"idx": idx, "p": srt[0] - (srt[1] if len(srt) > 1 else 0), "ms": (time.perf_counter() - t) * 1000}

class LLMGrounder:
    def __init__(self, model="qwen3:8b"): self.model = model; self.name = f"llm({model})"
    async def pick(self, instruction, cands):
        if not cands: return {"idx": None, "p": 0.0, "ms": 0.0}
        listing = "\n".join(f"[{k}] {c.text}" for k, c in enumerate(cands))
        prompt = f"Page elements:\n{listing}\n\nInstruction: {instruction}\nWhich element number should be acted on? Answer with only the number."
        t = time.perf_counter()
        r = await asyncio.to_thread(_ollama, "/api/chat", {"model": self.model, "stream": False, "think": False, "keep_alive": "60s",
            "messages": [{"role": "user", "content": prompt}], "options": {"temperature": 0, "num_predict": 8}})
        m = re.search(r"\d+", r["message"]["content"]); idx = int(m.group()) if m else None
        if idx is not None and idx >= len(cands): idx = None
        return {"idx": idx, "p": 1.0, "ms": (time.perf_counter() - t) * 1000}


class PointwiseLayaGrounder:
    """One yes/no (noul) question per candidate, all candidates packed into a single batched forward pass."""
    def __init__(self, brain, tag="laya-point"): self.brain = brain; self.name = tag
    async def pick(self, instruction, cands):
        if not cands: return {"idx": None, "p": 0.0, "ms": 0.0}
        ps, ms = await self.brain.judge_batch([f"Instruction: {instruction}\nElement: {c.text}" for c in cands],
                                              "Is this the element the instruction refers to?")
        idx = max(range(len(ps)), key=ps.__getitem__)
        return {"idx": idx, "p": ps[idx], "ms": ms}
