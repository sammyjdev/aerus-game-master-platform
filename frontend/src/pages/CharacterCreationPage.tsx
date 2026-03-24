import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { createCharacter } from '../api/http';
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
  dwarf: 'Dwarf',
  'half-elf': 'Half-Elf',
  corrupted: 'Corrupted',
};

export function CharacterCreationPage() {
  const navigate = useNavigate();
  const token = useGameStore((state) => state.token);

  const [name, setName] = useState('');
  const [race, setRace] = useState<Race>('human');
  const [faction, setFaction] = useState<Faction>('church_pure_flame');
  const [backstory, setBackstory] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => backstory.trim().length >= 50, [backstory]);

  const submit = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    if (!token || !canSubmit) return;

    void (async () => {
      setError(null);
      setLoading(true);
      logClient('info', 'character', 'Character creation started', {
        name,
        race,
        faction,
        backstory_length: backstory.trim().length,
      });

      try {
        await createCharacter(token, { name, race, faction, backstory });
        logClient('info', 'character', 'Character creation completed', {
          name,
          race,
          faction,
        });
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
            onChange={(event) => setRace(event.target.value as Race)}
          >
            {RACES.map((option) => (
              <option key={option} value={option}>
                {RACE_LABELS[option]}
              </option>
            ))}
          </select>
        </label>

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
        <button type='submit' disabled={!canSubmit || loading}>
          Enter the world
        </button>
      </form>
    </main>
  );
}
