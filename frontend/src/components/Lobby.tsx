import React, { useState, useRef, useEffect } from "react";
import { Send, Mic, Square, MessageCircle, Play } from "lucide-react";

// Types (you'll need to import these from your actual types file)
type MessageType = {
  text: string;
  source: string;
  sender: string;
  ai_response: string;
  isVoiceMessage?: boolean;
  audioUrl?: string;
};

type User = {
  name: string;
  picture?: string;
};

type LobbyProps = {
  user: User;
  onLogout: () => void;
}

type VoiceMessagePlayerProps = {
  audioUrl: string;
  isPlaying: boolean;
  onPlay: () => void;
  onStop: () => void;
}

const LobbyPage: React.FC<LobbyProps> = ({user, onLogout}) => {  
  const [currentlyPlaying, setCurrentlyPlaying] = useState<number | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [messages, setMessages] = useState<MessageType[]>([]);
  // const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  // const wsTextRef = useRef<WebSocket | null>(null);
  const wsVoiceRef = useRef<WebSocket | null>(null);    
  const currentAudioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const playbackQueueRef = useRef<Float32Array[]>([]);
  const token = localStorage.getItem("access_token") || "not found"  
  

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);
  
  // Clean up audio when component unmounts
  useEffect(() => {
    return () => {
      if (audioElement) {
        audioElement.pause();
      }
      // Clean up WebAudio resources
      if (currentAudioSourceRef.current) {
        try {
          currentAudioSourceRef.current.stop();
          currentAudioSourceRef.current.disconnect();
        } catch (e) {}
      }
      if (playbackContextRef.current) {
        playbackContextRef.current.close();
      }
    };
  }, [audioElement]);
  
  // // ============= VOICE RECORDING

  // Audio cancellation function
  const cancelCurrentAudio = () => {
    console.log("🛑 Cancelling current audio playback");
    
    // Stop current audio source if playing
    if (currentAudioSourceRef.current) {
      try {
        currentAudioSourceRef.current.stop();
        currentAudioSourceRef.current.disconnect();
      } catch (e) {
        // Audio might already be stopped
      }
      currentAudioSourceRef.current = null;
    }
    
    // Clear the audio queue
    playbackQueueRef.current = [];
    
    // Close and recreate audio context for clean state
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }
    
    console.log("✅ Audio cancelled and queue cleared");
  };

  // Modified play queued audio function
  const playQueuedAudio = () => {
    if (!playbackQueueRef.current.length) return;

    if (!playbackContextRef.current) {
      playbackContextRef.current = new AudioContext({ sampleRate: 22050 }); // Piper sample rate
    }

    const float32 = playbackQueueRef.current.shift()!;
    const buffer = playbackContextRef.current.createBuffer(1, float32.length, 22050);
    buffer.getChannelData(0).set(float32);

    const source = playbackContextRef.current.createBufferSource();
    source.buffer = buffer;
    source.connect(playbackContextRef.current.destination);
    
    // Store reference to current playing source
    currentAudioSourceRef.current = source;
    
    source.start();

    // Play next audio when done
    source.onended = () => {
      // Clear reference when audio ends naturally
      if (currentAudioSourceRef.current === source) {
        currentAudioSourceRef.current = null;
      }
      
      // Continue playing queue if not cancelled
      if (playbackQueueRef.current.length > 0) {
        playQueuedAudio();
      }
    };
  };

 

  let audioContext: AudioContext | null = null;
  let processor: ScriptProcessorNode | null = null;
  let input: MediaStreamAudioSourceNode | null = null;
  
  // Add silence detection variables
  const silenceThreshold = 0.01; // Adjust this value (0.001 = very sensitive, 0.1 = less sensitive)
  const minSilenceDuration = 500; // milliseconds of silence before stopping transmission
  let lastSoundTime = Date.now();
  let isSendingAudio = false;

  

  function mergeBuffers(chunks: Float32Array[]): Float32Array{
    const length = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const result = new Float32Array(length);
    let offset = 0;
    for (const chunk of chunks) {
      result.set(chunk, offset);
      offset += chunk.length;
    }
    return result;
  }
  function floatTo16BitPCM(float32Array: Float32Array): ArrayBuffer {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
  }
  function hasAudioActivity(float32Array: Float32Array): boolean {
    // Function to detect if audio contains speech
    let sum = 0;
    for (let i = 0; i < float32Array.length; i++) {
      sum += Math.abs(float32Array[i]);
    }
    const average = sum / float32Array.length;
    return average > silenceThreshold;
  }
  const startRecording = async () => {

    const ws = new WebSocket(`ws://localhost:8000/stream/voicein?token=${encodeURIComponent(token)}`);
    ws.binaryType = "arraybuffer";
    
    ws.onopen = async () => {
      wsVoiceRef.current = ws
      console.log("Voice WS connected ✅");
      setIsRecording(true);

      audioContext = new AudioContext({ sampleRate: 16000 });
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000 } });
      input = audioContext.createMediaStreamSource(stream);

      // 4096 buffer, mono
      processor = audioContext.createScriptProcessor(4096, 1, 1);

      let audioBuffer: Float32Array[] = []; // collect chunks

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const now = Date.now();
        const hasActivity = hasAudioActivity(inputData);

        if (hasActivity) {
          lastSoundTime = now;
          audioBuffer.push(new Float32Array(inputData)); // store speech
          if (!isSendingAudio) {
            console.log("🎤 Speech started");
            isSendingAudio = true;

            // 🛑 Stop AI playback IMMEDIATELY
            cancelCurrentAudio();
          }
        }

        const timeSinceLastSound = now - lastSoundTime;

        // when silence persists long enough, flush buffer
        if (isSendingAudio && timeSinceLastSound >= minSilenceDuration) {
          console.log("🔇 Speech ended, sending audio batch");

          // Merge collected audio into one array
          const merged = mergeBuffers(audioBuffer);

          // Convert to PCM16 and send once
          const pcm16 = floatTo16BitPCM(merged);
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(pcm16);

            // reset all
            audioBuffer = [];
            lastSoundTime = Date.now();
            isSendingAudio = false;
            console.log("message sent");
          }

          // reset state
          isSendingAudio = false;
          audioBuffer = [];
        }
      };

      input.connect(processor);
      processor.connect(audioContext.destination); 
    };

    ws.onmessage = (evt) => {
      /// This handles incoming message via websocket
      if(typeof evt.data === "string"){
        let message = evt.data;       

        // Handle audio cancellation - ADD THIS
        if (message === "CANCEL_AUDIO") {
          cancelCurrentAudio();
          return;
        }

        if (message.startsWith("TRANSCRIPT::")) {        
          const transcript = message.substring(12);
          if (transcript.trim() != "") {
            const userMessage = { 
              text: transcript, 
              source: "voice", 
              sender: "user", 
              ai_response: "" 
            };
            setMessages((prev) => [...prev, userMessage]);
          }
    
        } else if (message.startsWith("AI_RESPONSE::")) {
          const aiResponse = message.substring(13);
          if (aiResponse.trim() != ""){
            const errorMessage = { 
              text: "", 
              source: "text", 
              sender: "system", 
              ai_response: aiResponse.trim() 
            };      
            setMessages((prev) => [...prev, errorMessage]);
          }
        }
      } else if (evt.data instanceof ArrayBuffer) {
        cancelCurrentAudio();
        // PCM16 audio from Piper
        const int16 = new Int16Array(evt.data);
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) {
          float32[i] = int16[i] / 32768;
        }
        playbackQueueRef.current.push(float32);
        playQueuedAudio();
      }
    }

    ws.onclose = () => {      
      wsVoiceRef.current?.close();

      console.log("WS closed ❌");
      const errorMessage = { 
        text: "", 
        source: "text", 
        sender: "system", 
        ai_response: "Voice call ended."
      };      
      setMessages((prev) => [...prev, errorMessage]);
      setIsRecording(false);
      if (processor && input) {      
        input.disconnect(processor);
        processor.disconnect();      
        processor.onaudioprocess = null;
        processor = null;
        console.log("Processor disconnected");
      }
    }

    ws.onerror = (err) => {
      console.error("WS error ❌", err);
      const errorMessage = { 
        text: "", 
        source: "text", 
        sender: "system", 
        ai_response: "Error: Something wen't wrong."
      };      
      setMessages((prev) => [...prev, errorMessage]);
      setIsRecording(false);
    }

  };

  

  const stopRecording = () => {
    // Cancel current audio playback when stopping recording
    cancelCurrentAudio();
    
    // Reset silence detection variables
    isSendingAudio = false;
    lastSoundTime = Date.now();
    
    audioContext?.close();
    if (wsVoiceRef.current && wsVoiceRef.current.readyState === WebSocket.OPEN){
      console.log("Stopped recording");
      wsVoiceRef.current.close(); 
    } 
    setIsRecording(false);
  };

  
  

  const VoiceMessagePlayer:React.FC<VoiceMessagePlayerProps> = ({ audioUrl, isPlaying, onPlay, onStop }) => {
    return (
      <div className="flex items-center gap-2 audio">
        {isPlaying ? (
          <button
            onClick={onStop}
            className="bg-red-500 hover:bg-red-600 text-white p-2 rounded-full transition-colors"
          >
            <Square size={16} />
          </button>
        ) : (
          <button
            onClick={onPlay}
            className="bg-blue-500 hover:bg-blue-600 text-white p-2 rounded-full transition-colors"
          >
            <Play size={16} />
          </button>
        )}
        <span className="text-sm text-gray-600">Voice message</span>
      </div>
    );
  };

  // Add these functions
  const playAudio = (audioUrl: string, messageIndex: number | null) => {
    if (audioElement) {
      audioElement.pause();
    }
    
    const audio = new Audio(audioUrl);
    audio.onended = () => {
      setCurrentlyPlaying(null);
      setAudioElement(null);
    };
    
    audio.play();
    setCurrentlyPlaying(messageIndex);
    setAudioElement(audio);
  };

  const stopAudio = () => {    
    if (audioElement) {
      audioElement.pause();
      audioElement.currentTime = 0;
    }
    setCurrentlyPlaying(null);
    setAudioElement(null);
  };

  const handleKeyPress = () => console.log("handleKeyPress")
  const handleSendText = () => console.log("handleSendText")

  return (
    <div className="bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 items-center justify-center">
      <header className="header">
        <h1>Generative (AI)</h1>
        <div className="human-info">
          <img
            src={user?.picture || "https://via.placeholder.com/40"}
            alt="User"
            className="human-avatar"
          />
          <span>{user?.name}</span>
          <button className="logout-btn" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>
      <div className="flex min-h-[calc(100vh-95px)] bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 items-center justify-center p-4">      
        <div className="w-full max-w-2xl h-[600px] bg-white/10 backdrop-blur-lg rounded-3xl shadow-2xl border border-white/20 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 p-6 text-white">
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 rounded-full">
                <MessageCircle size={24} />
              </div>
              <div>
                <h1 className="text-xl font-bold">Customer Support Agentic</h1>
                <p className="text-purple-100 text-sm">Powered by Maiden AI</p>
              </div>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-gradient-to-b from-transparent to-black/5">
            {messages.length === 0 ? (
              <div className="text-center text-white/60 mt-20">
                <MessageCircle size={48} className="mx-auto mb-4 opacity-50" />
                <p className="text-lg">Start a conversation</p>
                <p className="text-sm">Type a message or use voice input</p>
              </div>
            ) : (
              messages.map((message, idx) => (
                <div
                  key={idx}
                  className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.sender === "user"
                        ? "bg-blue-500 text-white"
                        : "bg-gray-200 text-gray-800"
                    }`}
                  >
                    {message.isVoiceMessage && message.audioUrl && (
                      <VoiceMessagePlayer
                        audioUrl={message.audioUrl}
                        isPlaying={currentlyPlaying === idx}
                        onPlay={() => playAudio(message.audioUrl ?? "", idx)}
                        onStop={stopAudio}
                      />
                    )}
                    <p>{message.sender === "user" ? message.text : message.ai_response}</p>                  
                  </div>
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white/80 backdrop-blur p-4 rounded-2xl border border-white/20 shadow-lg">
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-gray-600 text-sm">Processing...</span>
                  </div>
                </div>
              </div>
            )}
            {isRecording && (
              <div className="flex justify-start">
                <div className="bg-white/80 backdrop-blur p-4 rounded-2xl border border-white/20 shadow-lg">
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-gray-600 text-sm">I'm Listening...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-6 bg-white/5 backdrop-blur border-t border-white/10">
            <div className="flex items-center justify-center gap-3 leading-none">
              { !isRecording && (<div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  rows={1}
                  className="w-full p-4 pr-14 bg-white/10 backdrop-blur border border-white/20 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-400/50 focus:border-purple-400/50 focus:bg-white/15 transition-all duration-200 text-white placeholder-white/60"
                  style={{ 
                    minHeight: '56px',
                    maxHeight: '120px',
                    height: 'auto'
                  }}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;                    
                    target.style.height = 'auto';
                    target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                  }}
                  disabled={isLoading}
                />
                <button
                  onClick={handleSendText}
                  disabled={!inputText.trim() || isLoading}
                  className="absolute right-2 bottom-2 p-3 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-xl hover:from-purple-600 hover:to-blue-600 hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:from-purple-500 disabled:hover:to-blue-500 shadow-lg"
                >
                  <Send size={18} />
                </button>
              </div>
              )}
              
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isLoading}
                className={`p-3.5 rounded-2xl transition-all duration-200 shadow-lg hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 w-[56px] h-[56px] flex items-center justify-center ${
                  isRecording
                    ? "bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white animate-pulse shadow-red-500/25"
                    : "bg-white/10 hover:bg-white/20 text-white border border-white/20 backdrop-blur shadow-purple-500/25"
                }`}
              >
                {isRecording ? <Square size={20} /> : <Mic size={20} />}
              </button>
            </div>
            
            {isRecording && (
              <div className="mt-3 flex items-center justify-center gap-2 text-white/80">
                <div className="w-2 h-2 bg-red-400 rounded-full animate-ping"></div>
                <span className="text-sm">Recording... Tap stop when finished</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LobbyPage;