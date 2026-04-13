import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useShallow } from 'zustand/shallow';

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
const SKILL_CATEGORIES: Array<{ key: string; label: string; skills: string[] }> = [
  { key: 'combat',     label: 'Combat Arts',        skills: ['grapple', 'counterstrike', 'dual_wield', 'weapon_flow', 'endurance_combat'] },
  { key: 'stealth',    label: 'Shadow Arts',         skills: ['conceal', 'pickpocket', 'lockpick', 'ambush', 'disguise'] },
  { key: 'social',     label: 'Social Arts',         skills: ['persuasion', 'intimidation', 'deception', 'negotiation', 'charm'] },
  { key: 'politics',   label: 'Court & Politics',    skills: ['court_etiquette', 'faction_negotiation', 'rhetoric', 'law', 'influence_trade'] },
  { key: 'survival',   label: 'Survival',            skills: ['foraging', 'tracking', 'navigation', 'first_aid', 'camp_craft'] },
  { key: 'medicine',   label: 'Medicine',            skills: ['wound_treatment', 'poison_lore', 'disease_diagnosis', 'herbalism', 'surgery'] },
  { key: 'lore',       label: 'Lore',                skills: ['arcane_lore', 'history', 'faction_lore', 'creature_lore', 'ruin_reading'] },
  { key: 'crafting',   label: 'Crafting',            skills: ['smithing', 'alchemy', 'artifice', 'runework', 'tailoring'] },
  { key: 'ritual',     label: 'Ritual Arts',         skills: ['thread_sensing', 'spirit_binding', 'corruption_reading', 'seal_work', 'resonance'] },
  { key: 'athletics',  label: 'Athletics',           skills: ['climbing', 'swimming', 'sprinting', 'acrobatics', 'lifting'] },
  { key: 'perception', label: 'Perception',          skills: ['detect_magic', 'detect_lie', 'search', 'listen', 'appraise'] },
  { key: 'nature',     label: 'Nature & Beasts',     skills: ['beast_handling', 'herbalism_wild', 'weather_reading', 'terrain_lore', 'poison_craft'] },
  { key: 'tactics',    label: 'Tactics & Leadership',skills: ['battle_tactics', 'group_command', 'ambush_planning', 'retreat_coordination', 'morale'] },
  { key: 'mysticism',  label: 'Mysticism',           skills: ['dream_reading', 'void_lore', 'prophecy', 'fragment_reading', 'ash_memory'] },
];

function skillImpactThreshold(rank: number): number {
  return (rank + 1) ** 2 * 2.0;
}

function ppCost(currentRank: number): number {
  return Math.floor(currentRank / 4) + 1;
}

function formatSkillKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
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

export const CharacterSheet = memo(function CharacterSheet() {
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
  const [macroName, setMacroName] = useState('');
  const [macroTemplate, setMacroTemplate] = useState('');
  const [selectedSpellBase, setSelectedSpellBase] = useState('');
  const [spellAlias, setSpellAlias] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'ok' | 'error'>('idle');
  const [spendingAttr, setSpendingAttr] = useState<string | null>(null);
  const [spendingProf, setSpendingProf] = useState<string | null>(null);
  const [spendError, setSpendError] = useState<string | null>(null);

  const handleSpendAttr = useCallback(async (attribute: string) => {
    if (!token) return;
    setSpendingAttr(attribute);
    setSpendError(null);
    const currentVal = player.attributes[attribute as keyof typeof player.attributes];
    try {
      const result = await spendAttributePoints(token, { attribute, target_value: currentVal + 1 });
      patchCurrentPlayer({
        attributes: { ...player.attributes, [attribute]: result.new_value },
        attribute_points_available: result.points_remaining,
      });
    } catch (err) {
      setSpendError(err instanceof Error ? err.message : 'Failed to spend AP');
    } finally {
      setSpendingAttr(null);
    }
  }, [token, player.attributes, player.attribute_points_available, patchCurrentPlayer]);

  const handleSpendProf = useCallback(async (profType: 'weapon' | 'magic', key: string, currentRank: number) => {
    if (!token) return;
    const profKey = `${profType}:${key}`;
    setSpendingProf(profKey);
    setSpendError(null);
    try {
      const result = await spendProficiencyPoints(token, { prof_type: profType, key, target_rank: currentRank + 1 });
      const profField = profType === 'weapon' ? 'weapon_proficiency' : 'magic_proficiency';
      patchCurrentPlayer({
        [profField]: { ...(profType === 'weapon' ? player.weapon_proficiency : player.magic_proficiency), [key]: result.new_rank },
        proficiency_points_available: result.points_remaining,
      });
    } catch (err) {
      setSpendError(err instanceof Error ? err.message : 'Failed to spend PP');
    } finally {
      setSpendingProf(null);
    }
  }, [token, player.weapon_proficiency, player.magic_proficiency, player.proficiency_points_available, patchCurrentPlayer]);

  // Auto-dismiss "Saved!" after 3 seconds
  useEffect(() => {
    if (saveStatus !== 'ok') return;
    const t = setTimeout(() => setSaveStatus('idle'), 3000);
    return () => clearTimeout(t);
  }, [saveStatus]);

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
  let missionStatusLabel = 'Inactive';
  if (missionCompleted) {
    missionStatusLabel = 'Completed';
  } else if (missionActive) {
    missionStatusLabel = 'Active (blocking)';
  }

  return (
    <aside className='panel sheet'>
      <header>
        <h2>{player.name || 'No character'}</h2>
        <p>
          {player.inferred_class} • Level {player.level}
        </p>
        <span className='faction-badge'>{factionLabel}</span>
      </header>

      <nav
        className='sheet-tabs'
        aria-label='Character sheet tabs'
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
        {(['Stats', 'Spells', 'Items', 'Skills', 'Macros'] as const).map(
          (label, i) => {
            const tab = TABS[i];
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
                {label}
              </button>
            );
          },
        )}
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
            <h3>Attributes</h3>
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
            <h3>Backstory</h3>
            <textarea
              value={backstoryDraft}
              onChange={(event) => {
                setBackstoryDraft(event.target.value);
                setSaveStatus('idle');
              }}
              maxLength={1200}
            />
            <div className='backstory-footer'>
              <small className='muted'>{backstoryDraft.length}/1200</small>
              <div className='backstory-actions'>
                {saveStatus === 'ok' && (
                  <small className='save-ok'>Saved!</small>
                )}
                {saveStatus === 'error' && (
                  <small className='error'>Failed</small>
                )}
                <button
                  type='button'
                  disabled={
                    !token || saving || backstoryDraft.trim().length < 10
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
                  {saving ? 'Saving…' : 'Save backstory'}
                </button>
              </div>
            </div>
          </section>

          <section>
            <h3>Secret Objective</h3>
            <p>{secretObjective || 'Secret objective unavailable.'}</p>
          </section>

          <section>
            <h3>Initial Cooperative Mission</h3>
            <p>
              Shared location: <strong>{worldState.current_location}</strong>
            </p>
            <p>{missionObjective}</p>
            <small className='muted'>
              Status: {missionStatusLabel} · Progress: {missionDone}/
              {missionRequired}
            </small>
          </section>

          <section>
            <h3>Conditions</h3>
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
                <span className='muted'>No conditions</span>
              )}
            </div>
          </section>

          {Object.keys(factionReputations).length > 0 && (
            <section>
              <h3>Reputation</h3>
              {Object.entries(factionReputations).map(([factionId, score]) => (
                <div key={factionId} className='reputation-row'>
                  <span className='faction-name'>
                    {formatFactionName(factionId)}
                  </span>
                  <span
                    className={`reputation-score ${score >= 0 ? 'positive' : 'negative'}`}
                  >
                    {score > 0 ? '+' : ''}
                    {score} ({getReputationLabel(score)})
                  </span>
                </div>
              ))}
            </section>
          )}

          <section>
            <h3>Passive Milestones</h3>
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
                <li className='muted'>No milestones unlocked</li>
              )}
            </ul>
          </section>
        </div>
      )}

      {activeTab === 'spells' && (
        <div role='tabpanel' id='panel-spells' aria-labelledby='tab-spells'>
          <section>
            <h3>Magic Proficiency</h3>
            <ul>
              {Object.entries(player.magic_proficiency).map(
                ([element, level]) => (
                  <li key={element}>
                    {element} • level {level}
                    {player.spell_aliases[element]
                      ? ` • alias: ${player.spell_aliases[element]}`
                      : ''}
                  </li>
                ),
              )}
              {Object.keys(player.magic_proficiency).length === 0 && (
                <li className='muted'>No magic proficiency recorded</li>
              )}
            </ul>

            {Object.keys(player.magic_proficiency).length > 0 && (
              <>
                <label>
                  <span>Spell base</span>
                  <select
                    value={selectedSpellBase}
                    onChange={(event) => {
                      const base = event.target.value;
                      setSelectedSpellBase(base);
                      setSpellAlias(player.spell_aliases[base] ?? '');
                    }}
                  >
                    <option value=''>Select</option>
                    {Object.keys(player.magic_proficiency).map((base) => (
                      <option key={base} value={base}>
                        {base}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Custom name (cosmetic)</span>
                  <input
                    value={spellAlias}
                    onChange={(event) => setSpellAlias(event.target.value)}
                    placeholder='Example: Aurora Ember Slash'
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
                  {saving ? 'Saving...' : 'Save alias'}
                </button>
                {saveStatus === 'ok' && (
                  <small className='save-ok'>Saved!</small>
                )}
                {saveStatus === 'error' && (
                  <small className='error'>Failed to save</small>
                )}
                <small className='muted'>
                  The alias only changes the displayed name; damage and effects
                  still follow the base rules.
                </small>
              </>
            )}
          </section>
        </div>
      )}

      {activeTab === 'items' && (
        <div role='tabpanel' id='panel-items' aria-labelledby='tab-items'>
          <section>
            <h3>Weight</h3>
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
              Current load: {weightPercent.toFixed(1)}%
            </small>
          </section>

          <section>
            <h3>Currency</h3>
            <ul className='currency-grid'>
              <li>Copper: {player.currency.copper}</li>
              <li>Silver: {player.currency.silver}</li>
              <li>Gold: {player.currency.gold}</li>
              <li>Platinum: {player.currency.platinum}</li>
            </ul>
            <small className='muted'>
              Total in copper:{' '}
              {player.currency.copper +
                player.currency.silver * 100 +
                player.currency.gold * 10_000 +
                player.currency.platinum * 1_000_000}
            </small>
          </section>

          <section>
            <h3>Inventory</h3>
            <ul>
              {player.inventory.map((item) => (
                <li key={item.item_id}>
                  {item.name} x{item.quantity}
                </li>
              ))}
              {player.inventory.length === 0 && (
                <li className='muted'>Inventory is empty</li>
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
              <button type='button' className='link' onClick={() => setSpendError(null)} style={{ marginLeft: '0.5rem' }}>✕</button>
            </div>
          )}

          {/* Section 1: Points Available */}
          <section>
            <h3>Points Available</h3>
            <ul className='attributes'>
              <li>
                <strong>AP</strong> {player.attribute_points_available}
                <small className='muted'> (attribute points)</small>
              </li>
              <li>
                <strong>PP</strong> {player.proficiency_points_available}
                <small className='muted'> (proficiency points)</small>
              </li>
            </ul>
          </section>

          {/* Section 2: Weapon & Magic Proficiency */}
          <section>
            <h3>Weapon Proficiency</h3>
            {Object.keys(player.weapon_proficiency).length === 0 ? (
              <p className='muted'>No weapon proficiency recorded</p>
            ) : (
              <ul className='prof-list'>
                {Object.entries(player.weapon_proficiency).map(([weapon, rank]) => {
                  const cost = ppCost(rank);
                  const profKey = `weapon:${weapon}`;
                  const canAfford = player.proficiency_points_available >= cost && rank < 20;
                  return (
                    <li key={weapon} className='prof-row'>
                      <span>{weapon}</span>
                      <span className='muted'>rank {rank}/20</span>
                      {canAfford ? (
                        <button
                          type='button'
                          className='btn-small'
                          disabled={spendingProf === profKey}
                          onClick={() => handleSpendProf('weapon', weapon, rank)}
                          title={`Cost: ${cost} PP`}
                        >
                          {spendingProf === profKey ? '…' : `+1 (${cost} PP)`}
                        </button>
                      ) : rank >= 20 ? (
                        <span className='muted'>MAX</span>
                      ) : (
                        <span className='muted' title={`Need ${cost} PP`}>need {cost} PP</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section>
            <h3>Magic Proficiency</h3>
            {Object.keys(player.magic_proficiency).length === 0 ? (
              <p className='muted'>No magic proficiency recorded</p>
            ) : (
              <ul className='prof-list'>
                {Object.entries(player.magic_proficiency).map(([element, rank]) => {
                  const cost = ppCost(rank);
                  const profKey = `magic:${element}`;
                  const canAfford = player.proficiency_points_available >= cost && rank < 20;
                  return (
                    <li key={element} className='prof-row'>
                      <span>{element}</span>
                      <span className='muted'>rank {rank}/20</span>
                      {canAfford ? (
                        <button
                          type='button'
                          className='btn-small'
                          disabled={spendingProf === profKey}
                          onClick={() => handleSpendProf('magic', element, rank)}
                          title={`Cost: ${cost} PP`}
                        >
                          {spendingProf === profKey ? '…' : `+1 (${cost} PP)`}
                        </button>
                      ) : rank >= 20 ? (
                        <span className='muted'>MAX</span>
                      ) : (
                        <span className='muted' title={`Need ${cost} PP`}>need {cost} PP</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* Section 3: Skills (organic, grouped by category) */}
          <section>
            <h3>Skills</h3>
            <small className='muted'>Skills grow through use — no points to spend.</small>
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
                          <span className='skill-name'>{formatSkillKey(key)}</span>
                          <span className='skill-rank'>rank {entry.rank}</span>
                          <div className='bar skill-bar' title={`${entry.impact.toFixed(1)} / ${threshold.toFixed(1)} impact`}>
                            <span className='fill skill' style={{ width: `${progress * 100}%` }} />
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
            {Object.values(player.skills).every((s) => !s || s.rank === 0) && (
              <p className='muted'>No skills developed yet.</p>
            )}
          </section>

          {/* Section 4: Attributes with AP spend */}
          <section>
            <h3>Attributes</h3>
            {player.attribute_points_available > 0 && (
              <small className='muted'>{player.attribute_points_available} AP available — click +1 to spend (cap 250)</small>
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
                const canSpend = player.attribute_points_available > 0 && val < 250;
                return (
                  <li key={attr} className={isMilestone ? 'milestone-attr' : ''}>
                    <span>{label} {val}{isMilestone ? ' ★' : ''}</span>
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
            <h3>Hot Actions</h3>
            <ul>
              {player.macros.map((macro) => (
                <li key={macro.name}>
                  <strong>{macro.name}</strong> — {macro.template}
                </li>
              ))}
              {player.macros.length === 0 && (
                <li className='muted'>No macros created.</li>
              )}
            </ul>

            <label>
              <span>Command (example: /wind-slash)</span>
              <input
                value={macroName}
                onChange={(event) => setMacroName(event.target.value)}
                placeholder='/name-macro'
              />
            </label>
            <label>
              <span>Action template</span>
              <textarea
                value={macroTemplate}
                onChange={(event) => setMacroTemplate(event.target.value)}
                placeholder='Describe the action that will be expanded when the command is used'
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
              {saving ? 'Saving...' : 'Save macro'}
            </button>
            {saveStatus === 'ok' && <small className='save-ok'>Saved!</small>}
            {saveStatus === 'error' && (
              <small className='error'>Failed to save</small>
            )}
          </section>
        </div>
      )}
    </aside>
  );
});
