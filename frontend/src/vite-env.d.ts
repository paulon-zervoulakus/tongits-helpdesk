/// <reference types="vite/client" />

declare global {
    interface Window {
        webkitAudioContext: typeof AudioContext;
    }
}