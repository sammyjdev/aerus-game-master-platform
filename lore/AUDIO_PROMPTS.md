# Aerus RPG - Audio Assets And AI Prompt Library

> Prompt library for generating sound effects, ambient loops, and music cues for Aerus.
> Export assets as `mp3` files and place them in `frontend/public/audio/`.

---

## Conventions

| Category | Recommended Duration | Suggested Tool |
| --- | --- | --- |
| Short SFX | 0.5s to 3s | ElevenLabs Sound Effects |
| Ambient loops | 30s to 120s | Stable Audio or Suno |
| Theme or boss tracks | 60s to 180s | Suno |

General guidance:

- keep effects readable in a game mix
- avoid excessive reverb tails
- prefer dark fantasy texture over generic cinematic polish
- keep loops stable enough for repeated playback

---

## Combat - Physical

### `sword_hit.mp3`

Context: sword, axe, or bladed melee impact

```text
Sharp metallic slash impact, dark fantasy melee hit, steel through air into flesh,
brief ring, punchy and immediate, low reverb, realistic with stylized game clarity, 0.8 seconds
```

### `blunt_hit.mp3`

Context: hammer, mace, club, or crushing impact

```text
Heavy blunt weapon strike, deep thud with brutal weight, dark fantasy battlefield impact,
short bone-crack undertone, powerful low-end punch, 0.7 seconds
```

### `bow_shoot.mp3`

Context: bow or crossbow release

```text
Bowstring snap, wooden tension release, arrow whoosh, precise medieval ranged attack,
dark fantasy RPG, clean and fast, 1.0 second
```

### `unarmed_hit.mp3`

Context: punch, kick, elbow, or body blow

```text
Bare-knuckle hit, compact body-impact sound, visceral but not gory,
dark fantasy combat, dry and immediate, 0.5 seconds
```

---

## Combat - Magic

### `magic_fire.mp3`

Context: fire spell or magma-like fusion

```text
Fire spell cast, ignition burst with crackling flame surge, dark fantasy magic,
primordial heat, controlled but dangerous, 1.2 seconds
```

### `magic_ice.mp3`

Context: ice, cold water, or freezing burst

```text
Ice spell cast, rushing water into instant freeze, crystalline snap,
cold arcane precision, dark fantasy RPG, 1.0 second
```

### `magic_lightning.mp3`

Context: air or lightning spell

```text
Lightning cast, electric crack and violent discharge, short thunder snap,
dark fantasy spell impact, sharp and immediate, 1.1 seconds
```

### `magic_earth.mp3`

Context: earth shaping, stone impact, Keth resonance

```text
Earth magic cast, stone grinding upward, dense rock fracture, subterranean force,
heavy and grounded, dark fantasy RPG, 1.1 seconds
```

### `magic_spirit.mp3`

Context: spirit, shadow, omen, or dead-adjacent power

```text
Spirit spell cast, whispering tonal swell, distant voices, hollow resonance,
dark fantasy supernatural cue, eerie but controlled, 1.4 seconds
```

### `magic_arcane.mp3`

Context: unstable Thread, raw arcane force, forbidden manipulation

```text
Arcane surge, unstable magical distortion, layered resonance with corrupted undertone,
dark fantasy ritual energy, dangerous and intelligent, 1.3 seconds
```

---

## UI And System Cues

### `dice_roll.mp3`

Context: visible dice resolution

```text
Tabletop dice tumble, short roll across wood, clean stop, satisfying but restrained, 0.9 seconds
```

### `critical_success.mp3`

Context: critical success or dramatic breakthrough

```text
Short triumphant stinger, dark fantasy but hopeful, bright metallic accent,
brief rising impact, 1.2 seconds
```

### `critical_failure.mp3`

Context: fumble, collapse, or severe setback

```text
Abrupt failure sting, cracked tone, low-end drop, dark fantasy tension cue,
short and memorable, 1.0 second
```

### `level_up.mp3`

Context: growth, milestone, mutation unlock

```text
Mystical ascension pulse, layered chime and low magical bloom,
earned progression feeling, dark fantasy RPG, 1.5 seconds
```

### `loot_found.mp3`

Context: item discovery or reward reveal

```text
Soft treasure reveal, subtle metallic touch with arcane shimmer,
quick reward cue, elegant not cartoonish, 0.8 seconds
```

---

## Ambient Loops

### `port_myr_idle.mp3`

Context: daytime Port Myr exploration

```text
Harbor ambience, waves against wood, gulls, rope tension, distant market voices,
humid maritime dark fantasy port, seamless loop, 60 seconds
```

### `broken_square_idle.mp3`

Context: Broken Square and nearby anomaly

```text
Busy urban square with subtle unnatural hum beneath street life,
stone plaza footsteps, distant conversation, faint magical pulse,
dark fantasy city ambience, seamless loop, 60 seconds
```

### `ash_desert_idle.mp3`

Context: Khorrath and the Ash Desert

```text
Burned wasteland ambience, dry wind across black glass, distant ash movement,
occasional low magical rumble, oppressive but sparse, seamless loop, 75 seconds
```

### `ruins_idle.mp3`

Context: ancient Aeridian ruins

```text
Ancient ruin ambience, hollow stone chambers, dust, distant unstable resonance,
forbidden dark fantasy atmosphere, seamless loop, 75 seconds
```

### `void_zone_idle.mp3`

Context: high-corruption or void-adjacent areas

```text
Reality-tearing ambience, low droning absence, unstable pressure, faint distortion,
minimalist cosmic dread in dark fantasy setting, seamless loop, 90 seconds
```

---

## Music Cues

### `combat_boss_theme.mp3`

Context: major boss encounter

```text
Dark fantasy boss music, heavy ritual percussion, low strings, corrupted choir textures,
high tension but readable for gameplay, cinematic without becoming generic, 120 seconds
```

### `mystery_theme.mp3`

Context: discovery, hidden truth, investigative scenes

```text
Dark fantasy mystery theme, restrained strings, soft pulse, distant choral fragments,
curiosity mixed with unease, 90 seconds
```

### `campfire_theme.mp3`

Context: rest, reflection, party bonding

```text
Quiet dark fantasy camp theme, warm but fragile, soft strings and low woodwinds,
temporary safety with underlying sadness, 90 seconds
```

---

## Quality Bar

Reject generated assets that feel:

- overly synthetic
- too heroic for the setting
- cartoonish
- washed out by reverb
- too busy to loop under dialogue

Accept assets that feel:

- readable in play
- moody without mud
- specific to place or action
- aligned with dark fantasy and magical instability
