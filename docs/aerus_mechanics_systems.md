# Aerus RPG - Systems Reference

> Consolidated reference for rumors, Flame Seals, and faction reputation.

---

## Port Myr Rumor System

Rumors are one of the easiest ways to make Port Myr feel alive. They should mix truth, distortion, fear, and opportunism.

### Design Rules

- A good rumor should point toward action, not only atmosphere.
- Not every rumor should be accurate.
- True rumors should become more valuable after later confirmation.
- Dangerous rumors should create faction interest or player risk.

### Example Rumor Types

- imperial instability
- guild accidents and sealed archives
- Broken Thread activity
- suspicious arrivals by sea
- anomalies linked to the Dome or the Thread

---

## Flame Seal System

### What Flame Seals Are

Flame Seals are the Church of the Pure Flame's licensing and control system for magic use in regulated territories. In practice they are both a legal instrument and an ideological cage.

### Major Seal Categories

| Seal | Access Level | Typical Use |
| --- | --- | --- |
| Common Seal | low-tier elemental use | public civilian use |
| Trade Seal | professional licensed use | healers, crafters, sanctioned specialists |
| High Flame Seal | advanced or restricted magic | high clergy and elite imperial agents |
| Null Seal | suppressive restraint | magical prisoners |
| Conclave Authorization | guild-internal unrestricted status | high-trust internal circulation |

### Gameplay Effects

- Public magic without valid authorization increases institutional pressure.
- False seals can bypass casual inspection but collapse under expert scrutiny.
- Repeated use of church-issued seals damages standing with anti-control factions.
- Deep corruption zones can destabilize or destroy seal-bound objects.

### Black Market Role

Port Myr is a natural center for forged seals, smuggling, and document laundering. This makes seals a mechanical tool, a social risk, and a faction hook all at once.

---

## Faction Reputation

### Core Factions

- `church_pure_flame`
- `empire_valdrek`
- `guild_of_threads`
- `children_of_broken_thread`
- `myr_council`

### Reputation Bands

| Score | Meaning |
| --- | --- |
| -100 to -50 | hostile enemy |
| -49 to -20 | distrusted |
| -19 to 19 | neutral or unknown |
| 20 to 49 | friendly |
| 50 to 100 | allied |

### General Effects

- Higher reputation unlocks access, information, protection, and missions.
- Lower reputation increases surveillance, refusal of service, obstruction, and violence.
- Extreme positive or negative values should have persistent campaign consequences.

### Typical Positive Triggers

- completing faction-aligned missions
- protecting faction assets
- sharing useful intelligence
- reinforcing the faction's ideology in public

### Typical Negative Triggers

- helping a rival faction
- exposing secrets
- sabotaging operations
- publicly rejecting a faction's authority
- violence against members or institutions

---

## Cross-Faction Pressure

Some actions should raise one faction while lowering another.

Examples:

- helping the Church enforce magical control harms relations with the Guild and the Broken Thread
- assisting imperial surveillance harms relations with smugglers and dissidents
- exposing hidden truths may help the Guild while damaging imperial trust
- protecting contraband networks may help the Myr Council while angering the Empire

This cross-pressure is important because it makes alignment meaningful without forcing simplistic moral binaries.

---

## Runtime Event Shape

Reputation changes should remain easy for the backend to emit and the frontend to display.

```json
{
  "type": "faction_reputation",
  "faction_id": "guild_of_threads",
  "delta": 10,
  "reason": "Shared unstable archive findings with the Guild"
}
```

Rules:

- `faction_id` must match the normalized runtime identifiers
- `delta` must be an integer
- multiple faction changes may be emitted from the same action

---

## GM Guidance

- Reputation should change because of visible action, not hidden bookkeeping alone.
- Rumors should create movement.
- Seals should create tension between legality and necessity.
- Factions should feel ideological, material, and human at the same time.
