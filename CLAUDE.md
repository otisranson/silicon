# CLAUDE.md — Phosphor

This file is read by Claude Code at session start. It is the source of truth for project state, decisions, and next steps. Update it after each meaningful session.

---

## What This Project Is

`Phosphor` — a single-file, browser-based stack-machine calculator with a
live gate-network visualization. Type an arithmetic/bitwise expression;
it's tokenized, converted to postfix, and executed one instruction at a
time against an 8-slot, 8-bit memory stack. Each `PUSH` and each op
(`+ - *` and `AND`/`OR`/`XOR`) is animated in a Canvas panel as a gate
diagram — a ripple-carry adder for `+`/`-`, a bitwise gate row for the
logic ops — with genuinely computed inputs/outputs per keystroke, not a
canned animation. Styled as a green-phosphor terminal (Share Tech Mono,
dark background, `#2aff88` on near-black).

Stack: plain HTML + inline CSS + vanilla JS. No framework, no build step,
no server, no dependencies. Everything lives in `phosphor.html`.

---

## Project History

This repo started (2026-07-30) as `silicon` — a Python/GTK4/Cairo desktop
app that rendered a real-time CPU die visualizer (per-core transistor
grid driven by live `psutil` load data). That version was scaffolded
end-to-end but only `metrics.py` was ever actually run; `renderer.py` and
`silicon.py` were never executed against a real GTK4 display before the
project pivoted.

On 2026-08-04 the project pivoted to `Phosphor`: the Python/GTK4 code
(`silicon/` — `silicon.py`, `renderer.py`, `metrics.py`) and
`requirements.txt` were deleted, and `phosphor.html` — a from-scratch,
different concept (stack-machine calculator, not a CPU visualizer) — is
now the entire project. The `silicon` → `Phosphor` naming carries no
functional continuity beyond the shared green-phosphor visual aesthetic
and the general spirit of "make normally-invisible computation visible."

The "real-time logic gate panel" idea captured below under Scope Ideas
predates the pivot and was originally scoped as an addition to the CPU
die visualizer. `phosphor.html`'s gate-network panel is a spiritual
descendant of that idea (live-computed gate diagrams from real inputs,
not canned animation) but stands on its own now, decoupled from CPU
metrics entirely.

**Resolved (2026-08-04):** the GitHub repo was renamed
`otisranson/silicon` → `otisranson/Phosphor`, and the local `origin`
remote was repointed to `https://github.com/otisranson/Phosphor.git` to
match. Local project directory, this file, and the GitHub repo name are
now all consistent.

---

## Repo Structure (current)

```
Phosphor/
├── CLAUDE.md
├── README.md
├── LICENSE           (GPLv3)
├── .gitignore
└── phosphor.html     — everything: markup, CSS, and all JS
```

---

## Current State

- [x] Pivoted from the `silicon` GTK4 CPU visualizer to `Phosphor`, a
  single-file HTML/JS stack-machine calculator (2026-08-04).
- [x] Old Python project (`silicon/`, `requirements.txt`) removed from
  the working tree. **Not yet committed** — `git status` at pivot time
  showed the deletions staged as unstaged changes plus `phosphor.html`
  untracked; nothing committed to `master` yet as of this session.
- [x] `.gitignore` simplified — Python-specific entries (`__pycache__/`,
  `*.pyc`, `.venv/`, `venv/`) removed since there's no Python left.
- [x] `LICENSE` relicensed from Apache 2.0 to GPLv3 (2026-08-04), at the
  user's request. Copied verbatim from this machine's
  `/usr/share/common-licenses/GPL-3` (the canonical FSF text Debian/Ubuntu
  ships) rather than reproduced from memory, since the GPL explicitly
  disallows redistributing an altered copy of the license document
  itself. No per-file GPL header boilerplate added to `phosphor.html` —
  just the root `LICENSE` file, matching how the previous Apache 2.0
  license was applied in this repo.
- [x] `README.md` rewritten to describe `phosphor.html` (was describing
  the GTK4 app).
- [x] `phosphor.html` — implemented (by the user, outside this session):
  tokenizer + shunting-yard-style postfix conversion (`tokenize`,
  `toPostfix`, `buildInstrs`), stack machine (`sPush`/`sPop` against an
  8-slot `sData` array), Canvas-based gate-network renderer
  (`makeBitwiseLayout`, `makeAdderLayout`, `makePushLayout`), a small
  phase-based animation engine (`animate()`), and DOM wiring for the
  stack panel and expression input. **Not runtime-tested by Claude this
  session** — only read/analyzed, never opened in a browser.
- [x] Pivot committed (`27e92bc`, 2026-08-04) and pushed to `origin/master`.
- [x] GitHub repo renamed `otisranson/silicon` → `otisranson/Phosphor`;
  local `origin` remote repointed to match.
- [x] `screenshots/screenshot.png` added and linked from `README.md` —
  shows a real run (`PUSH 3 · PUSH 8 · *` → `24`), which confirms
  `phosphor.html` does actually run correctly in a browser (tokenizer,
  postfix conversion, gate animation, and stack rendering all visibly
  working). Only one example run confirmed this way, not the edge cases
  in Next Task below.

---

## Scope Ideas / Follow-ups

Not scheduled, not built — just captured so they aren't lost.

- **(Pre-pivot, CPU-visualizer-era) Real-time logic gate panel
  (2026-07-30).** Originally: user wanted a small illustrative gate
  circuit near the CPU die whose inputs were derived from live
  `metrics.py` signals (load threshold crossings, frequency deltas, L3
  flash-pulse booleans) and whose outputs were genuinely computed each
  frame. This idea is now superseded/absorbed by `phosphor.html`'s gate
  network, which does exactly this pattern (real inputs → genuinely
  computed gate outputs, not canned animation) but for stack-machine
  arithmetic instead of CPU load. Kept here for lineage; no longer
  actionable as originally scoped since the CPU visualizer it was meant
  to attach to no longer exists in this repo.

---

## Next Task

Exercise `phosphor.html`'s edge cases in a browser — the screenshot
confirms the happy path (`PUSH 3 · PUSH 8 · *`) works, but nobody has
checked: empty-stack `POP` (op with no operands pushed yet — `sPop()`
returns `0` rather than erroring, confirm that's the desired behavior),
deeply nested parens, stack overflow past 8 pushes (`sPush` clamps `sp`
at `STACK_SIZE - 1`, silently overwriting the top slot rather than
erroring — confirm that's desired), and mixed word/symbol operators
(`9 XOR 14` vs `9 ^ 14`).

---

## Working Conventions

- Update the "Current State" checklist and add a dated session note here
  at the end of every session.
- This file was rewritten during the `silicon` → `Phosphor` pivot
  (2026-08-04) without ever running `phosphor.html` in a browser — treat
  the "Not runtime-tested" note above as load-bearing until it's updated
  to say otherwise.
