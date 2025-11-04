// audio-processor.js - Place this in your public folder
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.silenceThreshold = 0.01;
    this.minSilenceDuration = 1000;
    this.lastSoundTime = Date.now();
    this.isSendingAudio = false;
  }

  hasAudioActivity(float32Array) {
    let sum = 0;
    for (let i = 0; i < float32Array.length; i++) {
      sum += Math.abs(float32Array[i]);
    }
    const average = sum / float32Array.length;
    return average > this.silenceThreshold;
  }

  floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    
    if (!input || !input[0]) {
      return true;
    }

    const inputData = input[0]; // First channel (mono)
    
    // Check if there's audio activity
    const hasActivity = this.hasAudioActivity(inputData);
    const now = Date.now();
    
    if (hasActivity) {
      this.lastSoundTime = now;
      if (!this.isSendingAudio) {
        console.log("🎤 Started detecting speech - beginning audio transmission");
        this.isSendingAudio = true;
      }
    }
    
    // Only send audio if there's current activity or we were recently sending
    const timeSinceLastSound = now - this.lastSoundTime;
    const shouldSend = hasActivity || (this.isSendingAudio && timeSinceLastSound < this.minSilenceDuration);
    
    if (shouldSend) {
      const pcm16 = this.floatTo16BitPCM(inputData);
      // Send data to main thread
      this.port.postMessage({ type: 'audio', data: pcm16 });
    } else if (this.isSendingAudio && timeSinceLastSound >= this.minSilenceDuration) {
      console.log("🔇 Silence detected - stopping audio transmission");
      this.isSendingAudio = false;
    }
    
    return true; // Keep processor alive
  }
}

registerProcessor('audio-processor', AudioProcessor);