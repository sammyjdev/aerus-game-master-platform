import { Suspense, lazy, useEffect, type ReactElement } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import { DebugPanel } from './components/ui/DebugPanel';
import { logClient } from './debug/logger';
import { useGameStore } from './store/gameStore';

const LoginPage = lazy(async () => {
  const module = await import('./pages/LoginPage');
  return { default: module.LoginPage };
});

const CharacterCreationPage = lazy(async () => {
  const module = await import('./pages/CharacterCreationPage');
  return { default: module.CharacterCreationPage };
});

const GamePage = lazy(async () => {
  const module = await import('./pages/GamePage');
  return { default: module.GamePage };
});

const AdminPage = lazy(async () => {
  const module = await import('./pages/AdminPage');
  return { default: module.AdminPage };
});

function ProtectedRoute({ children }: Readonly<{ children: ReactElement }>) {
  const token = useGameStore((state) => state.token);
  if (!token) {
    return <Navigate to='/' replace />;
  }
  return children;
}

function App() {
  const location = useLocation();

  useEffect(() => {
    logClient('info', 'router', 'Navigation', { path: location.pathname });
  }, [location.pathname]);

  return (
    <>
      <Suspense fallback={<main className='auth-page'>Loading...</main>}>
        <Routes>
          <Route path='/' element={<LoginPage />} />
          <Route
            path='/character'
            element={
              <ProtectedRoute>
                <CharacterCreationPage />
              </ProtectedRoute>
            }
          />
          <Route
            path='/game'
            element={
              <ProtectedRoute>
                <GamePage />
              </ProtectedRoute>
            }
          />
          <Route path='/admin' element={<AdminPage />} />
        </Routes>
      </Suspense>
      <DebugPanel />
    </>
  );
}

export default App;
