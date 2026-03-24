> Extracted from `aerus_npcs.md` - principal NPCs, Port Myr additions, and quick stat references.

# Aerus RPG - Main NPCs
> Profiles for the most important recurring NPCs in the campaign.
> See the mission documents for where these characters become central.

---

## X. Main NPCs

### Maren Toss - Keeper of Pier Seven

**Role:** The first NPC of the campaign. He asks for documents the Travelers do not have.

**Appearance:** 52 years old, sea-weathered skin, close white hair, faded but clean dock uniform, cataract in the left eye, always smoking a ceramic pipe.

**Real motivation:** Low-level informant tied to the Kael Archive. He does not know the full meaning of the information he passes along.

**Secret:** Eleven years earlier, he saw three people arrive without a ship and logged them as shipwreck survivors. All three died within two months. He did not connect the pattern until the current Travelers arrived.

**Reveal trigger:** If the players mention dreams, blue light, or hearing a voice in their own language, Maren stops what he is doing and treats them very differently.

```yaml
npc_id: "maren_toss"
location: "port_myr_pier_seven"
faction_affiliation: "kael_archive"
disposition: "neutral_bureaucratic"
bribe_threshold: 8
information_value: "high"
combat_relevance: "none"
reveal_trigger: "isekai_mention OR dream_mention OR blue_light_mention"
```

---

### Valdek IV - The Emperor Who Must Not Die Yet

**Appearance:** A 67-year-old man who looks closer to 80, except for his amber eyes. He wears a ring set with a minor Aeridian Fragment, and people notice when he enters a room even before they know why.

**Real motivation:** He understands that Valdoria may have only decades left before magical collapse if Fragment infrastructure fails. He is not truly looking for a political heir. He is looking for a solution to the real problem.

**Secret:** He has known about Vor'Athek and old prophecies for decades. Once he understands what the Travelers are, he will try to control them, and if control fails, remove them.

**Narrative function:** A political antagonist who is broadly correct about the scale of the crisis, but wrong about the kind of control he believes can solve it.

---

### The Weaver - True Name Unknown

**Appearance:** No two reliable witnesses describe her the same way. The only points of agreement are a calm voice, visible hands, and almost no unnecessary movement.

**Real motivation:** Once a Guild researcher, she discovered that the Thread is actively deteriorating and that the Last Chamber is the only place where the world can still be changed at scale. She knows the chamber matters, but not every consequence of using it.

**Relationship with the Travelers:** If she learns of the summoning, she will try to recruit the Travelers immediately. She is certain they can reach the Last Chamber. She is not aligned with what the Dome wants them to do there.

### Quick Stat Blocks - Principal NPCs

```yaml
npc_id: "maren_toss"
location: "port_myr_pier_seven"
faction_affiliation: "myr_council"
disposition: 5
attributes: { STR: 16, DEX: 12, INT: 10, VIT: 14, LUK: 12, CAR: 8 }
level: 4
hp: 60
mp: 0
special_ability: "Dock Memory - knows the name, origin, and manifest of every ship berthed over the last 3 years."
combat_relevance: "low"
secret: "He saw the Dome light during the Travelers' arrival and has 20 years of notes about related anomalies."
```

```yaml
npc_id: "valdek_iv"
location: "auramveld_spine_palace"
faction_affiliation: "empire_valdrek"
disposition: 0
attributes: { STR: 14, DEX: 8, INT: 18, VIT: 12, LUK: 6, CAR: 20 }
level: 22
hp: 180
mp: 120
special_ability: "Ring of Fragments - lowers magical stability DCs nearby and creates an anomalous resonance for Guild-trained observers."
combat_relevance: "extreme / political only"
secret: "He is being kept alive beyond his natural lifespan by a corrupted Fragment and considers the cost acceptable."
```

```yaml
npc_id: "the_weaver"
location: "wandering - appears where the Thread is most unstable"
faction_affiliation: "none_officially"
disposition: -10
attributes: { STR: 6, DEX: 16, INT: 22, VIT: 10, LUK: 14, CAR: 12 }
level: 35
hp: 140
mp: 300
special_ability: "Contradictory Presence - descriptions of her never remain stable and magical tracking fails automatically."
combat_relevance: "extreme / avoid direct combat"
secret: "She knows how to complete the Sealing and has consciously chosen not to do it."
```

---

## New NPCs - Port Myr

### Seyla Vorn - Alchemical Master of Broken Square

**Appearance:** Around 40, hair coated in herb dust, acid-marked apron, stained fingers, and always several experiments away from finishing at least one thing.

**Function:** Entry point for crafting. She sells basic ingredients, alchemist kits, and practical training.

**Secret:** She has been documenting the Broken Square Fissure for years and believes it is a resonance point tied to Vor'Athek.

```yaml
npc_id: "seyla_vorn"
location: "port_myr_broken_square"
faction_affiliation: "none"
disposition: 0
attributes: { STR: 6, DEX: 14, INT: 20, VIT: 8, LUK: 10, CAR: 14 }
level: 8
hp: 55
mp: 80
special_ability: "Rapid Synthesis - can craft any common alchemical recipe in half the usual time when supplied."
combat_relevance: "low"
```

### Caden Orryl - Kael Archive Analyst

**Appearance:** Well-kept merchant-clerk clothing, always carrying a locked notebook, and the posture of a man who records before he speaks.

**Function:** Holds the leaked Sealing degradation report and was sent to assess the Travelers.

**Secret:** He increasingly believes the Empire will suppress the truth again and is considering an information defection.

```yaml
npc_id: "caden_orryl"
location: "port_myr_five_flags_docks"
faction_affiliation: "empire_valdrek"
disposition: -5
attributes: { STR: 8, DEX: 14, INT: 18, VIT: 10, LUK: 12, CAR: 12 }
level: 6
hp: 45
mp: 40
special_ability: "Pattern Analysis - can identify contradictions in testimony with a moderate INT check."
combat_relevance: "low"
```

### Thresh - Contact of the Children of the Broken Thread

**Appearance:** Looks like an ordinary textile trader until you notice a fighter's hands and a man who always measures exits.

**Function:** Recruiter and tester for the Children. He probes moral ambiguity before he offers trust.

**Secret:** He is a former Church novice who discovered that the Flame Seals were built as political control rather than true protection.

```yaml
npc_id: "thresh"
location: "port_myr_vel_alleys"
faction_affiliation: "children_of_broken_thread"
disposition: 0
attributes: { STR: 12, DEX: 16, INT: 14, VIT: 10, LUK: 10, CAR: 10 }
level: 7
hp: 70
mp: 30
special_ability: "Underground Contacts - can source Children intelligence and black-market resources inside Port Myr."
combat_relevance: "moderate"
```
