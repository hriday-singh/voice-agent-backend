import React, { useState, useEffect, useRef } from "react";
import {
  fetchAudioRecordings,
  getAudioFileUrl,
  AudioRecording,
} from "../../services/api";
import { FaPlay, FaPause, FaDownload } from "react-icons/fa";

const AudioRecordings: React.FC = () => {
  const [recordings, setRecordings] = useState<AudioRecording[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPlayingIndex, setCurrentPlayingIndex] = useState<number | null>(
    null
  );
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const audioRef = useRef<HTMLAudioElement>(null);

  // Fetch recordings when component mounts
  useEffect(() => {
    const loadRecordings = async () => {
      setIsLoading(true);
      try {
        const result = await fetchAudioRecordings();
        if (result.success && result.data) {
          setRecordings(result.data);
          setError(null);
        } else {
          setError(result.error || "Failed to load audio recordings");
        }
      } catch (err) {
        setError("An error occurred while loading recordings");
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadRecordings();
  }, []);

  // Handle play/pause
  const togglePlayPause = (index: number) => {
    if (!audioRef.current) return;

    // If user clicks on a different recording
    if (currentPlayingIndex !== index) {
      // Set the new audio source
      audioRef.current.src = getAudioFileUrl(recordings[index].file_name);
      audioRef.current.load();
      setCurrentPlayingIndex(index);
      audioRef.current
        .play()
        .then(() => {
          setIsPlaying(true);
        })
        .catch((err) => {
          console.error("Error playing audio:", err);
        });
    } else {
      // Toggle play/pause for current audio
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current
          .play()
          .then(() => {
            setIsPlaying(true);
          })
          .catch((err) => {
            console.error("Error playing audio:", err);
          });
      }
    }
  };

  // Handle audio ended event
  const handleAudioEnded = () => {
    setIsPlaying(false);
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Format date
  const formatDate = (timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  // Handle download
  const handleDownload = (fileName: string) => {
    try {
      const downloadUrl = getAudioFileUrl(fileName);

      // Create a temporary anchor element
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      console.error("Error downloading file:", err);
      setError("Failed to download file");
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6 text-[#140d0c]">
        Audio Recordings
      </h1>

      {/* Hidden audio element for playback */}
      <audio
        ref={audioRef}
        onEnded={handleAudioEnded}
        style={{ display: "none" }}
      />

      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#ffcc33]"></div>
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      ) : recordings.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No audio recordings found
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg shadow">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  File Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Modified
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {recordings.map((recording, index) => (
                <tr key={recording.file_name} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {recording.file_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatFileSize(recording.size_bytes)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(recording.modified_time)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex items-center space-x-4">
                      <button
                        onClick={() => togglePlayPause(index)}
                        className="text-[#ffcc33] hover:text-[#e6b800] transition-colors"
                        aria-label={
                          currentPlayingIndex === index && isPlaying
                            ? "Pause"
                            : "Play"
                        }
                      >
                        {currentPlayingIndex === index && isPlaying ? (
                          <FaPause className="w-5 h-5" />
                        ) : (
                          <FaPlay className="w-5 h-5" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDownload(recording.file_name)}
                        className="text-blue-600 hover:text-blue-800 transition-colors"
                        aria-label="Download"
                      >
                        <FaDownload className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AudioRecordings;
