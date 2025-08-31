// src/services/googleAuth.ts
import { GoogleCredentialResponse } from '../types';

/**
 * Initializes Google Authentication
 * This should be called early in your application lifecycle
 * typically in App.tsx or another root component
 */
declare global {
  interface Window {
    google: any;
  }
}
export const initializeGoogleAuth = (): Promise<void> => {
  return new Promise(async (resolve, reject) => {
    try {
      // First load the Google script
      await loadGoogleScript();
      
      // Wait for the Google API to be fully available
      if (!window.google || !window.google.accounts || !window.google.accounts.id) {
        // If not available immediately, wait a short time
        await new Promise(r => setTimeout(r, 100));
        
        // Check again
        if (!window.google || !window.google.accounts || !window.google.accounts.id) {
          throw new Error('Google Identity Services not loaded properly');
        }
      }
      
      // Initialize with default configuration
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || 'xxx',
        callback: () => {
          // Default callback - can be overridden when rendering the button
          console.log('Google Sign-In initialized successfully');
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      
      console.log('Google Auth initialized successfully');
      resolve();
    } catch (error) {
      console.error('Failed to initialize Google Auth:', error);
      reject(error);
    }
  });
};

/**
 * Renders the Google Sign-In button in the specified element
 * and sets up the callback for handling the sign-in response
 */
export const renderGoogleSignInButton = (
  elementId: string, 
  callback: (response: GoogleCredentialResponse) => void
): void => {
  const container = document.getElementById(elementId);
  if (!container) return;
    
  // Clear the container first
  container.innerHTML = '';      
  // Check if Google Identity Services is loaded
  if (window.google && window.google.accounts && window.google.accounts.id) {
    // Configure the Google Sign-In button with the specific callback  
    const clientid = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'YYYY';    
    window.google.accounts.id.initialize({
      client_id: clientid,
      callback: callback,
      auto_select: false,
      cancel_on_tap_outside: true,
    });      
    // Render the button
    window.google.accounts.id.renderButton(container, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      text: 'signin_with',
      shape: 'rectangular',
      logo_alignment: 'left',
      width: container.offsetWidth,
    });
  } else {
    console.error('Google Identity Services not loaded properly');
    
    // Fallback message
    const errorMessage = document.createElement('div');
    errorMessage.textContent = 'Google Sign-In is not available right now. Please try again later.';
    errorMessage.style.color = 'red';
    container.appendChild(errorMessage);
  }
};

/**
 * Loads the Google Identity Services script
 */
export const loadGoogleScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    // Skip if already loaded
    if (document.querySelector('script#google-identity-services')) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-identity-services';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google Identity Services'));
    
    document.head.appendChild(script);
  });
};