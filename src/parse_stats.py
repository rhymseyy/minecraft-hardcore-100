"""
parse_stats.py
--------------
Reads Minecraft's native stats JSON file (saved automatically by the game)
and outputs clean, analysis-ready dataframes.

HOW TO FIND YOUR STATS FILE:
  Windows: %appdata%/AppData/Roaming/.minecraft/saves/<WorldName>/stats/<uuid>.json
  Mac:     ~/Library/Application Support/minecraft/saves/<WorldName>/stats/<uuid>.json
  Linux:   ~/.minecraft/saves/<WorldName>/stats/<uuid>.json

USAGE:
  python src/parse_stats.py --stats path/to/<uuid>.json --session 1

  This will:
  - Parse the JSON and save a clean snapshot to data/sessions/session_001.json
  - Print a summary of current run progress
  - Output CSVs to outputs/ for dashboard use
"""

import json
import argparse
import os
import csv
from datetime import datetime
from pathlib import Path

# ── PATHS ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
OUTPUTS_DIR = ROOT / "outputs"
ITEMS_CSV = DATA_DIR / "items_required.csv"
RUN_LOG = DATA_DIR / "run_log.csv"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# ── STAT CATEGORY KEYS (Minecraft's internal naming) ──────────────────────────
STAT_KEYS = {
    "mined":      "minecraft:mined",
    "crafted":    "minecraft:crafted",
    "picked_up":  "minecraft:picked_up",
    "dropped":    "minecraft:dropped",
    "used":       "minecraft:used",
    "killed":     "minecraft:killed",
    "killed_by":  "minecraft:killed_by",
    "custom":     "minecraft:custom",
}

# Custom stats we care about for the risk score
CUSTOM_STATS = {
    "play_time":          "minecraft:play_time",          # ticks (divide by 20 for seconds)
    "time_since_death":   "minecraft:time_since_death",
    "time_since_rest":    "minecraft:time_since_rest",
    "total_world_time":   "minecraft:total_world_time",
    "damage_taken":       "minecraft:damage_taken",
    "damage_dealt":       "minecraft:damage_dealt",
    "damage_dealt_absorbed": "minecraft:damage_dealt_absorbed",
    "deaths":             "minecraft:deaths",
    "jumps":              "minecraft:jumps",
    "walk_distance":      "minecraft:walk_one_cm",        # centimetres
    "swim_distance":      "minecraft:swim_one_cm",
    "fly_distance":       "minecraft:fly_one_cm",
    "walk_under_water":   "minecraft:walk_under_water_one_cm",
    "nether_travel":      "minecraft:travel_one_cm",      # all travel combined
    "sleep_in_bed":       "minecraft:sleep_in_bed",
    "traded_with_villager": "minecraft:traded_with_villager",
    "items_enchanted":    "minecraft:enchant_item",
    "chests_opened":      "minecraft:open_chest",
    "fish_caught":        "minecraft:fish_caught",
    "mobs_killed":        "minecraft:mob_kills",
    "animals_bred":       "minecraft:animals_bred",
    "drop_count":         "minecraft:drop",
    "pickup_count":       "minecraft:pickup",
}

# High-risk mob kills — used in risk score
HIGH_RISK_MOBS = {
    "minecraft:wither":         10,
    "minecraft:ender_dragon":   10,
    "minecraft:elder_guardian": 8,
    "minecraft:warden":         10,
    "minecraft:blaze":          6,
    "minecraft:ghast":          5,
    "minecraft:creeper":        7,
    "minecraft:witch":          5,
    "minecraft:piglin_brute":   6,
    "minecraft:ravager":        7,
    "minecraft:enderman":       4,
}


def load_stats(stats_path: str) -> dict:
    """Load and return the raw Minecraft stats JSON."""
    with open(stats_path, "r") as f:
        return json.load(f)


def extract_stat(stats: dict, category: str, key: str = None) -> dict | int:
    """
    Extract a stat category or specific stat.
    category: one of STAT_KEYS values e.g. 'minecraft:mined'
    key: specific item e.g. 'minecraft:diamond'
    """
    cat = stats.get("stats", {}).get(category, {})
    if key:
        return cat.get(key, 0)
    return cat


def get_custom_stat(stats: dict, stat_key: str) -> int:
    """Get a specific custom stat by its minecraft key."""
    return stats.get("stats", {}).get("minecraft:custom", {}).get(stat_key, 0)


def parse_session(stats: dict, session_num: int) -> dict:
    """
    Parse a full session snapshot from stats JSON.
    Returns a structured dict with all relevant metrics.
    """
    custom = stats.get("stats", {}).get("minecraft:custom", {})

    # Time calculations
    play_ticks = custom.get("minecraft:play_time", 0)
    play_hours = play_ticks / 20 / 3600

    # Damage
    damage_taken = custom.get("minecraft:damage_taken", 0) / 10  # stored as tenths
    damage_dealt = custom.get("minecraft:damage_dealt", 0) / 10

    # Travel
    walk_km = custom.get("minecraft:walk_one_cm", 0) / 100000
    swim_km = custom.get("minecraft:swim_one_cm", 0) / 100000
    fly_km  = custom.get("minecraft:fly_one_cm", 0) / 100000

    # Kills
    killed = stats.get("stats", {}).get("minecraft:killed", {})
    killed_by = stats.get("stats", {}).get("minecraft:killed_by", {})
    total_kills = sum(killed.values())

    # High-risk encounters
    high_risk_kills = {
        mob: killed.get(mob, 0)
        for mob in HIGH_RISK_MOBS
        if killed.get(mob, 0) > 0
    }

    return {
        "session": session_num,
        "timestamp": datetime.now().isoformat(),
        "play_hours": round(play_hours, 2),
        "damage_taken": round(damage_taken, 1),
        "damage_dealt": round(damage_dealt, 1),
        "damage_per_hour": round(damage_taken / max(play_hours, 0.01), 2),
        "deaths": custom.get("minecraft:deaths", 0),
        "mob_kills_total": total_kills,
        "high_risk_kills": high_risk_kills,
        "walk_km": round(walk_km, 2),
        "swim_km": round(swim_km, 2),
        "fly_km":  round(fly_km, 2),
        "items_crafted_unique": len(stats.get("stats", {}).get("minecraft:crafted", {})),
        "items_picked_up_unique": len(stats.get("stats", {}).get("minecraft:picked_up", {})),
        "fish_caught": custom.get("minecraft:fish_caught", 0),
        "chests_opened": custom.get("minecraft:open_chest", 0),
        "sleep_count": custom.get("minecraft:sleep_in_bed", 0),
        "trades": custom.get("minecraft:traded_with_villager", 0),
        "animals_bred": custom.get("minecraft:animals_bred", 0),
        "enchants": custom.get("minecraft:enchant_item", 0),
        "killed_by": dict(killed_by),
    }


def load_items_required() -> list[dict]:
    """Load the master item list, skipping comment lines."""
    items = []
    with open(ITEMS_CSV, "r") as f:
        reader = csv.DictReader(
            (line for line in f if not line.startswith("#")),
            fieldnames=["item_id","display_name","category","subcategory",
                        "stack_size","obtain_method","difficulty","notes"]
        )
        next(reader, None)  # skip header row
        for row in reader:
            if row["item_id"] and not row["item_id"].startswith("#"):
                items.append(row)
    return items


def calculate_completion(stats: dict) -> dict:
    """
    Cross-reference picked_up stats against items_required.csv
    to calculate completion percentage per category and overall.
    Returns a dict with completion data.
    """
    items_required = load_items_required()
    picked_up = stats.get("stats", {}).get("minecraft:picked_up", {})
    crafted = stats.get("stats", {}).get("minecraft:crafted", {})

    results = []
    by_category = {}

    for item in items_required:
        item_id = item["item_id"]
        required = int(item["stack_size"])
        category = item["category"]

        # Check both picked_up and crafted counts
        count_picked = picked_up.get(item_id, 0)
        count_crafted = crafted.get(item_id, 0)
        count_total = max(count_picked, count_crafted)

        has_stack = count_total >= required
        pct = min(count_total / required * 100, 100)

        results.append({
            "item_id": item_id,
            "display_name": item["display_name"],
            "category": category,
            "subcategory": item["subcategory"],
            "required": required,
            "obtained": count_total,
            "has_stack": has_stack,
            "pct": round(pct, 1),
            "obtain_method": item["obtain_method"],
            "difficulty": item["difficulty"],
            "notes": item["notes"],
        })

        if category not in by_category:
            by_category[category] = {"total": 0, "complete": 0}
        by_category[category]["total"] += 1
        if has_stack:
            by_category[category]["complete"] += 1

    total_items = len(results)
    completed_items = sum(1 for r in results if r["has_stack"])
    overall_pct = round(completed_items / total_items * 100, 2) if total_items > 0 else 0

    # Category percentages
    cat_summary = {
        cat: {
            "complete": v["complete"],
            "total": v["total"],
            "pct": round(v["complete"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        }
        for cat, v in by_category.items()
    }

    return {
        "overall_pct": overall_pct,
        "completed": completed_items,
        "total": total_items,
        "remaining": total_items - completed_items,
        "by_category": cat_summary,
        "items": results,
    }


def calculate_risk_score(session: dict, completion: dict) -> float:
    """
    Composite Death Probability Index (DPI).

    Components:
      - damage_rate:     damage taken per hour (normalised)
      - high_risk_expo:  weighted high-risk mob encounters
      - sleep_debt:      proxy for phantom / fatigue risk
      - completion_rush: higher completion = riskier areas required
      - deaths:          past deaths (even 0 in hardcore = tension indicator)

    Returns a score 0.0–10.0
    """
    play_hours = max(session.get("play_hours", 0.01), 0.01)

    # 1. Damage rate (0–3 points)
    dmg_per_hour = session.get("damage_per_hour", 0)
    damage_component = min(dmg_per_hour / 50, 1.0) * 3.0

    # 2. High-risk mob exposure (0–3 points)
    high_risk_kills = session.get("high_risk_kills", {})
    risk_exposure = sum(
        HIGH_RISK_MOBS.get(mob, 1) * count
        for mob, count in high_risk_kills.items()
    )
    risk_component = min(risk_exposure / 20, 1.0) * 3.0

    # 3. Sleep debt — time_since_rest proxy (0–2 points)
    # If player hasn't slept and it's been a while, phantoms spawn
    sleep_count = session.get("sleep_count", 0)
    session_hours = play_hours
    expected_sleeps = session_hours / 2  # ~1 sleep per 2 hours is safe
    sleep_debt = max(0, expected_sleeps - sleep_count)
    sleep_component = min(sleep_debt / 5, 1.0) * 2.0

    # 4. Completion pressure (0–2 points)
    # As you complete more, you need rarer / more dangerous items
    completion_pct = completion.get("overall_pct", 0)
    completion_component = (completion_pct / 100) * 2.0

    total = damage_component + risk_component + sleep_component + completion_component
    return round(min(total, 10.0), 2)


def save_session_snapshot(stats: dict, session_num: int) -> Path:
    """Save a timestamped copy of the raw stats JSON to data/sessions/."""
    filename = SESSIONS_DIR / f"session_{session_num:03d}.json"
    with open(filename, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  ✓ Session snapshot saved → {filename}")
    return filename


def save_completion_csv(completion: dict, session_num: int) -> Path:
    """Save per-item completion data as CSV."""
    filename = OUTPUTS_DIR / f"completion_session_{session_num:03d}.csv"
    fields = ["item_id", "display_name", "category", "subcategory",
              "required", "obtained", "has_stack", "pct",
              "obtain_method", "difficulty", "notes"]
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(completion["items"])
    print(f"  ✓ Completion CSV saved → {filename}")
    return filename


def save_session_log(session: dict, completion: dict, risk: float) -> None:
    """Append this session's summary to run_log.csv."""
    log_fields = [
        "session", "timestamp", "play_hours", "damage_taken",
        "damage_per_hour", "mob_kills_total", "fish_caught",
        "chests_opened", "sleep_count", "trades", "enchants",
        "overall_pct", "completed_items", "remaining_items", "risk_score",
        "session_notes"
    ]
    write_header = not RUN_LOG.exists()
    with open(RUN_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=log_fields)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "session":          session["session"],
            "timestamp":        session["timestamp"],
            "play_hours":       session["play_hours"],
            "damage_taken":     session["damage_taken"],
            "damage_per_hour":  session["damage_per_hour"],
            "mob_kills_total":  session["mob_kills_total"],
            "fish_caught":      session["fish_caught"],
            "chests_opened":    session["chests_opened"],
            "sleep_count":      session["sleep_count"],
            "trades":           session["trades"],
            "enchants":         session["enchants"],
            "overall_pct":      completion["overall_pct"],
            "completed_items":  completion["completed"],
            "remaining_items":  completion["remaining"],
            "risk_score":       risk,
            "session_notes":    "",  # fill manually after each session
        })
    print(f"  ✓ Run log updated → {RUN_LOG}")


def print_summary(session: dict, completion: dict, risk: float) -> None:
    """Print a clean terminal summary after parsing."""
    print("\n" + "═" * 55)
    print(f"  MINECRAFT HARDCORE 100% — SESSION {session['session']}")
    print("═" * 55)
    print(f"  ⏱  Play time:       {session['play_hours']}h")
    print(f"  💥  Damage taken:   {session['damage_taken']} HP")
    print(f"  ☠️   Damage/hour:    {session['damage_per_hour']} HP/h")
    print(f"  ⚔️   Mob kills:      {session['mob_kills_total']}")
    print(f"  😴  Sleeps:         {session['sleep_count']}")
    print()
    print(f"  📦  COMPLETION:     {completion['overall_pct']}%")
    print(f"       Items done:    {completion['completed']} / {completion['total']}")
    print(f"       Remaining:     {completion['remaining']}")
    print()
    print("  📊  By Category:")
    for cat, data in sorted(completion["by_category"].items(),
                            key=lambda x: x[1]["pct"], reverse=True):
        bar_len = int(data["pct"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"       {cat:<18} {bar} {data['pct']:5.1f}%  ({data['complete']}/{data['total']})")
    print()
    print(f"  🎲  RISK SCORE:     {risk} / 10.0")
    risk_label = (
        "LOW — keep going"        if risk < 3 else
        "MODERATE — stay sharp"   if risk < 5 else
        "HIGH — be careful"       if risk < 7 else
        "CRITICAL — slow down"
    )
    print(f"       Status:        {risk_label}")

    if session.get("high_risk_kills"):
        print()
        print("  ⚠️   High-risk encounters this run:")
        for mob, count in session["high_risk_kills"].items():
            mob_name = mob.replace("minecraft:", "").replace("_", " ").title()
            print(f"       {mob_name:<22} ×{count}")

    if session.get("killed_by"):
        print()
        print("  💀  Killed by (so far — this is hardcore, be careful):")
        for mob, count in session["killed_by"].items():
            mob_name = mob.replace("minecraft:", "").replace("_", " ").title()
            print(f"       {mob_name:<22} ×{count}")

    print("═" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Parse Minecraft stats JSON for Hardcore 100% tracking"
    )
    parser.add_argument(
        "--stats",
        required=True,
        help="Path to your Minecraft stats JSON file (saves/<World>/stats/<uuid>.json)"
    )
    parser.add_argument(
        "--session",
        type=int,
        required=True,
        help="Session number (1, 2, 3, ...)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print summary only, don't save files"
    )
    args = parser.parse_args()

    print(f"\nParsing stats from: {args.stats}")

    # Load and parse
    stats = load_stats(args.stats)
    session = parse_session(stats, args.session)
    completion = calculate_completion(stats)
    risk = calculate_risk_score(session, completion)

    # Print summary
    print_summary(session, completion, risk)

    if not args.no_save:
        print("Saving outputs...")
        save_session_snapshot(stats, args.session)
        save_completion_csv(completion, args.session)
        save_session_log(session, completion, risk)
        print("\nDone. Run 'python src/dashboard.py' to regenerate charts.\n")


if __name__ == "__main__":
    main()
