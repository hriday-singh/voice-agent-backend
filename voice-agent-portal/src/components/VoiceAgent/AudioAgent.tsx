import React, { useState, useEffect, useRef } from "react";
import { VoiceVisualizer } from "./AudioVisualizer";
import { BsMicFill, BsMicMuteFill } from "react-icons/bs";
import { IoArrowBack } from "react-icons/io5";
import { IconWrapper } from "./IconWrapper";
import { API_BASE_URL } from "../../config/api";
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
  const dataChannelRef = useRef<RTCDataChannel | null>(null);
  const webrtcIdRef = useRef<string>("");

  // Notify parent of connection state changes
  useEffect(() => {
    onConnectionChange?.(isConnected);
  }, [isConnected, onConnectionChange]);

  // Setup microphone
  const setupMicrophone = async () => {
    try {
      // Get the stream for our local UI
      const micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1,
        },
      });

      // Set the local stream for UI purposes
      setStream(micStream);
      setErrorMessage("");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`Failed to access microphone: ${errorMsg}`);
    }
  };

  // Connect to voice agent
  const connectToAgent = async () => {
    if (isConnecting || isConnected) return;

    // Double check we have a microphone stream
    if (!stream) {
      setErrorMessage("Please enable microphone first");
      return;
    }

    setErrorMessage("");
    setIsConnecting(true);

    try {
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }

      // Create new RTCPeerConnection with STUN servers
      // const pc = new RTCPeerConnection({
      //   iceServers: [
      //     {
      //       urls: "stun:stun.l.google.com:19302",
      //    },
      //  ],
      //   iceCandidatePoolSize: 0,
      // });
      const pc = new RTCPeerConnection();
      peerConnectionRef.current = pc;

      // Add audio tracks to the peer connection
      stream.getTracks().forEach((track) => {
        pc.addTrack(track, stream);
      });

      // Handle incoming tracks (for audio output)
      pc.addEventListener("track", (evt) => {
        if (audioRef.current && audioRef.current.srcObject !== evt.streams[0]) {
          audioRef.current.srcObject = evt.streams[0];
          setOutputStream(evt.streams[0]);
          setAudioActive(true);
        }
      });

      // Create data channel for text communication
      const dataChannel = pc.createDataChannel("text");
      dataChannelRef.current = dataChannel;

      // Create initial offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // Construct the full WebRTC endpoint URL
      const webrtcEndpoint = `${API_BASE_URL}${apiPath}/webrtc/offer`;

      // Generate a random webrtc ID
      const webrtc_id = Math.random().toString(36).substring(7);

      // Send ice candidates immediately
      const iceCandidateQueue: RTCIceCandidate[] = [];
      let remoteSet = false;

      pc.onicecandidate = ({ candidate }) => {
        if (candidate) {
          if (!remoteSet) {
            // Queue until remote SDP is set
            iceCandidateQueue.push(candidate);
          } else {
            // Send immediately
            sendIceCandidate(candidate);
          }
        }
      };

      const sendIceCandidate = (candidate: RTCIceCandidate) => {
        fetch(webrtcEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            candidate: candidate.toJSON(),
            webrtc_id: webrtc_id,
            type: "ice-candidate",
          }),
        });
      };

      const response = await fetch(webrtcEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sdp: pc.localDescription?.sdp,
          type: pc.localDescription?.type,
          webrtc_id: webrtc_id,
        }),
      });

      // Handle server response
      const serverResponse = await response.json();
      await pc.setRemoteDescription(serverResponse);
      remoteSet = true;
      console.log("Server response:", serverResponse);
      console.log("Sending queued ICE candidates");
      // Send queued ICE candidates now
      iceCandidateQueue.forEach(sendIceCandidate);
      iceCandidateQueue.length = 0;

      // Setup data channel handlers
      dataChannel.onopen = () => {
        console.log("Data channel opened");
      };

      dataChannel.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          // console.log("Received message from server:", message);
        } catch (e) {
          console.log("Received raw message:", event.data);
        }
      };

      // Connection state changes
      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "connected") {
          setIsConnected(true);
          setIsConnecting(false);
        } else if (
          pc.connectionState === "disconnected" ||
          pc.connectionState === "failed" ||
          pc.connectionState === "closed"
        ) {
          setIsConnected(false);
          setAudioActive(false);
          setIsConnecting(false);
        }
      };

      // ICE connection state changes
      pc.oniceconnectionstatechange = () => {
        console.log("ICE connection state:", pc.iceConnectionState);
      };
    } catch (error) {
      console.error("Error connecting:", error);
      const errorMsg = "Credits exhausted. Please contact hello@caw.tech";
      setErrorMessage(errorMsg);
      setAudioActive(false);
      setIsConnecting(false);

      // Clean up failed connection
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (stream) {
      stream.getAudioTracks().forEach((track) => {
        track.enabled = !track.enabled;
      });
      setIsMuted(!isMuted);
    }
  };

  // Disconnect from voice agent
  const disconnectFromAgent = async () => {
    try {
      setErrorMessage("");

      // First set UI state to prevent user interaction during disconnect
      setIsConnected(false);
      setAudioActive(false);
      setOutputStream(null);

      // Close the peer connection
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }

      // Close data channel
      if (dataChannelRef.current) {
        dataChannelRef.current.close();
        dataChannelRef.current = null;
      }

      webrtcIdRef.current = "";

      // Clean up audio element
      if (audioRef.current) {
        try {
          audioRef.current.pause();
          audioRef.current.srcObject = null;
        } catch (e) {
          console.error("Error cleaning up audio element:", e);
        }
      }
    } catch (error) {
      console.error("Error disconnecting:", error);
      setErrorMessage("Error during disconnection. Please refresh the page.");
    }
  };

  // Clean up on unmount
  useEffect(() => {
    // Ensure proper cleanup on unmount
    return () => {
      try {
        // Clean up audio element
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.srcObject = null;
        }

        // Clean up input stream if it exists
        if (stream) {
          stream.getTracks().forEach((track) => {
            try {
              track.stop();
            } catch (e) {
              console.error(`Error stopping track ${track.kind}:`, e);
            }
          });
        }

        // Close the peer connection
        if (peerConnectionRef.current) {
          peerConnectionRef.current.close();
        }

        // Close data channel
        if (dataChannelRef.current) {
          dataChannelRef.current.close();
        }
      } catch (e) {
        console.error("Error during cleanup:", e);
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
          <p className="mt-4 text-sm">
            For any feedback, please contact us at{" "}
            <a
              href="mailto:hello@caw.tech"
              className="text-[#ffcc33] hover:underline"
            >
              hello@caw.tech
            </a>
          </p>
        </div>
      </div>
      <audio ref={audioRef} autoPlay playsInline style={{ display: "none" }} />
    </div>
  );
};

export default AudioAgent;
