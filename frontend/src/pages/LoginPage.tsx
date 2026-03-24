import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getCharacter, login, redeemInvite } from '../api/http';
import { logClient } from '../debug/logger';
import { useGameStore } from '../store/gameStore';

export function LoginPage() {
  const navigate = useNavigate();
  const token = useGameStore((state) => state.token);
  const setToken = useGameStore((state) => state.setToken);

  const [mode, setMode] = useState<'redeem' | 'login'>('redeem');
  const [inviteCode, setInviteCode] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    logClient('info', 'auth', 'Session detected; validating character');
    getCharacter(token)
      .then(() => {
        logClient(
          'info',
          'auth',
          'Existing character found; redirecting to game',
        );
        navigate('/game');
      })
      .catch(() => {
        logClient(
          'warn',
          'auth',
          'Account without character; redirecting to character creation',
        );
        navigate('/character');
      });
  }, [navigate, token]);

  const handleSubmit = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    logClient('info', 'auth', 'Authentication request started', {
      mode,
      username,
      has_invite: Boolean(inviteCode.trim()),
    });

    void (async () => {
      try {
        if (mode === 'redeem') {
          const response = await redeemInvite({
            invite_code: inviteCode,
            username,
            password,
          });
          setToken(response.access_token);
          logClient('info', 'auth', 'First access completed successfully', {
            username,
          });
          navigate('/character');
        } else {
          const response = await login({ username, password });
          setToken(response.access_token);
          logClient('info', 'auth', 'Login completed successfully', {
            username,
          });
          navigate('/game');
        }
      } catch (error_) {
        const message =
          error_ instanceof Error ? error_.message : 'Failed to sign in';
        logClient('error', 'auth', 'Authentication failed', {
          username,
          mode,
          message,
        });
        setError(message);
      } finally {
        setLoading(false);
      }
    })();
  };

  const switchMode = (next: 'redeem' | 'login') => {
    setMode(next);
    setError(null);
    logClient('debug', 'auth', 'Authentication mode changed', { mode: next });
  };

  return (
    <main className='auth-page'>
      <h1>Aerus Game Master Platform</h1>

      <div className='auth-tabs'>
        <button
          type='button'
          className={mode === 'redeem' ? 'active' : ''}
          onClick={() => switchMode('redeem')}
        >
          First access
        </button>
        <button
          type='button'
          className={mode === 'login' ? 'active' : ''}
          onClick={() => switchMode('login')}
        >
          I already have an account
        </button>
      </div>

      <form onSubmit={handleSubmit} className='auth-form'>
        {mode === 'redeem' && (
          <label>
            <span>Invite code</span>
            <input
              value={inviteCode}
              onChange={(event) => setInviteCode(event.target.value)}
              required
            />
          </label>
        )}
        <label>
          <span>Username</span>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label>
          <span>Password</span>
          <input
            type='password'
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && <p className='error'>{error}</p>}
        <button type='submit' disabled={loading}>
          {mode === 'redeem' ? 'Enter the world' : 'Sign in'}
        </button>
      </form>
    </main>
  );
}
