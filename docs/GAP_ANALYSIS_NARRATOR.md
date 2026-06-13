# GAP ANALYSIS NARRATOR — AERUM RPG

> Gap analysis document for training the narrator model (SLM fine-tune).
> Produced on: 2026-04-14
> Based on a complete reading of all the documentation listed.

---

## LEGEND

- ✅ Covered — rule, example, or protocol documented in the indicated source.
- PARTIAL — something exists, but it is incomplete or ambiguous for the GM.
- ❌ MISSING — no relevant documentation exists.
- **CRITICAL** — the absence breaks the session.
- **HIGH** — the absence leads to wrong improvisation.
- **MEDIUM** — the absence makes the narration generic.

---

## SECTION 1 — MECHANICS THAT DICTATE THE NARRATIVE

---

### COMBAT

---

#### Initiative and turn order

- (a) Arbitration rule: ❌ MISSING — No document defines the attribute used, the die rolled, or tie-breakers.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no rule for ties, multiple enemies, or a "surprise round".

---

#### Successful attack by type (physical, magical, ranged)

- (a) Arbitration rule: ❌ MISSING — aerus_base_classes.md describes combat roles but does not define the attack die, defense DC, or damage formula.
- (b) Narrative example: PARTIAL — narration_bible.md and narration_bible_kernel.md have tone guidelines ("dry, tense sentences") but no example of resolving a hit.
- (c) Edge cases: ❌ MISSING — no rule for an attack vs. Keth armor, an attack with a magical seal in a corrupted zone, or maximum range.

---

#### Failed attack and exposed flank

- (a) Arbitration rule: ❌ MISSING — no "miss" mechanic documented; there is no mechanical consequence for a failure.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Critical hit (natural 20) — what changes in the narrative

- (a) Arbitration rule: ❌ MISSING — no definition of "natural 20" for Aerum; the attribute table exists (STR, DEX, INT, VIT, LUK, CAR) but with no crit mechanic.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Critical failure (natural 1) — mandatory consequence

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Damage by element type (fire, ice, earth, air, energy, spirit)

- (a) Arbitration rule: PARTIAL — world_kernel.md lists corruption effects by element ("fire -> burns the caster; water -> necrotizes; earth -> erodes consciousness; air -> attracts an Echo; energy -> causes a Surge; spirit -> awakens something"), BUT only as a backfire risk, not as a damage formula against targets.
- (b) Narrative example: ❌ MISSING — no example of how to narrate an ice hit vs. a fire creature, for instance.
- (c) Edge cases: ❌ MISSING — no rule for immunity, resistance, or healing from a matching element.

---

#### Damage in a corruption zone (unstable magic)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_magic_isekai.md §Aeridian Fragments states that within 50m of a Fragment magic is completely stable; aerus_mechanics_languages_crafting.md §Keth by Grade lists stabilization grades; world_kernel.md lists backfire effects. But there is no instability probability table by zone, nor any numerical penalty.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for defensive magic in a corrupted zone, nor a difference between a T2 vs. a T4 zone.

---

#### Instant death vs. 0 HP vs. stabilization

- (a) Arbitration rule: ❌ MISSING — campaign.yaml confirms `permadeath: true` and `difficulty: brutal` but does not define an HP threshold, "death saves", or a stabilization protocol.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Character Death has a voice fragment ("There is no heroic final monologue, only the abrupt violence of a life interrupted") but no mechanical protocol.
- (c) Edge cases: ❌ MISSING — no rule for a character at 1 HP, an unconscious character, or stabilization by an ally.

---

#### Permanent death (permadeath) — narrative protocol

- (a) Arbitration rule: PARTIAL — campaign.yaml `permadeath: true` confirms that death is permanent; aerus_mechanics_magic_isekai.md §Model: Log Horizon confirms "Death is real death." But there is no protocol for what the GM should do immediately after a death.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Character Death has 4 lines of voice but does not say whether the GM pauses, transitions, or continues the scene.
- (c) Edge cases: ❌ MISSING — no rule for death from area damage (who dies first?), or death during combat with multiple players.

---

#### A dead character becomes a spectator — narrative transition

- (a) Arbitration rule: ❌ MISSING — no document describes what happens mechanically after death: can the player watch the scene? participate? create a new character immediately?
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a "spectator with a secret objective still active" or a "spectator who knows vital information".

---

#### Multiple attackers on the same target

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Area attack in a mixed group (allies + enemies)

- (a) Arbitration rule: ❌ MISSING — campaign.yaml has `friendly_fire: false` but does not explain how this interacts narratively with area magic.
- (b) Narrative example: ❌ MISSING — no example of how to narrate an area spell that technically does not affect allies but puts them in visible danger.
- (c) Edge cases: ❌ MISSING — what if the allied target is incapacitated inside the zone?

---

#### Combat on special terrain (ruin, corrupted zone, water, altitude)

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Combat Scenes mentions "terrain" as an element that makes a fight unique, but with no mechanical modifiers.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Danger Zone has a voice fragment for the Ash Desert, but none for combat inside a corrupted zone.
- (c) Edge cases: ❌ MISSING — no rule for combat inside Ondrek Pass (a no-magic zone), water, or extreme altitude.

---

#### Fleeing combat — when it is possible, how to narrate it

- (a) Arbitration rule: ❌ MISSING — no document defines a flee condition (HP threshold? a specific action? a cost?).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no rule for fleeing when surrounded, fleeing a boss, or a pursuit after fleeing.

---

#### Enemy surrender — what happens mechanically

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for an enemy who surrenders and then betrays, or for executing a surrendered enemy and the reputation consequence.

---

#### Monster with a phase (boss phase change) — trigger and narrative

- (a) Arbitration rule: ❌ MISSING — no HP threshold or condition defined for the phase change.
- (b) Narrative example: ✅ aerus_gm_guide.md §Boss Phase Change — a complete exemplary fragment ("The second phase does not announce itself... The party has one turn.").
- (c) Edge cases: ❌ MISSING — no rule for how many phases exist, whether the phase change heals HP, or whether the GM should give advance warning.

---

#### Combat against an allied NPC (betrayal, mind control)

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for "an allied NPC under mind control attacks a player" or "a player with a secret objective to eliminate the ally".

---

#### Battle while another player performs a different action

- (a) Arbitration rule: PARTIAL — CLAUDE.md mentions the 3s batch system (`action_batch_window_seconds: 3`) but does not define how the GM resolves narrative simultaneity.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for player B negotiating while player A is in combat in the same scene.

---

### CONDITIONS AND STATES

---

#### Complete list of system conditions (stunned, poisoned, etc.)

- (a) Arbitration rule: ❌ MISSING — no document lists Aerum's status conditions. aerus_mechanics_systems.md does not define a list of conditions. Only world_kernel.md mentions "progressive corruption" as a backfire effect.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### How long each condition lasts

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### How to narrate the application of each condition

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### How to narrate the removal of each condition

- (a) Arbitration rule: ❌ MISSING — narration_bible_kernel.md mentions "Healing and recovery must indicate the source" but not by condition type.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Conditions that interact with each other

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Progressive magical corruption — stages and narrative per stage

- (a) Arbitration rule: PARTIAL — world_kernel.md lists backfire effects by element but with no numbered stages or accumulation threshold. aerus_mechanics_magic_isekai.md mentions Travelers' vulnerability to corruption but with no scale.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for "a character at corruption stage 3 who uses healing magic".

---

#### Rooting of the Travelers — how it changes the narrative per stage

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §Rooting — a table of 5 periods with defined physical/narrative signs.
- (b) Narrative example: PARTIAL — the table describes the sign ("The Thread becomes perceptible as atmospheric pressure") but does not illustrate how the GM should narrate it in a scene.
- (c) Edge cases: ❌ MISSING — no protocol for a player trying to leave before rooting is complete, or for two Travelers at different stages in the same scene.

---

#### Frenzy or loss of character control

- (a) Arbitration rule: ❌ MISSING — no document defines a trigger or mechanic for frenzy/loss of control.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### MAGIC AND THE PRIMORDIAL THREAD

---

#### Surge — what triggers it, how to escalate it, how to narrate it

- (a) Arbitration rule: PARTIAL — world_kernel.md defines "energy -> causes a Surge" as a backfire. aerus_lore_cosmology_history.md explains that Surges are Vor'Athek pressing against the prison. But there is no Surge DC table, radius scale, or trigger by magic level.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Danger Zone has danger-zone voice but no specific example of a Surge in progress.
- (c) Edge cases: ❌ MISSING — no rule for a Surge caused by a destroyed Fragment (cited in aerus_mechanics_magic_isekai.md as "energy equivalent to a maximum-grade Surge" but with no narrative protocol).

---

#### Backfire in a corrupted zone — probability and consequences

- (a) Arbitration rule: PARTIAL — world_kernel.md lists backfire types by element. aerus_mechanics_languages_crafting.md §Keth by Grade implies that Keth reduces risk but with no number. There is no probability table by zone (T1-T5).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no rule for a character with an Aeridian Fragment in a corrupted zone, or the effect of Keth Grade 4 vs. Grade 1.

---

#### Two simultaneous spells on the same target

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Elemental fusion (when two elements interact)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_magic_isekai.md §Alchemical Fusions has a requirements table (minimum level in the base elements), but does not define what happens when two players use different elements on the same turn without coordination.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no rule for unintentional fusion (fire vs. water from two players).

---

#### Healing magic that causes necrosis (Thread corruption)

- (a) Arbitration rule: PARTIAL — aerus_lore_cosmology_history.md and world.md mention that "healing magic could cause necrosis" as an effect of Thread corruption; world_kernel.md lists "water -> necrotizes". But there is no DC for when this happens, nor a protocol for how much necrosis it causes.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a healer with Keth vs. without Keth, or healing in a zone stabilized by a Fragment.

---

#### Partial vs. total spell failure

- (a) Arbitration rule: ❌ MISSING — no document distinguishes partial failure (reduced effect) from total failure (nothing happens) from backfire (negative effect).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Open Channel (Channeler) — narrative risk and reward

- (a) Arbitration rule: PARTIAL — aerus_base_classes.md §Channeler describes "Open Channel" as a base ability that "temporarily aligns the self with a source of power for increased effect and increased risk." But with no definition of the risk (DC? damage? duration?).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a Channeler who keeps the channel open across multiple turns, or an open channel in a corrupted zone.

---

#### Using magic without a Flame Seal in imperial territory

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §Flame Seals + aerus_mechanics_systems.md §Flame Seal System — defines Seal categories, that using magic without authorization "increases institutional pressure", and that forgeries collapse under specialized inspection.
- (b) Narrative example: PARTIAL — aerus_mechanics_systems.md §Black Market Role and §Gameplay Effects describe abstract consequences but with no concrete scene example.
- (c) Edge cases: PARTIAL — aerus_mechanics_magic_isekai.md mentions that "Kethara never adopted the system, and Myr accepts Seals but does not require them" — useful, but with no protocol for a transition zone (entering imperial territory by sea).

---

#### Aeridian Fragment nearby — how it changes magic

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §Aeridian Fragments — "Within a 50-meter radius, magic becomes completely stable."
- (b) Narrative example: PARTIAL — aerus_lore_dome_factions.md §The Dome Mark mentions that the Mark "pulses more intensely near Aeridian Fragments" but with no narrative example of what the GM describes to the player.
- (c) Edge cases: ❌ MISSING — no protocol for two nearby Fragments, a corrupted Fragment (the Valdek IV case), or a destroyed Fragment.

---

#### Crystal of Silence — effect on surrounding magic

- (a) Arbitration rule: PARTIAL — aerus_lore_cosmology_history.md mentions that it "emits a low-frequency sound that humans do not hear but animals avoid" and that "the vault should never remain open for long." campaign_mission_arcs.md §Arc III mentions that the Guild wants the Travelers to carry the Crystal to the Last Chamber. But with no definition of its effect radius, its effect on spells, or its interaction with corrupted zones.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### PROGRESSION AND MUTATION

---

#### Level up during a session — when it happens, how to narrate it

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md mentions "Actions with real impact... must yield explicit XP in the state." campaign.yaml defines `level_cap: 100` and `passive_milestone_every_points: 25`. But there is no DC for the XP required per level, nor a protocol for when to interrupt the scene to narrate the level up.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for two players leveling on the same turn, or leveling during combat.

---

#### Passive milestone unlocked — narrative interruption or not

- (a) Arbitration rule: ❌ MISSING — campaign.yaml defines `passive_milestone_every_points: 25` and `class_mutation_every_levels: 25` but with no narrative protocol for how the GM communicates the unlock.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Formal mutation (levels 25/50/75/100) — narrative protocol

- (a) Arbitration rule: PARTIAL — aerus_class_mutations.md §Mutation Framework defines expected outcomes per level but with no protocol for how the GM presents the options to the player or how it narrates the transformation.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a mutation rejected by the player, or a mutation in the context of active combat.

---

#### Attribute reaching the cap (250 per attribute) — narrative consequence

- (a) Arbitration rule: PARTIAL — campaign.yaml defines `attribute_per_cap: 250` and `attribute_campaign_cap: 500`. But with no narrative protocol for what happens when an attribute is maxed out.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### XP by action type (combat, diplomacy, objective)

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md: "Actions with real impact, that resolve an obstacle, save someone, or advance the story, must yield explicit XP in the state." But with no table of XP amounts by action type.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for diplomacy that partially fails, or an objective completed in an unforeseen way.

---

#### Wrongly inferred class — how to correct it without breaking the narrative

- (a) Arbitration rule: ❌ MISSING — CLAUDE.md mentions `behavior_trajectory.py` which "scores player episodes by action category; drives class mutation path selection" but with no narrative correction protocol.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Two players leveling at the same time

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### CRAFTING AND ECONOMY

---

#### Successful crafting attempt — narrating the process

- (a) Arbitration rule: ✅ aerus_mechanics_languages_crafting.md §Principle — "Crafting is resolved narratively by the GM using the recipe tables... The GM describes the process, calls for an attribute check against a difficulty class, and narrates the result."
- (b) Narrative example: ❌ MISSING — the document defines the protocol but does not provide an example of narrating a successful craft.
- (c) Edge cases: ❌ MISSING — no protocol for a partially successful craft (passed the DC but by 1), or crafting under adverse conditions.

---

#### Crafting failure — consequence (broken item, lost ingredient, accident)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_languages_crafting.md defines the check (INT DC X or STR DC X) but does not define what happens on failure: is the ingredient consumed? does the item break? is there damage to the crafter?
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Critical crafting failure — severe consequence

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Crafting in a corrupted zone with Keth

- (a) Arbitration rule: PARTIAL — aerus_mechanics_languages_crafting.md §Keth by Grade defines that Keth stabilizes magic of the corresponding level, but with no specific protocol for crafting in a corrupted T3+ zone even with Keth Grade 3.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Consumable item used in combat — narrative timing

- (a) Arbitration rule: ❌ MISSING — no document defines whether using a potion consumes a turn action, a free action, or has a timing restriction in combat.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Trade and price negotiation with an NPC

- (a) Arbitration rule: PARTIAL — aerus_lore_geopolitics_economy.md §Regional Price Table has regional prices, reputation_gates.yaml has a 15% discount for Myr Council friendly. But with no attribute-check protocol for haggling.
- (b) Narrative example: PARTIAL — narration_bible.md §Response to a social action has an example of an NPC reacting, but with no context of price negotiation specifically.
- (c) Edge cases: ❌ MISSING — no protocol for negotiating with a hostile NPC (-50 or below), or for an illegal item.

---

#### Buying an illegal item (gray market)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §Black Market Role and aerus_lore_geopolitics_economy.md §Gray Market in Port Myr describe the market. aerus_main_npcs.md cites Seyla Vorn as a Keth supplier with no paperwork. But with no DC for finding a seller, risk of being caught, or specific reputation consequence.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for an item bought on the black market being found during an imperial inspection.

---

#### Stolen item being recognized by its owner

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### TRAVEL AND ENCOUNTERS

---

#### Travel encounter in each terrain type

- (a) Arbitration rule: ✅ aerus_travel.md §Encounter Types by Terrain + backend/config/travel.yaml §encounter_tables — complete tables by terrain with roll ranges, types, and tiers.
- (b) Narrative example: PARTIAL — aerus_gm_guide.md §Danger Zone has a fragment for the Ash Desert; aerus_travel.md mentions short descriptions by type. But with no narrative examples for each specific encounter.
- (c) Edge cases: PARTIAL — aerus_travel.md §Special Location Notes covers Gorath Fissures, Vel'Arath, Limen, Keth-Ara, Wandering Cities, and Heart of Ashes with special notes. But with no protocol for "an encounter during camp" or "two encounters on the same day".

---

#### Encounter of a Tier above the party — mandatory flight?

- (a) Arbitration rule: PARTIAL — travel.yaml §corrupted lists "Abyss Lord — Abyss Lord encounter where escape is wiser than combat" (tier 4) but with no mandatory flight mechanic or "fight or flee" rule by tier difference.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Arrival at a new location during an active mission

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Arrival Scenes has a 4-point checklist but with no integration with active mission state.
- (b) Narrative example: PARTIAL — narration_bible.md §Scene Opening has a 3-beat structure with a concrete Port Myr example.
- (c) Edge cases: ❌ MISSING — no protocol for arriving at a location where the party is "wanted" (reputation gate `empire_hostile_wanted`).

---

#### Extreme weather during travel (magical storm, arctic snow)

- (a) Arbitration rule: PARTIAL — travel.yaml lists "ice_storm: Blizzard with near-zero visibility and hypothermia risk" and "storm: Storm damages the ship and may push it off course" as encounter types but with no mechanical rules for damage or penalty.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a magical vs. a normal storm, or hypothermia in a VIT mechanic.

---

#### Boat travel vs. overland — narrative differences

- (a) Arbitration rule: PARTIAL — travel.yaml defines speed multipliers (sea: 0.6 = faster; mountain: 3.0 = slower) and different encounter tables. But with no explicit narrative difference (discomfort, different risk, NPCs encountered).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a shipwreck, pirate boarding, or group separation on the open sea.

---

#### Travel through the Pale Belt (Void Zone) — special effects

- (a) Arbitration rule: PARTIAL — aerus_lore_geography.md mentions "Permanent fog, pervasive danger, and only one truly safe crossing through Ondrek Pass." aerus_mechanics_magic_isekai.md §Flame Seals implies that magic does not work in Ondrek Pass. But with no table of Void Zone effects on magic, HP, or orientation.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a Khorathi (Body Without Thread) vs. a Channeler traveling through the Void Zone.

---

#### Vel'Arath — special entry rules

- (a) Arbitration rule: PARTIAL — aerus_travel.md §Special Location Notes: "The forest decides who may enter. There is no fixed route; duration is narrative." travel.yaml notes "The forest only admits those it chooses." But with no criterion for whom the forest admits, nor a mechanic for attempt and refusal.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a Wandering Fae trying to enter, or a group with one non-admitted member.

---

#### Heart of Ashes — mandatory narrative preparation

- (a) Arbitration rule: PARTIAL — aerus_travel.md and travel.yaml list "Extremely dangerous. Not recommended below level 100." campaign_mission_arcs.md describes what exists there (Last Chamber). But with no mandatory preparation checklist (equipment, minimum level, protection against corruption).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a subleveled party that insists on going.

---

#### Camping and resting — how much it recovers, how much time passes

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md: "The location matters: a safe bed, temple, or inn improves recovery; danger and interruption reduce it. Healing and recovery must indicate the source: light rest, safe sleep, first aid, potion, ritual, or magic." But with no concrete number of HP/MP recovered by rest type.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for resting in a corrupted zone (does it recover less? does it accumulate corruption?).

---

#### Ambush during rest

- (a) Arbitration rule: ❌ MISSING — no document defines a "sleeping party" penalty (no armor, no normal initiative, etc.).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### SOCIAL AND FACTIONS

---

#### Reputation check before interacting with an NPC

- (a) Arbitration rule: ✅ aerus_mechanics_systems.md §Reputation Bands + §General Effects — defines the bands and general effects. reputation_gates.yaml defines content gates unlockable by threshold.
- (b) Narrative example: PARTIAL — aerus_npc_sheets.md and aerus_main_npcs.md have an "initial posture" per NPC but with no example of how the GM adjusts the narration for each reputation band.
- (c) Edge cases: ❌ MISSING — no protocol for an NPC who does not know the party's reputation (unknown city), or an NPC with a memory of a specific event that contradicts the current reputation.

---

#### Hostile NPC (-50 or below) — can it attack immediately?

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §General Effects: "Lower reputation increases surveillance, refusal of service, obstruction, and violence." reputation_gates.yaml cites "Church inquisitors are now actively tracking the player" and "Imperial soldiers in any location will challenge them on sight." But with no protocol for when violence is immediate vs. gradual.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a hostile NPC in a neutral location (Port Myr), or for a party with different reputation per player.

---

#### Allied NPC (+50 or above) — what it does spontaneously

- (a) Arbitration rule: PARTIAL — reputation_gates.yaml defines specific benefits per gate (military escort, smuggling route, etc.) but with no general behavior for an allied NPC outside the documented gates.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for an allied NPC in danger and spontaneous rescue behavior.

---

#### Trying to persuade an NPC of an enemy faction

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §General Effects implies increased difficulty but with no attribute modifier or specific DC.
- (b) Narrative example: PARTIAL — narration_bible.md §Response to a social action has structure and an example (Maren Toss) but with no enemy-faction context.
- (c) Edge cases: ❌ MISSING — no protocol for an NPC who is persuaded to betray their faction, and the resulting reputation consequence.

---

#### Revealing a Traveler's identity (the Dome Mark) in a hostile context

- (a) Arbitration rule: ✅ aerus_mechanics_magic_isekai.md §How NPCs React to the Mark — a table by region with specific reactions and NPC dialogue lines.
- (b) Narrative example: ✅ aerus_mechanics_magic_isekai.md — NPC dialogue such as "Roll your sleeve up, or I will ask anyway." and "Traveler. Good. You people usually die fast or last long."
- (c) Edge cases: PARTIAL — aerus_lore_dome_factions.md §The Dome Mark describes the Mark's behavior (it cannot be permanently removed, it pulses near Fragments, it goes cold in places where a Traveler died). But with no protocol for the Mark pulsing during a secret diplomatic negotiation, or for actively trying to hide the Mark.

---

#### A rumor being spread by the players — how to track it

- (a) Arbitration rule: PARTIAL — CLAUDE.md mentions `rumor_manager.py` which "injects faction-biased rumor variants per player into L2 context once per rumor_id". rumors.yaml has a base + faction-variants structure. But with no protocol for what happens when a player creates a new rumor (not listed in the yaml).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a true vs. false rumor spread by the players, or a rumor that contradicts canon.

---

#### A faction mission that contradicts another active one

- (a) Arbitration rule: PARTIAL — campaign_mission_structure.md §Reputation conflict rule: "When players complete a faction mission, the GM should automatically apply a partial negative delta to antagonistic factions." aerus_mechanics_systems.md §Cross-Faction Pressure has examples of actions that affect multiple factions. But with no protocol for how the GM narrates the conflict when the player has two active missions simultaneously.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a mission where completing objective A of church_01 makes the objective of children_01 impossible at the same time.

---

#### Two players with opposing factions in the same negotiation scene

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### An NPC who dies by the player's choice — reputation consequence

- (a) Arbitration rule: PARTIAL — aerus_mechanics_systems.md §Typical Negative Triggers: "violence against members or institutions". aerus_npc_sheets.md §NPC Design Rules: "If an NPC matters politically, treat combat against them as campaign-shaping." But with no table of how much reputation drops for killing an NPC by tier/importance.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for accidentally killing an allied NPC of another faction, or a witness who saw the murder.

---

#### A secret objective conflicting with the group's action

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Secret Objectives has design guidelines but with no protocol for how the GM arbitrates when player A's secret objective prevents player B's success.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### DEATH AND PERMANENT CONSEQUENCES

---

#### Death of an important allied NPC — narrative protocol

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Consequences lists "An NPC now trusts or fears the group" as a consequence pattern, and aerus_npc_sheets.md defines NPCs as "campaign-shaping" if important. But with no specific narration protocol for the death of an allied NPC.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for Thresh dying before completing children_03, or Maren dying with vital information unrevealed.

---

#### Death of an NPC who still held vital information

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Destroyed Fragment — immediate Surge with a 200km radius

- (a) Arbitration rule: PARTIAL — aerus_mechanics_magic_isekai.md §Aeridian Fragments: "Destroying a Fragment releases energy equivalent to a maximum-grade Surge." But with no narrative protocol for what happens within the 200km radius, who knows about the event, or the faction consequence.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for the Valdek IV Fragment being destroyed (campaign_mission_arcs §Arc II).

---

#### Failed sealing in the Final Chamber — what happens

- (a) Arbitration rule: ❌ MISSING — campaign_mission_arcs §The Final Choice describes 4 options but with no protocol for "a sealing attempt that fails mechanically" (vs. "choosing not to seal").
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### A player who tries to make their character commit suicide

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Permanent loss of an attribute (curse, severe corruption)

- (a) Arbitration rule: PARTIAL — aerus_mechanics_races.md §Corrupted Fae: "Lose permanent vitality over long progression milestones" (Onus Entis). But with no general protocol for how the GM applies permanent attribute loss from corruption.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for an attribute dropping below the racial minimum, or for recovering a permanently lost attribute.

---

#### A location destroyed by the group — geopolitical consequence

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Consequences: "A corrupted zone expands" and "A route becomes unsafe" as patterns. But with no protocol for the specific consequences of destroying a key location (Vel'Ossian, Port Myr Broken Square).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### A secret revealed publicly — reaction of the factions involved

- (a) Arbitration rule: PARTIAL — aerus_lore_geopolitics_economy.md §Recent Events describes who knows what about each event, useful as a model. aerus_mechanics_systems.md §Cross-Faction Pressure has examples of actions that activate multiple factions. But with no protocol for how the GM applies the "who reacts how" when the group reveals a specific secret.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a secret revealed to a faction that was not on the "who knows" list.

---

### MULTIPLAYER AND COOPERATION

---

#### Two players performing simultaneous actions — 3s batching

- (a) Arbitration rule: PARTIAL — CLAUDE.md describes `action_batch_window_seconds: 3` and `game_master.py` as the turn orchestrator. But with no narrative protocol for how the GM arbitrates and narrates two conflicting simultaneous actions (A tries to negotiate while B attacks).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for actions that cancel each other out.

---

#### Players in different locations in the same session

- (a) Arbitration rule: ❌ MISSING — no document defines how the GM manages parallel narration, when to cut between scenes, or how to maintain coherent tension.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for player A in combat while player B is traveling.

---

#### One player dead (a spectator) while the group continues

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### Conflict between players (PvP) — is it allowed? protocol

- (a) Arbitration rule: PARTIAL — campaign.yaml has `friendly_fire: false`, which implies PvP is disabled. But with no protocol for "what the GM does when a player declares the intent to attack another player."
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING — no protocol for a secret objective that explicitly asks to harm another player.

---

#### A player absent in a session — does the character disappear or stay?

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### A player's secret objective revealed accidentally

- (a) Arbitration rule: ❌ MISSING — aerus_gm_guide.md §Secret Objectives has general guidelines but with no protocol for how the GM arbitrates an accidental reveal.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### One player sabotages another's action (intentional or not)

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### All players fail the same critical roll

- (a) Arbitration rule: ❌ MISSING — no document defines a protocol for a total group failure.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

### GM CLARIFICATION SYSTEM

---

#### When the GM should pause and ask for a roll vs. decide alone

- (a) Arbitration rule: PARTIAL — narration_bible_kernel.md: "If there is a die roll, state it before the result: who rolls, which die, and what is at stake." But with no criterion for when an action requires a roll vs. when it is automatic.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### An action impossible by the lore — how to refuse it without breaking immersion

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Table Rules: "Be direct when the world is clear." But with no specific protocol for how to refuse an impossible action (flying without magic, teleporting to another continent) while keeping the literary tone.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### An action with no defined rule — how to improvise consistently

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Table Rules: "Make failure productive whenever possible" and "Protect momentum." But with no protocol for structured improvisation (similar to "yes, and" or to the Ironsworn Move trigger).
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### A player tries to use OOC (out-of-character) knowledge

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### An action that contradicts Aerum's canonical lore

- (a) Arbitration rule: ❌ MISSING
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

#### A question about a mechanic the GM has no clear answer for

- (a) Arbitration rule: PARTIAL — aerus_gm_guide.md §Table Rules: "Be ambiguous only when the fiction supports ambiguity." But with no explicit protocol for how the GM masks the absence of a rule.
- (b) Narrative example: ❌ MISSING
- (c) Edge cases: ❌ MISSING

---

---

## SECTION 2 — GAPS BY COMPARISON WITH MATURE SYSTEMS

---

### Comparison with D&D 5E

| Concept | Equivalent in Aerum | Status |
|---|---|---|
| Conditions with precise mechanical effects (complete list) | No list of conditions exists. world_kernel.md lists backfires but not status conditions. | ❌ MISSING — **CRITICAL** |
| Concentration rule for maintained spells | Does not exist. Channeler has "Open Channel" but with no defined concentration cost. | ❌ MISSING — **HIGH** |
| Saving throw vs. a specific attribute | Does not exist. Checks use attributes but with no separate "saving throw" framework. | ❌ MISSING — **HIGH** |
| Advantage/Disadvantage | Does not exist. The racial Onus Entis cites penalties such as "-2 on magical rolls" but with no general system. | ❌ MISSING — **HIGH** |
| Short rest vs. long rest (partial recovery) | PARTIAL — narration_bible_kernel.md distinguishes "light rest" from "safe sleep" but with no values. | PARTIAL — **HIGH** |
| Death saving throws | Does not exist. Permadeath is confirmed but with no limbo mechanic before death. | ❌ MISSING — **CRITICAL** |
| Opportunity attack | Does not exist. | ❌ MISSING — **MEDIUM** |
| Flanking (positioning bonus) | Does not exist. | ❌ MISSING — **MEDIUM** |
| Cover (cover on ranged attacks) | Does not exist. | ❌ MISSING — **MEDIUM** |
| Grapple and the restrained condition | Does not exist as a defined condition. | ❌ MISSING — **MEDIUM** |
| Concentration break from damage | Does not exist. | ❌ MISSING — **HIGH** |

---

### Comparison with Blades in the Dark

| Concept | Equivalent in Aerum | Status |
|---|---|---|
| Pressure clock | PARTIAL — campaign.yaml has `tension_thresholds` (1-10) that affect the chosen model. But with no visual clock or narrative protocol for progress. | PARTIAL — **HIGH** |
| Flashback | Does not exist. | ❌ MISSING — **MEDIUM** |
| Resistance (taking a lesser consequence by paying a cost) | Does not exist. | ❌ MISSING — **HIGH** |
| Consequence scale (reduced/normal/increased/catastrophic) | PARTIAL — aerus_gm_guide.md §Consequences has general patterns but no formal scale. | PARTIAL — **HIGH** |
| Position and Effect (risk vs. impact before rolling) | Does not exist. narration_bible_kernel.md asks to "state it before the result: who rolls, which die, and what is at stake" but with no Position/Effect framework. | ❌ MISSING — **CRITICAL** |
| Devil's Bargain | Does not exist formally. But aerus_gm_guide.md §Table Rules "Let victory cost something" comes close. | ❌ MISSING — **HIGH** |
| Downtime actions | Does not exist. No definition of what the characters do between sessions. | ❌ MISSING — **HIGH** |
| Heat and Wanted Level | PARTIAL — reputation_gates.yaml has "faction_pressure" as a gate type (e.g. inquisitors tracking, wanted notices). But with no numerical heat system. | PARTIAL — **MEDIUM** |
| Trauma (permanent consequence of a severe non-death failure) | Does not exist formally. aerus_mechanics_races.md §Corrupted Fae has "Lose permanent vitality" but is not generalized. | ❌ MISSING — **HIGH** |

---

### Comparison with Vampire: The Masquerade

| Concept | Equivalent in Aerum | Status |
|---|---|---|
| Social conflict with a mechanic (Persuasion, Intimidation with dice) | PARTIAL — aerus_mechanics_systems.md §Faction Reputation has bands and aerus_main_npcs.md has `bribe_threshold` and `disposition`, but with no persuasion/intimidation roll. | PARTIAL — **CRITICAL** |
| Frenzy/loss of control (trigger and narrative) | Does not exist. Mentioned as a concept for Chimerics but with no mechanic. | ❌ MISSING — **HIGH** |
| Blood pool / limited power resource | PARTIAL — MP exists in NPC stat blocks but with no recovery/depletion rules for players. | PARTIAL — **HIGH** |
| Masquerade (the Travelers' secret being exposed) | PARTIAL — aerus_mechanics_magic_isekai.md §How NPCs React to the Mark has regional reactions. aerus_lore_dome_factions.md has "The Dome Mark cannot be permanently removed." But with no public-exposure scale with escalating consequences. | PARTIAL — **HIGH** |
| Diablerie (absorbing another's power) | Does not exist. | ❌ MISSING — **MEDIUM** |
| Compulsion (behavior forced by one's nature) | PARTIAL — the races' Onus Entis is the closest equivalent, but with no trigger mechanic. | PARTIAL — **MEDIUM** |
| Humanity/morality | Does not exist. aerus_gm_guide.md has "consequences are durable" but with no morality track. | ❌ MISSING — **MEDIUM** |

---

### Comparison with Ironsworn / Forbidden Lands

| Concept | Equivalent in Aerum | Status |
|---|---|---|
| Move triggers (what forces a roll vs. what is automatic) | PARTIAL — narration_bible_kernel.md: "If there is a die roll, state it before..." but with no list of roll triggers. | PARTIAL — **CRITICAL** |
| Supply as a narrative resource (food, torch, etc.) | PARTIAL — items.yaml has weight and aerus_mechanics_languages_crafting.md §Required Tools has tools, but with no supply/depletion system. | PARTIAL — **HIGH** |
| Progressive corruption track with narrative milestones | PARTIAL — aerus_mechanics_magic_isekai.md has Rooting as a track, world_kernel.md has backfires. But with no corruption track with defined milestones (e.g. Stage 1 = visions; Stage 3 = partial loss of control). | PARTIAL — **CRITICAL** |
| Oracles (the GM rolls to determine details of the world) | Does not exist. rumors.yaml is the closest (world event generation), but with no oracle-roll framework. | ❌ MISSING — **MEDIUM** |
| Solo vs. group mechanics (the difference when a player is alone) | Does not exist. | ❌ MISSING — **MEDIUM** |

---

---

## SECTION 3 — SITUATIONS THE SLM WILL HIT WITHOUT AN ANSWER

The 30 most likely in-session questions with no clear answer in the current documentation:

---

| # | Question the GM would need to answer | Closest document | Priority |
|---|---|---|---|
| 1 | "I attack with my sword. Which die do I roll? Which attribute?" | aerus_base_classes.md §Blade — but with no attack mechanic | **CRITICAL** |
| 2 | "How much HP do I lose from this attack?" | NPC stat blocks in aerus_main_npcs.md have HP but no damage formula for players | **CRITICAL** |
| 3 | "My character is at 0 HP. Am I dead, or can I be stabilized?" | campaign.yaml `permadeath: true` + aerus_mechanics_magic_isekai.md "Death is real death" but with no threshold | **CRITICAL** |
| 4 | "Which die do I roll to resist a condition (poison, stun)?" | None | **CRITICAL** |
| 5 | "I cast a level 3 spell in a corrupted zone. What is the chance of a backfire?" | world_kernel.md lists types but with no probability by zone/level | **CRITICAL** |
| 6 | "How much XP do I get for killing a Tier 2 enemy?" | narration_bible_kernel.md mentions XP for impactful actions but with no table | **CRITICAL** |
| 7 | "I want to flee combat. What do I roll and what is the cost?" | None | **CRITICAL** |
| 8 | "I am poisoned. When does the effect end and how do I narrate it?" | None — no list of conditions exists | **CRITICAL** |
| 9 | "Two players cast different spells on the same turn. Which one do I resolve first?" | CLAUDE.md describes 3s batching but with no narrative arbitration | **CRITICAL** |
| 10 | "Can I negotiate the price with this merchant? Which attribute do I roll?" | aerus_lore_geopolitics_economy.md has prices but with no haggling mechanic | **CRITICAL** |
| 11 | "My character rested at a tavern. How much HP do I recover?" | narration_bible_kernel.md talks about safe rest with no numbers | **HIGH** |
| 12 | "I want to craft a Minor Stability Amulet in a T3 zone. Is it possible? What is the modifier?" | aerus_mechanics_languages_crafting.md has a DC but with no zone penalty | **HIGH** |
| 13 | "The boss reached 50% HP. What is the trigger for phase 2?" | aerus_gm_guide.md §Boss Phase Change has a narration example but with no numerical trigger | **HIGH** |
| 14 | "I have -51 reputation with the Church. Does the inquisitor I met attack me immediately?" | reputation_gates.yaml cites tracking and "challenge on sight" for imperial soldiers but with no general rule | **HIGH** |
| 15 | "My allied NPC has been mind-controlled and is attacking me. How does the combat work?" | None | **HIGH** |
| 16 | "Player B is 500km away on a journey while Player A is in combat. Do I narrate both scenes?" | None | **HIGH** |
| 17 | "My character failed 3 consecutive magic attempts. Has he accumulated corruption?" | world_kernel.md lists backfires but with no cumulative track | **HIGH** |
| 18 | "Which attribute do I use to intimidate the border guard?" | None — no explicit mapping of social action → attribute | **HIGH** |
| 19 | "My level 25 mutation was unlocked during combat. Do I get it now or later?" | aerus_class_mutations.md describes outcomes but with no timing | **HIGH** |
| 20 | "I am in the Pale Belt (Void Zone). Can I use magic normally?" | aerus_lore_geography.md mentions "permanent fog" but with no rule for magic in the Void Zone | **HIGH** |
| 21 | "The player wants to buy Keth Grade 2 in Port Myr. It is illegal. What happens if they get caught?" | aerus_lore_geopolitics_economy.md §Keth Gray Market cites generic risks but with no protocol for being caught | **HIGH** |
| 22 | "A player tried to make their character commit suicide. What does the GM do?" | None | **HIGH** |
| 23 | "The party destroyed the Aeridian Fragment of Valdek IV. What happens over the next 5 narrative minutes?" | campaign_mission_arcs §Arc II mentions the event but with no immediate protocol | **HIGH** |
| 24 | "The player uses OOC knowledge ('I know the Weaver is in the Pale Belt because I read the sheet'). How does the GM arbitrate it?" | None | **HIGH** |
| 25 | "My character attacked and killed Thresh. What is the exact reputation penalty with the Children?" | aerus_mechanics_systems.md §Typical Negative Triggers: "violence against members" but with no specific delta | **MEDIUM** |
| 26 | "We are camping in the wilderness. How many hours of watch are needed to prevent an ambush?" | None | **MEDIUM** |
| 27 | "Vel'Arath — my Mist Elf character tries to enter. Does the forest admit them automatically?" | aerus_travel.md: "The forest decides who may enter" but with no criterion by race | **MEDIUM** |
| 28 | "The player wants to create a false rumor about the Empire in Port Myr. How do I track its effect?" | rumors.yaml has a rumor system but with no protocol for a player-created rumor | **MEDIUM** |
| 29 | "Two players have opposing reputations with the Church. One is at +60, the other at -55. How does the NPC react to the party?" | None — no protocol for collective vs. individual reputation | **MEDIUM** |
| 30 | "The player uses the LUK attribute to try something. What is the base DC and when is LUK the right attribute?" | aerus_mechanics_races.md mentions LUK but with no framework for when to use each attribute | **MEDIUM** |

---

---

## SECTION 4 — WHAT TO DOCUMENT BEFORE THE FINE-TUNE

---

### CRITICAL (without this the model breaks the session)

- **`aerus_combat_core.md`** — Complete combat mechanics: attack die by class, base damage formula, initiative (attribute + die), defense (DEX + armor), HP/0HP/death. Without this the model invents inconsistent rules in every session.

- **`aerus_conditions_list.md`** — Complete list of status conditions (poisoned, stunned, frightened, corrupted, immobilized, etc.) with: default duration, mechanical effect, how to apply it, how to remove it, and 1-2 narration sentences for each.

- **`aerus_corruption_track.md`** — Progressive corruption track with 4-5 numbered stages: accumulation threshold (e.g. 3 magic failures = Stage 1), mechanical effect per stage, narrative sign per stage, how to remove each stage. Includes interaction with Keth and Fragments.

- **`aerus_roll_triggers.md`** — A map of when the GM asks for a roll vs. when the action is automatic. Includes: which attribute per action type (combat, social, exploration, craft, magic), what is at stake in each roll, what distinguishes success from partial success from failure.

- **`aerus_death_protocol.md`** — Complete death protocol: 0 HP threshold, "death window" (does it exist or not?), immediate permadeath vs. stabilization, transition to spectator, when to create a new character, mandatory death narration.

- **`aerus_magic_resolution.md`** — Magic resolution framework: spell die, base attribute (INT for elementals, CAR for Spirit), DC by magic level (1-10), backfire table by zone (normal/corrupted/Fragment nearby/Void Zone), partial vs. total spell failure vs. backfire.

- **`aerus_xp_table.md`** — XP table by action type: combat by tier, mission objective by type, successful diplomacy, craft, lore discovery. XP threshold per level (or milestone framework). Protocol for when the GM announces and narrates the level up.

---

### HIGH (without this the model improvises wrong)

- **`aerus_social_mechanics.md`** — Social interaction mechanics: attribute for persuasion (CAR), intimidation (STR or CAR), deception (DEX or INT), base DC by NPC disposition, reputation modifiers by band, partial-success outcome in negotiation. Narrative examples by result type.

- **`aerus_rest_recovery.md`** — Recovery table by rest type: light rest (1-2h), safe sleep (6-8h), sleep in a corrupted zone, rest with magical healing. HP and MP values recovered. Protocol for a rest interrupted by ambush.

- **`aerus_flee_surrender.md`** — Flee-from-combat mechanic (when possible, DEX roll vs. enemy, narrative cost) and enemy surrender (what happens, how the GM narrates it, what the player can do with a prisoner).

- **`aerus_crafting_failure.md`** — What happens on a crafting failure: failure by 1-4 (main ingredient lost), failure by 5+ (all ingredients + damage to the crafter), critical failure (accident with a backfire effect). Narrative examples for each level.

- **`aerus_multiplayer_protocol.md`** — How the GM manages: conflicting simultaneous actions (3s batch), players in different locations in the same session, spectator after death, player absence, secret objective revealed accidentally, sabotage between players.

- **`aerus_npc_kill_consequences.md`** — Consequence table by type of NPC killed: street NPC (light delta), faction agent (moderate delta by faction), key NPC with an active mission (mission canceled + heavy delta), NPC with vital information (information lost → workaround protocol). Examples for each faction.

- **`aerus_surge_protocol.md`** — Complete Surge protocol: radius by level (1-10 of magic), narrative effects by stage, who knows/feels it in the world, faction consequence after a public Surge, the difference between a normal Surge and a Surge from a destroyed Fragment.

- **`aerus_attribute_guide.md`** — When to use each attribute (STR, DEX, INT, VIT, LUK, CAR) as the basis for a roll in common situations. Includes cases of LUK as a roll attribute and CAR for social. Essential for GM consistency.

- **`aerus_faction_conflict_arbitration.md`** — Protocol for: simultaneous conflicting missions, two players with opposing factions in the same scene, an NPC who knows one player as an ally and another as an enemy, individual vs. collective party reputation.

- **`aerus_combat_special_terrain.md`** — Mechanical and narrative modifiers for: corrupted zone (magic penalty), Ondrek Pass (magic blocked), Vel'Arath (unstable/ancient magic), Heart of Ashes (T4-5 zone), water (STR/DEX penalty), altitude (VIT penalty).

---

### MEDIUM (without this the model stays generic)

- **`aerus_downtime.md`** — What the characters can do between sessions: language training (sessions required per language already documented), learning magic, recovering a permanent attribute, crafting without urgency, reputation management.

- **`aerus_boss_design.md`** — Boss-fight protocol: when to use a phase change (suggested HP threshold: 50%, 25%), what changes in phase 2 (new attacks, mobility, corruption aura), how to narrate each transition, who can have multiple phases.

- **`aerus_ooc_handling.md`** — How the GM refuses OOC actions without breaking immersion: an action impossible by the lore (refusal with a narrative anchor), OOC knowledge used by the player (the difference between "would my character know this?" and "I know this"), an action that contradicts canon (how the world reacts naturally).

- **`aerus_travel_narrative.md`** — Narrative examples by travel encounter type: how to narrate each encounter type from travel.yaml (bandits, merchants, lesser leviathan, ghost ship, avalanche, etc.). Includes examples of extreme weather and arrival at special locations.

- **`aerus_void_zone_rules.md`** — Specific Void Zone rules (Pale Belt, Red Sea, Limen Vel'Arath): effect on magic, navigation, character health, how long someone can endure, interaction with the Khorathi race (Body Without Thread).

- **`aerus_rumor_injection.md`** — How the GM creates and tracks player-generated rumors: format, how it affects NPCs and factions, the difference between a true/false rumor being spread, how the GM can use a player rumor as a hook.

- **`aerus_vel_arath_entry.md`** — Entry criteria for Vel'Arath: whom the forest admits (by race, by action history, by intent), what happens when a member is refused, what happens inside the forest (distorted time, the Mark's effect, ancient Thread magic).

- **`aerus_morality_track.md`** — A simple morality/humanity track for Aerum: actions that move it up/down, visible narrative markers by band, the consequence of a low band (NPCs distant, the Mark reacts differently, factions distrust). It does not need to be as complex as VtM.

- **`aerus_leveling_narration.md`** — Complete narrative protocol for level up: when to interrupt the scene, the GM's standard sentences, how to narrate a formal mutation in each class (examples for Blade, Sorcerer, Channeler), how to present the path choice to the player.

---

> END OF DOCUMENT
> Total gaps identified: ~130 items (Section 1) + 25 items (Section 2) + 30 situations (Section 3)
> Total priority of documents to create: 7 CRITICAL + 10 HIGH + 9 MEDIUM = 26 documents
