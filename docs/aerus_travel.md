# Aerus Travel and Encounter System

> Canonical reference for the GM and players. Version: 1.0 - 2026-03-23

---

## Overview

Travel between locations in Aerus is measured in **travel days**. For each day, the server rolls a **d20** to determine whether an encounter occurs. The terrain crossed that day defines the base chance and the encounter table.

Travel is narratively significant. Crossing the sea to Khorrath or climbing the mountains of Estravar is never an instant transition. The world keeps moving on the road.

---

## Encounter Mechanics

### Daily Roll

```text
d20 <= (base_chance + tension_bonus) x 20  ->  an encounter occurs
```

**Tension bonus:** +3% per tension point above 5  
_(tension 8 = +9% over the base chance; tension 10 = +15%)_

### Base Chance by Terrain

| Terrain | Base chance | Description |
| --- | --- | --- |
| `road` | 15% | Patrolled road, lower risk |
| `sea` | 20% | Sea travel, aquatic creatures and pirates |
| `trail` | 30% | Trail or forest, moderate risk |
| `mountain` | 35% | Mountains, Keth beasts and bandits |
| `arctic` | 30% | Arctic zones, storms and deep-ice predators |
| `wilderness` | 40% | Open land, high risk |
| `corrupted` | 60% | Corrupted zone, **HIGH RISK** (Tier 2-4+) |

---

## Canonical Locations

### Isles of Myr
| ID | Name | Faction | Danger |
| --- | --- | --- | --- |
| `port_myr` | Port Myr | Myr Council | - |
| `vel_ossian` | Vel'Ossian | Guild of Threads | - |
| `sanctum` | Sanctum | Church of the Pure Flame | - |
| `leviathan_cave` | Leviathan Myri - Nauta Cave | - | High |

### Valdoria
| ID | Name | Faction | Danger |
| --- | --- | --- | --- |
| `auramveld` | Auramveld | Empire of Valdrek | - |
| `osthara` | Osthara | Neutral | - |
| `calmveth` | Calmveth | Neutral | - |
| `marchado_ferren` | Ferren March | Empire of Valdrek | - |
| `fendas_de_gorath` | Gorath Fissures | - | High |

### Shaleth
| ID | Name | Faction | Danger |
| --- | --- | --- | --- |
| `vel_shar` | Vel-Shar | Neutral | - |
| `vel_arath` | Vel'Arath | - | - |
| `limen_vel_arath` | Limen Vel'Arath | - | Extreme |

### Estravar
| ID | Name | Terrain |
| --- | --- | --- |
| `kethara` | Kethara | Mountain |
| `keth_ara` | Keth-Ara | Arctic |
| `stenvaard` | Stenvaard | Mountain |
| `passagem_ondrek` | Ondrek Pass | Mountain |

### Khorrath
| ID | Name | Danger |
| --- | --- | --- |
| `khor_ath` | Khor-Ath | - |
| `urbes_ambulantes` | Wandering Cities | - |
| `coracao_cinzas` | Heart of Ashes | Extreme |
| `ordo_cineris` | Ordo Cineris | High |

### Veth
| ID | Name | Danger |
| --- | --- | --- |
| `veth_ara` | Veth-Ara | - |
| `terra_incognita` | Terra Incognita | Extreme |

---

## Main Routes

| Origin | Destination | Days | Notes |
| --- | --- | --- | --- |
| `port_myr` | `vel_ossian` | 1 | Daily inter-island boat |
| `port_myr` | `auramveld` | 7 | 4 sea days + 3 imperial road days |
| `port_myr` | `calmveth` | 3 | Direct trade route |
| `port_myr` | `vel_shar` | 8 | 5 sea days + 3 forest days |
| `port_myr` | `stenvaard` | 7 | Northern sea, rough in winter |
| `port_myr` | `khor_ath` | 8 | 6 sea days + 2 desert days |
| `port_myr` | `veth_ara` | 10 | Long crossing, few navigators |
| `port_myr` | `coracao_cinzas` | 13 | EXTREME, Tier 4-5 |
| `auramveld` | `stenvaard` | 12 | Through Ondrek Pass |
| `khor_ath` | `coracao_cinzas` | 7 | Tier 4-5 |

> All routes are bidirectional. See `backend/config/travel.yaml` for the complete segmented route data.

---

## Encounter Types by Terrain

### Road (`road`)
| Roll | Type | Tier |
| --- | --- | --- |
| 1-8 | Bandits | 1 |
| 9-14 | Merchants | 0 |
| 15-17 | Tier 1 creature | 1 |
| 18-20 | Narrative event | 0 |

### Corrupted Zone (`corrupted`)
| Roll | Type | Tier |
| --- | --- | --- |
| 1-4 | Ash Golem | 2 |
| 5-8 | Corruption surge | 0 |
| 9-12 | Tier 3 creature | 3 |
| 13-15 | Echo of Vor'Athek | 3 |
| 16-18 | Aeridian ruins | 0 |
| 19-20 | Abyss Lord | 4 |

> Full terrain tables live in `backend/config/travel.yaml`.

---

## Special Location Notes

- **Gorath Fissures:** Temporal anomalies. Real travel time may differ from perceived time.
- **Vel'Arath:** The forest decides who may enter. There is no fixed route; duration is narrative.
- **Limen Vel'Arath:** "Ultra Hic Nemo Redit." No maps beyond this point. Return is not guaranteed.
- **Keth-Ara:** 1 mark on the regional map equals 3 days of travel across the ice.
- **Wandering Cities:** Caravan-cities with drifting positions, variable by +/-2 days.
- **Heart of Ashes:** A 40 km crater, epicenter of the Sealing. Not recommended below level 100.

---

## System Integration

- **Start travel:** `travel_manager.start_travel(conn, origin_id, destination_id)`
- **Each GM turn:** `_advance_travel_if_active()` advances travel by 1 day automatically
- **L2 context:** travel state is injected automatically into the GM prompt
- **WebSocket events emitted:** `TRAVEL_ARRIVED`, `TRAVEL_ENCOUNTER`
- **Persisted state:** `world_state` table with `travel_*` keys
