"""Aurora chart style for notebooks (matplotlib → static PNGs that also render on GitHub).

Colour follows the **molecule**, never the rank, in every chart of the project:
    tirzepatide = violet · semaglutide = teal · dulaglutide = amber · liraglutide = blue · other = rose
Palette validated for colour-blind separation (dataviz validate_palette.js: all checks pass; two hues are
below 3:1 contrast on white, so charts always carry direct value labels).
Obesity brands (Zepbound, Wegovy, Saxenda) reuse their molecule's colour with a dashed line / hatched bar,
so identity never depends on colour alone.
"""
import matplotlib.pyplot as plt
from matplotlib import rcParams

from .paths import ROOT

FIG_DIR = ROOT / "reports" / "figures"

INK, TEXT, TEXT_2, GRID, SURFACE = "#140F33", "#1E1B3A", "#6B6790", "#E7E3F7", "#FFFFFF"
MOLECULE_COLOR = {
    "tirzepatide": "#7C5CFF",
    "semaglutide": "#0EA5A0",
    "dulaglutide": "#E8A33D",
    "liraglutide": "#3B82F6",
    "other":       "#E0607E",
}
BRAND_MOLECULE = {
    "xultophy": "liraglutide", "mounjaro": "tirzepatide", "zepbound": "tirzepatide", "foundayo": "other",
    "ozempic": "semaglutide", "wegovy": "semaglutide", "rybelsus": "semaglutide",
    "trulicity": "dulaglutide", "victoza": "liraglutide", "saxenda": "liraglutide", "liraglutide": "liraglutide",
}
OBESITY_BRANDS = {"zepbound", "wegovy", "saxenda"}
MUTED = "#C9C3E6"                                        # context / "everything else"


def brand_color(brand: str) -> str:
    return MOLECULE_COLOR[BRAND_MOLECULE.get(brand.lower().split()[0], "other")]


def style() -> None:
    """Apply the Aurora look: quiet axes, horizontal grid only, readable sizes."""
    rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10.5,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.titlelocation": "left",
        "axes.titlepad": 30, "axes.axisbelow": True, "axes.labelcolor": TEXT_2, "axes.edgecolor": GRID,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "x", "grid.color": GRID, "grid.linewidth": 0.8,
        "xtick.color": TEXT_2, "ytick.color": TEXT, "xtick.major.size": 0, "ytick.major.size": 0,
        "legend.frameon": False, "legend.fontsize": 9.5, "lines.linewidth": 2.2,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
    })


def subtitle(ax, text: str) -> None:
    """Grey one-line subtitle under the title (source, unit, period)."""
    ax.text(0, 1.02, text, transform=ax.transAxes, color=TEXT_2, fontsize=9.5, va="bottom")


def end_labels(ax, x: float, items: list[tuple[str, float]], min_gap: float | None = None, **text_kw) -> None:
    """Direct labels at the end of lines, nudged apart so they never overlap.

    items = [(label, y_value), ...]. min_gap defaults to 5% of the y-axis range.
    """
    lo, hi = ax.get_ylim()
    gap = min_gap if min_gap is not None else 0.05 * (hi - lo)
    placed = []
    for label, y in sorted(items, key=lambda t: t[1]):
        y_pos = max(y, placed[-1] + gap) if placed else y
        placed.append(y_pos)
        ax.text(x, y_pos, label, va="center", fontsize=9.5, color=TEXT, **text_kw)


def save(fig, name: str) -> None:
    """Save to reports/figures/<name>.png for the README and the report."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png")


style()
