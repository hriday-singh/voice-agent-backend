import React, { useEffect, useRef, useState } from "react";
import { getWebSocketUrl } from "../../config";
import "./VoiceAgent.css";
import { IoArrowBack } from "react-icons/io5";
import { IconWrapper } from "./IconWrapper";

interface VoiceAgentStreamProps {
  agentType?: string;
  onBackToSelection?: () => void;
  onConnectionStatusChange?: (
    status: "connecting" | "connected" | "error" | "disconnected"
  ) => void;
}

const VoiceAgentStream: React.FC<VoiceAgentStreamProps> = ({
  agentType = "realestate",
  onBackToSelection,
  onConnectionStatusChange,
}) => {
  const [inputStream, setInputStream] = useState<MediaStream | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [audioLevel, setAudioLevel] = useState<number>(0);

  // Refs
  const audioRef = useRef<HTMLAudioElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioAnalyserRef = useRef<AnalyserNode | null>(null);

  // Setup microphone
  const setupMicrophone = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1,
        },
      });
      setInputStream(stream);

      // Set up audio analyzer for visualization
      setupAudioAnalyzer(stream);
      setError(null);
      return true;
    } catch (err: any) {
      setError(`Failed to access microphone: ${err.message}`);
      return false;
    }
  };

  // Setup audio analyzer for visualizations
  const setupAudioAnalyzer = (stream: MediaStream) => {
    try {
      // Create audio context
      const audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;

      // Create analyzer
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      audioAnalyserRef.current = analyser;

      // Create source from the stream
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      // Start visualization loop
      startVisualization();
    } catch (err: any) {
      console.error("Error setting up audio analyzer:", err);
    }
  };

  // Start visualization loop
  const startVisualization = () => {
    if (!canvasRef.current || !audioAnalyserRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const analyser = audioAnalyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      if (!canvasRef.current || !ctx || !audioAnalyserRef.current) return;

      // Request next frame
      animationFrameRef.current = requestAnimationFrame(draw);

      // Get audio data
      analyser.getByteFrequencyData(dataArray);

      // Calculate audio level (average of frequencies)
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      const avg = sum / bufferLength;
      const normalizedLevel = Math.min(1, avg / 128);
      setAudioLevel(normalizedLevel);

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw simple circle that pulses with audio
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 20 + normalizedLevel * 80;

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(52, 152, 219, ${0.3 + normalizedLevel * 0.7})`;
      ctx.fill();
    };

    draw();
  };

  // Toggle mute
  const toggleMute = () => {
    if (inputStream) {
      const audioTracks = inputStream.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = isMuted;
      });
      setIsMuted(!isMuted);
    }
  };

  // Connect to agent
  const connect = async () => {
    if (!inputStream) {
      const success = await setupMicrophone();
      if (!success) return;
    }

    try {
      setIsConnecting(true);
      onConnectionStatusChange?.("connecting");

      const token = localStorage.getItem("token");
      if (!token) {
        throw new Error("Authentication token not found. Please log in again.");
      }

      // Use the helper function to get the correct WebSocket URL
      const wsUrl = getWebSocketUrl(agentType, token);

      // Create WebSocket connection
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        onConnectionStatusChange?.("connected");
        startAudioProcessing();
      };

      ws.onmessage = (event) => {
        try {
          // Handle different types of messages from the server
          if (event.data instanceof Blob) {
            const url = URL.createObjectURL(event.data);
            if (audioRef.current) {
              audioRef.current.src = url;
              audioRef.current.play().catch(console.error);
            }
          }
        } catch (error) {
          console.error("Error handling message:", error);
        }
      };

      ws.onerror = () => {
        setError("Connection error. Please try again.");
        setIsConnected(false);
        setIsConnecting(false);
        onConnectionStatusChange?.("error");
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
        stopAudioProcessing();
        onConnectionStatusChange?.("disconnected");
      };
    } catch (err: any) {
      setError(`Connection error: ${err.message}`);
      setIsConnected(false);
      setIsConnecting(false);
      onConnectionStatusChange?.("error");
    }
  };

  const startAudioProcessing = () => {
    if (!inputStream || !wsRef.current) return;

    const audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)({
      sampleRate: 16000,
    });

    const source = audioContext.createMediaStreamSource(inputStream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    source.connect(processor);
    processor.connect(audioContext.destination);

    processor.onaudioprocess = (e) => {
      if (
        wsRef.current &&
        wsRef.current.readyState === WebSocket.OPEN &&
        !isMuted
      ) {
        try {
          const inputData = e.inputBuffer.getChannelData(0);
          const pcmData = new Uint8Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            // Convert Float32 (-1 to 1) to Uint8 (0 to 255)
            pcmData[i] = Math.max(
              0,
              Math.min(255, Math.floor((inputData[i] + 1) * 127.5))
            );
          }

          // Directly send the PCM data as a byte array
          wsRef.current.send(pcmData.buffer);
        } catch (error) {
          console.error("Error processing audio:", error);
        }
      }
    };

    audioProcessorRef.current = processor;
    audioContextRef.current = audioContext;
  };

  const stopAudioProcessing = () => {
    if (audioProcessorRef.current && audioContextRef.current) {
      audioProcessorRef.current.disconnect();
      audioProcessorRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close().catch(console.error);
      audioContextRef.current = null;
    }
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    stopAudioProcessing();

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }

    setIsConnected(false);
  };

  useEffect(() => {
    return () => {
      disconnect();

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      if (inputStream) {
        inputStream.getTracks().forEach((track) => {
          track.stop();
        });
      }
    };
  }, [inputStream]);

  return (
    <div className="container">
      <div className="w-full mb-8">
        <h1>Voice Agent: {agentType}</h1>

        {onBackToSelection && (
          <button
            className="text-[#ffcc33] hover:text-[#ffcc33]/80 flex items-center gap-2 transition-colors mb-4"
            onClick={onBackToSelection}
          >
            <IconWrapper icon={IoArrowBack} />
            Back to Agents
          </button>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      <div className="visualizers">
        <div className="visualizer">
          <h3>Your Voice</h3>
          <canvas ref={canvasRef} width={200} height={200} />
          {isMuted && <div className="muted-overlay">Muted</div>}
        </div>

        <div className="agent-status">
          <h3>Agent Status</h3>
          <div
            className={`status-indicator ${
              isConnected ? "connected" : "disconnected"
            }`}
          >
            {isConnected
              ? "Connected"
              : isConnecting
              ? "Connecting..."
              : "Disconnected"}
          </div>
        </div>
      </div>

      <div className="controls">
        {!inputStream ? (
          <button className="button primary" onClick={setupMicrophone}>
            Enable Microphone
          </button>
        ) : (
          <>
            {isConnected && (
              <button
                className={`button ${isMuted ? "warning" : "secondary"}`}
                onClick={toggleMute}
              >
                {isMuted ? "Unmute" : "Mute"}
              </button>
            )}

            {!isConnected ? (
              <button
                className="button primary"
                onClick={connect}
                disabled={isConnecting}
              >
                {isConnecting ? "Connecting..." : "Connect"}
              </button>
            ) : (
              <button className="button danger" onClick={disconnect}>
                Disconnect
              </button>
            )}
          </>
        )}
      </div>

      {/* Instructions */}
      <div className="mt-8 p-4 bg-[#31261a]/20 rounded-lg text-[#f2efe3] text-sm max-w-md mx-auto">
        <p className="mb-3">
          <strong>Important Instructions:</strong>
        </p>
        <ul className="list-disc list-inside space-y-2">
          <li>
            Please mute yourself when not talking to prevent echo and feedback.
          </li>
          <li>
            This feature is still in development and may not provide the most
            accurate results.
          </li>
          <li>For best results, speak clearly and in a quiet environment.</li>
        </ul>
      </div>

      {/* Hidden audio element for playback */}
      <audio ref={audioRef} autoPlay style={{ display: "none" }} />
    </div>
  );
};

export default VoiceAgentStream;
