#!/usr/bin/env python3
"""Render a newspaper front page summing up the world news of 20 November 2026.

Writes entry.png (1024x1024) next to this file. Deterministic: no clocks, no
randomness, no network; fonts come from the local DejaVu install.

Every piece of text is measured as it is drawn. After layout, the script checks
that each text bounding box lies inside the box it was assigned, that no two
text boxes overlap, and that nothing leaves the page. If any check fails it
exits non-zero instead of writing the image.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W = H = 1024
MARGIN = 32
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

PAPER = (248, 244, 232)  # #f8f4e8
INK = (24, 22, 20)
GREY = (92, 88, 80)
RED = (178, 28, 36)
TICKER_BG = (28, 26, 24)
TICKER_FG = (240, 235, 220)

_font_cache = {}


def font(name, size):
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    return _font_cache[key]


SERIF_BOLD = "DejaVuSerif-Bold.ttf"
SERIF = "DejaVuSerif.ttf"
SANS_BOLD = "DejaVuSans-Bold.ttf"

# ---------------------------------------------------------------- content ---
DATELINE = "FRIDAY 20 NOVEMBER 2026"

LEAD = {
    "kicker": "UKRAINE WAR",
    "headline": "Russia Fires 400 Drones and 110 Missiles at Ukraine; "
                "Two Missiles Fall in Poland",
    "summary": "Kyiv said the overnight barrage struck three bridges over the "
               "Dnipro River and knocked out power across the capital, killing "
               "at least eight people and injuring nearly 30. Two Russian "
               "missiles came down inside Poland, and Prime Minister Donald "
               "Tusk called the incursion a deliberate provocation.",
}

GRID = [
    {
        "kicker": "WORLD COURT",
        "headline": "World Court Finds Myanmar Responsible for Rohingya Genocide",
        "summary": "The International Court of Justice ruled that Myanmar bears "
                   "responsibility for genocide against the Rohingya minority in "
                   "a landmark judgment at The Hague. Myanmar rejected the "
                   "ruling, which orders reparations.",
    },
    {
        "kicker": "DIPLOMACY",
        "headline": "Trump, Xi and Putin Issue Joint Peace Declaration in Shenzhen",
        "summary": "The leaders of the United States, China and Russia closed "
                   "their first trilateral summit with a joint peace declaration. "
                   "The three also agreed that humans must oversee any military "
                   "use of artificial intelligence.",
    },
    {
        "kicker": "EUROPE",
        "headline": "Britain and EU Seal Biggest Post-Brexit Deal in Brussels",
        "summary": "London and Brussels agreed to scrap checks on food trade, "
                   "link their carbon markets and launch a youth mobility scheme "
                   "for 100,000 young people, the biggest reset since Brexit.",
    },
    {
        "kicker": "CLIMATE",
        "headline": "COP31 Talks Deadlock Over Fossil Fuels in Antalya",
        "summary": "Negotiators at the UN climate summit in Turkey ran into "
                   "overtime, deadlocked over whether the final text should "
                   "commit countries to phasing out fossil fuels.",
    },
]

TICKER = [
    "Houthi missile strikes Riyadh's tallest skyscraper, blowing out windows "
    "across eight floors.",
    "Haitian police kill 34 suspected gang members in a raid, the force says.",
    "AI selloff spreads: Anthropic shares slide after record IPO as Nikkei "
    "falls 4.8%.",
]


# --------------------------------------------------------------- helpers ---
def wrap(text, fnt, max_width):
    """Greedy word wrap using measured pixel widths."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if fnt.getlength(trial) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            if fnt.getlength(word) > max_width:
                raise ValueError(f"word {word!r} wider than {max_width}px")
            cur = word
    if cur:
        lines.append(cur)
    return lines


def block_height(lines, line_h):
    return len(lines) * line_h


class Page:
    def __init__(self):
        self.img = Image.new("RGB", (W, H), PAPER)
        self.draw = ImageDraw.Draw(self.img)
        self.records = []  # (label, bbox, container)

    def text(self, xy, s, fnt, fill, container, label, tracking=0):
        """Draw text (optionally letter-spaced) and record its real bbox."""
        x, y = xy
        if tracking == 0:
            self.draw.text((x, y), s, font=fnt, fill=fill)
            bbox = self.draw.textbbox((x, y), s, font=fnt)
        else:
            boxes = []
            cx = x
            for ch in s:
                self.draw.text((cx, y), ch, font=fnt, fill=fill)
                if ch.strip():
                    boxes.append(self.draw.textbbox((cx, y), ch, font=fnt))
                cx += fnt.getlength(ch) + tracking
            bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                    max(b[2] for b in boxes), max(b[3] for b in boxes))
        self.records.append((label, bbox, container))
        return bbox

    def rule(self, y, width=1, x0=MARGIN, x1=W - MARGIN, fill=INK):
        self.draw.rectangle([x0, y, x1, y + width - 1], fill=fill)


def tracked_width(s, fnt, tracking):
    return sum(fnt.getlength(c) for c in s) + tracking * (len(s) - 1)


def story_layout(story, width, k_size, h_size, s_size, s_lead=1.42):
    """Return (lines, total height) for a story at given font sizes."""
    k_font = font(SANS_BOLD, k_size)
    h_font = font(SERIF_BOLD, h_size)
    s_font = font(SERIF, s_size)
    h_lines = wrap(story["headline"], h_font, width)
    s_lines = wrap(story["summary"], s_font, width)
    k_lh = round(k_size * 1.25)
    h_lh = round(h_size * 1.18)
    s_lh = round(s_size * s_lead)
    gap_k, gap_h = round(k_size * 0.45), round(s_size * 0.6)
    total = k_lh + gap_k + len(h_lines) * h_lh + gap_h + len(s_lines) * s_lh
    return {
        "fonts": (k_font, h_font, s_font),
        "lh": (k_lh, h_lh, s_lh),
        "gaps": (gap_k, gap_h),
        "h_lines": h_lines,
        "s_lines": s_lines,
        "height": total,
    }


def draw_story(page, story, lay, x, y, container, label):
    k_font, h_font, s_font = lay["fonts"]
    k_lh, h_lh, s_lh = lay["lh"]
    gap_k, gap_h = lay["gaps"]
    page.text((x, y), story["kicker"], k_font, RED, container,
              f"{label}/kicker", tracking=1)
    y += k_lh + gap_k
    for i, line in enumerate(lay["h_lines"]):
        page.text((x, y), line, h_font, INK, container, f"{label}/headline{i}")
        y += h_lh
    y += gap_h
    for i, line in enumerate(lay["s_lines"]):
        page.text((x, y), line, s_font, INK, container,
                  f"{label}/summary{i}")
        y += s_lh
    return y


# ---------------------------------------------------------------- layout ---
def render():
    page = Page()
    d = page.draw
    content_w = W - 2 * MARGIN
    full = (MARGIN, 0, W - MARGIN, H)

    # --- Masthead -----------------------------------------------------------
    y = 22
    page.rule(y, 4)
    page.rule(y + 8, 1)
    mast_font = font(SERIF_BOLD, 78)
    mast = "THE WORLD TODAY"
    tr = 4
    mw = tracked_width(mast, mast_font, tr)
    mast_box = (MARGIN, y + 10, W - MARGIN, y + 112)
    bb = page.text(((W - mw) / 2, y + 20), mast, mast_font, INK, mast_box,
                   "masthead", tracking=tr)
    y = bb[3] + 16
    page.rule(y, 1)

    # Dateline row: date dead centre, small edition labels at the edges.
    row_top, row_bot = y + 1, y + 52
    date_font = font(SERIF_BOLD, 32)
    dtr = 3
    dw = tracked_width(DATELINE, date_font, dtr)
    asc, desc = date_font.getmetrics()
    dy = row_top + (row_bot - row_top - asc - desc) / 2 + 2
    date_box = (MARGIN, row_top, W - MARGIN, row_bot)
    dbb = page.text(((W - dw) / 2, dy), DATELINE, date_font, INK, date_box,
                    "dateline", tracking=dtr)
    # red diamonds flanking the date
    cy = (dbb[1] + dbb[3]) / 2
    for cx in (dbb[0] - 22, dbb[2] + 22):
        d.polygon([(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)],
                  fill=RED)
    lab_font = font(SANS_BOLD, 13)
    la, ld = lab_font.getmetrics()
    ly = row_top + (row_bot - row_top - la - ld) / 2
    left_box = (MARGIN, row_top, dbb[0] - 40, row_bot)
    right_box = (dbb[2] + 40, row_top, W - MARGIN, row_bot)
    page.text((MARGIN, ly), "WORLD EDITION", lab_font, GREY, left_box,
              "label-left", tracking=1)
    rlab = "DAILY DIGEST"
    page.text((int(W - MARGIN - tracked_width(rlab, lab_font, 1)) - 1, ly), rlab,
              lab_font, GREY, right_box, "label-right", tracking=1)
    y = row_bot
    page.rule(y, 1)
    page.rule(y + 4, 3)
    y += 4 + 3

    # --- Ticker band (fixed at the bottom; computed first for the budget) --
    tick_font = font(SANS_BOLD, 14)
    t_lh = 22
    band_pad = 12
    band_h = band_pad * 2 + t_lh * len(TICKER)
    band_bot = H - 20
    band_top = band_bot - band_h

    # --- Lead story --------------------------------------------------------
    lead_top = y + 16
    lead_box = (MARGIN, lead_top, W - MARGIN, lead_top + 270)
    lay = None
    for h_size in range(46, 30, -1):
        s_size = 19 if h_size >= 40 else 18
        cand = story_layout(LEAD, content_w - 2, 16, h_size, s_size)
        if len(cand["h_lines"]) <= 2 and len(cand["s_lines"]) <= 4 \
                and cand["height"] <= lead_box[3] - lead_box[1]:
            lay = cand
            break
    if lay is None:
        sys.exit("lead story does not fit")
    lead_end = draw_story(page, LEAD, lay, MARGIN + 1, lead_top, lead_box, "lead")
    y = lead_end + 10
    page.rule(y, 2)
    grid_top = y + 2

    # --- 2x2 grid -------------------------------------------------------------
    # Rows are sized to their content (tallest story in the row), so a row with
    # short headlines does not reserve the space a 3-line headline needs. Pick
    # the largest type that lets both rows fit, then share leftover space.
    gutter = 36
    cell_w = (content_w - gutter) // 2
    grid_bot = band_top - 14
    pad_top, row_gap = 14, 26
    avail = grid_bot - grid_top - pad_top - row_gap
    chosen = None
    for h_size in range(32, 17, -1):
        for s_lead in (1.5, 1.45, 1.42):
            s_size = max(14, min(18, round(h_size * 0.64)))
            lays = [story_layout(s, cell_w - 2, 15, h_size, s_size, s_lead)
                    for s in GRID]
            row_h = [max(lays[0]["height"], lays[1]["height"]),
                     max(lays[2]["height"], lays[3]["height"])]
            if sum(row_h) <= avail:
                chosen = lays
                break
        if chosen:
            break
    if chosen is None:
        sys.exit("grid stories do not fit")
    slack = avail - sum(row_h)
    cell_hs = [row_h[0] + slack // 2, row_h[1] + slack - slack // 2]

    col_x = [MARGIN, MARGIN + cell_w + gutter]
    row_y = [grid_top + pad_top, grid_top + pad_top + cell_hs[0] + row_gap]
    for i, (story, lay_i) in enumerate(zip(GRID, chosen)):
        cx, cy0 = col_x[i % 2], row_y[i // 2]
        box = (cx, cy0, cx + cell_w, cy0 + cell_hs[i // 2])
        draw_story(page, story, lay_i, cx + 1, cy0, box, f"grid{i}")
    # column rule and row rule
    vx = MARGIN + cell_w + gutter // 2
    d.rectangle([vx, grid_top + 12, vx, grid_bot], fill=INK)
    ry = row_y[1] - row_gap // 2 - 1
    page.rule(ry, 1, x1=vx - 14)
    page.rule(ry, 1, x0=vx + 14)

    # --- Ticker band ---------------------------------------------------------
    d.rectangle([MARGIN, band_top, W - MARGIN, band_bot], fill=TICKER_BG)
    lab_w = 118
    d.rectangle([MARGIN, band_top, MARGIN + lab_w, band_bot], fill=RED)
    in_font = font(SANS_BOLD, 17)
    for i, word in enumerate(("IN", "BRIEF")):
        ww = tracked_width(word, in_font, 2)
        page.text((MARGIN + (lab_w - ww) / 2,
                   band_top + band_h / 2 - 22 + i * 22), word, in_font,
                  TICKER_FG, (MARGIN, band_top, MARGIN + lab_w, band_bot),
                  f"ticker-label{i}", tracking=2)
    tx = MARGIN + lab_w + 18
    t_box = (tx, band_top, W - MARGIN - 12, band_bot)
    ta, td = tick_font.getmetrics()
    for i, item in enumerate(TICKER):
        ly = band_top + band_pad + i * t_lh + (t_lh - ta - td) / 2
        bx, by = tx + 4, ly + ta * 0.55
        d.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=RED)
        if 16 + tick_font.getlength(item) > t_box[2] - tx:
            sys.exit(f"ticker item {i} too wide")
        page.text((tx + 16, ly), item, tick_font, TICKER_FG, t_box,
                  f"ticker{i}")

    return page, {"lead_h": lay["h_lines"], "grid_h": chosen[0]["fonts"][1].size,
                  "grid_s": chosen[0]["fonts"][2].size,
                  "grid_lead": chosen[0]["lh"][2], "grid_slack": slack,
                  "lead_hsize": lay["fonts"][1].size}


# -------------------------------------------------------------- checking ---
def check(page):
    problems = []
    recs = page.records
    for label, bb, box in recs:
        if bb[0] < box[0] or bb[1] < box[1] or bb[2] > box[2] or bb[3] > box[3]:
            problems.append(f"{label}: bbox {bb} outside container {box}")
        if bb[0] < 0 or bb[1] < 0 or bb[2] > W or bb[3] > H:
            problems.append(f"{label}: off page {bb}")
    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            a, b = recs[i][1], recs[j][1]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                problems.append(f"overlap: {recs[i][0]} {a} vs {recs[j][0]} {b}")
    return problems


def main():
    page, info = render()
    problems = check(page)
    if problems:
        for p in problems:
            print("LAYOUT ERROR:", p, file=sys.stderr)
        sys.exit(1)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")
    page.img.save(out, format="PNG", optimize=True)
    print(f"layout OK: {len(page.records)} text boxes checked; "
          f"lead headline {info['lead_hsize']}px x{len(info['lead_h'])} lines, "
          f"grid headline {info['grid_h']}px, grid body {info['grid_s']}px "
          f"(line {info['grid_lead']}px), grid slack {info['grid_slack']}px")
    print(f"wrote {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
