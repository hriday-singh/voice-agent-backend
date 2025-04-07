import React, { useEffect, useRef } from "react";

interface AudioVisualizerProps {
  stream: MediaStream | null;
  label: string;
}

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ stream, label }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | undefined>(undefined);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  useEffect(() => {
    if (!stream || !canvasRef.current) return;

    // Cleanup previous audio context and connections
    if (sourceRef.current) {
      sourceRef.current.disconnect();
    }
    if (analyserRef.current) {
      analyserRef.current.disconnect();
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    // Create new audio context
    const audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    audioContextRef.current = audioContext;

    // Create and configure analyser
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    analyserRef.current = analyser;

    // Create and connect source
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    sourceRef.current = source;

    // Handle high DPI displays
    const canvas = canvasRef.current;
    const canvasCtx = canvas.getContext("2d")!;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvasCtx.scale(dpr, dpr);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      const WIDTH = canvas.width / dpr;
      const HEIGHT = canvas.height / dpr;

      animationFrameRef.current = requestAnimationFrame(draw);

      analyser.getByteFrequencyData(dataArray);

      // Clear canvas with semi-transparent background for trail effect
      canvasCtx.fillStyle = "rgba(242, 239, 227, 0.2)"; // CAW light cream
      canvasCtx.fillRect(0, 0, WIDTH, HEIGHT);

      const barWidth = (WIDTH / bufferLength) * 2.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * HEIGHT;

        // Create gradient effect based on CAW color palette
        const hue = 230 + (i / bufferLength) * 30; // Blue range based on CAW blue accent
        const saturation = 70 + (dataArray[i] / 255) * 20; // Intensity based on volume
        const lightness = 45 + (dataArray[i] / 255) * 10;

        canvasCtx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`;

        // Round the top of the bars
        canvasCtx.beginPath();
        canvasCtx.roundRect(x, HEIGHT - barHeight, barWidth, barHeight, 2);
        canvasCtx.fill();

        x += barWidth + 1;
      }
    };

    draw();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (sourceRef.current) {
        sourceRef.current.disconnect();
      }
      if (analyserRef.current) {
        analyserRef.current.disconnect();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream]);

  return (
    <div className="bg-foreground/5 rounded-md p-4 my-2 border border-border transition-all duration-300 hover:translate-y-[-2px] hover:shadow-md">
      <div className="text-sm font-medium text-foreground mb-3 text-left tracking-wide">
        {label}
      </div>
      <canvas
        ref={canvasRef}
        className="w-full h-[160px] bg-foreground/5 rounded-md border border-border"
      />
    </div>
  );
};

interface BallVisualizerProps {
  audioData: Float32Array | null;
  isActive: boolean;
}

export const BallVisualizer: React.FC<BallVisualizerProps> = ({
  audioData,
  isActive,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameId = useRef<number | null>(null);

  // Smoother transitions
  const smoothedRadius = useRef<number>(60);
  const smoothingConstant = 0.92; // Higher value = smoother transition

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set actual canvas dimensions to match display size
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    // Function to draw the visualizer
    const draw = () => {
      // Clear the canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (!isActive || !audioData) {
        // When inactive, draw a small static circle
        ctx.beginPath();
        ctx.arc(canvas.width / 2, canvas.height / 2, 60, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(255, 204, 51, 0.3)"; // CAW yellow with low opacity
        ctx.fill();
        animationFrameId.current = requestAnimationFrame(draw);
        return;
      }

      // Calculate the average amplitude from audio data
      let sum = 0;
      const dataLength = audioData.length;

      for (let i = 0; i < dataLength; i++) {
        sum += Math.abs(audioData[i]);
      }

      const average = sum / dataLength;

      // Calculate radius based on audio amplitude
      // Mapping average amplitude (usually between 0 and 1) to radius values
      const minRadius = 80;
      const maxRadius = 140;
      const targetRadius = minRadius + average * (maxRadius - minRadius);

      // Apply smoothing
      smoothedRadius.current =
        smoothedRadius.current * smoothingConstant +
        targetRadius * (1 - smoothingConstant);

      // Draw the circle
      ctx.beginPath();
      ctx.arc(
        canvas.width / 2,
        canvas.height / 2,
        smoothedRadius.current,
        0,
        2 * Math.PI
      );

      // Opacity based on audio level
      const opacity = 0.3 + average * 0.6; // Ranges from 0.3 to 0.9
      ctx.fillStyle = `rgba(255, 204, 51, ${opacity})`; // CAW yellow with dynamic opacity
      ctx.fill();

      animationFrameId.current = requestAnimationFrame(draw);
    };

    // Start animation
    draw();

    // Cleanup function
    return () => {
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [audioData, isActive]);

  return (
    <div className="ballVisualizer">
      <canvas ref={canvasRef} className="canvas min-h-[180px]" />
    </div>
  );
};

interface VoiceVisualizerProps {
  audioStream: MediaStream | null;
  isActive: boolean;
}

export const VoiceVisualizer: React.FC<VoiceVisualizerProps> = ({
  audioStream,
  isActive,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const setupAudioContext = () => {
      if (!audioStream) return;

      // Create audio context if it doesn't exist
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext ||
          (window as any).webkitAudioContext)();
      }

      // Create analyser node
      if (!analyserRef.current) {
        analyserRef.current = audioContextRef.current.createAnalyser();
        analyserRef.current.fftSize = 256;
        analyserRef.current.smoothingTimeConstant = 0.8;
      }

      // Create and connect source node
      if (sourceNodeRef.current) {
        sourceNodeRef.current.disconnect();
      }
      sourceNodeRef.current =
        audioContextRef.current.createMediaStreamSource(audioStream);
      sourceNodeRef.current.connect(analyserRef.current);
    };

    setupAudioContext();

    return () => {
      if (sourceNodeRef.current) {
        sourceNodeRef.current.disconnect();
        sourceNodeRef.current = null;
      }
    };
  }, [audioStream]);

  useEffect(() => {
    const draw = () => {
      if (!canvasRef.current || !analyserRef.current || !isActive) return;

      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // Set up canvas dimensions
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);

      // Get audio data
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      analyserRef.current.getByteFrequencyData(dataArray);

      // Calculate average volume
      const average =
        dataArray.reduce((acc, val) => acc + val, 0) / bufferLength;
      const normalizedVolume = Math.min(1, average / 128);

      // Clear canvas with fade effect
      ctx.fillStyle = "rgba(26, 19, 16, 0.2)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw outer glow
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const maxRadius = Math.min(rect.width, rect.height) / 2.5;
      const radius = maxRadius * (0.5 + normalizedVolume * 0.5);

      // Create gradient for glow
      const gradient = ctx.createRadialGradient(
        centerX,
        centerY,
        radius * 0.8,
        centerX,
        centerY,
        radius * 1.2
      );
      gradient.addColorStop(
        0,
        `rgba(255, 204, 51, ${0.3 + normalizedVolume * 0.4})`
      );
      gradient.addColorStop(1, "rgba(255, 204, 51, 0)");

      // Draw glow
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius * 1.2, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Draw main circle
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 204, 51, ${0.4 + normalizedVolume * 0.6})`;
      ctx.fill();

      // Request next frame
      animationFrameRef.current = requestAnimationFrame(draw);
    };

    if (isActive) {
      draw();
    } else {
      // Draw inactive state
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          const dpr = window.devicePixelRatio || 1;
          const rect = canvas.getBoundingClientRect();
          canvas.width = rect.width * dpr;
          canvas.height = rect.height * dpr;
          ctx.scale(dpr, dpr);

          // Clear canvas
          ctx.fillStyle = "rgba(26, 19, 16, 1)";
          ctx.fillRect(0, 0, canvas.width, canvas.height);

          // Draw inactive circle
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;
          const radius = Math.min(rect.width, rect.height) / 5;

          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(255, 204, 51, 0.2)";
          ctx.fill();
        }
      }
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isActive]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full rounded-full min-h-[200px]"
      style={{ background: "rgba(26, 19, 16, 1)" }}
    />
  );
};

export default AudioVisualizer;
