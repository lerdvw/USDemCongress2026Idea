# -*- coding: utf-8 -*-
"""
Build the page from facts.py and the files in web/.

    python3 build.py           write index.html next to this file
    python3 build.py FOLDER    write FOLDER/index.html instead, for hosting

web/page.html holds the words. Wherever they need a fact they carry a
placeholder in double braces, which this script fills in:

    {{ house_seats_for_veto_proof_majority }}
                            a figure from facts.PAGE_FIGURES
    {{ cite: yale_tariff_costs }}
                            a citation of a source in facts.SOURCES; several
                            sources can share one: {{ cite: first, second }}
    {{ senate_race_list }}  the states that elect a senator this year
    {{ source_list }}       the numbered list of every source cited
    {{ stylesheet }}        web/page.css, inlined
    {{ script }}            web/page.js, inlined

Sources are numbered in the order the page first cites them, so adding a
citation never means renumbering by hand. The page that comes out is one
self-contained file that loads nothing from anywhere else. One file travels
with it: web/share-card.png, the picture behind link previews, copied next
to the page.
"""

import html
import os
import re
import shutil
import sys

import facts

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_FOLDER = os.path.join(HERE, "web")
OUTPUT_FILE_NAME = "index.html"

# Matches {{ anything }}; fill_placeholder() works out what the inside means.
PLACEHOLDER = re.compile(r"\{\{\s*(.*?)\s*\}\}")

# Filled in a second pass: the source list needs every citation numbered
# first, and the stylesheet and script go in last so that nothing inside
# them is ever mistaken for a placeholder.
FILLED_IN_SECOND_PASS = ("source_list", "stylesheet", "script")


def read_web_file(file_name):
    """One of the page's files in web/, as text."""
    with open(os.path.join(WEB_FOLDER, file_name), encoding="utf-8") as web_file:
        return web_file.read()


def long_date(day):
    """A date as the page prints it: 2026-11-03 becomes "November 3, 2026"."""
    return f"{day:%B} {day.day}, {day.year}"


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------

class Citations:
    """Hands out source numbers in the order the page first cites each one."""

    def __init__(self):
        self.number_of_source = {}   # source key -> its number on the page

    def number_for(self, source_key):
        if source_key not in facts.SOURCES:
            raise SystemExit(f"build.py: the page cites {source_key!r}, which facts.SOURCES does not list")
        if source_key not in self.number_of_source:
            self.number_of_source[source_key] = len(self.number_of_source) + 1
        return self.number_of_source[source_key]

    def marker(self, source_keys):
        """The superscript [3, 7] that links a claim to its sources."""
        source_numbers = [self.number_for(source_key) for source_key in source_keys]
        links = ", ".join(
            f'<a href="#source-{number}" aria-label="Source {number}">{number}</a>'
            for number in source_numbers
        )
        # The word joiner (U+2060) keeps the marker on the same line as the
        # word or punctuation before it.
        return f'⁠<sup class="cite">[{links}]</sup>'

    def source_list(self):
        """The numbered list of every source cited, for the end of the page."""
        list_items = []
        in_citation_order = sorted(self.number_of_source.items(), key=lambda key_and_number: key_and_number[1])
        for source_key, number in in_citation_order:
            source = facts.SOURCES[source_key]
            published = f", {long_date(source.published)}" if source.published else ""
            # A title that ends in its own period or question mark gets no second one.
            after_title = "" if source.title.endswith((".", "?", "!")) else "."
            list_items.append(
                f'  <li id="source-{number}">'
                f'<a href="{html.escape(source.url)}" target="_blank" rel="noopener noreferrer">'
                f"{html.escape(source.title)}</a>{after_title} {html.escape(source.publisher)}{published}.</li>"
            )
        return '<ol class="source-list">\n' + "\n".join(list_items) + "\n</ol>"


# ---------------------------------------------------------------------------
# Generated blocks
# ---------------------------------------------------------------------------

def senate_race_list():
    """The states electing a senator this year, with special elections marked."""
    list_items = []
    for state, kind_of_race, _ in facts.SENATE_RACES_2026:
        label = state if kind_of_race == "regular" else f"{state} ({kind_of_race})"
        list_items.append(f"<li>{html.escape(label)}</li>")
    return "<ul>" + "".join(list_items) + "</ul>"


def fill_second_pass_placeholder(page, placeholder_name, content):
    """Puts content where {{ placeholder_name }} stands, taking the content literally."""
    pattern = re.compile(r"\{\{\s*" + placeholder_name + r"\s*\}\}")
    # A function as the replacement stops re.sub from reading the backslashes
    # in the stylesheet and script as escape codes.
    return pattern.sub(lambda match: content, page)


# ---------------------------------------------------------------------------
# The page
# ---------------------------------------------------------------------------

def fill_page(template):
    """The finished page, and the Citations that numbered its sources."""
    citations = Citations()

    def fill_placeholder(match):
        placeholder = match.group(1)
        if placeholder in FILLED_IN_SECOND_PASS:
            return match.group(0)
        if placeholder.startswith("cite:"):
            source_keys = [source_key.strip() for source_key in placeholder[len("cite:"):].split(",")]
            return citations.marker(source_keys)
        if placeholder == "senate_race_list":
            return senate_race_list()
        if placeholder in facts.PAGE_FIGURES:
            return html.escape(facts.PAGE_FIGURES[placeholder])
        raise SystemExit(f"build.py: web/page.html asks for {{{{ {placeholder} }}}}, which nothing provides")

    page = PLACEHOLDER.sub(fill_placeholder, template)
    page = fill_second_pass_placeholder(page, "source_list", citations.source_list())
    page = fill_second_pass_placeholder(page, "stylesheet", read_web_file("page.css").strip())
    page = fill_second_pass_placeholder(page, "script", read_web_file("page.js").strip())
    return page, citations


def main():
    output_folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else HERE
    os.makedirs(output_folder, exist_ok=True)

    page, citations = fill_page(read_web_file("page.html"))

    output_path = os.path.join(output_folder, OUTPUT_FILE_NAME)
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(page)
    shutil.copyfile(os.path.join(WEB_FOLDER, facts.SHARE_IMAGE_FILE_NAME),
                    os.path.join(output_folder, facts.SHARE_IMAGE_FILE_NAME))

    page_kilobytes = len(page.encode("utf-8")) / 1024
    print(f"wrote {os.path.relpath(output_path, HERE)}: {page_kilobytes:.0f} KB, "
          f"{len(citations.number_of_source)} of {len(facts.SOURCES)} sources cited")


if __name__ == "__main__":
    main()
