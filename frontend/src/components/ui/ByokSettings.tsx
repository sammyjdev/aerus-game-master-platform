import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { registerByokKey } from '../../api/http';
import { logClient } from '../../debug/logger';

interface ByokSettingsProps {
  token: string | null;
}

export function ByokSettings({ token }: Readonly<ByokSettingsProps>) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!token || !apiKey.trim()) {
      logClient('warn', 'byok', 'Attempted to save an invalid key');
      setError(t('game_ui.byok.errors.invalid_key'));
      return;
    }

    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      await registerByokKey(token, apiKey.trim());
      logClient('info', 'byok', 'BYOK key registered successfully');
      setMessage(t('game_ui.byok.status.saved'));
      setApiKey('');
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : t('game_ui.byok.errors.save_failed');
      logClient('error', 'byok', 'Failed to register BYOK key', {
        message: msg,
      });
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className='byok-settings'>
      <button
        className='byok-toggle'
        onClick={() => {
          setOpen((v) => !v);
          logClient('debug', 'byok', 'BYOK panel toggled', { open: !open });
        }}
        aria-label={t('game_ui.byok.aria_label')}
        title='BYOK'
      >
        🔑
      </button>

      {open && (
        <div className='byok-panel'>
          <div className='byok-title'>{t('game_ui.byok.title')}</div>
          <input
            className='byok-input'
            type='password'
            placeholder={t('game_ui.byok.placeholder')}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            disabled={loading}
          />
          <button className='byok-save' onClick={handleSave} disabled={loading}>
            {loading
              ? t('game_ui.byok.actions.saving')
              : t('game_ui.byok.actions.save')}
          </button>
          {message && <div className='byok-message'>{message}</div>}
          {error && <div className='byok-error'>{error}</div>}
        </div>
      )}
    </div>
  );
}
