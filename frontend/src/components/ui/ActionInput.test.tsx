import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useGameStore } from '../../store/gameStore';
import { ActionInput } from './ActionInput';

const onSend = vi.fn();

describe('ActionInput', () => {
  beforeEach(() => {
    onSend.mockReset();
    useGameStore.setState((state) => ({
      ...state,
      gameState: {
        ...state.gameState,
        current_player: {
          ...state.gameState.current_player,
          macros: [
            {
              name: '/slash',
              template: 'I swing my weapon in a wide arc.',
            },
          ],
        },
      },
    }));
  });

  it('expands a macro command before sending', async () => {
    const user = userEvent.setup();
    render(<ActionInput onSend={onSend} />);

    await user.type(
      screen.getByPlaceholderText('Action... (↑↓ history · Ctrl+Enter to send)'),
      '/slash',
    );
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(onSend).toHaveBeenCalledWith(
      'I swing my weapon in a wide arc.',
    );
  });
});
