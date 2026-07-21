# Methodology — Death Probability Index (DPI)

## Overview

The Death Probability Index is a composite risk score (0.0–10.0) computed after each play session. It quantifies how dangerous the current state of the run is, based on measurable in-game behaviour. The higher the score, the more likely death becomes if risk behaviour continues.

## Data Source

All input data comes from Minecraft's native `stats/<uuid>.json` file, saved automatically by the game after each session ends. No mods required.

## Formula

```
DPI = damage_component + risk_component + sleep_component + completion_component
```

Where each component is normalised to its maximum contribution (sum = 10.0):

### 1. Damage Component (max 3.0 points)

```python
damage_per_hour = cumulative_damage_taken / total_play_hours
damage_component = min(damage_per_hour / 50, 1.0) * 3.0
```

- **What it measures:** Rate of damage taken per hour of gameplay
- **Normalisation:** 50 HP/hour = maximum contribution (3.0)
- **Rationale:** A player taking damage faster than they can regenerate is statistically closer to death

### 2. Risk Exposure Component (max 3.0 points)

```python
risk_exposure = sum(MOB_WEIGHTS[mob] * kill_count for mob in high_risk_kills)
risk_component = min(risk_exposure / 20, 1.0) * 3.0
```

Mob weights:

| Mob | Weight | Rationale |
|-----|--------|-----------|
| Warden | 10 | Near-instant death if caught |
| Wither | 10 | Boss fight, wither effect, projectiles |
| Ender Dragon | 10 | Required for 100% run |
| Elder Guardian | 8 | Mining fatigue + high damage |
| Piglin Brute | 6 | High DPS, no aggro warning |
| Blaze | 6 | Fire + ranged in Nether |
| Ravager | 7 | Very high melee damage |
| Creeper | 7 | Instant explosion, no warning at night |
| Witch | 5 | Instant Harming II potions |
| Ghast | 5 | Ranged, explosion on miss |
| Enderman | 4 | Teleports, high health |

- **What it measures:** Cumulative danger of mobs encountered
- **Rationale:** Each high-risk mob kill represents a dangerous encounter survived; more encounters = higher cumulative risk

### 3. Sleep Debt Component (max 2.0 points)

```python
expected_sleeps = play_hours / 2       # safe = 1 sleep per 2 hours
sleep_debt = max(0, expected_sleeps - actual_sleeps)
sleep_component = min(sleep_debt / 5, 1.0) * 2.0
```

- **What it measures:** Phantom spawn risk — Minecraft spawns phantoms after 3 in-game nights without sleep
- **Rationale:** Phantoms add unpredictable aerial damage; sleep debt is a measurable proxy
- **Note:** This component incentivises regular sleep, which also resets the spawn point

### 4. Completion Pressure Component (max 2.0 points)

```python
completion_component = (overall_completion_pct / 100) * 2.0
```

- **What it measures:** How far into the run you are
- **Rationale:** As completion increases, the remaining items become progressively harder and more dangerous to obtain (Ancient City, Nether Fortress, End Cities, Wither fight, Elder Guardian). A 90% complete run requires entering more dangerous areas than a 10% run.
- **This is the most interesting component:** It means risk always increases as you approach the goal, even if your play improves.

## Thresholds

| DPI | Status |
|-----|--------|
| 0.0–2.9 | 🟢 LOW — sustainable pace |
| 3.0–4.9 | 🟡 MODERATE — stay sharp |
| 5.0–6.9 | 🟠 HIGH — reduce aggression |
| 7.0–10.0 | 🔴 CRITICAL — slow down, prepare, consider postponing risky activities |

## Limitations

1. **Cumulative vs. session-level:** The current DPI uses cumulative stats. A future version will compute per-session delta DPI (change in risk this session vs. last session), which will be more sensitive to sudden spikes.
2. **Death doesn't exist in this run (hardcore):** The `deaths` counter should remain 0. Any non-zero value means the run is over. A future field will track the run outcome.
3. **Context is not captured by the formula:** A 9.0 DPI because you fought the Wither is different from a 9.0 DPI because you keep taking creeper damage at night. Session notes in `run_log.csv` provide this context.
4. **The formula will be recalibrated after the first complete run.** Weights are initialised based on in-game mechanics knowledge; empirical recalibration will follow.

## Future Enhancements

- Delta DPI (session-over-session change)
- Biome exposure tracking (Nether time as separate component)
- Economic pressure score (inventory fullness, resource reserves)
- Predictive model: logistic regression trained on the run log to estimate P(death in next session)

---

*This document is updated as the methodology evolves.*  
*Last updated: April 2026*
