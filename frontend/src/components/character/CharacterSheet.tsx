import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { useShallow } from 'zustand/shallow';

import {
  updateCharacterSpellAliases,
  updateCharacterBackstory,
  updateCharacterMacros,
} from '../../api/http';
import { logClient } from '../../debug/logger';
import { useGameStore } from '../../store/gameStore';

const FACTION_LABELS = {
  church_pure_flame: 'Church of the Pure Flame',
  empire_valdrek: 'Empire of Valdrek',
  guild_of_threads: 'Guild of Threads',
  children_of_broken_thread: 'Children of the Broken Thread',
};

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

const TABS = ['summary', 'spells', 'items', 'proficiencies', 'macros'] as const
type TabId = typeof TABS[number]

export const CharacterSheet = memo(function CharacterSheet() {
  const { player, secretObjective, worldState, token, patchCurrentPlayer } = useGameStore(
    useShallow((state) => ({
      player: state.gameState.current_player,
      secretObjective: state.gameState.secret_objective,
      worldState: state.gameState.world_state,
      token: state.token,
      patchCurrentPlayer: state.patchCurrentPlayer,
    })),
  );
  const factionReputations = useGameStore(
    useShallow((state) => state.faction_reputations[state.gameState.current_player.player_id] ?? {}),
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
          const idx = TABS.indexOf(activeTab)
          if (e.key === 'ArrowRight') {
            e.preventDefault()
            const next = TABS[(idx + 1) % TABS.length]
            setActiveTab(next)
            tabRefs.current[(idx + 1) % TABS.length]?.focus()
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault()
            const prev = TABS[(idx - 1 + TABS.length) % TABS.length]
            setActiveTab(prev)
            tabRefs.current[(idx - 1 + TABS.length) % TABS.length]?.focus()
          }
        }}
      >
        {(['Summary', 'Spells', 'Items', 'Proficiencies', 'Macros'] as const).map((label, i) => {
          const tab = TABS[i]
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
              ref={(el) => { tabRefs.current[i] = el }}
              onClick={() => setActiveTab(tab)}
            >
              {label}
            </button>
          )
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
            <small className='muted'>{backstoryDraft.length}/1200</small>
            <button
              type='button'
              disabled={!token || saving || backstoryDraft.trim().length < 10}
              onClick={async () => {
                if (!token) return;
                setSaving(true);
                setSaveStatus('idle');
                try {
                  await updateCharacterBackstory(token, backstoryDraft.trim());
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
              {saving ? 'Saving...' : 'Save backstory'}
            </button>
            {saveStatus === 'ok' && <small className='save-ok'>Saved!</small>}
            {saveStatus === 'error' && (
              <small className='error'>Failed to save</small>
            )}
          </section>

          <section>
            <h3>Secret Objective</h3>
            <p>{secretObjective || 'Secret objective unavailable.'}</p>
          </section>

          <section>
            <h3>Initial Cooperative Mission</h3>
            <p>
              Shared location:{' '}
              <strong>{worldState.current_location}</strong>
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
                  <span className='faction-name'>{formatFactionName(factionId)}</span>
                  <span className={`reputation-score ${score >= 0 ? 'positive' : 'negative'}`}>
                    {score > 0 ? '+' : ''}{score} ({getReputationLabel(score)})
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
              {saveStatus === 'ok' && <small className='save-ok'>Saved!</small>}
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
        <div role='tabpanel' id='panel-proficiencies' aria-labelledby='tab-proficiencies'>
          <section>
          <h3>Weapon Proficiency</h3>
          <ul>
            {Object.entries(player.weapon_proficiency).map(
              ([weapon, level]) => (
                <li key={weapon}>
                  {weapon} • level {level}
                </li>
              ),
            )}
            {Object.keys(player.weapon_proficiency).length === 0 && (
              <li className='muted'>No weapon proficiency recorded</li>
            )}
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
                logClient('error', 'character-sheet', 'Failed to save macro', {
                  name: macroName.trim(),
                });
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
})

