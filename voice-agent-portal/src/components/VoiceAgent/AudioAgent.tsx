import React, { useState, useEffect, useRef } from "react";
import { VoiceVisualizer } from "./AudioVisualizer";
import { connectVoiceAgent, disconnectVoiceAgent } from "../../services/webrtc";
import { BsMicFill, BsMicMuteFill } from "react-icons/bs";
import { IoArrowBack } from "react-icons/io5";
import { IconWrapper } from "./IconWrapper";
import "./AudioAgent.css";

interface AudioAgentProps {
  agentId: string;
  apiPath: string;
  onBackToSelection?: () => void;
  onConnectionChange?: (connected: boolean) => void;
}

const AudioAgent: React.FC<AudioAgentProps> = ({
  agentId,
  apiPath,
  onBackToSelection,
  onConnectionChange,
}) => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [outputStream, setOutputStream] = useState<MediaStream | null>(null);
  const [audioActive, setAudioActive] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const audioRef = useRef<HTMLAudioElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);

  // Notify parent of connection state changes
  useEffect(() => {
    onConnectionChange?.(isConnected);
  }, [isConnected, onConnectionChange]);

  // Setup microphone
  const setupMicrophone = async () => {
    try {
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1,
        },
      });
      setStream(micStream);
      setErrorMessage("");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`Failed to access microphone: ${errorMsg}`);
    }
  };

  // Connect to voice agent
  const connectToAgent = async () => {
    if (!stream) {
      setErrorMessage("Please enable microphone first");
      return;
    }

    setErrorMessage("");
    setIsConnecting(true);

    try {
      setAudioActive(true);

      const { pc, stream: remoteStream } = await connectVoiceAgent(
        stream,
        agentId,
        apiPath
      );

      peerConnectionRef.current = pc;

      // Set up audio output
      if (audioRef.current && remoteStream) {
        audioRef.current.srcObject = remoteStream;
        setOutputStream(remoteStream);
      }

      // Monitor connection state
      pc.onconnectionstatechange = () => {
        const state = pc.connectionState;

        if (state === "connected") {
          setIsConnected(true);
          setIsConnecting(false);
          // Ensure microphone is active
          stream.getAudioTracks().forEach((track) => {
            track.enabled = !isMuted;
          });
        } else if (
          state === "failed" ||
          state === "disconnected" ||
          state === "closed"
        ) {
          setIsConnected(false);
          setAudioActive(false);
          setErrorMessage("Connection lost. Please try reconnecting.");
        }
      };

      // Monitor ICE connection state
      pc.oniceconnectionstatechange = () => {
        const state = pc.iceConnectionState;

        if (state === "connected" || state === "completed") {
          // Double check microphone tracks are enabled
          stream.getAudioTracks().forEach((track) => {
            if (!track.enabled && !isMuted) {
              track.enabled = true;
            }
          });
        }
      };

      setIsConnected(true);
      setIsConnecting(false);
    } catch (error) {
      console.error("Error:", error);
      const errorMsg =
        error instanceof Error
          ? error.message
          : "Failed to connect to voice agent";
      setErrorMessage(errorMsg);
      setAudioActive(false);
      setIsConnecting(false);
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (stream) {
      const audioTracks = stream.getAudioTracks();
      const newMuteState = !isMuted;
      audioTracks.forEach((track) => {
        track.enabled = !newMuteState;
      });
      setIsMuted(newMuteState);
    }
  };

  // Disconnect from voice agent
  const disconnectFromAgent = async () => {
    try {
      if (peerConnectionRef.current) {
        await disconnectVoiceAgent(peerConnectionRef.current);
        peerConnectionRef.current = null;
      }

      if (audioRef.current) {
        audioRef.current.srcObject = null;
      }

      setOutputStream(null);
      setIsConnected(false);
      setAudioActive(false);
    } catch (error) {
      console.error("Error disconnecting:", error);
    }
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
      }
    };
  }, [stream]);

  return (
    <div className="flex flex-col items-center w-[calc(100%-2rem)] max-w-2xl mx-auto p-4">
      <div className="w-[calc(100%-2rem)]">
        <button
          className="text-[#ffcc33] hover:text-[#ffcc33]/80 flex items-center gap-2 transition-colors mb-6"
          onClick={onBackToSelection}
        >
          <IconWrapper icon={IoArrowBack} />
          Back to Agents
        </button>

        <div className="relative w-full max-w-md aspect-square mx-auto">
          <VoiceVisualizer
            audioStream={outputStream}
            isActive={audioActive && isConnected}
          />
        </div>
      </div>

      <div className="flex flex-col items-center gap-4 w-full mt-8">
        {errorMessage && (
          <div className="bg-red-500/10 text-red-500 px-4 py-2 rounded-lg text-sm w-full max-w-md text-center">
            {errorMessage}
          </div>
        )}

        <div className="flex flex-wrap justify-center gap-4">
          {!stream ? (
            <button
              className="bg-[#ffcc33] hover:bg-[#ffcc33]/90 text-[#140d0c] px-6 py-2 rounded-lg flex items-center gap-2 transition-colors"
              onClick={setupMicrophone}
            >
              <IconWrapper icon={BsMicFill} /> Enable Microphone
            </button>
          ) : isConnected ? (
            <>
              <button
                className="bg-red-500 hover:bg-red-600 text-white px-6 py-2 rounded-lg flex items-center gap-2 transition-colors"
                onClick={disconnectFromAgent}
              >
                Disconnect
              </button>
              <button
                className={`border ${
                  isMuted
                    ? "bg-white text-[#140d0c]"
                    : "bg-[#1a1310] text-white"
                } px-6 py-2 rounded-lg flex items-center gap-2 transition-colors`}
                onClick={toggleMute}
              >
                {isMuted ? (
                  <>
                    <IconWrapper icon={BsMicFill} /> Unmute
                  </>
                ) : (
                  <>
                    <IconWrapper icon={BsMicMuteFill} /> Mute
                  </>
                )}
              </button>
            </>
          ) : (
            <button
              className="bg-[#ffcc33] hover:bg-[#ffcc33]/90 text-[#140d0c] px-6 py-2 rounded-lg flex items-center gap-2 transition-colors"
              onClick={connectToAgent}
              disabled={isConnecting}
            >
              {isConnecting ? "Connecting..." : "Connect"}
            </button>
          )}
        </div>

        {/* Instructions */}
        <div className="mt-8 p-4 bg-[#31261a]/20 rounded-lg text-[#f2efe3] text-sm max-w-md w-full">
          <p className="mb-3">
            <strong>Important Instructions:</strong>
          </p>
          <ul className="list-disc list-inside space-y-2">
            <li>
              Please mute yourself when not talking to prevent echo and
              feedback.
            </li>
            <li>
              This feature is still in development and may not provide the most
              accurate results.
            </li>
            <li>For best results, speak clearly and in a quiet environment.</li>
          </ul>
        </div>
      </div>
      <audio ref={audioRef} autoPlay playsInline style={{ display: "none" }} />
    </div>
  );
};

export default AudioAgent;
