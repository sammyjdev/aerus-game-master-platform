> Extracted from the campaign missions master document - index and mission structure.

# Aerus RPG - Campaign Missions and Narrative Arcs

> Companion document to the project bible.
> Canonical source for faction missions, campaign arc structure, and narrative convergence.

---

## Index

1. [Mission Structure](#mission-structure)
2. [Church of the Pure Flame](#church-of-the-pure-flame)
3. [Empire of Valdrek](#empire-of-valdrek)
4. [Guild of Threads](#guild-of-threads)
5. [Children of the Broken Thread](#children-of-the-broken-thread)
6. [Main Narrative Arcs](#main-narrative-arcs)
7. [Convergence - The Last Chamber](#convergence---the-last-chamber)

---

## Mission Structure

Each mission entry follows this format:

```text
mission_id      - unique slug
Faction         - who offers the mission
Reputation      - minimum score required to unlock it
Objective       - what the players must accomplish
Hidden agenda   - what the faction actually wants
Location        - where it happens
Key NPC         - who intermediates the mission
Reward          - reputation delta + currency + item
Conflict        - which other factions lose reputation
Unlocks         - which mission becomes available next
```

**Reputation conflict rule:** When players complete a faction mission, the GM should automatically apply a partial negative delta to antagonistic factions. See the faction systems document for the cross-conflict table.
