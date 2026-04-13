import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { analyzeBackstory, createCharacter } from '../api/http';
import { logClient } from '../debug/logger';
import { useGameStore } from '../store/gameStore';
import type { Faction, Race } from '../types';

const FACTIONS: {
  id: Faction;
  name: string;
  description: string;
  color: string;
}[] = [
  {
    id: 'church_pure_flame',
    name: 'Church of the Pure Flame',
    description: 'Sacred and austere.',
    color: '#FFD700',
  },
  {
    id: 'empire_valdrek',
    name: 'Empire of Valdrek',
    description: 'Militaristic and imposing.',
    color: '#C41E3A',
  },
  {
    id: 'guild_of_threads',
    name: 'Guild of Threads',
    description: 'Mysterious and scholarly.',
    color: '#7B2FBE',
  },
  {
    id: 'children_of_broken_thread',
    name: 'Children of the Broken Thread',
    description: 'Outcast and desperate.',
    color: '#8B8680',
  },
];

const RACES: Race[] = ['human', 'elf', 'dwarf', 'half-elf', 'corrupted'];
const RACE_LABELS: Record<Race, string> = {
  human: 'Human',
  elf: 'Elf',
  dwarf: 'Forger (Dwarf)',
  'half-elf': 'Half-Elf',
  corrupted: 'Corrupted',
};

const SUBRACES: Partial<Record<Race, Array<{ id: string; label: string }>>> = {
  human: [
    { id: 'human_northerner', label: 'Northerner — STR/INT focused, ash memory' },
    { id: 'human_trader',     label: 'Trader — LUK/DEX focused, negotiation' },
    { id: 'human_khorathi',   label: 'Khorathi — VIT focused, endurance' },
    { id: 'human_dawnmere',   label: 'Dawnmere — balanced, thread-sensitive' },
  ],
  elf: [
    { id: 'elf_twilight',       label: 'Twilight Elf — high INT, arcane focus' },
    { id: 'elf_corrupted_fae',  label: 'Corrupted Fae — INT/LUK, void-touched' },
    { id: 'elf_mist',           label: 'Mist Elf — LUK/DEX, elusive nature' },
    { id: 'elf_wandering_fae',  label: 'Wandering Fae — high DEX, swift' },
  ],
  dwarf: [
    { id: 'forger_stone_goliath', label: 'Stone Goliath — high STR, smithing' },
    { id: 'forger_deep_dwarf',    label: 'Deep Dwarf — INT/VIT, ruin reader' },
    { id: 'forger_stenvaard',     label: 'Stenvaard — STR/VIT, battle-hardened' },
  ],
};

export function CharacterCreationPage() {
  const navigate = useNavigate();
  const token = useGameStore((state) => state.token);

  const [name, setName] = useState('');
  const [race, setRace] = useState<Race>('human');
  const [subrace, setSubrace] = useState<string>('human_northerner');
  const [faction, setFaction] = useState<Faction>('church_pure_flame');
  const [backstory, setBackstory] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skillsGranted, setSkillsGranted] = useState<string[] | null>(null);

  const subraceOptions = SUBRACES[race] ?? [];

  const handleRaceChange = (newRace: Race) => {
    setRace(newRace);
    const options = SUBRACES[newRace];
    setSubrace(options ? options[0].id : '');
  };

  const canSubmit = useMemo(() => backstory.trim().length >= 50, [backstory]);

  const submit = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    if (!token || !canSubmit) return;

    void (async () => {
      setError(null);
      setSkillsGranted(null);
      setLoading(true);
      logClient('info', 'character', 'Character creation started', {
        name,
        race,
        subrace: subrace || null,
        faction,
        backstory_length: backstory.trim().length,
      });

      try {
        await createCharacter(token, {
          name,
          race,
          faction,
          backstory,
          subrace: subrace || null,
        });
        logClient('info', 'character', 'Character creation completed', { name, race, subrace, faction });

        // Analyze backstory to seed initial skills
        try {
          const analysis = await analyzeBackstory(token);
          const skillNames = Object.keys(analysis.granted_skills);
          if (skillNames.length > 0) {
            setSkillsGranted(skillNames);
            logClient('info', 'character', 'Backstory skills seeded', { skills: skillNames });
            // Brief delay so user can read the message, then navigate
            await new Promise((r) => setTimeout(r, 2500));
          }
        } catch {
          // Backstory analysis is non-critical — proceed anyway
          logClient('warn', 'character', 'Backstory analysis skipped');
        }

        navigate('/game');
      } catch (error_) {
        const message =
          error_ instanceof Error ? error_.message : 'Failed to create character';
        logClient('error', 'character', 'Character creation failed', {
          message,
          name,
          race,
          faction,
        });
        setError(message);
      } finally {
        setLoading(false);
      }
    })();
  };

  return (
    <main className='character-page'>
      <h1>Character Creation</h1>
      <form onSubmit={submit} className='character-form'>
        <label>
          <span>Name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </label>

        <label>
          <span>Race</span>
          <select
            value={race}
            onChange={(event) => handleRaceChange(event.target.value as Race)}
          >
            {RACES.map((option) => (
              <option key={option} value={option}>
                {RACE_LABELS[option]}
              </option>
            ))}
          </select>
        </label>

        {subraceOptions.length > 0 && (
          <label>
            <span>Subrace</span>
            <select
              value={subrace}
              onChange={(event) => setSubrace(event.target.value)}
            >
              {subraceOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        )}

        <div className='faction-grid'>
          {FACTIONS.map((option) => (
            <button
              key={option.id}
              type='button'
              className={`faction-card ${faction === option.id ? 'active' : ''}`}
              onClick={() => setFaction(option.id)}
              style={{ borderColor: option.color }}
            >
              <strong>{option.name}</strong>
              <p>{option.description}</p>
            </button>
          ))}
        </div>

        <label>
          <span>Backstory</span>
          <textarea
            value={backstory}
            onChange={(event) => setBackstory(event.target.value)}
            minLength={50}
            rows={5}
            required
          />
        </label>

        {error && <p className='error'>{error}</p>}

        {skillsGranted && skillsGranted.length > 0 && (
          <p className='save-ok'>
            Skills from backstory: {skillsGranted.join(', ')}. Entering the world…
          </p>
        )}

        <button type='submit' disabled={!canSubmit || loading}>
          {loading ? 'Creating character…' : 'Enter the world'}
        </button>
      </form>
    </main>
  );
}
