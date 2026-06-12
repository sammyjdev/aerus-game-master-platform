import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useGameStore } from '../../store/gameStore';
import { CharacterSheet } from './CharacterSheet';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const labels: Record<string, string> = {
        'sheet.tabs.spells': 'Spells',
        'sheet.tabs.macros': 'Macros',
        'sheet.spells.custom_name_placeholder': 'Example: Aurora Ember Slash',
        'sheet.actions.save_alias': 'Save alias',
        'sheet.macros.command_placeholder': '/name-macro',
        'sheet.macros.template_placeholder':
          'Describe the action that will be expanded when the command is used',
        'sheet.actions.save_macro': 'Save macro',
      };
      return labels[key] ?? key;
    },
  }),
}));

const apiMocks = vi.hoisted(() => ({
  updateCharacterBackstory: vi.fn().mockResolvedValue({ status: 'updated' }),
  updateCharacterMacros: vi
    .fn()
    .mockResolvedValue({ status: 'updated', macros: [] }),
  updateCharacterSpellAliases: vi
    .fn()
    .mockResolvedValue({ status: 'updated', aliases: {} }),
  spendAttributePoints: vi.fn(),
  spendProficiencyPoints: vi.fn(),
}));

vi.mock('../../api/http', () => ({
  updateCharacterBackstory: apiMocks.updateCharacterBackstory,
  updateCharacterMacros: apiMocks.updateCharacterMacros,
  updateCharacterSpellAliases: apiMocks.updateCharacterSpellAliases,
  spendAttributePoints: apiMocks.spendAttributePoints,
  spendProficiencyPoints: apiMocks.spendProficiencyPoints,
}));

describe('CharacterSheet', () => {
  beforeEach(() => {
    apiMocks.updateCharacterBackstory.mockClear();
    apiMocks.updateCharacterMacros.mockClear();
    apiMocks.updateCharacterSpellAliases.mockClear();
    apiMocks.spendAttributePoints.mockClear();
    apiMocks.spendProficiencyPoints.mockClear();
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
          magic_level: 12,
          magic_rank_cap: 4,
          magic_damage_bonus: 2,
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
