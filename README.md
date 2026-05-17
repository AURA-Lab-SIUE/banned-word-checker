# Banned Word Checker for Federal Grants

A research-grade tool that implements the **leaked NSF 3-stage decision tree** for reviewing federal grant text for flagged DEIA and other Executive Order language. Built by the **AURA Lab** (Avatars, Users, Relationships, and Affect) at **Southern Illinois University Edwardsville**.

Ships as **two frontends sharing one engine**:

- **Static web tool** (`web/`) — runs entirely in the browser, embeddable on any site. All processing is local; no text leaves your computer.
- **Streamlit app** (`app.py`) — for internal pipeline use and Streamlit Community Cloud deployment.

## What's new in v2

This is a substantial rewrite of the original tool. Changes:

| Area | v1 | v2 |
|---|---|---|
| Logic | Flat word-frequency scan of whole document | 3-stage decision tree (Title/Abstract → Project Summary → Project Description) with early-exit |
| Output | Count table | Category 1 (clean) / Category 3 (flagged), per-stage breakdown, context snippets |
| Word list | Hardcoded Python set, 290 terms | Canonical `data/banned-words.json` (447 terms) with provenance per term |
| Frontends | Streamlit only | Streamlit + static HTML/JS (both load same JSON) |
| Output modes | One | Plain (FLAGGED/CLEAN) and Reviewer (Category 1/3) toggle |
| Privacy | Server-side parsing | Static-web version parses files entirely in-browser |

## The decision tree

Faithful to the leaked NSF source:

```
Start
  → Stage 1: TITLE or ABSTRACT contains flagged term?
      → Yes: Category 3 (Retain flag, DEIA/EO language found). END.
      → No: continue
  → Stage 2: PROJECT SUMMARY contains flagged term?
      → Yes: Category 3. END.
      → No: continue
  → Stage 3: PROJECT DESCRIPTION contains flagged term?
      → Yes: Category 3. END.
      → No: Category 1 (Clean; reviewer adds comment explaining "no"). END.
```

Early-exit means a hit in the title produces a shorter report than a hit in the description. This mirrors how a reviewer would actually triage applications.

## Word list

`data/banned-words.json` is the single source of truth, loaded identically by the Python engine and the JS port. Each term carries a `source` tag:

- **`leaked`** — appears in the leaked NSF decision-tree word list
- **`existing`** — added defensively from a community-compiled list (banned-word-checker v1)
- **`both`** — appears in both

447 terms total at the time of the v2 release. The leaked NSF subset is the authoritative signal; the existing-only terms over-flag relative to NSF and are kept as defensive checks for the writer.

To update the list, edit `scripts/merge_wordlists.py` and re-run it:

```bash
python scripts/merge_wordlists.py
```

## Running the static web tool

The static tool is the recommended deployment for the lab website. It needs no server, no Python, and no uploads — everything runs in the browser via PDF.js and mammoth.js.

**Local preview:**
```bash
cd banned-word-checker
python -m http.server 8000
# open http://localhost:8000/web/index.html
```

**Deploy to GitHub Pages or any static host:** push the repo (or just `web/` and `data/`) to a Pages-enabled branch. The page loads `../data/banned-words.json` relative to itself, so keep the folder structure intact.

**Embed on the AURA Lab site:** copy `web/index.html`, `web/checker.js`, `web/styles.css`, `web/aura-mark.svg`, and `data/banned-words.json` to the lab site, preserving the relative path from `index.html` to `../data/banned-words.json`. Or link out to it as a separate page.

The static page adopts the AURA Lab v2 design system: dark canvas (`#0E0E12`), violet primary accent (`#7C3AED`), amber for flag signals (`#F59E0B`), Fraunces + Instrument Sans + JetBrains Mono typography, and the same `card` / `pill` / `link-underline` / `divider` patterns used on the lab site. Tokens live in `web/styles.css` and should stay in sync with `aura-lab-siue.github.io/src/styles/tokens.css` if either side changes.

## Running the Streamlit app

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# or: source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```

The Streamlit app uses the same `core.py` engine as the JS port, so any change to the word list or the decision-tree logic affects both frontends.

### Streamlit Community Cloud deployment

Push to GitHub, point Streamlit at `app.py`, deploy. The `assets/` and `data/` folders need to be committed for the app to find logos and the word list.

## Project structure

```
banned-word-checker/
├── core.py                       # Python engine: decision tree + section detection
├── app.py                        # Streamlit frontend
├── data/
│   └── banned-words.json         # Canonical word list (shared by both frontends)
├── web/
│   ├── index.html                # Static page
│   ├── checker.js                # JS port of core.py
│   └── styles.css                # Page styling
├── scripts/
│   └── merge_wordlists.py        # Regenerate banned-words.json from sources
├── assets/                       # Logos and brand assets
├── .streamlit/
│   └── config.toml               # Theme for Streamlit app
├── requirements.txt
├── LICENSE
└── README.md
```

## Privacy

The static web tool processes everything locally. Files dragged into the upload box are parsed in your browser using PDF.js and mammoth.js. No grant text is sent to any server. This matters because federal grant drafts often contain unpublished research plans and PII.

The Streamlit app also processes files locally on whichever machine is running it, but if you deploy it to Streamlit Community Cloud, your text passes through Streamlit's servers. For sensitive drafts, prefer the static web tool or run Streamlit locally.

## Provenance and intent

The decision tree was reconstructed from a leaked NSF process diagram. The leaked word list was OCR-extracted and cleaned (de-duplicated, run-together lines split, OCR splits like "hate" + "speech" reassembled into "hate speech").

This tool exists so grant writers can self-check their drafts against the same logic federal reviewers appear to use, **before** submission, with enough lead time to revise. Whether you agree or disagree with the underlying policy is separate from whether you need to navigate it. The tool simply makes the process transparent.

## License

MIT. See `LICENSE`.

## Contact

AURA Lab @ SIUE — [aura-lab-siue.github.io](https://aura-lab-siue.github.io)

Project: [github.com/AURA-Lab-SIUE/banned-word-checker](https://github.com/AURA-Lab-SIUE/banned-word-checker)
