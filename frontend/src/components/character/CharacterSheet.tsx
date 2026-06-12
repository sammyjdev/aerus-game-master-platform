import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useShallow } from 'zustand/shallow';
import { useTranslation } from 'react-i18next';

import {
  updateCharacterSpellAliases,
  updateCharacterBackstory,
  updateCharacterMacros,
  spendAttributePoints,
  spendProficiencyPoints,
} from '../../api/http';
import { logClient } from '../../debug/logger';
import { useGameStore } from '../../store/gameStore';

const FACTION_LABELS = {
  church_pure_flame: 'Church of the Pure Flame',
  empire_valdrek: 'Empire of Valdrek',
  guild_of_threads: 'Guild of Threads',
  children_of_broken_thread: 'Children of the Broken Thread',
};

// 14 skill categories with their sub-skill keys
const SKILL_CATEGORIES: Array<{
  key: string;
  label: string;
  skills: string[];
}> = [
  {
    key: 'combat',
    label: 'Combat Arts',
    skills: [
      'grapple',
      'counterstrike',
      'dual_wield',
      'weapon_flow',
      'endurance_combat',
    ],
  },
  {
    key: 'stealth',
    label: 'Shadow Arts',
    skills: ['conceal', 'pickpocket', 'lockpick', 'ambush', 'disguise'],
  },
  {
    key: 'social',
    label: 'Social Arts',
    skills: ['persuasion', 'intimidation', 'deception', 'negotiation', 'charm'],
  },
  {
    key: 'politics',
    label: 'Court & Politics',
    skills: [
      'court_etiquette',
      'faction_negotiation',
      'rhetoric',
      'law',
      'influence_trade',
    ],
  },
  {
    key: 'survival',
    label: 'Survival',
    skills: ['foraging', 'tracking', 'navigation', 'first_aid', 'camp_craft'],
  },
  {
    key: 'medicine',
    label: 'Medicine',
    skills: [
      'wound_treatment',
      'poison_lore',
      'disease_diagnosis',
      'herbalism',
      'surgery',
    ],
  },
  {
    key: 'lore',
    label: 'Lore',
    skills: [
      'arcane_lore',
      'history',
      'faction_lore',
      'creature_lore',
      'ruin_reading',
    ],
  },
  {
    key: 'crafting',
    label: 'Crafting',
    skills: ['smithing', 'alchemy', 'artifice', 'runework', 'tailoring'],
  },
  {
    key: 'ritual',
    label: 'Ritual Arts',
    skills: [
      'thread_sensing',
      'spirit_binding',
      'corruption_reading',
      'seal_work',
      'resonance',
    ],
  },
  {
    key: 'athletics',
    label: 'Athletics',
    skills: ['climbing', 'swimming', 'sprinting', 'acrobatics', 'lifting'],
  },
  {
    key: 'perception',
    label: 'Perception',
    skills: ['detect_magic', 'detect_lie', 'search', 'listen', 'appraise'],
  },
  {
    key: 'nature',
    label: 'Nature & Beasts',
    skills: [
      'beast_handling',
      'herbalism_wild',
      'weather_reading',
      'terrain_lore',
      'poison_craft',
    ],
  },
  {
    key: 'tactics',
    label: 'Tactics & Leadership',
    skills: [
      'battle_tactics',
      'group_command',
      'ambush_planning',
      'retreat_coordination',
      'morale',
    ],
  },
  {
    key: 'mysticism',
    label: 'Mysticism',
    skills: [
      'dream_reading',
      'void_lore',
      'prophecy',
      'fragment_reading',
      'ash_memory',
    ],
  },
];

function skillImpactThreshold(rank: number): number {
  return (rank + 1) ** 2 * 2.0;
}

function ppCost(currentRank: number): number {
  return Math.floor(currentRank / 4) + 1;
}

function magicLevelCost(currentLevel: number): number {
  return Math.floor(currentLevel / 10) + 1;
}

function requiredMagicLevelForRank(targetRank: number): number {
  if (targetRank <= 0) return 0;
  return Math.floor((targetRank - 1) / 2) * 10 + 1;
}

function characterLevelNeededForMagicLevel(targetMagicLevel: number): number {
  if (targetMagicLevel <= 0) return 1;
  return Math.ceil(targetMagicLevel / 5);
}

function formatSkillKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function elementToneClass(element: string): string {
  const normalized = element.toLowerCase();
  if (['air', 'wind', 'vento'].includes(normalized)) return 'air';
  if (['fire', 'flame', 'fogo'].includes(normalized)) return 'fire';
  if (['water', 'ice', 'agua', 'água', 'gelo'].includes(normalized)) {
    return 'water';
  }
  if (['earth', 'stone', 'terra', 'rocha'].includes(normalized)) {
    return 'earth';
  }
  if (['spirit', 'espirito', 'espírito'].includes(normalized)) {
    return 'spirit';
  }
  return 'energy';
}

function formatFactionName(id: string): string {
  const names: Record<string, string> = {
    church_pure_flame: 'Church of the Pure Flame',
    empire_valdrek: 'Empire of Valdrek',
    guild_of_threads: 'Guild of Threads',
    children_of_broken_thread: 'Children of the Broken Thread',
    myr_council: 'Myr Council',
  };
  return names[id] ?? id;
}

function getReputationLabel(score: number): string {
  if (score <= -50) return 'Enemies';
  if (score <= -20) return 'Hostile';
  if (score < 20) return 'Neutral';
  if (score < 50) return 'Friendly';
  return 'Allied';
}

const TABS = ['summary', 'spells', 'items', 'proficiencies', 'macros'] as const;
type TabId = (typeof TABS)[number];
const BACKSTORY_MIN = 50;
const BACKSTORY_MAX = 3000;

export const CharacterSheet = memo(function CharacterSheet() {
  const { t } = useTranslation();
  const { player, secretObjective, worldState, token, patchCurrentPlayer } =
    useGameStore(
      useShallow((state) => ({
        player: state.gameState.current_player,
        secretObjective: state.gameState.secret_objective,
        worldState: state.gameState.world_state,
        token: state.token,
        patchCurrentPlayer: state.patchCurrentPlayer,
      })),
    );
  const factionReputations = useGameStore(
    useShallow(
      (state) =>
        state.faction_reputations[state.gameState.current_player.player_id] ??
        {},
    ),
  );
  const [activeTab, setActiveTab] = useState<TabId>('summary');
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const [backstoryDraft, setBackstoryDraft] = useState(player.backstory ?? '');
  const [backstoryDirty, setBackstoryDirty] = useState(false);
  const [macroName, setMacroName] = useState('');
  const [macroTemplate, setMacroTemplate] = useState('');
  const [selectedSpellBase, setSelectedSpellBase] = useState('');
  const [spellAlias, setSpellAlias] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'ok' | 'error'>('idle');
  const [spendingAttr, setSpendingAttr] = useState<string | null>(null);
  const [spendingProf, setSpendingProf] = useState<string | null>(null);
  const [spendError, setSpendError] = useState<string | null>(null);
  const magicLevelCapByCharacter = Math.min(500, player.level * 5);

  const getElementLabel = useCallback(
    (element: string) =>
      t(`sheet.elements.${element.toLowerCase()}`, {
        defaultValue: formatSkillKey(element),
      }),
    [t],
  );

  const handleSpendAttr = useCallback(
    async (attribute: string) => {
      if (!token) return;
      setSpendingAttr(attribute);
      setSpendError(null);
      const currentVal =
        player.attributes[attribute as keyof typeof player.attributes];
      try {
        const result = await spendAttributePoints(token, {
          attribute,
          target_value: currentVal + 1,
        });
        patchCurrentPlayer({
          attributes: { ...player.attributes, [attribute]: result.new_value },
          attribute_points_available: result.points_remaining,
          max_mp: result.max_mp ?? player.max_mp,
          current_mp: result.current_mp ?? player.current_mp,
          magic_level: result.magic_level ?? player.magic_level,
        });
      } catch (err) {
        setSpendError(
          err instanceof Error ? err.message : 'Failed to spend AP',
        );
      } finally {
        setSpendingAttr(null);
      }
    },
    [
      token,
      player.attributes,
      player.attribute_points_available,
      patchCurrentPlayer,
    ],
  );

  const handleSpendProf = useCallback(
    async (
      profType: 'weapon' | 'magic' | 'magic_level',
      key: string,
      currentRank: number,
    ) => {
      if (!token) return;
      const profKey = `${profType}:${key}`;
      setSpendingProf(profKey);
      setSpendError(null);
      try {
        const result = await spendProficiencyPoints(token, {
          prof_type: profType,
          key,
          target_rank: currentRank + 1,
        });
        if (profType === 'magic_level') {
          patchCurrentPlayer({
            magic_level: result.new_rank,
            max_mp: result.max_mp ?? player.max_mp,
            current_mp: result.current_mp ?? player.current_mp,
            magic_rank_cap: result.magic_rank_cap ?? player.magic_rank_cap,
            magic_damage_bonus:
              result.magic_damage_bonus ?? player.magic_damage_bonus,
            proficiency_points_available: result.points_remaining,
          });
          return;
        }
        const profField =
          profType === 'weapon' ? 'weapon_proficiency' : 'magic_proficiency';
        patchCurrentPlayer({
          [profField]: {
            ...(profType === 'weapon'
              ? player.weapon_proficiency
              : player.magic_proficiency),
            [key]: result.new_rank,
          },
          proficiency_points_available: result.points_remaining,
          magic_rank_cap: result.magic_rank_cap ?? player.magic_rank_cap,
        });
      } catch (err) {
        setSpendError(
          err instanceof Error ? err.message : 'Failed to spend PP',
        );
      } finally {
        setSpendingProf(null);
      }
    },
    [
      token,
      player.weapon_proficiency,
      player.magic_proficiency,
      player.proficiency_points_available,
      player.max_mp,
      player.current_mp,
      player.magic_level,
      player.magic_rank_cap,
      player.magic_damage_bonus,
      patchCurrentPlayer,
    ],
  );

  // Auto-dismiss "Saved!" after 3 seconds
  useEffect(() => {
    if (saveStatus !== 'ok') return;
    const t = setTimeout(() => setSaveStatus('idle'), 3000);
    return () => clearTimeout(t);
  }, [saveStatus]);

  // Keep draft aligned with server-loaded backstory when user is not actively editing.
  useEffect(() => {
    const serverBackstory = player.backstory ?? '';
    if (!backstoryDirty && backstoryDraft !== serverBackstory) {
      setBackstoryDraft(serverBackstory);
    }
  }, [player.backstory, backstoryDirty, backstoryDraft]);

  const hpPercent = useMemo(() => {
    if (player.max_hp <= 0) return 0;
    return Math.max(
      0,
      Math.min(100, (player.current_hp / player.max_hp) * 100),
    );
  }, [player.current_hp, player.max_hp]);

  const mpPercent = useMemo(() => {
    if (player.max_mp <= 0) return 0;
    return Math.max(
      0,
      Math.min(100, (player.current_mp / player.max_mp) * 100),
    );
  }, [player.current_mp, player.max_mp]);

  const staminaPercent = useMemo(() => {
    if (player.max_stamina <= 0) return 0;
    return Math.max(
      0,
      Math.min(100, (player.current_stamina / player.max_stamina) * 100),
    );
  }, [player.current_stamina, player.max_stamina]);

  let hpClass: 'good' | 'warn' | 'danger' = 'danger';
  if (hpPercent > 50) {
    hpClass = 'good';
  } else if (hpPercent >= 25) {
    hpClass = 'warn';
  }
  const xpPercent =
    player.experience_next > 0
      ? (player.experience / player.experience_next) * 100
      : 0;

  const weightPercent = useMemo(() => {
    if (player.weight_capacity <= 0) return 0;
    return Math.max(
      0,
      Math.min(120, (player.inventory_weight / player.weight_capacity) * 100),
    );
  }, [player.inventory_weight, player.weight_capacity]);

  let weightClass: 'good' | 'warn' | 'danger' = 'danger';
  if (weightPercent < 80) {
    weightClass = 'good';
  } else if (weightPercent < 120) {
    weightClass = 'warn';
  }

  const factionLabel = FACTION_LABELS[player.faction] ?? 'Unknown faction';
  const missionActive =
    worldState.quest_flags['cooperative_mission_active'] === '1';
  const missionCompleted =
    worldState.quest_flags['cooperative_mission_completed'] === '1';
  const missionRequired =
    worldState.quest_flags['cooperative_mission_required_players'] ?? '0';
  const missionDone =
    worldState.quest_flags['cooperative_mission_completed_players'] ?? '0';
  const missionObjective =
    worldState.quest_flags['cooperative_mission_objective'] ??
    'Gather in the Isles of Myr and align on a joint plan before moving forward.';
  let missionStatusLabel = t('sheet.mission.inactive');
  if (missionCompleted) {
    missionStatusLabel = t('sheet.mission.completed');
  } else if (missionActive) {
    missionStatusLabel = t('sheet.mission.active_blocking');
  }

  const tabLabels: Record<TabId, string> = {
    summary: t('sheet.tabs.summary'),
    spells: t('sheet.tabs.spells'),
    items: t('sheet.tabs.items'),
    proficiencies: t('sheet.tabs.proficiencies'),
    macros: t('sheet.tabs.macros'),
  };

  return (
    <aside className='panel sheet'>
      <header>
        <h2>{player.name || t('sheet.no_character')}</h2>
        <p>
          {player.inferred_class} • Level {player.level}
        </p>
        <span className='faction-badge'>{factionLabel}</span>
      </header>

      <nav
        className='sheet-tabs'
        aria-label={t('sheet.tabs.aria_label')}
        role='tablist'
        onKeyDown={(e) => {
          const idx = TABS.indexOf(activeTab);
          if (e.key === 'ArrowRight') {
            e.preventDefault();
            const next = TABS[(idx + 1) % TABS.length];
            setActiveTab(next);
            tabRefs.current[(idx + 1) % TABS.length]?.focus();
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            const prev = TABS[(idx - 1 + TABS.length) % TABS.length];
            setActiveTab(prev);
            tabRefs.current[(idx - 1 + TABS.length) % TABS.length]?.focus();
          }
        }}
      >
        {TABS.map((tab, i) => {
          return (
            <button
              key={tab}
              type='button'
              role='tab'
              id={`tab-${tab}`}
              aria-selected={activeTab === tab}
              aria-controls={`panel-${tab}`}
              tabIndex={activeTab === tab ? 0 : -1}
              className={activeTab === tab ? 'active' : ''}
              ref={(el) => {
                tabRefs.current[i] = el;
              }}
              onClick={() => setActiveTab(tab)}
            >
              {tabLabels[tab]}
            </button>
          );
        })}
      </nav>

      {activeTab === 'summary' && (
        <div role='tabpanel' id='panel-summary' aria-labelledby='tab-summary'>
          <section>
            <strong>
              HP: {player.current_hp}/{player.max_hp}
            </strong>
            <div className='bar'>
              <span
                className={`fill ${hpClass}`}
                style={{ width: `${hpPercent}%` }}
              />
            </div>
          </section>

          <section>
            <strong>
              MP: {player.current_mp}/{player.max_mp}
            </strong>
            <div className='bar'>
              <span className='fill mp' style={{ width: `${mpPercent}%` }} />
            </div>
          </section>

          <section>
            <strong>
              Stamina: {player.current_stamina}/{player.max_stamina}
            </strong>
            <div className='bar'>
              <span
                className='fill stamina'
                style={{ width: `${staminaPercent}%` }}
              />
            </div>
          </section>

          <section>
            <strong>
              XP: {player.experience}/{player.experience_next}
            </strong>
            <div className='bar'>
              <span
                className='fill xp'
                style={{ width: `${Math.max(0, Math.min(100, xpPercent))}%` }}
              />
            </div>
          </section>

          <section>
            <h3>{t('sheet.sections.attributes')}</h3>
            <ul className='attributes'>
              <li>STR {player.attributes.strength}</li>
              <li>DEX {player.attributes.dexterity}</li>
              <li>INT {player.attributes.intelligence}</li>
              <li>VIT {player.attributes.vitality}</li>
              <li>LUK {player.attributes.luck}</li>
              <li>CAR {player.attributes.charisma}</li>
            </ul>
          </section>

          <section>
            <h3>{t('sheet.sections.backstory')}</h3>
            <textarea
              value={backstoryDraft}
              onChange={(event) => {
                setBackstoryDraft(event.target.value);
                setBackstoryDirty(true);
                setSaveStatus('idle');
              }}
              maxLength={BACKSTORY_MAX}
            />
            <div className='backstory-footer'>
              <small className='muted'>
                {t('sheet.backstory_counter', { count: backstoryDraft.length })}
              </small>
              <div className='backstory-actions'>
                {saveStatus === 'ok' && (
                  <small className='save-ok'>{t('sheet.saved')}</small>
                )}
                {saveStatus === 'error' && (
                  <small className='error'>{t('sheet.failed')}</small>
                )}
                <button
                  type='button'
                  disabled={
                    !token ||
                    saving ||
                    backstoryDraft.trim().length < BACKSTORY_MIN
                  }
                  onClick={async () => {
                    if (!token) return;
                    setSaving(true);
                    setSaveStatus('idle');
                    try {
                      await updateCharacterBackstory(
                        token,
                        backstoryDraft.trim(),
                      );
                      patchCurrentPlayer({ backstory: backstoryDraft.trim() });
                      setBackstoryDirty(false);
                      logClient('info', 'character-sheet', 'Backstory saved', {
                        length: backstoryDraft.trim().length,
                      });
                      setSaveStatus('ok');
                    } catch {
                      logClient(
                        'error',
                        'character-sheet',
                        'Failed to save backstory',
                      );
                      setSaveStatus('error');
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  {saving
                    ? t('sheet.actions.saving')
                    : t('sheet.actions.save_backstory')}
                </button>
              </div>
            </div>
            <small className='muted'>{t('sheet.backstory_help')}</small>
          </section>

          <section>
            <h3>{t('sheet.sections.secret_objective')}</h3>
            <p>{secretObjective || t('sheet.secret_objective_unavailable')}</p>
          </section>

          <section>
            <h3>{t('sheet.sections.coop_mission')}</h3>
            <p>
              {t('sheet.shared_location')}:{' '}
              <strong>{worldState.current_location}</strong>
            </p>
            <p>{missionObjective}</p>
            <small className='muted'>
              {t('sheet.status')}: {missionStatusLabel} · {t('sheet.progress')}:{' '}
              {missionDone}/{missionRequired}
            </small>
          </section>

          <section>
            <h3>{t('sheet.sections.conditions')}</h3>
            <div className='chips'>
              {player.conditions.map((condition) => (
                <span
                  key={condition.condition_id}
                  className={`chip ${condition.is_buff ? 'buff' : 'debuff'}`}
                >
                  {condition.name}
                </span>
              ))}
              {player.conditions.length === 0 && (
                <span className='muted'>{t('sheet.no_conditions')}</span>
              )}
            </div>
          </section>

          {Object.keys(factionReputations).length > 0 && (
            <section>
              <h3>{t('sheet.sections.reputation')}</h3>
              {Object.entries(factionReputations).map(([factionId, score]) => (
                <div key={factionId} className='reputation-row'>
                  <span className='faction-name'>
                    {t(`sheet.factions.${factionId}`, {
                      defaultValue: formatFactionName(factionId),
                    })}
                  </span>
                  <span
                    className={`reputation-score ${score >= 0 ? 'positive' : 'negative'}`}
                  >
                    {score > 0 ? '+' : ''}
                    {score} (
                    {t(
                      `sheet.reputation_labels.${getReputationLabel(score).toLowerCase()}`,
                    )}
                    )
                  </span>
                </div>
              ))}
            </section>
          )}

          <section>
            <h3>{t('sheet.sections.passive_milestones')}</h3>
            <ul className='milestones'>
              {player.passive_milestones.map((m) => (
                <li
                  key={m.name}
                  className='milestone unlocked'
                  title={m.description}
                >
                  {m.name}
                </li>
              ))}
              {player.passive_milestones.length === 0 && (
                <li className='muted'>{t('sheet.no_milestones')}</li>
              )}
            </ul>
          </section>
        </div>
      )}

      {activeTab === 'spells' && (
        <div role='tabpanel' id='panel-spells' aria-labelledby='tab-spells'>
          <section>
            <h3>{t('sheet.sections.elemental_proficiency')}</h3>
            <ul className='prof-list'>
              {Object.entries(player.magic_proficiency).map(
                ([element, level]) => {
                  const cost = ppCost(level);
                  const nextRank = level + 1;
                  const neededMagicLevel = requiredMagicLevelForRank(nextRank);
                  const profKey = `magic:${element}`;
                  const rankBlocked = nextRank > player.magic_rank_cap;
                  const canAfford =
                    player.proficiency_points_available >= cost &&
                    nextRank <= 20 &&
                    !rankBlocked;
                  const toneClass = elementToneClass(element);
                  return (
                    <li
                      key={element}
                      className={`prof-row prof-row-magic element-${toneClass}`}
                    >
                      <div className='prof-row-head'>
                        <div className='prof-title-wrap'>
                          <span
                            className={`element-badge element-${toneClass}`}
                          >
                            {getElementLabel(element)}
                          </span>
                          {player.spell_aliases[element] && (
                            <span className='prof-passive-note'>
                              alias: {player.spell_aliases[element]}
                            </span>
                          )}
                        </div>
                        <span className='prof-rank-pill'>
                          {t('sheet.rank')} {level}/20
                        </span>
                      </div>
                      <div className='prof-row-foot'>
                        {level >= 20 ? (
                          <span className='muted'>{t('sheet.max')}</span>
                        ) : (
                          <button
                            type='button'
                            className='btn-small'
                            disabled={spendingProf === profKey || !canAfford}
                            onClick={() =>
                              handleSpendProf('magic', element, level)
                            }
                            title={
                              canAfford
                                ? `Cost: ${cost} PP`
                                : rankBlocked
                                  ? t('sheet.need_magic_level', {
                                      level: neededMagicLevel,
                                      rank: nextRank,
                                    })
                                  : t('sheet.need_pp', { count: cost })
                            }
                          >
                            {spendingProf === profKey ? '…' : '+1'}
                          </button>
                        )}
                      </div>
                    </li>
                  );
                },
              )}
              {Object.keys(player.magic_proficiency).length === 0 && (
                <li className='muted'>{t('sheet.no_magic_proficiency')}</li>
              )}
            </ul>

            {Object.keys(player.magic_proficiency).length > 0 && (
              <>
                <label>
                  <span>{t('sheet.spells.spell_base')}</span>
                  <select
                    value={selectedSpellBase}
                    onChange={(event) => {
                      const base = event.target.value;
                      setSelectedSpellBase(base);
                      setSpellAlias(player.spell_aliases[base] ?? '');
                    }}
                  >
                    <option value=''>{t('sheet.select')}</option>
                    {Object.keys(player.magic_proficiency).map((base) => (
                      <option key={base} value={base}>
                        {base}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>{t('sheet.spells.custom_name')}</span>
                  <input
                    value={spellAlias}
                    onChange={(event) => setSpellAlias(event.target.value)}
                    placeholder={t('sheet.spells.custom_name_placeholder')}
                  />
                </label>
                <button
                  type='button'
                  disabled={
                    !token || saving || !selectedSpellBase || !spellAlias.trim()
                  }
                  onClick={async () => {
                    if (!token || !selectedSpellBase) return;
                    const next = {
                      ...player.spell_aliases,
                      [selectedSpellBase]: spellAlias.trim(),
                    };
                    setSaving(true);
                    setSaveStatus('idle');
                    try {
                      await updateCharacterSpellAliases(token, next);
                      patchCurrentPlayer({ spell_aliases: next });
                      logClient(
                        'info',
                        'character-sheet',
                        'Spell alias saved',
                        {
                          base: selectedSpellBase,
                          alias: spellAlias.trim(),
                        },
                      );
                      setSaveStatus('ok');
                    } catch {
                      logClient(
                        'error',
                        'character-sheet',
                        'Failed to save spell alias',
                        {
                          base: selectedSpellBase,
                        },
                      );
                      setSaveStatus('error');
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  {saving
                    ? t('sheet.actions.saving')
                    : t('sheet.actions.save_alias')}
                </button>
                {saveStatus === 'ok' && (
                  <small className='save-ok'>{t('sheet.saved')}</small>
                )}
                {saveStatus === 'error' && (
                  <small className='error'>{t('sheet.failed_to_save')}</small>
                )}
              </>
            )}
          </section>
        </div>
      )}

      {activeTab === 'items' && (
        <div role='tabpanel' id='panel-items' aria-labelledby='tab-items'>
          <section>
            <h3>{t('sheet.sections.weight')}</h3>
            <strong>
              {player.inventory_weight.toFixed(1)} /{' '}
              {player.weight_capacity.toFixed(1)} kg
            </strong>
            <div className='bar'>
              <span
                className={`fill ${weightClass}`}
                style={{ width: `${Math.min(weightPercent, 100)}%` }}
              />
            </div>
            <small className='muted'>
              {t('sheet.current_load')}: {weightPercent.toFixed(1)}%
            </small>
          </section>

          <section>
            <h3>{t('sheet.sections.currency')}</h3>
            <ul className='currency-grid'>
              <li>
                {t('sheet.currency.copper')}: {player.currency.copper}
              </li>
              <li>
                {t('sheet.currency.silver')}: {player.currency.silver}
              </li>
              <li>
                {t('sheet.currency.gold')}: {player.currency.gold}
              </li>
              <li>
                {t('sheet.currency.platinum')}: {player.currency.platinum}
              </li>
            </ul>
            <small className='muted'>
              {t('sheet.currency.total_copper')}:{' '}
              {player.currency.copper +
                player.currency.silver * 100 +
                player.currency.gold * 10_000 +
                player.currency.platinum * 1_000_000}
            </small>
          </section>

          <section>
            <h3>{t('sheet.sections.inventory')}</h3>
            <ul>
              {player.inventory.map((item) => (
                <li key={item.item_id}>
                  {item.name} x{item.quantity}
                </li>
              ))}
              {player.inventory.length === 0 && (
                <li className='muted'>{t('sheet.inventory_empty')}</li>
              )}
            </ul>
          </section>
        </div>
      )}

      {activeTab === 'proficiencies' && (
        <div
          role='tabpanel'
          id='panel-proficiencies'
          aria-labelledby='tab-proficiencies'
        >
          {spendError && (
            <div className='error' style={{ marginBottom: '0.5rem' }}>
              {spendError}
              <button
                type='button'
                className='link'
                onClick={() => setSpendError(null)}
                style={{ marginLeft: '0.5rem' }}
              >
                ✕
              </button>
            </div>
          )}

          {/* Section 1: Points Available */}
          <section>
            <h3>{t('sheet.sections.points_available')}</h3>
            <ul className='attributes'>
              <li>
                <strong>AP</strong> {player.attribute_points_available}
                <small className='muted'>
                  {' '}
                  ({t('sheet.attribute_points')})
                </small>
              </li>
              <li>
                <strong>PP</strong> {player.proficiency_points_available}
                <small className='muted'>
                  {' '}
                  ({t('sheet.proficiency_points')})
                </small>
              </li>
            </ul>
          </section>

          {/* Section 2: Weapon & Magic Proficiency */}
          <section>
            <h3>{t('sheet.sections.weapon_proficiency')}</h3>
            {Object.keys(player.weapon_proficiency).length === 0 ? (
              <p className='muted'>{t('sheet.no_weapon_proficiency')}</p>
            ) : (
              <ul className='prof-list'>
                {Object.entries(player.weapon_proficiency).map(
                  ([weapon, rank]) => {
                    const cost = ppCost(rank);
                    const profKey = `weapon:${weapon}`;
                    const canAfford =
                      player.proficiency_points_available >= cost && rank < 20;
                    return (
                      <li key={weapon} className='prof-row'>
                        <div className='prof-row-head'>
                          <span className='prof-label'>
                            {formatSkillKey(weapon)}
                          </span>
                          <span className='prof-rank-pill'>
                            {t('sheet.rank')} {rank}/20
                          </span>
                        </div>
                        <div className='prof-row-foot'>
                          {rank >= 20 ? (
                            <span className='muted'>{t('sheet.max')}</span>
                          ) : (
                            <button
                              type='button'
                              className='btn-small'
                              disabled={spendingProf === profKey || !canAfford}
                              onClick={() =>
                                handleSpendProf('weapon', weapon, rank)
                              }
                              title={
                                canAfford
                                  ? `Cost: ${cost} PP`
                                  : t('sheet.need_pp', { count: cost })
                              }
                            >
                              {spendingProf === profKey ? '…' : '+1'}
                            </button>
                          )}
                        </div>
                      </li>
                    );
                  },
                )}
              </ul>
            )}
          </section>

          <section>
            <h3>{t('sheet.sections.magic_level')}</h3>
            <div className='prof-row magic-core-card'>
              <div className='prof-row-head'>
                <div className='prof-title-wrap'>
                  <span className='prof-label'>
                    {t('sheet.magic_level_title')}
                  </span>
                  {(player.magic_level > 0 ||
                    Object.keys(player.magic_proficiency).length > 0) && (
                    <span className='prof-usage-badge'>
                      {t('sheet.usable_now')}
                    </span>
                  )}
                </div>
                <span className='prof-rank-pill'>
                  {t('sheet.level_label')} {player.magic_level}/500
                </span>
              </div>
              <div className='prof-stat-grid'>
                <div className='prof-stat'>
                  <strong>{player.max_mp}</strong>
                  <span>{t('sheet.magic_stats.max_mp')}</span>
                </div>
                <div className='prof-stat'>
                  <strong>+{player.magic_damage_bonus}%</strong>
                  <span>{t('sheet.magic_stats.damage_bonus')}</span>
                </div>
                <div className='prof-stat'>
                  <strong>{player.magic_rank_cap}/20</strong>
                  <span>{t('sheet.magic_stats.element_cap')}</span>
                </div>
              </div>
              <div className='prof-row-foot'>
                {player.magic_level >= 500 ? (
                  <span className='muted'>{t('sheet.max')}</span>
                ) : (
                  <button
                    type='button'
                    className='btn-small'
                    disabled={
                      spendingProf === 'magic_level:core' ||
                      player.magic_level >= magicLevelCapByCharacter ||
                      player.proficiency_points_available <
                        magicLevelCost(player.magic_level)
                    }
                    onClick={() =>
                      handleSpendProf('magic_level', 'core', player.magic_level)
                    }
                    title={
                      player.magic_level >= magicLevelCapByCharacter
                        ? t('sheet.need_character_level_for_magic', {
                            level: characterLevelNeededForMagicLevel(
                              player.magic_level + 1,
                            ),
                            magicLevel: player.magic_level + 1,
                          })
                        : player.proficiency_points_available <
                            magicLevelCost(player.magic_level)
                          ? t('sheet.need_pp', {
                              count: magicLevelCost(player.magic_level),
                            })
                          : `Cost: ${magicLevelCost(player.magic_level)} PP`
                    }
                  >
                    {spendingProf === 'magic_level:core' ? '…' : '+1'}
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* Section 3: Skills (organic, grouped by category) */}
          <section>
            <h3>{t('sheet.sections.skills')}</h3>
            <small className='muted'>{t('sheet.skills_hint')}</small>
            {SKILL_CATEGORIES.map((cat) => {
              const activeSkills = cat.skills
                .map((key) => ({ key, entry: player.skills[key] }))
                .filter(({ entry }) => entry && entry.rank > 0);
              if (activeSkills.length === 0) return null;
              return (
                <div key={cat.key} className='skill-category'>
                  <h4>{cat.label}</h4>
                  <ul className='skill-list'>
                    {activeSkills.map(({ key, entry }) => {
                      const threshold = skillImpactThreshold(entry.rank);
                      const progress = Math.min(1, entry.impact / threshold);
                      return (
                        <li key={key} className='skill-row'>
                          <div className='skill-row-head'>
                            <span className='skill-name'>
                              {formatSkillKey(key)}
                            </span>
                            <span className='skill-rank'>
                              {t('sheet.rank')} {entry.rank}
                            </span>
                          </div>
                          <div
                            className='bar skill-bar'
                            title={`${entry.impact.toFixed(1)} / ${threshold.toFixed(1)} impact`}
                          >
                            <span
                              className='fill skill'
                              style={{ width: `${progress * 100}%` }}
                            />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
            {Object.values(player.skills).every((s) => !s || s.rank === 0) && (
              <p className='muted'>{t('sheet.no_skills')}</p>
            )}
          </section>

          {/* Section 4: Attributes with AP spend */}
          <section>
            <h3>{t('sheet.sections.attributes')}</h3>
            {player.attribute_points_available > 0 && (
              <small className='muted'>
                {t('sheet.ap_available', {
                  count: player.attribute_points_available,
                })}
              </small>
            )}
            <ul className='attributes'>
              {(
                [
                  ['strength', 'STR'],
                  ['dexterity', 'DEX'],
                  ['intelligence', 'INT'],
                  ['vitality', 'VIT'],
                  ['luck', 'LUK'],
                  ['charisma', 'CAR'],
                ] as const
              ).map(([attr, label]) => {
                const val = player.attributes[attr];
                const isMilestone = val >= 20 && val % 20 === 0;
                const canSpend =
                  player.attribute_points_available > 0 && val < 250;
                return (
                  <li
                    key={attr}
                    className={isMilestone ? 'milestone-attr' : ''}
                  >
                    <span>
                      {label} {val}
                      {isMilestone ? ' ★' : ''}
                    </span>
                    {canSpend && (
                      <button
                        type='button'
                        className='btn-small'
                        disabled={spendingAttr === attr}
                        onClick={() => handleSpendAttr(attr)}
                      >
                        {spendingAttr === attr ? '…' : '+1'}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        </div>
      )}

      {activeTab === 'macros' && (
        <div role='tabpanel' id='panel-macros' aria-labelledby='tab-macros'>
          <section>
            <h3>{t('sheet.sections.hot_actions')}</h3>
            <ul>
              {player.macros.map((macro) => (
                <li key={macro.name}>
                  <strong>{macro.name}</strong> — {macro.template}
                </li>
              ))}
              {player.macros.length === 0 && (
                <li className='muted'>{t('sheet.no_macros')}</li>
              )}
            </ul>

            <label>
              <span>{t('sheet.macros.command')}</span>
              <input
                value={macroName}
                onChange={(event) => setMacroName(event.target.value)}
                placeholder={t('sheet.macros.command_placeholder')}
              />
            </label>
            <label>
              <span>{t('sheet.macros.template')}</span>
              <textarea
                value={macroTemplate}
                onChange={(event) => setMacroTemplate(event.target.value)}
                placeholder={t('sheet.macros.template_placeholder')}
              />
            </label>
            <button
              type='button'
              disabled={
                !token ||
                saving ||
                !macroName.trim().startsWith('/') ||
                !macroTemplate.trim()
              }
              onClick={async () => {
                if (!token) return;
                const nextMacros = [
                  ...player.macros.filter((m) => m.name !== macroName.trim()),
                  { name: macroName.trim(), template: macroTemplate.trim() },
                ];
                setSaving(true);
                setSaveStatus('idle');
                try {
                  await updateCharacterMacros(token, nextMacros);
                  patchCurrentPlayer({ macros: nextMacros });
                  logClient('info', 'character-sheet', 'Macro saved', {
                    name: macroName.trim(),
                  });
                  setMacroName('');
                  setMacroTemplate('');
                  setSaveStatus('ok');
                } catch {
                  logClient(
                    'error',
                    'character-sheet',
                    'Failed to save macro',
                    {
                      name: macroName.trim(),
                    },
                  );
                  setSaveStatus('error');
                } finally {
                  setSaving(false);
                }
              }}
            >
              {saving
                ? t('sheet.actions.saving')
                : t('sheet.actions.save_macro')}
            </button>
            {saveStatus === 'ok' && (
              <small className='save-ok'>{t('sheet.saved')}</small>
            )}
            {saveStatus === 'error' && (
              <small className='error'>{t('sheet.failed_to_save')}</small>
            )}
          </section>
        </div>
      )}
    </aside>
  );
});
