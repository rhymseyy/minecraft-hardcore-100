"""
dashboard.py
------------
Generates charts from your run data for the GitHub README and YouTube video.

USAGE:
  python src/dashboard.py

Outputs to outputs/charts/:
  - completion_overall.png    Line chart: completion % over sessions
  - completion_by_category.png   Horizontal bar: category breakdown (latest)
  - risk_score_timeline.png   Line chart: DPI risk score over time
  - damage_timeline.png       Bar chart: damage taken per session
  - kills_heatmap.png         What you've been killing
  - run_summary_card.png      Single stat card (for README badge)
"""

import csv
import json
import os
from pathlib import Path
from datetime import datetime

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib import rcParams
    import numpy as np
except ImportError:
    print("Installing matplotlib...")
    os.system("pip install matplotlib numpy --break-system-packages -q")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib import rcParams
    import numpy as np

ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = ROOT / "outputs"
CHARTS_DIR = OUTPUTS_DIR / "charts"
RUN_LOG = ROOT / "data" / "run_log.csv"
SESSIONS_DIR = ROOT / "data" / "sessions"

CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ── STYLE ──────────────────────────────────────────────────────────────────────
BG = "#0D1117"          # GitHub dark background
CARD_BG = "#161B22"     # Card background
GREEN = "#3FB950"       # GitHub green
YELLOW = "#D29922"      # Warning
RED = "#F85149"         # Danger
BLUE = "#58A6FF"        # Info
PURPLE = "#BC8CFF"      # Accent
TEXT = "#C9D1D9"        # Primary text
SUBTEXT = "#8B949E"     # Secondary text

CATEGORY_COLORS = {
    "Building":   "#7EE787",
    "Nature":     "#56D364",
    "Food":       "#FFA657",
    "Tools":      "#79C0FF",
    "Weapons":    "#F85149",
    "Armor":      "#BC8CFF",
    "Materials":  "#D2A8FF",
    "Redstone":   "#FF7B72",
    "Brewing":    "#A5D6FF",
    "Music":      "#D29922",
    "Misc":       "#8B949E",
    "Utility":    "#58A6FF",
    "New 1.21.5": "#3FB950",
    "New 1.21.6": "#56D364",
}


def set_style():
    rcParams.update({
        "figure.facecolor": BG,
        "axes.facecolor": CARD_BG,
        "axes.edgecolor": "#30363D",
        "axes.labelcolor": TEXT,
        "axes.titlecolor": TEXT,
        "text.color": TEXT,
        "xtick.color": SUBTEXT,
        "ytick.color": SUBTEXT,
        "grid.color": "#21262D",
        "grid.alpha": 0.6,
        "font.family": "monospace",
        "font.size": 11,
    })


def load_run_log() -> list[dict]:
    if not RUN_LOG.exists():
        return []
    with open(RUN_LOG) as f:
        return list(csv.DictReader(f))


def load_latest_completion() -> list[dict]:
    """Load the most recent completion CSV from outputs/."""
    csvs = sorted(OUTPUTS_DIR.glob("completion_session_*.csv"))
    if not csvs:
        return []
    with open(csvs[-1]) as f:
        return list(csv.DictReader(f))


def chart_completion_timeline(log: list[dict]) -> None:
    """Line chart of overall completion % over sessions."""
    if not log:
        print("  ⚠ No run log data yet. Play a session first.")
        return

    sessions = [int(r["session"]) for r in log]
    pcts = [float(r["overall_pct"]) for r in log]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(sessions, pcts, alpha=0.15, color=GREEN)
    ax.plot(sessions, pcts, color=GREEN, linewidth=2.5, marker="o",
            markersize=6, markerfacecolor=BG, markeredgewidth=2)

    for s, p in zip(sessions, pcts):
        ax.annotate(f"{p:.1f}%", (s, p), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9, color=SUBTEXT)

    ax.set_title("100% Completion Progress — Hardcore Run", fontsize=14,
                 pad=15, color=TEXT, fontweight="bold")
    ax.set_xlabel("Session", color=SUBTEXT)
    ax.set_ylabel("% Items Collected (stacks)", color=SUBTEXT)
    ax.set_ylim(0, 105)
    ax.set_xlim(min(sessions) - 0.5, max(sessions) + 0.5)
    ax.grid(True, axis="y", linestyle="--")
    ax.spines[:].set_visible(False)

    # Milestone lines
    for milestone, label in [(25, "25%"), (50, "50%"), (75, "75%"), (100, "DONE")]:
        ax.axhline(milestone, color=GREEN if milestone < 100 else YELLOW,
                   linestyle=":", alpha=0.4, linewidth=1)
        ax.text(max(sessions) + 0.1, milestone + 1, label,
                fontsize=8, color=SUBTEXT, va="bottom")

    plt.tight_layout()
    out = CHARTS_DIR / "completion_overall.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  ✓ {out.name}")


def chart_category_breakdown(completion: list[dict]) -> None:
    """Horizontal bar chart of completion by category."""
    if not completion:
        print("  ⚠ No completion data. Run parse_stats.py first.")
        return

    from collections import defaultdict
    cats = defaultdict(lambda: {"done": 0, "total": 0})
    for item in completion:
        cat = item["category"]
        cats[cat]["total"] += 1
        if item["has_stack"] == "True":
            cats[cat]["done"] += 1

    # Sort by completion %
    sorted_cats = sorted(
        cats.items(),
        key=lambda x: x[1]["done"] / max(x[1]["total"], 1),
        reverse=True
    )

    labels = [c[0] for c in sorted_cats]
    pcts = [c[1]["done"] / max(c[1]["total"], 1) * 100 for c in sorted_cats]
    counts = [f"{c[1]['done']}/{c[1]['total']}" for c in sorted_cats]
    colors = [CATEGORY_COLORS.get(lab, BLUE) for lab in labels]

    fig, ax = plt.subplots(figsize=(10, max(6, len(labels) * 0.55)))

    bars = ax.barh(labels, pcts, color=colors, alpha=0.85, height=0.65)

    # Add count labels
    for bar, count, pct in zip(bars, counts, pcts):
        ax.text(min(pct + 1, 102), bar.get_y() + bar.get_height() / 2,
                count, va="center", fontsize=9, color=SUBTEXT)

    ax.set_title("Completion by Category", fontsize=14, pad=15,
                 color=TEXT, fontweight="bold")
    ax.set_xlabel("% Complete", color=SUBTEXT)
    ax.set_xlim(0, 115)
    ax.axvline(100, color=GREEN, linestyle="--", alpha=0.4)
    ax.grid(True, axis="x", linestyle="--")
    ax.spines[:].set_visible(False)
    ax.invert_yaxis()

    plt.tight_layout()
    out = CHARTS_DIR / "completion_by_category.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  ✓ {out.name}")


def chart_risk_timeline(log: list[dict]) -> None:
    """Line chart of DPI risk score over sessions."""
    if not log:
        return

    sessions = [int(r["session"]) for r in log]
    risks = [float(r["risk_score"]) for r in log]

    fig, ax = plt.subplots(figsize=(10, 5))

    # Colour zones
    ax.axhspan(0, 3, alpha=0.06, color=GREEN)
    ax.axhspan(3, 5, alpha=0.06, color=YELLOW)
    ax.axhspan(5, 7, alpha=0.06, color="#FFA657")
    ax.axhspan(7, 10, alpha=0.06, color=RED)

    # Zone labels
    for y, label, color in [
        (1.5, "LOW", GREEN), (4, "MODERATE", YELLOW),
        (6, "HIGH", "#FFA657"), (8.5, "CRITICAL", RED)
    ]:
        ax.text(0.02, y, label, transform=ax.get_yaxis_transform(),
                fontsize=8, color=color, alpha=0.5, va="center")

    # Risk line — color by zone
    for i in range(len(sessions) - 1):
        r = risks[i]
        color = GREEN if r < 3 else YELLOW if r < 5 else "#FFA657" if r < 7 else RED
        ax.plot([sessions[i], sessions[i+1]], [risks[i], risks[i+1]],
                color=color, linewidth=2.5)

    ax.scatter(sessions, risks, zorder=5,
               c=[GREEN if r < 3 else YELLOW if r < 5 else "#FFA657" if r < 7 else RED
                  for r in risks],
               s=60, edgecolors=BG, linewidths=2)

    ax.set_title("Death Probability Index — Run Timeline", fontsize=14,
                 pad=15, color=TEXT, fontweight="bold")
    ax.set_xlabel("Session", color=SUBTEXT)
    ax.set_ylabel("Risk Score (0–10)", color=SUBTEXT)
    ax.set_ylim(0, 10)
    ax.set_xlim(min(sessions) - 0.5, max(sessions) + 0.5)
    ax.grid(True, axis="y", linestyle="--")
    ax.spines[:].set_visible(False)

    plt.tight_layout()
    out = CHARTS_DIR / "risk_score_timeline.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  ✓ {out.name}")


def chart_damage_timeline(log: list[dict]) -> None:
    """Bar chart of damage taken per session."""
    if not log:
        return

    sessions = [int(r["session"]) for r in log]
    damages = [float(r["damage_taken"]) for r in log]
    risks = [float(r["risk_score"]) for r in log]

    bar_colors = [
        GREEN if r < 3 else YELLOW if r < 5 else "#FFA657" if r < 7 else RED
        for r in risks
    ]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(sessions, damages, color=bar_colors, alpha=0.85, width=0.65)

    for bar, val in zip(bars, damages):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(damages) * 0.01,
                f"{val:.0f}", ha="center", fontsize=9, color=SUBTEXT)

    ax.set_title("Cumulative Damage Taken by Session", fontsize=14,
                 pad=15, color=TEXT, fontweight="bold")
    ax.set_xlabel("Session", color=SUBTEXT)
    ax.set_ylabel("Damage (HP)", color=SUBTEXT)
    ax.grid(True, axis="y", linestyle="--")
    ax.spines[:].set_visible(False)

    # Legend
    patches = [
        mpatches.Patch(color=GREEN, label="Low risk"),
        mpatches.Patch(color=YELLOW, label="Moderate"),
        mpatches.Patch(color="#FFA657", label="High"),
        mpatches.Patch(color=RED, label="Critical"),
    ]
    ax.legend(handles=patches, loc="upper left", framealpha=0.3,
              facecolor=CARD_BG, edgecolor="#30363D", labelcolor=TEXT)

    plt.tight_layout()
    out = CHARTS_DIR / "damage_timeline.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  ✓ {out.name}")


def chart_summary_card(log: list[dict], completion: list[dict]) -> None:
    """Single summary stat card — good for README header and thumbnail."""
    if not log:
        return

    latest = log[-1]
    overall_pct = float(latest["overall_pct"])
    risk = float(latest["risk_score"])
    play_hours = float(latest["play_hours"])
    session_num = int(latest["session"])

    risk_color = (GREEN if risk < 3 else YELLOW if risk < 5
                  else "#FFA657" if risk < 7 else RED)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    # Title
    ax.text(5, 4.3, "MINECRAFT HARDCORE 100%", ha="center", fontsize=16,
            color=GREEN, fontweight="bold", fontfamily="monospace")
    ax.text(5, 3.75, f"Brandon Rhymes  ·  1.21.8  ·  Session {session_num}",
            ha="center", fontsize=10, color=SUBTEXT, fontfamily="monospace")

    # Big completion %
    ax.text(5, 2.5, f"{overall_pct:.1f}%", ha="center", fontsize=48,
            color=TEXT, fontweight="bold", fontfamily="monospace")
    ax.text(5, 1.6, "items collected", ha="center", fontsize=11,
            color=SUBTEXT, fontfamily="monospace")

    # Stats row
    stats_row = [
        (f"{play_hours:.1f}h", "playtime"),
        (f"{risk}/10", "risk score"),
        (latest["mob_kills_total"], "mob kills"),
        (session_num, "sessions"),
    ]
    for i, (val, label) in enumerate(stats_row):
        x = 1.5 + i * 2.3
        color = risk_color if label == "risk score" else TEXT
        ax.text(x, 0.9, str(val), ha="center", fontsize=16,
                color=color, fontweight="bold", fontfamily="monospace")
        ax.text(x, 0.4, label, ha="center", fontsize=9,
                color=SUBTEXT, fontfamily="monospace")

    # Progress bar
    bar_width = 8
    bar_x = 1
    bar_y = 0.1
    ax.add_patch(mpatches.FancyBboxPatch(
        (bar_x, bar_y), bar_width, 0.15,
        boxstyle="round,pad=0.02", facecolor=CARD_BG,
        edgecolor="#30363D", linewidth=1
    ))
    ax.add_patch(mpatches.FancyBboxPatch(
        (bar_x, bar_y), bar_width * (overall_pct / 100), 0.15,
        boxstyle="round,pad=0.02", facecolor=GREEN, edgecolor="none"
    ))

    plt.tight_layout()
    out = CHARTS_DIR / "run_summary_card.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  ✓ {out.name}")


def main():
    set_style()
    print("\n📊 Generating Minecraft Hardcore 100% Dashboard...\n")

    log = load_run_log()
    completion = load_latest_completion()

    if not log and not completion:
        print("  No data yet. Run parse_stats.py --stats <path> --session 1 first.\n")
        return

    chart_completion_timeline(log)
    chart_category_breakdown(completion)
    chart_risk_timeline(log)
    chart_damage_timeline(log)
    chart_summary_card(log, completion)

    print(f"\n  All charts → {CHARTS_DIR}\n")
    print("  Update your README.md with:\n")
    print("  ![Completion](outputs/charts/completion_overall.png)")
    print("  ![Risk Score](outputs/charts/risk_score_timeline.png)")
    print("  ![Summary](outputs/charts/run_summary_card.png)\n")


if __name__ == "__main__":
    main()
