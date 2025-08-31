import React, { useEffect, useRef, useState } from 'react';
import { AuthData, GoogleCredentialResponse } from '../types/index';
import { renderGoogleSignInButton } from '../services/googleAuth';

interface AuthPageProps {
  onLogin: (authData: AuthData) => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onLogin }) => {
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const initGoogleSignIn = () => {
      if (googleButtonRef.current) {
        renderGoogleSignInButton('google-signin-button', handleGoogleSignIn);
      } else {
        // Retry if Google hasn't loaded yet
        setTimeout(initGoogleSignIn, 100);
      }
    };

    initGoogleSignIn();
  }, []);

  const handleGoogleSignIn = async (response: GoogleCredentialResponse) => {
    setIsLoading(true);
    setError('');

    try {
      // Send the credential to your backend for verification
      const result = await fetch('http://localhost:8000/api/auth/google', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ credential: response.credential })
      });

      if (!result.ok) {
        throw new Error('Authentication failed');
      }

      const authData = await result.json();
      
      onLogin(authData.data);
    } catch (error) {
      console.error('Google sign-in error:', error);
      setError('Failed to sign in with Google. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>📅 Booking Platform</h1>
        <p>Sign in to manage your bookings and chat with our assistant</p>
        
        {error && <div className="error-message">{error}</div>}
        
        <div className="google-signin-container">
          <div
            id="google-signin-button"
            ref={googleButtonRef}
            style={{ width: '100%' }}
          />
        </div>
        
        {isLoading && (
          <div style={{ marginTop: '10px', color: '#666' }}>
            Signing in...
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthPage;