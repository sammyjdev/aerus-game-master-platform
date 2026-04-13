import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useGameStore } from '../../store/gameStore';
import { CharacterSheet } from './CharacterSheet';

const apiMocks = vi.hoisted(() => ({
  updateCharacterBackstory: vi.fn().mockResolvedValue({ status: 'updated' }),
  updateCharacterMacros: vi
    .fn()
    .mockResolvedValue({ status: 'updated', macros: [] }),
  updateCharacterSpellAliases: vi
    .fn()
    .mockResolvedValue({ status: 'updated', aliases: {} }),
}));

vi.mock('../../api/http', () => ({
  updateCharacterBackstory: apiMocks.updateCharacterBackstory,
  updateCharacterMacros: apiMocks.updateCharacterMacros,
  updateCharacterSpellAliases: apiMocks.updateCharacterSpellAliases,
}));

describe('CharacterSheet', () => {
  beforeEach(() => {
    apiMocks.updateCharacterBackstory.mockClear();
    apiMocks.updateCharacterMacros.mockClear();
    apiMocks.updateCharacterSpellAliases.mockClear();
    useGameStore.setState((state) => ({
      ...state,
      token: 'token',
      gameState: {
        ...state.gameState,
        current_player: {
          ...state.gameState.current_player,
          name: 'Kael',
          backstory: 'Former mercenary summoned to Aerus.',
          magic_proficiency: { fogo: 2 },
          spell_aliases: {},
          macros: [],
        },
      },
    }));
  });

  it('updates the spell alias in the UI immediately after saving', async () => {
    const user = userEvent.setup();
    render(<CharacterSheet />);

    await user.click(screen.getByRole('tab', { name: 'Spells' }));
    await user.selectOptions(screen.getByRole('combobox'), 'fogo');
    await user.type(
      screen.getByPlaceholderText('Example: Aurora Ember Slash'),
      'Crimson Blade',
    );
    await user.click(screen.getByRole('button', { name: 'Save alias' }));

    await waitFor(() => {
      expect(apiMocks.updateCharacterSpellAliases).toHaveBeenCalled();
      expect(screen.getByText(/alias: Crimson Blade/i)).toBeInTheDocument();
    });
  });

  it('adds a macro to the UI immediately after saving', async () => {
    const user = userEvent.setup();
    render(<CharacterSheet />);

    await user.click(screen.getByRole('tab', { name: 'Macros' }));
    await user.type(screen.getByPlaceholderText('/name-macro'), '/strike');
    await user.type(
      screen.getByPlaceholderText(
        'Describe the action that will be expanded when the command is used',
      ),
      'I step forward with a heavy strike.',
    );
    await user.click(screen.getByRole('button', { name: 'Save macro' }));

    await waitFor(() => {
      expect(apiMocks.updateCharacterMacros).toHaveBeenCalled();
      expect(screen.getByText('/strike')).toBeInTheDocument();
      expect(
        screen.getByText(/I step forward with a heavy strike./i),
      ).toBeInTheDocument();
    });
  });
});
