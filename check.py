# -*- coding: utf-8 -*-
"""
Sanity checks for the facts and the page built from them.

    python3 build.py && python3 check.py

Prints a summary, then every failed check; exits with status 1 if any
failed. If index.html has not been built yet, the checks on it are skipped.
"""

import calendar
import os
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from html.parser import HTMLParser

import facts

HERE = os.path.dirname(os.path.abspath(__file__))
FAILED = []

# Matches {{ anything }} in the template, as build.py does.
PLACEHOLDER = re.compile(r"\{\{\s*(.*?)\s*\}\}")

# Placeholders build.py fills itself rather than from facts.PAGE_FIGURES.
BUILT_BY_BUILD_PY = {"senate_race_list", "source_list", "stylesheet", "script"}

US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
}


def check(ok, message):
    """Record a failure; the run carries on, so every failure gets listed."""
    if not ok:
        FAILED.append(message)


def read_file(relative_path):
    with open(os.path.join(HERE, relative_path), encoding="utf-8") as text_file:
        return text_file.read()


# ---------------------------------------------------------------------------
# The facts
# ---------------------------------------------------------------------------

def tuesday_after_first_monday_in_november(year):
    """Election Day is the Tuesday after the first Monday in November (2 U.S.C. 7)."""
    first_of_november = date(year, 11, 1)
    days_until_first_monday = (0 - first_of_november.weekday()) % 7   # Monday is weekday 0
    return first_of_november + timedelta(days=days_until_first_monday + 1)


def election_day():
    """Both election days the page relies on follow the rule."""
    check(facts.ELECTION_DAY == tuesday_after_first_monday_in_november(facts.ELECTION_DAY.year),
          "ELECTION_DAY is not the Tuesday after the first Monday in November")
    check(facts.ELECTION_DAY_2024 == tuesday_after_first_monday_in_november(2024),
          "ELECTION_DAY_2024 is not the Tuesday after the first Monday in November 2024")
    check(facts.FACTS_CHECKED_ON < facts.ELECTION_DAY, "FACTS_CHECKED_ON is not before Election Day")
    print(f"election day    {facts.ELECTION_DAY:%A} {facts.ELECTION_DAY.day} {facts.ELECTION_DAY:%B %Y}")


def veto_proof_targets():
    """Each target is the smallest number of seats that makes two-thirds of its chamber."""
    for chamber, seats_in_chamber, target in (
        ("House", facts.HOUSE_SEATS, facts.HOUSE_SEATS_FOR_VETO_PROOF_MAJORITY),
        ("Senate", facts.SENATE_SEATS, facts.SENATE_SEATS_FOR_VETO_PROOF_MAJORITY),
    ):
        # Whole-number arithmetic, independent of how facts.py worked it out.
        check(3 * target >= 2 * seats_in_chamber, f"{chamber}: {target} seats fall short of two-thirds")
        check(3 * (target - 1) < 2 * seats_in_chamber, f"{chamber}: {target - 1} seats would already be two-thirds")
        print(f"veto-proof      {chamber} {target} of {seats_in_chamber}")


def senate_races():
    """Every state named once, in order, and the count is the class up this year plus the specials."""
    states = [state for state, kind_of_race, party_holding_seat in facts.SENATE_RACES_2026]
    kinds = [kind_of_race for state, kind_of_race, party_holding_seat in facts.SENATE_RACES_2026]
    parties = [party_holding_seat for state, kind_of_race, party_holding_seat in facts.SENATE_RACES_2026]
    check(len(states) == len(set(states)), "a state appears twice in SENATE_RACES_2026")
    check(states == sorted(states), "SENATE_RACES_2026 is not in alphabetical order")
    check(set(states) <= US_STATES, f"not states: {sorted(set(states) - US_STATES)}")
    check(set(kinds) <= {"regular", "special"}, "a Senate race is neither regular nor special")
    check(set(parties) <= {"D", "R", "I"}, "a Senate seat is held by a party other than D, R or I")
    regular_races = kinds.count("regular")
    special_races = kinds.count("special")
    check(regular_races == facts.SENATE_CLASS_UP_IN_2026_SEATS,
          f"{regular_races} regular Senate races, but the class up this year has {facts.SENATE_CLASS_UP_IN_2026_SEATS} seats")
    check(regular_races + special_races == facts.SENATE_RACE_COUNT, "SENATE_RACE_COUNT does not add up")
    print(f"senate races    {facts.SENATE_RACE_COUNT} ({regular_races} regular, {special_races} special)")


def ceiling_of_two_thirds(seats_in_chamber):
    """Two-thirds of a chamber, rounded up, in whole-number arithmetic."""
    return -(-2 * seats_in_chamber // 3)


def months_by_counting(earlier_day, later_day):
    """Complete months from one day to a later one, counted a month at a time."""
    complete_months = 0
    year, month = earlier_day.year, earlier_day.month
    while True:
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        days_in_month = calendar.monthrange(year, month)[1]
        monthly_anniversary = date(year, month, min(earlier_day.day, days_in_month))
        if monthly_anniversary > later_day:
            return complete_months
        complete_months += 1


# How the page writes a small count at the start of a sentence.
NUMBER_NAMES = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight",
                9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen",
                16: "Sixteen", 17: "Seventeen", 18: "Eighteen", 19: "Nineteen", 20: "Twenty"}


def days_phrase(count):
    """A span of days as the page writes it, from the number names above: "one day", "nine days"."""
    return NUMBER_NAMES[count].lower() + (" day" if count == 1 else " days")


def cents(amount):
    """A dollar amount rounded to the cent with Decimal, as text: 4.4137 gives "$4.41"."""
    return "$" + str(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def distance_to_veto_proof():
    """Print how many seats Democrats would have to gain for two-thirds, and whether this year's races allow it."""
    senate_caucus_now = facts.SENATE_DEMOCRATS_NOW + facts.SENATE_INDEPENDENTS_NOW
    check(senate_caucus_now + facts.SENATE_REPUBLICANS_NOW == facts.SENATE_SEATS,
          "today's Senate parties do not add up to the whole Senate")
    check(facts.HOUSE_DEMOCRATS_NOW + facts.HOUSE_REPUBLICANS_NOW + facts.HOUSE_INDEPENDENTS_NOW
          + facts.HOUSE_VACANCIES_NOW == facts.HOUSE_SEATS, "today's House parties and vacancies do not add up to 435")

    seats_up_by_party = {}
    for state, kind_of_race, party_holding_seat in facts.SENATE_RACES_2026:
        seats_up_by_party[party_holding_seat] = seats_up_by_party.get(party_holding_seat, 0) + 1
    senate_seats_to_gain = facts.SENATE_SEATS_FOR_VETO_PROOF_MAJORITY - senate_caucus_now
    house_seats_to_gain = facts.HOUSE_SEATS_FOR_VETO_PROOF_MAJORITY - facts.HOUSE_DEMOCRATS_NOW
    # Democrats can only gain Senate seats that are on the ballot and held by someone else.
    check(senate_seats_to_gain <= seats_up_by_party.get("R", 0),
          "a veto-proof Senate cannot be won this year: it needs more seats than Republicans have up")
    print(f"to veto-proof   Senate: Democrats and allies hold {senate_caucus_now}, so reaching "
          f"{facts.SENATE_SEATS_FOR_VETO_PROOF_MAJORITY} takes {senate_seats_to_gain} of the "
          f"{seats_up_by_party.get('R', 0)} Republican seats up, while holding all "
          f"{seats_up_by_party.get('D', 0)} of their own")
    print(f"                House: Democrats hold {facts.HOUSE_DEMOCRATS_NOW}, so reaching "
          f"{facts.HOUSE_SEATS_FOR_VETO_PROOF_MAJORITY} takes {house_seats_to_gain} more")


def derived_figures():
    """Each derived figure shows what its inputs give, worked out again here in a different way."""
    recomputed = {
        "house_seats_for_veto_proof_majority": str(ceiling_of_two_thirds(facts.HOUSE_SEATS)),
        "senate_seats_for_veto_proof_majority": str(ceiling_of_two_thirds(facts.SENATE_SEATS)),
        "senate_race_count": str(facts.SENATE_CLASS_UP_IN_2026_SEATS
                                 + [kind for state, kind, party in facts.SENATE_RACES_2026].count("special")),
        "months_since_four_to_five_weeks_remark": NUMBER_NAMES[months_by_counting(facts.FOUR_TO_FIVE_WEEKS_REMARK_DAY,
                                                                                  facts.FACTS_CHECKED_ON)],
        "days_from_swiss_gifts_to_tariff_deal": NUMBER_NAMES[
            facts.SWISS_TARIFF_DEAL_DAY.toordinal() - facts.SWISS_GIFTS_DAY.toordinal()].lower(),
        "milton_donations_total": "$" + str((Decimal(facts.MILTON_DONATIONS_TO_TRUMP_47_DOLLARS[0])
                                             + Decimal(facts.MILTON_DONATIONS_TO_TRUMP_47_DOLLARS[1]))
                                            .scaleb(-6).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) + " million",
        "milton_restitution_sought": "$" + str(Decimal(str(facts.MILTON_RESTITUTION_SOUGHT_MILLIONS))
                                               .quantize(Decimal("1"), rounding=ROUND_HALF_UP)) + " million",
        "months_from_milton_donations_to_pardon": NUMBER_NAMES[months_by_counting(facts.MILTON_DONATIONS_LAST_DAY,
                                                                                  facts.MILTON_PARDON_DAY)],
        "days_from_war_start_to_threat_hearing": NUMBER_NAMES[
            facts.THREAT_HEARING_DAY.toordinal() - facts.IRAN_WAR_START.toordinal()],
        "months_from_midnight_hammer_to_war": NUMBER_NAMES[months_by_counting(facts.MIDNIGHT_HAMMER_DAY,
                                                                              facts.IRAN_WAR_START)].lower(),
        "days_from_ultimatum_to_war": days_phrase(facts.IRAN_WAR_START.toordinal() - facts.ULTIMATUM_DAY.toordinal()),
        "days_war_came_before_shortest_deadline": days_phrase(
            (facts.ULTIMATUM_DAY + timedelta(days=facts.ULTIMATUM_SHORTEST_DAYS)).toordinal() - facts.IRAN_WAR_START.toordinal()),
        "iran_war_us_wounded": str(facts.IRAN_WAR_US_KILLED_OR_WOUNDED - facts.IRAN_WAR_US_DEATHS),
        "iran_war_cost_billions": str(Decimal(str(facts.IRAN_WAR_COST_THROUGH_SEPTEMBER_3_BILLIONS))
                                      + Decimal(str(facts.IRAN_WAR_EXTRA_FUEL_BILLIONS))),
        "gas_price_today": cents(facts.GAS_PRICE_TODAY_DOLLARS),
        "gas_price_year_ago": cents(facts.GAS_PRICE_YEAR_AGO_DOLLARS),
    }
    check(set(recomputed) == set(facts.DERIVED_FIGURE_NAMES),
          "check.py and facts.DERIVED_FIGURE_NAMES list different derived figures")
    for figure_name, value_from_inputs in recomputed.items():
        shown = facts.PAGE_FIGURES.get(figure_name)
        check(shown == value_from_inputs, f"{figure_name} shows {shown!r}, but its inputs give {value_from_inputs!r}")
    print(f"derived figures {len(recomputed)} worked out again")


def comparisons():
    """The comparisons the page makes in words still hold for the figures in facts.py."""
    iran_2020_override_votes_cast = facts.IRAN_2020_OVERRIDE_VOTE_YEAS + facts.IRAN_2020_OVERRIDE_VOTE_NAYS
    comparisons_in_words = [
        # (does it hold?, what the page says)
        (facts.CLEAN_ENERGY_INVESTMENT_CANCELLED_BILLIONS > facts.CLEAN_ENERGY_INVESTMENT_ANNOUNCED_BILLIONS,
         "more clean-energy investment was cancelled than announced"),
        (facts.CLEAN_ENERGY_JOBS_CANCELLED > facts.CLEAN_ENERGY_JOBS_ANNOUNCED,
         "more clean-energy jobs were cancelled than announced"),
        (3 * facts.IRAN_2020_OVERRIDE_VOTE_YEAS < 2 * iran_2020_override_votes_cast,
         "the 2020 Iran override fell short of two-thirds"),
        (facts.SENATE_IRAN_VOTE_JUNE_23_YEAS > facts.SENATE_IRAN_VOTE_JUNE_23_NAYS,
         "the Senate agreed to the June resolution"),
        (facts.SENATE_IRAN_VOTE_SEPTEMBER_24_YEAS < facts.SENATE_IRAN_VOTE_SEPTEMBER_24_NAYS,
         "the September resolution failed in the Senate"),
        (facts.LOWEST_TENTH_YEARLY_CHANGE_DOLLARS < 0 < facts.HIGHEST_TENTH_YEARLY_CHANGE_DOLLARS,
         "the lowest income tenth loses and the highest gains"),
        (facts.PUBLIC_INTEGRITY_LAWYERS_SEPTEMBER_2025 < facts.PUBLIC_INTEGRITY_LAWYERS_START_2025,
         "the Public Integrity Section shrank in 2025"),
        ((facts.IRAN_WAR_START - facts.MEDIATOR_BREAKTHROUGH_DAY).days == 1,
         "the strikes began the day after the mediator's announcement"),
        (facts.MIDNIGHT_HAMMER_DAY < facts.IRAN_WAR_START < facts.THREAT_HEARING_DAY,
         "the June 2025 strikes came before the war, and the threat hearing after it began"),
        (facts.ULTIMATUM_DAY < facts.MEDIATOR_BREAKTHROUGH_DAY < facts.IRAN_WAR_START,
         "the ultimatum came before the mediator's announcement, and the strikes after both"),
        (facts.ULTIMATUM_SHORTEST_DAYS < facts.ULTIMATUM_LONGEST_DAYS
         and facts.IRAN_WAR_START < facts.ULTIMATUM_DAY + timedelta(days=facts.ULTIMATUM_SHORTEST_DAYS),
         "the strikes came before even the ultimatum's shorter deadline"),
        (facts.SWISS_TARIFF_AFTER_DEAL_PERCENT < facts.SWISS_TARIFF_BEFORE_DEAL_PERCENT,
         "the Swiss deal cut tariffs"),
        (facts.IRAN_WAR_US_DEATHS < facts.IRAN_WAR_US_KILLED_OR_WOUNDED,
         "more troops were killed or wounded than died, so some were wounded"),
        (facts.SWISS_GIFTS_DAY < facts.SWISS_TARIFF_DEAL_DAY,
         "the Swiss gifts came before the tariff deal"),
        (len(facts.MILTON_DONATIONS_TO_TRUMP_47_DOLLARS) == 2
         and facts.MILTON_DONATIONS_TOTAL_DOLLARS > 1_800_000,
         "the Miltons' two donations came to more than $1.8 million"),
        (facts.MILTON_DONATIONS_LAST_DAY < facts.ELECTION_DAY_2024 < facts.MILTON_PARDON_DAY,
         "the Miltons gave before the 2024 election, and the pardon came after it"),
    ]
    for holds, what_the_page_says in comparisons_in_words:
        check(holds, f"the page says {what_the_page_says}, but the figures in facts.py disagree")
    holding = sum(holds for holds, _ in comparisons_in_words)
    print(f"comparisons     {holding} of {len(comparisons_in_words)} hold")


def sources():
    """Sources are linked securely, dated no later than the fact check, and keyed plainly."""
    for source_key, source in facts.SOURCES.items():
        check(re.fullmatch(r"[a-z0-9_]+", source_key) is not None, f"source key {source_key!r} is not lower_snake_case")
        check(source.url.startswith("https://"), f"source {source_key} is not an https link")
        check(source.published is None or source.published <= facts.FACTS_CHECKED_ON,
              f"source {source_key} is dated after FACTS_CHECKED_ON")


# ---------------------------------------------------------------------------
# The template
# ---------------------------------------------------------------------------

def template():
    """The template names only facts and sources that exist, cites every source, and types no derived figure."""
    template_text = read_file(os.path.join("web", "page.html"))
    cited_source_keys = set()
    figures_used = set()
    for placeholder in PLACEHOLDER.findall(template_text):
        if placeholder.startswith("cite:"):
            for source_key in placeholder[len("cite:"):].split(","):
                cited_source_keys.add(source_key.strip())
        else:
            figures_used.add(placeholder)
            check(placeholder in facts.PAGE_FIGURES or placeholder in BUILT_BY_BUILD_PY,
                  f"web/page.html asks for {{{{ {placeholder} }}}}, which nothing provides")
    check(cited_source_keys <= set(facts.SOURCES),
          f"cited but not in SOURCES: {sorted(cited_source_keys - set(facts.SOURCES))}")
    check(set(facts.SOURCES) <= cited_source_keys,
          f"in SOURCES but never cited: {sorted(set(facts.SOURCES) - cited_source_keys)}")
    check(set(facts.PAGE_FIGURES) <= figures_used,
          f"in PAGE_FIGURES but never shown: {sorted(set(facts.PAGE_FIGURES) - figures_used)}")

    # A derived figure typed into the template would stop following its inputs.
    # Only the words a reader sees are searched, so markup such as rows="7" is
    # not mistaken for a figure.
    words_shown = re.sub(r"<!--.*?-->", " ", template_text, flags=re.DOTALL)
    words_shown = PLACEHOLDER.sub(" ", words_shown)
    words_shown = re.sub(r"<[^>]*>", " ", words_shown)
    for figure_name in facts.DERIVED_FIGURE_NAMES:
        shown = facts.PAGE_FIGURES.get(figure_name, "")
        typed_in = re.search(r"(?<![\w.,$])" + re.escape(shown) + r"(?![\w]|[.,]\d)", words_shown)
        check(not typed_in, f"web/page.html types {shown!r} by hand; use {{{{ {figure_name} }}}} instead")

    stylesheet = read_file(os.path.join("web", "page.css"))
    script = read_file(os.path.join("web", "page.js"))
    check("</style" not in stylesheet.lower(), "page.css contains </style, which would end the inlined stylesheet early")
    check("</script" not in script.lower(), "page.js contains </script, which would end the inlined script early")
    print(f"sources         {len(facts.SOURCES)} listed, {len(cited_source_keys)} cited")


def script_syntax():
    """page.js parses, when Node is installed to ask."""
    node = shutil.which("node")
    if node is None:
        print("javascript      not checked; Node is not installed")
        return
    result = subprocess.run([node, "--check", os.path.join(HERE, "web", "page.js")],
                            capture_output=True, text=True)
    check(result.returncode == 0, f"page.js does not parse: {result.stderr.strip()}")
    print("javascript      parses")


def share_image():
    """The link-preview picture exists, is the size the page declares, and its source names Election Day as facts.py does."""
    image_path = os.path.join(HERE, "web", facts.SHARE_IMAGE_FILE_NAME)
    if not os.path.exists(image_path):
        check(False, f"web/{facts.SHARE_IMAGE_FILE_NAME} is missing; render web/share-card.html (see its comment)")
        return
    with open(image_path, "rb") as image_file:
        header = image_file.read(24)
    check(header[:8] == b"\x89PNG\r\n\x1a\n", "the share image is not a PNG")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    check((width, height) == (facts.SHARE_IMAGE_WIDTH, facts.SHARE_IMAGE_HEIGHT),
          f"the share image is {width}x{height}, not {facts.SHARE_IMAGE_WIDTH}x{facts.SHARE_IMAGE_HEIGHT}")
    card_source = read_file(os.path.join("web", "share-card.html"))
    check(facts.PAGE_FIGURES["election_day_medium"] in card_source,
          "web/share-card.html does not name Election Day the way facts.py does")
    check(facts.PAGE_ADDRESS.startswith("https://") and facts.PAGE_ADDRESS.endswith("/"),
          "PAGE_ADDRESS must be https and end with a slash")
    print(f"share image     {width}x{height}")


# ---------------------------------------------------------------------------
# What build.py makes
# ---------------------------------------------------------------------------

class PageInventory(HTMLParser):
    """Collects, in one pass over the built page, what the checks below need."""

    def __init__(self):
        super().__init__()
        self.element_ids = []
        self.links = []                 # the attributes of every <a>
        self.headings_level_1 = 0
        self.language = None
        self.has_viewport = False
        self.canonical_address = None
        self.meta_properties = {}       # og:image and the like
        self.loads_from_elsewhere = []  # anything the browser would fetch from another site

    def handle_starttag(self, tag, attribute_pairs):
        attributes = dict(attribute_pairs)
        if "id" in attributes:
            self.element_ids.append(attributes["id"])
        if tag == "html":
            self.language = attributes.get("lang")
        if tag == "h1":
            self.headings_level_1 += 1
        if tag == "a":
            self.links.append(attributes)
        if tag == "meta" and attributes.get("name") == "viewport":
            self.has_viewport = True
        if tag == "meta" and attributes.get("property"):
            self.meta_properties[attributes["property"]] = attributes.get("content")
        # The canonical link only names the page's own address; nothing is fetched.
        is_canonical_link = tag == "link" and "canonical" in attributes.get("rel", "").split()
        if is_canonical_link:
            self.canonical_address = attributes.get("href")
        fetched_address = attributes.get("src") or (attributes.get("href") if tag == "link" and not is_canonical_link else None)
        if fetched_address and re.match(r"(https?:)?//", fetched_address):
            self.loads_from_elsewhere.append(f"<{tag}> {fetched_address}")


def built_page():
    """The built page is complete, self-contained, and every link goes somewhere real."""
    page_path = os.path.join(HERE, "index.html")
    if not os.path.exists(page_path):
        print("page            not built; run build.py first")
        return
    page = read_file("index.html")
    inventory = PageInventory()
    inventory.feed(page)

    check("{{" not in page and "}}" not in page, "index.html still holds an unfilled {{ placeholder }}")
    words_on_page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.DOTALL)
    words_on_page = re.sub(r"<[^>]*>", " ", words_on_page)
    leftover_stubs = re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", words_on_page)
    check(not leftover_stubs, f"the page still shows stand-in text: {sorted(set(leftover_stubs))}")
    source_list_words = re.sub(r"<[^>]*>", " ", re.search(r'<ol class="source-list">.*?</ol>', page, re.DOTALL).group(0))
    check(not re.search(r"[.?!]\.", source_list_words), "a source title's own punctuation is followed by a second full stop")
    check(inventory.language == "en", "the page does not declare lang=\"en\"")
    check(inventory.has_viewport, "the page has no viewport meta tag, so phones would zoom it out")
    check(inventory.headings_level_1 == 1, f"the page has {inventory.headings_level_1} <h1> headings, not 1")
    check(not inventory.loads_from_elsewhere, f"the page loads from other sites: {inventory.loads_from_elsewhere}")
    check(not re.search(r"@import|url\(\s*['\"]?(https?:)?//", page), "the stylesheet fetches from another site")
    check(inventory.canonical_address == facts.PAGE_ADDRESS, "the canonical link does not name PAGE_ADDRESS")
    check(inventory.meta_properties.get("og:url") == facts.PAGE_ADDRESS, "og:url does not name PAGE_ADDRESS")
    check(inventory.meta_properties.get("og:image") == facts.PAGE_ADDRESS + facts.SHARE_IMAGE_FILE_NAME,
          "og:image does not point at the share image next to the page")
    check(os.path.exists(os.path.join(HERE, facts.SHARE_IMAGE_FILE_NAME)),
          "build.py did not copy the share image next to index.html")

    duplicate_ids = sorted({element_id for element_id in inventory.element_ids
                            if inventory.element_ids.count(element_id) > 1})
    check(not duplicate_ids, f"ids used twice: {duplicate_ids}")
    for link in inventory.links:
        address = link.get("href")
        if address is None:
            continue    # filled in by the script
        if address.startswith("#"):
            check(address[1:] in inventory.element_ids, f"link to {address}, which no element has as its id")
        else:
            check(re.match(r"(https://|mailto:|sms:)", address) is not None, f"link {address} is not https")
        if link.get("target") == "_blank":
            check("noopener" in link.get("rel", ""), f"link {address} opens a new tab without rel=noopener")

    for figure_name in ("election_day_long", "house_seats_for_veto_proof_majority",
                        "senate_seats_for_veto_proof_majority"):
        check(facts.PAGE_FIGURES[figure_name] in page, f"the page never shows {figure_name}")
    page_kilobytes = len(page.encode("utf-8")) / 1024
    print(f"page            index.html, {page_kilobytes:.0f} KB, {len(inventory.links)} links, "
          f"{len(inventory.loads_from_elsewhere)} loads from other sites")


# ---------------------------------------------------------------------------

def main():
    election_day()
    veto_proof_targets()
    senate_races()
    distance_to_veto_proof()
    derived_figures()
    comparisons()
    sources()
    template()
    script_syntax()
    share_image()
    built_page()

    if FAILED:
        print(f"\n{len(FAILED)} check(s) failed:")
        for message in FAILED:
            print(f"  - {message}")
        sys.exit(1)
    print("\nall checks passed")


if __name__ == "__main__":
    main()
