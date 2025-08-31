import { useState, useEffect } from 'react';
import AuthPage from './components/Auth';
import LobbyPage from './components/Lobby';
import { initializeGoogleAuth } from './services/googleAuth';

function App() {
  const [authData, setAuthData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initApp = async () => {
      try {
        // Initialize Google Auth
        await initializeGoogleAuth();
        
        // Check for existing auth token
        const token = localStorage.getItem('access_token');
        const userData = localStorage.getItem('user_info');
        
        if (token && userData) {
          setAuthData({
            access_token: token,
            user: JSON.parse(userData)
          });
        }
      } catch (error) {
        console.error('Failed to initialize app:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initApp();
  }, []);

  const handleLogin = (data) => {
    setAuthData(data);
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user_info', JSON.stringify(data.user));
  };

  const handleLogout = () => {
    setAuthData(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    
    // Sign out from Google
    // if (window.google) {
    //   window.google.accounts.id.disableAutoSelect();
    // }
  };

  if (isLoading) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Loading...</h1>
        </div>
      </div>
    );
  }
  

  return (
    <div className="app">
      {!authData ? (
        <AuthPage onLogin={handleLogin} />
      ) : (
        <LobbyPage user={authData.user} onLogout={handleLogout} />
      )}
    </div>
  );
}

export default App;