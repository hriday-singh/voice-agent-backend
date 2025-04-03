import api from "./api";
// Import the API_URL constant to ensure consistency
// const API_URL = "http://localhost:8000/api";

export interface RTCConfig {
  iceServers: RTCIceServer[];
  iceCandidatePoolSize?: number;
  iceTransportPolicy?: RTCIceTransportPolicy;
  bundlePolicy?: RTCBundlePolicy;
  rtcpMuxPolicy?: RTCRtcpMuxPolicy;
}

export interface ConnectionStatus {
  isConnected: boolean;
  error: string | null;
  isListening: boolean;
}

// Simple connection result interface
export interface ConnectionResult {
  pc: RTCPeerConnection;
  stream: MediaStream | null;
}

export class WebRTCService {
  private peerConnection: RTCPeerConnection | null = null;
  private inputStream: MediaStream | null = null;
  private webrtcId: string = "";
  private apiPath: string = "";
  private onStatusChange: (status: ConnectionStatus) => void;
  private onAgentResponse: (response: string) => void;
  private audioElement: HTMLAudioElement | null = null;
  private dataChannel: RTCDataChannel | null = null;
  private status: ConnectionStatus = {
    isConnected: false,
    error: null,
    isListening: false,
  };

  constructor(
    statusCallback: (status: ConnectionStatus) => void = () => {},
    responseCallback: (response: string) => void = () => {}
  ) {
    this.onStatusChange = statusCallback;
    this.onAgentResponse = responseCallback;
    this.audioElement = new Audio();
    this.audioElement.autoplay = true;
  }

  private updateStatus(updates: Partial<ConnectionStatus>) {
    this.status = { ...this.status, ...updates };
    this.onStatusChange(this.status);
  }

  async setupMicrophone(): Promise<boolean> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1,
        },
      });

      this.inputStream = stream;
      this.updateStatus({ error: null });
      return true;
    } catch (err: any) {
      this.updateStatus({
        error: `Failed to access microphone: ${err.message}`,
      });
      return false;
    }
  }

  // Use existing microphone stream
  setMicrophoneStream(stream: MediaStream): void {
    this.inputStream = stream;
    this.updateStatus({ error: null });
  }

  toggleMute(): void {
    if (this.inputStream) {
      const audioTracks = this.inputStream.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = !track.enabled;
      });
      this.updateStatus({
        isListening: this.inputStream.getAudioTracks()[0]?.enabled || false,
      });
    }
  }

  async connect(agentType: string, apiPath: string): Promise<ConnectionResult> {
    if (!this.inputStream) {
      this.updateStatus({ error: "Please enable microphone first" });
      throw new Error("Microphone access required");
    }

    try {
      this.apiPath = apiPath;

      // Register access to the agent
      await api.post("/api/agents/access", { agent_type: agentType });

      // Generate WebRTC ID
      this.webrtcId = crypto.randomUUID();

      // Create peer connection
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" },
          { urls: "stun:stun1.l.google.com:19302" },
        ],
      });

      this.peerConnection = pc;

      // Create data channel
      this.dataChannel = pc.createDataChannel("text");

      this.dataChannel.onopen = () => {
        if (this.dataChannel && this.dataChannel.readyState === "open") {
          this.dataChannel.send(JSON.stringify({ type: "client_ready" }));
        }
      };

      this.dataChannel.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "response") {
            this.onAgentResponse(message.data);
          }
        } catch (error) {
          console.error("Error parsing data channel message:", error);
        }
      };

      // Create a promise to get the remote stream
      const streamPromise = new Promise<MediaStream>((resolve) => {
        pc.ontrack = (event) => {
          if (event.streams && event.streams[0]) {
            resolve(event.streams[0]);

            // If we have an audio element, set up playback
            if (this.audioElement) {
              this.audioElement.srcObject = event.streams[0];
              this.audioElement.muted = false;
              this.audioElement.volume = 1.0;

              this.audioElement.play().catch(() => {
                this.updateStatus({ error: "Click to start audio playback" });
              });
            }
          }
        };
      });

      // Add audio tracks
      this.inputStream.getAudioTracks().forEach((track) => {
        pc.addTrack(track, this.inputStream!);
      });

      // Connection state handlers
      pc.oniceconnectionstatechange = () => {
        if (
          pc.iceConnectionState === "connected" ||
          pc.iceConnectionState === "completed"
        ) {
          this.updateStatus({ isConnected: true, error: null });
        } else if (
          pc.iceConnectionState === "failed" ||
          pc.iceConnectionState === "disconnected" ||
          pc.iceConnectionState === "closed"
        ) {
          this.updateStatus({
            isConnected: false,
            error: "Connection lost. Try reconnecting.",
          });
        }
      };

      // Create offer
      const offer = await pc.createOffer({
        offerToReceiveAudio: true,
      });

      // Modify SDP for compatibility
      if (offer.sdp) {
        let sdp = offer.sdp;
        sdp = sdp.replace(
          /a=fmtp:(\d+) minptime=\d+;useinbandfec=\d(;stereo=\d)?(;maxaveragebitrate=\d+)?/g,
          "a=fmtp:$1 minptime=10;useinbandfec=1;stereo=0;maxaveragebitrate=24000"
        );
        offer.sdp = sdp;
      }

      await pc.setLocalDescription(offer);

      // Handle ICE candidates
      pc.onicecandidate = ({ candidate }) => {
        if (candidate) {
          api
            .post(`${this.apiPath}/webrtc/offer`, {
              candidate: candidate.toJSON(),
              webrtc_id: this.webrtcId,
              type: "ice-candidate",
            })
            .catch((error) => {
              console.error("Failed to send ICE candidate:", error);
            });
        }
      };

      // Send offer to server
      const response = await api.post(`${this.apiPath}/webrtc/offer`, {
        sdp: offer.sdp,
        type: offer.type,
        webrtc_id: this.webrtcId,
      });

      const answer = response.data;

      if (!answer.sdp) {
        throw new Error("Server returned invalid answer without SDP");
      }

      // Set remote description
      await pc.setRemoteDescription(
        new RTCSessionDescription({
          type: "answer",
          sdp: answer.sdp,
        })
      );

      this.updateStatus({ isListening: true });

      // Wait for the remote stream
      let remoteStream: MediaStream | null = null;
      try {
        remoteStream = await streamPromise;
      } catch (error) {
        console.error("Failed to get remote stream:", error);
      }

      return {
        pc: this.peerConnection,
        stream: remoteStream,
      };
    } catch (err: any) {
      this.updateStatus({
        error: `Connection error: ${err.response?.data || err.message}`,
        isConnected: false,
      });
      this.disconnect();
      throw err;
    }
  }

  disconnect(): void {
    if (this.dataChannel) {
      try {
        if (this.dataChannel.readyState === "open") {
          this.dataChannel.send(JSON.stringify({ type: "client_disconnect" }));
        }
        this.dataChannel.close();
      } catch (e) {
        console.error("Error closing data channel:", e);
      }
      this.dataChannel = null;
    }

    if (this.peerConnection) {
      // Remove all event listeners
      if (this.peerConnection.oniceconnectionstatechange) {
        this.peerConnection.oniceconnectionstatechange = null;
      }
      if (this.peerConnection.onicecandidate) {
        this.peerConnection.onicecandidate = null;
      }
      if (this.peerConnection.ontrack) {
        this.peerConnection.ontrack = null;
      }

      // Close the connection
      this.peerConnection.close();
      this.peerConnection = null;
    }

    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.srcObject = null;
    }

    this.updateStatus({
      isConnected: false,
      isListening: false,
    });
  }

  cleanup(): void {
    this.disconnect();

    if (this.inputStream) {
      this.inputStream.getTracks().forEach((track) => {
        track.stop();
      });
      this.inputStream = null;
    }

    if (this.audioElement) {
      this.audioElement = null;
    }
  }

  resetAudio(): void {
    if (this.audioElement && this.audioElement.srcObject) {
      // Create a new audio context to force a refresh
      const audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
      audioContext.resume().then(() => {
        if (this.audioElement) {
          const currentStream = this.audioElement.srcObject;
          this.audioElement.srcObject = null;
          setTimeout(() => {
            if (this.audioElement) {
              this.audioElement.srcObject = currentStream;
              this.audioElement.play().catch((e) => {
                console.error("Play error:", e);
              });
            }
          }, 100);
        }
      });
    }
  }
}

// Simplified wrapper functions that use WebRTCService
export async function connectVoiceAgent(
  micStream: MediaStream,
  agentId: string,
  apiPath: string
): Promise<ConnectionResult> {
  const service = new WebRTCService();
  service.setMicrophoneStream(micStream);
  return service.connect(agentId, apiPath);
}

export function disconnectVoiceAgent(pc: RTCPeerConnection): void {
  if (pc) {
    // Cleanup all event listeners
    if (pc.oniceconnectionstatechange) {
      pc.oniceconnectionstatechange = null;
    }
    if (pc.onicecandidate) {
      pc.onicecandidate = null;
    }
    if (pc.ontrack) {
      pc.ontrack = null;
    }

    // Close the peer connection
    pc.close();
  }
}
