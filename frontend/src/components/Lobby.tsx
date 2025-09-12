import React, { useState, useRef, useEffect } from "react";
import { Send, Mic, Square, MessageCircle, Play } from "lucide-react";
import { MessageType, User } from "../types";

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
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const wsTextRef = useRef<WebSocket | null>(null);
  const wsVoiceRef = useRef<WebSocket | null>(null);

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
    };
  }, [audioElement]);

  useEffect(() => {
    const wsText = new WebSocket("ws://localhost:8000/stream/textin");
    wsText.binaryType = "arraybuffer";
    wsTextRef.current = wsText;

    wsText.onopen = () => console.log("Connected ✅");
    wsText.onmessage = (evt) => {
      const userMessage = { text: evt.data, source: "text", sender: "user", ai_response:"" };
      console.log("Message obj:", userMessage);
      setMessages((prev) => [...prev, userMessage]);
    };

    wsText.onclose = () => console.log("Disconnected ❌");

    // cleanup on unmount
    return () => {
      wsText.close();
    };
  }, []);
 

  // Handle text message
  const sendTextMessage = async (text: string) => {
    if (!text.trim()) return;    
    setIsLoading(true);    
    try {
      if(wsTextRef.current?.readyState === WebSocket.OPEN){
        wsTextRef.current.send(text.trim())
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  // ============= VOICE RECORDING
  let recorder: MediaRecorder;  
  const startRecording = async () => {
    setIsRecording(true);

    // 1. Open WebSocket only when recording starts
    const ws = new WebSocket("ws://localhost:8000/stream/voicein");
    ws.binaryType = "arraybuffer";
    wsVoiceRef.current = ws;

    ws.onopen = () => console.log("Voice WS connected ✅");
    ws.onmessage = (evt) => console.log("Server:", evt.data);
    ws.onclose = () => console.log("Voice WS closed ❌");

    // 2. Wait until WebSocket is open before sending audio
    ws.onopen = async () => {
      console.log("Voice WS ready, starting recorder 🎤");

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && wsVoiceRef.current?.readyState === WebSocket.OPEN) {
          wsVoiceRef.current.send(e.data);
        }
      };
      recorder.start(500); // send chunks every 500ms
    };
  };

  const stopRecording = () => {
    setIsRecording(false);

    // Stop MediaRecorder
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }

    // Close WebSocket
    if (wsVoiceRef.current && wsVoiceRef.current.readyState === WebSocket.OPEN) {
      wsVoiceRef.current.close(1000, "Client stopped recording");
      wsVoiceRef.current = null;
    }
  };

  // const startRecording = async () => {
  //   const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  //   const audioCtx = new AudioContext();
  //   const source = audioCtx.createMediaStreamSource(stream);

  //   // Create ScriptProcessorNode (old API but widely supported)
  //   const processor = audioCtx.createScriptProcessor(4096, 1, 1);
  //   source.connect(processor);
  //   processor.connect(audioCtx.destination);

  //   processor.onaudioprocess = (e) => {
  //     const inputData = e.inputBuffer.getChannelData(0); // Float32 samples
  //     const int16Data = floatTo16BitPCM(inputData);

  //     if (wsVoiceRef.current?.readyState === WebSocket.OPEN) {
  //       wsVoiceRef.current.send(int16Data.buffer);
  //     }
  //   };
  // };

  // // helper to convert Float32 → Int16
  // function floatTo16BitPCM(float32Array: Float32Array) {
  //   const buffer = new ArrayBuffer(float32Array.length * 2);
  //   const view = new DataView(buffer);
  //   let offset = 0;
  //   for (let i = 0; i < float32Array.length; i++, offset += 2) {
  //     let s = Math.max(-1, Math.min(1, float32Array[i]));
  //     view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  //   }
  //   return new Int16Array(buffer);
  // }

  // Start voice recording
  // const startRecording = async () => {
  //   try {
  //     const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  //     const recorder = new MediaRecorder(stream);
  //     let chunks: Blob[] = [];

  //     recorder.ondataavailable = (e) => chunks.push(e.data);

  //     recorder.onstop = async () => {
  //       setIsLoading(true);
  //       const blob = new Blob(chunks, { type: "audio/webm" });

  //       // Create audio URL for playback
  //       const audioUrl = URL.createObjectURL(blob);  

  //       const formData = new FormData();
  //       formData.append("file", blob, "voice.webm");

  //       try {
  //         const response = await fetch("http://localhost:8000/api/transcribe", {
  //           method: "POST",
  //           body: formData,
  //           headers: {
  //             Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  //           }
          
  //         });
  //         const data = await response.json();          
  //         setMessages((prev) => [...prev, { ...data, sender: "user", audioBlob: blob, audioUrl: audioUrl, isVoiceMessage:true }]);
          
  //         // Add assistant response
  //         setMessages((prev) => [...prev, { ...data, sender: "assistant" }]);

  //       } catch (error) {
  //         console.error("Error sending voice message:", error);
  //         setMessages((prev) => [...prev, { 
  //           text: "Sorry, there was an error processing your voice message.", 
  //           ai_response: "",
  //           source: "error", 
  //           sender: "assistant",
  //           isVoiceMessage: true,
  //           audioBlob: blob,
  //           audioUrl: audioUrl
  //         }]);
  //       } finally {
  //         setIsLoading(false);
  //       }
        
  //       // Clean up stream
  //       stream.getTracks().forEach(track => track.stop());
  //     };

  //     recorder.start();
  //     setMediaRecorder(recorder);
  //     setRecording(true);
  //   } catch (error) {
  //     console.error("Error accessing microphone:", error);
  //     alert("Could not access microphone. Please check permissions.");
  //   }
  // };

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

  // // Stop voice recording
  // const stopRecording = () => {
  //   if (mediaRecorder) {
  //     mediaRecorder.stop();
  //     setRecording(false);
  //   }
  // };

  const handleSendText = () => {
    sendTextMessage(inputText);
    setInputText("");
    inputRef.current?.focus();
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendText();
    }
  };

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
                <h1 className="text-xl font-bold">Game Card Assistant</h1>
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
      </div>`
    </div>
  );
}

export default LobbyPage;