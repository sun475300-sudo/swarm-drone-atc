# -*- coding: utf-8 -*-
"""Inject v5 images back into gen_report_v6.py at proper section anchors."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = 'gen_report_v6.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# Abort if already patched (idempotent)
if 'def add_img(' in src:
    print('Already patched. Skipping.')
    sys.exit(0)

helper_code = (
    "\n"
    "IMG_DIR = r'C:\\Users\\sun47\\Desktop\\swarm-drone-atc\\.claude\\worktrees\\stupefied-hugle\\v5_images'\n"
    "IMG = {\n"
    "    'g0':  'c6f3b3d148e074da06cbee1afedfc120699640e4.png',\n"
    "    'g1':  '78cb17427a601bb078076de230d1279ef505df5a.png',\n"
    "    'g2':  'e0271e0a50ac6bc78f0398f2c240f4e573bbe062.png',\n"
    "    'g3':  'df06668eb85513a5ac7486fabc179561c38c8647.png',\n"
    "    'g4':  '80746b62fb86c64a171c54eec1e860c582be58ce.png',\n"
    "    'g5':  'cfa38868f013731afcd63c1435b362661dee6a83.png',\n"
    "    'g6':  'ce7ff024213fe4ac9b79445fa88b3974a8322ea9.png',\n"
    "    'g7':  '4894b105349392aeef769d0f24ad5b2d49e725a3.png',\n"
    "    'g8':  '152b2021b23eb93a4da13a6a82826edb8f0e7e2c.png',\n"
    "    'g9':  'f65473721ace1a8dabd5f3081c045a4e62b3dcfc.png',\n"
    "    'g10': 'dcd74a92f4ea60cab7a9d3640ebfa33963603eb3.png',\n"
    "    'g11': 'd0b4bce5521f952cd294984b8aa919b2eaaea0ea.png',\n"
    "    'g12': 'ac244e51158df836c161d6734de59149585a941d.png',\n"
    "    'g13': 'ca3c9b5e10bd3cd0f142ee2967693bf940d40e81.png',\n"
    "    'g14': '7f6dcc79e78a06e547906f2d89ba69fc67bf5ad5.png',\n"
    "}\n"
    "\n"
    "def add_img(key, caption, width_cm=14):\n"
    "    import os\n"
    "    ipath = os.path.join(IMG_DIR, IMG[key])\n"
    "    p = doc.add_paragraph()\n"
    "    p.alignment = WD_ALIGN_PARAGRAPH.CENTER\n"
    "    r = p.add_run()\n"
    "    r.add_picture(ipath, width=Cm(width_cm))\n"
    "    c = doc.add_paragraph()\n"
    "    c.alignment = WD_ALIGN_PARAGRAPH.CENTER\n"
    "    cr = c.add_run(caption)\n"
    "    cr.italic = True\n"
    "    cr.font.size = Pt(9)\n"
    "    cr.font.color.rgb = RGBColor(0x55, 0x55, 0x55)\n"
    "\n"
)

# Insert helper right after add_box function body
add_box_end = (
    "def add_box(text):\n"
    "    p = doc.add_paragraph()\n"
    "    p.paragraph_format.left_indent = Cm(1)\n"
    "    r = p.add_run(text)\n"
    "    r.font.size = Pt(9)\n"
    "    r.font.color.rgb = RGBColor(0x1E, 0x3A, 0x5F)\n"
)
if add_box_end not in src:
    print('ERROR: add_box anchor not found')
    sys.exit(1)
src = src.replace(add_box_end, add_box_end + helper_code, 1)

# Anchor-based image insertions
# Each tuple: (anchor_text, image_call_lines_to_append_after)
insertions = [
    # g0: cover summary - insert before 목차 page break
    (
        "doc.add_page_break()\n\n# \u2550\u2550\u2550 \ubaa9\ucc28 \u2550\u2550\u2550\nadd_h('\ubaa9   \ucc28', 1)",
        "add_img('g0', '[\uadf8\ub9bc 0] SDACS \ud575\uc2ec \uc131\uacfc \uc9c0\ud45c \uc694\uc57d', 14)\ndoc.add_page_break()\n\n# \u2550\u2550\u2550 \ubaa9\ucc28 \u2550\u2550\u2550\nadd_h('\ubaa9   \ucc28', 1)",
    ),
    (
        "add_h('1  \ubb38\uc81c \uc81c\uae30 \\u2014 \ud558\ub298\uae38\uc774 \ub9c9\ud788\uace0 \uc788\uc2b5\ub2c8\ub2e4', 1)",
        "add_h('1  \ubb38\uc81c \uc81c\uae30 \\u2014 \ud558\ub298\uae38\uc774 \ub9c9\ud788\uace0 \uc788\uc2b5\ub2c8\ub2e4', 1)\nadd_img('g1', '[\uadf8\ub9bc 1] \ubb38\uc81c\uc758 \uaddc\ubaa8 \u2014 4\uac00\uc9c0 \ud575\uc2ec \uc218\uce58', 14)\nadd_img('g2', '[\uadf8\ub9bc 2] \uae30\uc874 \ub808\uc774\ub354\uc758 \ud55c\uacc4 \u2014 \ub3c4\uc2ec \uc800\uace0\ub3c4 67%\uac00 \uc0ac\uac01\uc9c0\ub300', 14)",
    ),
    (
        "add_h('3  SDACS \ud575\uc2ec \uc544\uc774\ub514\uc5b4 \\u2014 \uc774\ub3d9\ud615 \uac00\uc0c1 \ub808\uc774\ub354 \ub3d4', 1)",
        "add_h('3  SDACS \ud575\uc2ec \uc544\uc774\ub514\uc5b4 \\u2014 \uc774\ub3d9\ud615 \uac00\uc0c1 \ub808\uc774\ub354 \ub3d4', 1)\nadd_img('g3', '[\uadf8\ub9bc 3] \uc774\ub3d9\ud615 \uac00\uc0c1 \ub808\uc774\ub354 \ub3d4 \u2014 20\ub300 \uad00\uc81c \ub4dc\ub860\uc774 Mesh \ub124\ud2b8\uc6cc\ud06c \ud615\uc131', 14)",
    ),
    (
        "add_h('4  \uc2dc\uc2a4\ud15c \uad6c\uc870 \\u2014 4\uacc4\uce35 \uc544\ud0a4\ud14d\ucc98', 1)",
        "add_h('4  \uc2dc\uc2a4\ud15c \uad6c\uc870 \\u2014 4\uacc4\uce35 \uc544\ud0a4\ud14d\ucc98', 1)\nadd_img('g4', '[\uadf8\ub9bc 4] SDACS 4\uacc4\uce35 \uc544\ud0a4\ud14d\ucc98', 14)",
    ),
    (
        "add_h('5  \ud575\uc2ec \uc54c\uace0\ub9ac\uc998 \\u2014 \uc5b4\ub5bb\uac8c \ucda9\ub3cc\uc744 \ub9c9\ub294\uac00', 1)",
        "add_h('5  \ud575\uc2ec \uc54c\uace0\ub9ac\uc998 \\u2014 \uc5b4\ub5bb\uac8c \ucda9\ub3cc\uc744 \ub9c9\ub294\uac00', 1)\nadd_img('g5', '[\uadf8\ub9bc 5] 5\uacb9 \uc548\uc804\ub9dd \u2014 \uc54c\uace0\ub9ac\uc998 \uacc4\uce35\ubcc4 \uc5ed\ud560', 14)\nadd_img('g6', '[\uadf8\ub9bc 6] \uc790\ub3d9 \uc6b0\uc120\uc21c\uc704 \uc804\ud658 \u2014 \uc0c1\ud669\uc5d0 \ub530\ub77c 5\ub2e8\uacc4\ub85c \uc790\ub3d9 \ubcc0\uacbd', 14)",
    ),
    (
        "add_h('6  \uc5f0\uad6c \ud504\ub808\uc784\uc6cc\ud06c \\u2014 \uc65c \uc2a4\ud0c0\ud06c\ub798\ud504\ud2b8\uc778\uac00', 1)",
        "add_h('6  \uc5f0\uad6c \ud504\ub808\uc784\uc6cc\ud06c \\u2014 \uc65c \uc2a4\ud0c0\ud06c\ub798\ud504\ud2b8\uc778\uac00', 1)\nadd_img('g7', '[\uadf8\ub9bc 7] \uac8c\uc784 AI \u2192 \uc2e4\uc81c \ub4dc\ub860 ATC Sim-to-Real Transfer \ud504\ub808\uc784\uc6cc\ud06c', 14)\nadd_img('g8', '[\uadf8\ub9bc 8] \uad70\uc9d1 \uaddc\ubaa8\ubcc4 \uc81c\uc5b4 \uc131\ub2a5 \u2014 \uad8c\uc7a5 \uad70\uc9d1 \ud06c\uae30: 50\ub300', 14)",
    ),
    (
        "add_h('7  \ud0d0\uc9c0 \\u2192 \ud1f4\uac01 \uc790\ub3d9\ud654 \ud30c\uc774\ud504\ub77c\uc778 \\u2014 1\ucd08 \uc774\ub0b4', 1)",
        "add_h('7  \ud0d0\uc9c0 \\u2192 \ud1f4\uac01 \uc790\ub3d9\ud654 \ud30c\uc774\ud504\ub77c\uc778 \\u2014 1\ucd08 \uc774\ub0b4', 1)\nadd_img('g9', '[\uadf8\ub9bc 9] \ud0d0\uc9c0 \u2192 \ud1f4\uac01 \uc790\ub3d9\ud654 \ud30c\uc774\ud504\ub77c\uc778 (5\ub2e8\uacc4 \xb7 \uc804\uccb4 1\ucd08 \uc774\ub0b4)', 14)",
    ),
    (
        "add_h('9  \uc131\ub2a5 \uac80\uc99d \uacb0\uacfc', 1)",
        "add_h('9  \uc131\ub2a5 \uac80\uc99d \uacb0\uacfc', 1)\nadd_img('g10', '[\uadf8\ub9bc 10] \uae30\uc874 \ubc29\uc2dd vs SDACS \u2014 \uc131\ub2a5 \ube44\uad50', 14)",
    ),
    (
        "add_h('13  \uac1c\ubc1c \ub85c\ub4dc\ub9f5', 1)",
        "add_h('13  \uac1c\ubc1c \ub85c\ub4dc\ub9f5', 1)\nadd_img('g11', '[\uadf8\ub9bc 11] \uac1c\ubc1c \ub85c\ub4dc\ub9f5 \u2014 \uce21\uc2a4\ud1a4 16\uc8fc \xb7 \uc7a5\uae30 10\ub144', 14)",
    ),
    (
        "add_h('15  \ud2b9\ud5c8 \uad00\uacc4\ub3c4', 1)",
        "add_h('15  \ud2b9\ud5c8 \uad00\uacc4\ub3c4', 1)\nadd_img('g12', '[\uadf8\ub9bc 12] SDACS \ud2b9\ud5c8 \uad00\uacc4\ub3c4 \u2014 \uae30\uc874 \ud2b9\ud5c8\uc640\uc758 \uacb9\uce68 \ubc0f \uc704\ud5d8\ub3c4 \ubd84\uc11d', 14)",
    ),
    (
        "add_h('16  \ud2b9\ud5c8 \ucd9c\uc6d0 \uc804\ub7b5', 1)",
        "add_h('16  \ud2b9\ud5c8 \ucd9c\uc6d0 \uc804\ub7b5', 1)\nadd_img('g13', '[\uadf8\ub9bc 13] \ud2b9\ud5c8 \ucd9c\uc6d0 \uac00\ub2a5 \uae30\uc220 5\uc120 \ubc0f \uc2e4\ud589 \uc808\ucc28 4\ub2e8\uacc4', 14)",
    ),
    (
        "add_h('v5 \\u2192 v6 \ubcf4\uc644 \uc0ac\ud56d \uc694\uc57d', 1)",
        "add_h('v5 \\u2192 v6 \ubcf4\uc644 \uc0ac\ud56d \uc694\uc57d', 1)\nadd_img('g14', '[\uadf8\ub9bc 14] \ucd94\uac00 \ucf58\ud150\uce20 6\uac00\uc9c0 \u2014 \ubaa9\uc801\uc5d0 \ub530\ub77c \uc120\ud0dd \ud3ec\ud568', 14)",
    ),
]

missing = []
for old, new in insertions:
    if old not in src:
        missing.append(old[:80])
        continue
    src = src.replace(old, new, 1)

if missing:
    print('MISSING ANCHORS:')
    for m in missing:
        print('  -', m)
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

print('Patched: %s' % path)
print('Inserted 15 image blocks + helper')
