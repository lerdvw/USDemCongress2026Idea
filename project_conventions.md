# Project conventions — USDemCongress2026

How this repo is worked on, by a person or by Claude Code. Borrowed from
USAWarsAnalyses. The folder-wide `CodingProjects/CLAUDE.md` loads only on the
Mac, so the rules that must hold everywhere are repeated here.

## Git

- Commit straight to `main`. Use a branch only when the owner says a piece of
  work is on one.
- Local commits need no permission once work is at a sensible point. Pushing,
  opening pull requests and anything else outward-facing need an explicit
  request.

## Commit messages

- **Subject:** short and imperative, naming the change (`Add the Senate
  races list`).
- **Description:** 28 words or fewer, after a blank line. Count them; do not
  round down.
- **No `Co-Authored-By:` trailers** unless the author explicitly asks for one,
  including for AI assistants.
- Any other trailer goes below the description and does not count toward the
  limit.

## Working on the page

- `facts.py` is the single source of truth for every date, figure and source
  the page shows. The words live in `web/page.html`; `build.py` fills in the
  facts and writes `index.html`. Never hand-edit a generated file.
- Never type a derived figure (a sum, difference, seat count or date worked
  out from others) into the page. Compute it in `facts.py` from its inputs;
  `check.py` fails if one is typed into the template.
- Run `python3 build.py` and then `python3 check.py` after every change and
  before every commit.
- Every figure and factual claim cites a source. A blank beats a guess: leave
  a claim out when no reliable source supports it, and where sources
  disagree, record each reading next to its source in `facts.py`.
- Voting rules differ by state. Link to official tools (vote.gov and the
  states' own sites) rather than restating deadlines or ID rules on the page.
- Generated pages are not committed; build them when needed.

## Backups on the Mac

A global git hook archives all of `~/CodingProjects` to iCloud after every
commit and keeps the newest 50 archives. Before landing a long run of commits
in one go, ask the owner whether to skip it for all but the last
(`git -c core.hooksPath=/dev/null commit ...`), so the run does not push out
older archives.
