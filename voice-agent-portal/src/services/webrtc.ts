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

// Connect to voice agent function
export async function connectVoiceAgent(
  micStream: MediaStream,
  agentId: string,
  apiPath: string
): Promise<ConnectionResult> {
  // Create a unique ID for this connection
  const webrtc_id = crypto.randomUUID();
  console.log(`Creating connection with ID: ${webrtc_id}`);

  // Create RTCPeerConnection with more explicit configuration
  const pc = new RTCPeerConnection({
    iceServers: [
      { urls: "stun:stun.l.google.com:19302" },
      { urls: "stun:stun1.l.google.com:19302" },
    ],
    iceCandidatePoolSize: 10,
    // Set these options to improve performance
    iceTransportPolicy: "all",
    bundlePolicy: "max-bundle",
    rtcpMuxPolicy: "require",
  });

  // Create data channel for control messages
  const dataChannel = pc.createDataChannel("control");
  dataChannel.onopen = () => {
    console.log("Data channel opened");
    // Send initial message to verify connection
    dataChannel.send(JSON.stringify({ type: "client_ready" }));
  };
  dataChannel.onmessage = (event) => {
    console.log(`Received message: ${event.data}`);
  };

  // Add tracks from microphone to peer connection
  micStream.getTracks().forEach((track) => {
    console.log(`Adding track: ${track.kind} to peer connection`);
    const sender = pc.addTrack(track, micStream);

    // Monitor track status
    track.onended = () => {
      console.log(`Track ${track.id} ended`);
    };
    track.onmute = () => {
      console.log(`Track ${track.id} muted`);
    };
    track.onunmute = () => {
      console.log(`Track ${track.id} unmuted`);
    };

    // Monitor sender status
    setInterval(() => {
      sender.getStats().then((stats) => {
        stats.forEach((report) => {
          if (report.type === "outbound-rtp") {
            console.log(`Sending audio data: ${report.bytesSent} bytes sent`);
          }
        });
      });
    }, 5000);
  });

  // Create a promise to get the remote stream
  const streamPromise = new Promise<MediaStream>((resolve) => {
    pc.ontrack = (event) => {
      console.log(
        `Remote track received: ${event.track.kind}, muted: ${event.track.muted}`
      );

      // Set up track event listeners
      event.track.onunmute = () => {
        console.log(`Track unmuted: ${event.track.id}`);
      };

      event.track.onmute = () => {
        console.log(`Track muted: ${event.track.id}`);
      };

      event.track.onended = () => {
        console.log(`Track ended: ${event.track.id}`);
      };

      if (event.streams && event.streams[0]) {
        console.log(
          `Stream received with ${event.streams[0].getTracks().length} tracks`
        );
        resolve(event.streams[0]);
      }
    };
  });

  // Create and set local description with specific audio constraints
  const offer = await pc.createOffer({
    offerToReceiveAudio: true,
  });

  // Add specific audio codec preferences
  const audioCodecPreferences = [
    {
      mimeType: "audio/opus",
      clockRate: 48000,
      channels: 2,
      sdpFmtpLine: "minptime=10;useinbandfec=1",
    },
    { mimeType: "audio/PCMU", clockRate: 8000, channels: 1 },
    { mimeType: "audio/PCMA", clockRate: 8000, channels: 1 },
  ];

  // Modify SDP to prioritize our preferred codecs
  let sdp = offer.sdp;
  audioCodecPreferences.forEach((codec) => {
    const regex = new RegExp(
      `a=rtpmap:(\\d+) ${codec.mimeType.split("/")[1]}/.*\\r\\n`
    );
    const match = sdp?.match(regex);
    if (match) {
      const pt = match[1];
      sdp = sdp?.replace(/(m=audio \d+ RTP\/SAVPF )(.*)/, `$1${pt} $2`);
    }
  });

  offer.sdp = sdp;
  console.log("Created offer with modified SDP");
  await pc.setLocalDescription(offer);
  console.log("Local description set");

  // Handle ICE candidates - limit sending to reduce traffic
  let lastCandidateSent = 0;
  const candidateQueue: RTCIceCandidate[] = [];
  let allCandidatesGathered = false;

  // Set timeout to force sending all candidates if gathering takes too long
  setTimeout(() => {
    if (candidateQueue.length > 0 && !allCandidatesGathered) {
      const candidates = [...candidateQueue];
      candidateQueue.length = 0;
      sendCandidates(candidates, webrtc_id, apiPath);
      console.log(
        `Force-sending ${candidates.length} ICE candidates after timeout`
      );
    }
  }, 1000);

  // Function to send candidates
  const sendCandidates = async (
    candidates: RTCIceCandidate[],
    webrtc_id: string,
    apiPath: string
  ) => {
    try {
      await api.post(`${apiPath}/webrtc/offer`, {
        candidates: candidates.map((c) => c.toJSON()),
        webrtc_id,
        type: "ice-candidates",
      });
    } catch (error) {
      console.error("Failed to send ICE candidates:", error);
    }
  };

  pc.onicegatheringstatechange = () => {
    console.log(`ICE gathering state: ${pc.iceGatheringState}`);
    if (pc.iceGatheringState === "complete") {
      allCandidatesGathered = true;
      if (candidateQueue.length > 0) {
        const candidates = [...candidateQueue];
        candidateQueue.length = 0;
        sendCandidates(candidates, webrtc_id, apiPath);
        console.log(
          `Sending final batch of ${candidates.length} ICE candidates`
        );
      }
    }
  };

  pc.onicecandidate = async ({ candidate }) => {
    if (candidate) {
      // Prioritize server reflexive candidates for faster connection
      if (candidate.candidate.includes("srflx")) {
        sendCandidates([candidate], webrtc_id, apiPath);
        console.log(`Immediately sending server reflexive candidate`);
      } else {
        candidateQueue.push(candidate);

        // Only send candidates in batches to reduce number of requests
        const now = Date.now();
        if (now - lastCandidateSent > 300 && candidateQueue.length > 3) {
          lastCandidateSent = now;
          const candidates = [...candidateQueue];
          candidateQueue.length = 0;
          console.log(`Sending batch of ${candidates.length} ICE candidates`);
          sendCandidates(candidates, webrtc_id, apiPath);
        }
      }
    }
  };

  // Send offer via HTTP POST
  console.log("Sending offer to server");
  const response = await api.post(`${apiPath}/webrtc/offer`, {
    sdp: offer.sdp,
    type: offer.type,
    webrtc_id,
    modality: "audio",
    mode: "send-receive",
  });

  const answer = response.data;
  console.log(`Received answer with type: ${answer.type}`);

  if (!answer.sdp) {
    throw new Error("Server returned invalid answer without SDP");
  }

  await pc.setRemoteDescription(new RTCSessionDescription(answer));
  console.log("Remote description set");

  // Wait for the remote stream with a timeout
  let remoteStream: MediaStream | null = null;
  try {
    remoteStream = await Promise.race([
      streamPromise,
      new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error("Stream timeout")), 10000);
      }),
    ]);
  } catch (error) {
    console.error("Failed to get remote stream:", error);
  }

  return {
    pc,
    stream: remoteStream,
  };
}

// Disconnect function
export function disconnectVoiceAgent(pc: RTCPeerConnection): void {
  if (pc) {
    // Close the peer connection which will automatically close data channels
    pc.close();
  }
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
    statusCallback: (status: ConnectionStatus) => void,
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
      console.log("Requesting microphone access...");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1,
        },
      });
      console.log("Microphone access granted", stream.getAudioTracks());
      this.inputStream = stream;
      this.updateStatus({ error: null });
      return true;
    } catch (err: any) {
      console.error("Microphone access denied:", err);
      this.updateStatus({
        error: `Failed to access microphone: ${err.message}`,
      });
      return false;
    }
  }

  toggleMute(): void {
    if (this.inputStream) {
      const audioTracks = this.inputStream.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = !track.enabled;
        console.log(`Track ${track.id} ${track.enabled ? "unmuted" : "muted"}`);
      });
      this.updateStatus({
        isListening: this.inputStream.getAudioTracks()[0]?.enabled || false,
      });
    }
  }

  async connect(agentType: string, apiPath: string): Promise<void> {
    if (!this.inputStream) {
      this.updateStatus({ error: "Please enable microphone first" });
      return;
    }

    try {
      console.log(`Starting connection to agent: ${agentType}`);
      this.apiPath = apiPath;

      // Step 1: Register access to the agent
      console.log("Registering access to agent");
      await api.post("/agents/access", { agent_type: agentType });

      // Step 2: Create a unique ID for this connection
      this.webrtcId = crypto.randomUUID();
      console.log(`Generated WebRTC ID: ${this.webrtcId}`);

      // Step 3: Create RTCPeerConnection with STUN servers
      const pc = new RTCPeerConnection({
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" },
          { urls: "stun:stun1.l.google.com:19302" },
        ],
        iceCandidatePoolSize: 10,
        iceTransportPolicy: "all",
        bundlePolicy: "max-bundle",
        rtcpMuxPolicy: "require",
      });

      this.peerConnection = pc;
      console.log("RTCPeerConnection created");

      // Step 4: Create data channel for control messages
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      this.dataChannel = pc.createDataChannel("control", {
        ordered: true,
        maxRetransmits: 3,
      });

      this.dataChannel.onopen = () => {
        console.log("Data channel opened");
        // Send a test message to verify the channel is working
        if (this.dataChannel && this.dataChannel.readyState === "open") {
          this.dataChannel.send(JSON.stringify({ type: "client_ready" }));
        }
      };

      this.dataChannel.onmessage = (event) => {
        try {
          console.log("Received data channel message:", event.data);
          const message = JSON.parse(event.data);
          if (message.type === "response") {
            // Handle agent response
            this.onAgentResponse(message.data);
          }
        } catch (error) {
          console.error("Error parsing data channel message:", error);
        }
      };

      this.dataChannel.onerror = (error) => {
        console.error("Data channel error:", error);
      };

      this.dataChannel.onclose = () => {
        console.log("Data channel closed");
      };

      // Step 5: Add tracks from microphone to peer connection
      this.inputStream.getAudioTracks().forEach((track) => {
        console.log(`Adding audio track to peer connection: ${track.label}`);
        pc.addTrack(track, this.inputStream!);
      });

      // Step 6: Handle incoming tracks for agent audio
      pc.ontrack = (event) => {
        console.log(`Remote track received: ${event.track.kind}`);

        // Set up track event listeners
        event.track.onunmute = () => {
          console.log(`Track unmuted: ${event.track.id}`);
        };

        event.track.onmute = () => {
          console.log(`Track muted: ${event.track.id}`);
        };

        event.track.onended = () => {
          console.log(`Track ended: ${event.track.id}`);
        };

        if (event.streams && event.streams[0]) {
          console.log(
            `Stream received with ${event.streams[0].getTracks().length} tracks`
          );

          // Explicitly attach stream to audio element
          if (this.audioElement) {
            this.audioElement.srcObject = event.streams[0];
            this.audioElement.muted = false;
            this.audioElement.volume = 1.0;

            // Force play attempt
            const playPromise = this.audioElement.play();
            if (playPromise !== undefined) {
              playPromise
                .then(() => {
                  console.log("Audio playback started successfully");

                  // Set playback rate slightly faster to compensate for network delay
                  this.audioElement!.playbackRate = 1.05;
                })
                .catch((error) => {
                  console.error("Autoplay failed:", error);
                  this.updateStatus({ error: "Click to start audio playback" });
                });
            }
          }
        }
      };

      // Step 7: Create and set local description
      console.log("Creating offer...");
      const offer = await pc.createOffer({
        offerToReceiveAudio: true,
      });

      console.log("Setting local description...");
      await pc.setLocalDescription(offer);
      console.log("Local description set, SDP length:", offer.sdp?.length);

      // Step 8: Handle ICE candidates
      let candidateQueue: RTCIceCandidate[] = [];
      let lastCandidateSent = 0;
      let allCandidatesGathered = false;

      // Set timeout to force sending all candidates if gathering takes too long
      setTimeout(() => {
        if (candidateQueue.length > 0 && !allCandidatesGathered) {
          const candidates = [...candidateQueue];
          candidateQueue.length = 0;
          this.sendCandidates(candidates);
          console.log(
            `Force-sending ${candidates.length} ICE candidates after timeout`
          );
        }
      }, 2000);

      pc.onicegatheringstatechange = () => {
        console.log(`ICE gathering state: ${pc.iceGatheringState}`);
        if (pc.iceGatheringState === "complete") {
          allCandidatesGathered = true;
          if (candidateQueue.length > 0) {
            const candidates = [...candidateQueue];
            candidateQueue.length = 0;
            this.sendCandidates(candidates);
            console.log(
              `Sending final batch of ${candidates.length} ICE candidates`
            );
          }
        }
      };

      pc.onicecandidate = ({ candidate }) => {
        if (candidate) {
          console.log(
            `New ICE candidate: ${candidate.candidate.substring(0, 50)}...`
          );

          // Prioritize server reflexive candidates for faster connection
          if (candidate.candidate.includes("srflx")) {
            this.sendCandidates([candidate]);
            console.log(`Immediately sending server reflexive candidate`);
          } else {
            candidateQueue.push(candidate);

            // Only send candidates in batches to reduce number of requests
            const now = Date.now();
            if (now - lastCandidateSent > 300 && candidateQueue.length > 3) {
              lastCandidateSent = now;
              const candidates = [...candidateQueue];
              candidateQueue.length = 0;
              console.log(
                `Sending batch of ${candidates.length} ICE candidates`
              );
              this.sendCandidates(candidates);
            }
          }
        }
      };

      // Step 9: Connection state handling
      pc.oniceconnectionstatechange = () => {
        console.log(`ICE connection state: ${pc.iceConnectionState}`);
        if (
          pc.iceConnectionState === "connected" ||
          pc.iceConnectionState === "completed"
        ) {
          this.updateStatus({ isConnected: true, error: null });

          // Force reattach audio element after connection is complete for better audio delivery
          setTimeout(() => {
            this.resetAudio();
          }, 300);
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

      pc.onconnectionstatechange = () => {
        console.log(`Connection state: ${pc.connectionState}`);
        if (pc.connectionState === "failed") {
          this.updateStatus({
            isConnected: false,
            error: "Connection failed. Please try again.",
          });
        }
      };

      // Step 10: Send offer to server
      console.log("Sending offer to server...");
      const response = await api.post(`${this.apiPath}/webrtc/offer`, {
        sdp: pc.localDescription?.sdp,
        type: pc.localDescription?.type,
        webrtc_id: this.webrtcId,
        agent_type: agentType,
      });

      console.log("Received answer from server");
      const data = response.data;

      if (!data.sdp) {
        throw new Error("Server returned invalid answer without SDP");
      }

      // Step 11: Set remote description from response
      console.log("Setting remote description...");
      await pc.setRemoteDescription(
        new RTCSessionDescription({
          type: "answer",
          sdp: data.sdp,
        })
      );
      console.log("Remote description set");
    } catch (err: any) {
      console.error("Connection error:", err);
      this.updateStatus({
        error: `Connection error: ${err.response?.data || err.message}`,
        isConnected: false,
      });
      this.disconnect();
    }
  }

  private async sendCandidates(candidates: RTCIceCandidate[]) {
    try {
      console.log(`Sending ${candidates.length} candidates`);

      // Use axios instead of fetch to ensure consistent URL handling
      await api.post(`${this.apiPath}/webrtc/offer`, {
        candidates: candidates.map((c) => c.toJSON()),
        webrtc_id: this.webrtcId,
        type: "ice-candidates",
      });

      console.log("Candidates sent successfully");
    } catch (error) {
      console.error("Failed to send ICE candidates:", error);
    }
  }

  disconnect(): void {
    console.log("Disconnecting...");

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
      this.peerConnection.close();
      this.peerConnection = null;
    }

    if (this.audioElement) {
      this.audioElement.srcObject = null;
    }

    this.updateStatus({
      isConnected: false,
      isListening: false,
    });

    console.log("Disconnected");
  }

  cleanup(): void {
    console.log("Cleanup...");
    this.disconnect();

    if (this.inputStream) {
      this.inputStream.getTracks().forEach((track) => {
        track.stop();
        console.log(`Stopped track: ${track.id}`);
      });
      this.inputStream = null;
    }

    if (this.audioElement) {
      this.audioElement = null;
    }

    console.log("Cleanup complete");
  }

  resetAudio(): void {
    if (this.audioElement && this.audioElement.srcObject) {
      console.log("Resetting audio playback");
      // Create a new audio context to force a refresh
      const audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
      audioContext.resume().then(() => {
        console.log(`Audio context state: ${audioContext.state}`);

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
