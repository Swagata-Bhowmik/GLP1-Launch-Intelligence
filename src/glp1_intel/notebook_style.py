"""Colour-coded markdown boxes used in every project notebook.

Each kind of cell has one colour and one icon, so a reader always knows what they are looking at:

    title()    hero banner (lavender → sky gradient)  notebook title, goal, inputs/outputs
    section()  🟣 light purple                         a numbered section heading
    concept()  🟠 light orange                         theory / explanation of a sub-topic
    code_intro 🟢 mint                                  what the next code cell does, step by step
    output()   🔵 light blue                            how to read the output above
    caution()  🔴 rose                                  traps, limitations, things that go wrong
    takeaway() 💚 green                                 key takeaway + interview questions

The boxes are plain HTML with inline styles, so they render in Jupyter, VS Code and Colab.
GitHub's notebook viewer strips colours but keeps the icons and text, so nothing is lost there.
Text colours are set explicitly so boxes stay readable in dark themes too.
"""

_BOX = ("border-left:6px solid {border}; background:{bg}; color:{text}; padding:14px 18px; "
        "border-radius:10px; margin:10px 0; box-shadow:0 1px 3px rgba(0,0,0,.06);")

STYLES = {
    #            border     background  text       label
    "section":  ("#8B5CF6", "#F3EEFF", "#3B1F7A", ""),
    "concept":  ("#FB923C", "#FFF4E8", "#7C2D12", "💡 Concept"),
    "code":     ("#14B8A6", "#E9FBF8", "#134E4A", "🛠️ What the next code does"),
    "output":   ("#3B82F6", "#EAF4FF", "#1E3A8A", "📊 Reading the output"),
    "caution":  ("#F43F5E", "#FFF0F3", "#881337", "⚠️ Watch out"),
    "takeaway": ("#10B981", "#EAFBF1", "#065F46", "🎯 Key takeaways"),
}


def box(kind: str, body: str, label: str | None = None) -> str:
    """Wrap markdown `body` in a coloured box. Blank lines around the body keep markdown rendering on."""
    border, bg, text, default_label = STYLES[kind]
    label = default_label if label is None else label
    head = f'<b style="font-size:1.02em; letter-spacing:.3px">{label}</b>\n\n' if label else ""
    return (f'<div style="{_BOX.format(border=border, bg=bg, text=text)}">\n\n'
            f"{head}{body.strip()}\n\n</div>")


def title(name: str, subtitle: str, body: str = "") -> str:
    """Gradient hero banner at the top of a notebook."""
    hero = ("background:linear-gradient(120deg,#EDE7FF 0%,#E3F0FF 55%,#E6FBF7 100%); color:#2A1B5C; "
            "padding:22px 26px; border-radius:14px; border:1px solid #DCD3FF; margin-bottom:8px;")
    return (f'<div style="{hero}">\n\n'
            f'<h1 style="margin:0 0 6px 0; color:#3B1F7A">{name}</h1>\n\n'
            f'<p style="margin:0 0 10px 0; font-size:1.1em; color:#4C3A8C">{subtitle}</p>\n\n'
            f"{body.strip()}\n\n</div>")


def section(number: int | str, heading: str, intro: str = "") -> str:
    """Purple section heading. A real markdown heading inside keeps the notebook's table of contents working."""
    return box("section", f"## {number} · {heading}\n\n{intro}".strip(), label="")


def concept(body: str, label: str | None = None) -> str:
    return box("concept", body, label)


def code_intro(body: str, label: str | None = None) -> str:
    return box("code", body, label)


def output(body: str, label: str | None = None) -> str:
    return box("output", body, label)


def caution(body: str, label: str | None = None) -> str:
    return box("caution", body, label)


def takeaway(body: str, label: str | None = None) -> str:
    return box("takeaway", body, label)


def show(df, caption: str = "", precision: int = 1):
    """Display a DataFrame as a soft-blue 'output' table: blue header, zebra rows, thousands separators."""
    def fmt(col):
        s = df[col].dropna()
        is_whole = s.dtype.kind in "iu" or (len(s) and (s == s.round()).all())
        return "{:,.0f}" if is_whole else f"{{:,.{precision}f}}"

    num = df.select_dtypes("number").columns
    return (df.style
            .format({c: fmt(c) for c in num}, na_rep="—")
            .set_caption(caption)
            .hide(axis="index")
            .set_table_styles([
                {"selector": "caption", "props": "caption-side:top; text-align:left; font-weight:600; color:#1E3A8A; "
                                                 "padding:6px 0; font-size:1.02em"},
                {"selector": "th", "props": "background:#C7DDFF; color:#1E3A8A; padding:7px 10px; text-align:left; font-weight:600"},
                {"selector": "td", "props": "padding:5px 10px; color:#1F2937"},
                {"selector": "tr:nth-child(even) td", "props": "background:#F5F9FF"},
                {"selector": "tr:nth-child(odd) td", "props": "background:#FFFFFF"},
            ]))


def legend() -> str:
    """A one-line colour key shown under the title of every notebook."""
    chip = ('<span style="background:{bg}; color:{text}; border-left:4px solid {border}; padding:3px 10px; '
            'border-radius:6px; margin-right:6px; display:inline-block; margin-bottom:4px">{label}</span>')
    chips = [chip.format(bg="#F3EEFF", text="#3B1F7A", border="#8B5CF6", label="🟣 Section")]
    for kind in ["concept", "code", "output", "caution", "takeaway"]:
        border, bg, text, label = STYLES[kind]
        chips.append(chip.format(bg=bg, text=text, border=border, label=label))
    return '<div style="margin:6px 0 4px 0"><b>How to read this notebook:</b><br>' + "".join(chips) + "</div>"
