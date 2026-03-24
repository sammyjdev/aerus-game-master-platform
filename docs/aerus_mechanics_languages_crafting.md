> Extracted from `aerus_mechanics.md` - playable languages and the crafting system.

## XIX. Playable Languages

### System Structure

Aerus supports six major learnable languages. Characters begin with **Common Tongue**. Additional languages are learned through narrative access, economic cost, or both. Character languages are stored in `languages_json` as a JSON array of string identifiers.

Example:

```json
["common_tongue", "kethic", "aeridian_archaic"]
```

### The Six Languages

#### Common Tongue (`common_tongue`)

- Spoken by most people engaged in trade or basic civic life.
- Functionally universal across the documented world.
- All characters begin with it automatically.

#### Aeridian Archaic (`aeridian_archaic`)

- Spoken by Guild scholars, Kael Archive researchers, and high-ranking Church clerics.
- Required to read original Aeridian documents and many high-level magical formulations.
- Learned through Guild instruction, heavy study, and significant cost.

#### Kethic (`kethic`)

- Spoken by merchants of Kethara, miners of Estravar, and eastern-route traders.
- Essential for direct Keth negotiation and local transactional records.
- Provides practical discounts and trust when dealing in Kethara or with Keth merchants.

#### Elven (`elven`)

- Spoken natively by elves and many communities tied to Shaleth.
- Required for direct exchange with Shaleth crews, elven texts, and certain wild beings of elven origin.
- Starts free for elven and half-elven backgrounds when appropriate.

#### Dwarven (`dwarven`)

- Spoken by dwarves, forgers, and some specialized mining communities.
- Important for technical forge contracts, refined Keth records, and high-trust artisan dealings.
- Begins free for dwarven-origin characters.

#### Corrupted Speech (`corrupted_speech`)

- Spoken by intelligent corrupted beings and a handful of dangerous intermediaries.
- Allows negotiation with cognitively intact corrupted entities.
- Cannot be purchased normally; it must be acquired through exposure, narrative consequence, and GM approval.

### Learning Summary

| Language | Cost | Sessions | Trainer | Free by origin |
| --- | --- | --- | --- | --- |
| Common Tongue | 0 | 0 | - | Everyone |
| Aeridian Archaic | 200 GM | 3 | Guild scholar | - |
| Kethic | 50 GM | 1 | Kethic merchant | - |
| Elven | 100 GM | 2 | Shaleth contact | Elven / half-elven |
| Dwarven | 100 GM | 2 | Forger | Dwarven |
| Corrupted Speech | 0 gold | narrative | none | - |

---

## XX. Crafting System

### Principle

Crafting is resolved narratively by the GM using the recipe tables as guidance. There is no dedicated crafting UI. The GM describes the process, calls for an attribute check against a difficulty class, and narrates the result. Crafted items enter inventory normally.

### Required Tools

| Tool | Cost | Where to find it | Typical use |
| --- | --- | --- | --- |
| Alchemist Kit | 25 SW | Port Myr, Vel'Ossian | potions, oils, filters, salves |
| Forge Access | 5 SW/hour | smiths in major settlements | weapons, armor, metal parts |
| Arcane Loom | 80 GM or 15 SW/use | Vel'Ossian, Guild facilities | mantles, enchanted textiles, arcane trinkets |

### Keth by Grade

| Grade | Name | Stabilization effect | Price in Kethara | Price in Port Myr | Gray market |
| --- | --- | --- | --- | --- | --- |
| Grade 1 | Raw Keth | stabilizes level 1-2 magic | 4 GM/kg | 8 GM/kg | 6 GM/kg |
| Grade 2 | Cut Keth | stabilizes level 3-4 magic | 20 GM/kg | not legal | 35 GM/kg |
| Grade 3 | Refined Keth | stabilizes level 5+ magic | 80 GM/kg | not legal | 140 GM/kg |
| Grade 4 | Pure Aeridian Keth | absolute stabilization | no fixed price | - | legendary |

### Common Bestiary Drops Used in Crafting

| Ingredient | Source | Tier | Notes |
| --- | --- | --- | --- |
| Draining Gland | MP-draining void creature | 1 | common in the Pale Belt |
| Ash-Thorn Sap | corrupted flora | 1 | collectible without combat |
| Fragmented Memory Crystal | ruin specters | 2 | openly traded in Khorrath |
| Ash Exoskeleton | ruin guardian beasts | 2 | fragile unless carefully harvested |
| Tracker Eye | surge predator | 2 | must be preserved immediately |
| Essence of Light | purified spectral entity | 3 | obtained through purification, not killing |
| Thread Fragment | corrupted thread-node | 3 | highly unstable without Keth containment |
| Predator Claw | large corrupted predator | 2-3 | larger specimens are more valuable |
| Echo Hide | mimic surge creature | 3 | keeps adaptive traits for limited time |
| Tangible Primordial Thread | extreme world event | 4+ | cosmologically rare |

---

## Recipes by Rarity

### Common (DC 10-12)

- **MP Absorption Potion**  
  Ingredients: 2x Draining Gland, 1x Grade 1 Keth  
  Check: `INT DC 10`  
  Effect: restore `2d6 MP`

- **Regeneration Salve**  
  Ingredients: 3x Ash-Thorn Sap, 1x Grade 1 Keth  
  Check: `INT DC 10`  
  Effect: restore `1d4 HP` per turn for 3 turns

- **Disruption Round**  
  Ingredients: 1x Draining Gland, common metal  
  Check: `DEX DC 12`  
  Effect: single ammunition dealing bonus disruption damage to corrupted targets

- **Arcane Bandage**  
  Ingredients: 1x Fragmented Memory Crystal, cloth  
  Check: `INT DC 10`  
  Effect: next healing received after stabilization gains bonus HP

- **Keth Oil**  
  Ingredients: 2x Grade 1 Keth, common oil  
  Check: `STR DC 10`  
  Effect: temporary bonus damage against corrupted enemies

### Rare (DC 13-15)

- **Light Ash Armor**  
  Ingredients: 5x Ash Exoskeleton, 2x Grade 2 Keth  
  Check: `STR DC 14`  
  Effect: higher defense and surge resistance

- **Disruption Blade**  
  Ingredients: quality metal, 3x Grade 2 Keth  
  Check: `STR DC 15`  
  Effect: extra damage to corrupted enemies and critical disruption effect

- **Minor Stability Amulet**  
  Ingredients: 3x Fragmented Memory Crystal, 1x Grade 2 Keth  
  Check: `INT DC 13`  
  Effect: reduces the impact of one magical failure per long rest

- **Perception Filter**  
  Ingredients: 2x Tracker Eye, 2x Grade 1 Keth  
  Check: `INT DC 14`  
  Effect: detects nearby corrupted presence for one hour

- **Keth Helm**  
  Ingredients: 4x Grade 2 Keth, common metal  
  Check: `STR DC 14`  
  Effect: improved resistance to mental control

### Epic (DC 16-18)

- **Heavy Ash Armor**  
  Ingredients: 10x Ash Exoskeleton, 3x Grade 3 Keth  
  Check: `STR DC 17`  
  Effect: major defense and immunity to low-tier passive corruption

- **Staff of the Stable Thread**  
  Ingredients: 1x Thread Fragment, 2x Grade 3 Keth  
  Check: `INT DC 18`  
  Effect: increases effective spellcasting level and cancels one spell failure per long rest

- **Purification Potion**  
  Ingredients: 3x Essence of Light, 1x Grade 3 Keth  
  Check: `INT DC 16`  
  Effect: removes one active corruption condition

- **Reinforced Ash Claw**  
  Ingredients: 5x Predator Claw, 4x Grade 2 Keth  
  Check: `STR DC 16`  
  Effect: epic gloves granting strong unarmed pressure against corrupted creatures

- **Observer's Mantle**  
  Ingredients: 3x Echo Hide, 2x Grade 3 Keth  
  Check: `INT DC 17`  
  Effect: partial invisibility while moving through active corruption zones

### Legendary (DC 19-21)

- **Blade of Scars**  
  Ingredients: small Aeridian Fragment, 1x Grade 4 Keth  
  Check: `STR DC 21`  
  Effect: ignores corrupted resistance and temporarily drains corruption from high-tier targets

- **The Weaver's Mantle**  
  Ingredients: 1x Tangible Primordial Thread, 1x Grade 4 Keth  
  Check: `INT DC 20`  
  Effect: reveals lines of the Primordial Thread and allows direct narrative interaction with them once per session

> Legendary crafting components should never be normal shop inventory. They are campaign-defining rewards, discoveries, or bargaining chips.
