# Veto-Proof 2026

A one-page, mobile-first case for electing a veto-proof Democratic Congress
on Tuesday, November 3, 2026. It makes three asks (register, recruit a
recruiter, vote) and three promises:

- **Facts Found**: subpoenas and sworn answers on the Epstein files, the
  price rises, the Iran war, and apparent bribery that goes unprosecuted.
- **Prices Down**: tariffs refocused on good jobs and lower prices, high-wage
  clean-energy jobs, and a Congress that works for working families before
  billionaires.
- **Peace Sound**: an end to the war with Iran, and a deal that inspectors can
  verify.

Every figure and claim on the page cites a numbered source. The page loads
nothing from other sites: no trackers, no cookies, no fonts or scripts from
elsewhere.

## Published page

https://lerdvw.github.io/USDemCongress2026/

Every push to `main` rebuilds, checks and republishes it through GitHub Pages
(`.github/workflows/pages.yml`).

## Files

| File | What it holds |
|---|---|
| `facts.py` | Every date, figure and source the page shows; derived figures are computed here |
| `web/page.html` | The page's words, with `{{ placeholders }}` for facts and citations |
| `web/page.css`, `web/page.js` | The page's stylesheet and script, which `build.py` inlines |
| `build.py` | Fills the template from `facts.py` and writes `index.html` |
| `check.py` | Sanity checks on the facts, the template and the built page |
| `project_conventions.md` | How this repo is worked on |

## Build

Python 3.9 or later, standard library only. Node is optional: when it is
installed, `check.py` also checks that the script parses.

```bash
python3 build.py
python3 check.py
```

`build.py FOLDER` writes `FOLDER/index.html` instead, ready to host
anywhere that serves static files.

`check.py` also prints how far a veto-proof majority is from today's House
and Senate, worked out from the counts in `facts.py`. The page itself does not
show those counts.
