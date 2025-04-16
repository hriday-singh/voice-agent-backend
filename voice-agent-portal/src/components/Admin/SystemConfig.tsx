import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  getVoiceConfig,
  getLanguageCodes,
  VoiceConfig,
  LanguageCodes,
  updateVoiceConfig,
} from "../../services/api";
import AnimatedLogo from "../Common/AnimatedLogo";

const SystemConfig: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [voiceConfig, setVoiceConfig] = useState<VoiceConfig>({});
  const [languageCodes, setLanguageCodes] = useState<LanguageCodes>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [voiceConfigData, languageCodesData] = await Promise.all([
          getVoiceConfig(),
          getLanguageCodes(),
        ]);
        setVoiceConfig(voiceConfigData);
        setLanguageCodes(languageCodesData);
      } catch (err: any) {
        console.error("Error fetching data:", err);
        setError(err.message || "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleVoiceConfigChange = (
    language: string,
    field: string,
    value: string
  ) => {
    setVoiceConfig((prev) => ({
      ...prev,
      [language]: {
        ...prev[language],
        [field]: value,
      },
    }));
  };

  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const response = await updateVoiceConfig(voiceConfig);

      setSuccess("Voice configuration updated successfully!");

      // Display success message for 3 seconds
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (err: any) {
      console.error("Error saving settings:", err);
      setError(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="flex flex-col items-center">
          <AnimatedLogo
            gifSrc="/assets/caw-tech-logo.svg"
            fallbackSrc="/assets/caw-tech-logo.svg"
            alt="Loading..."
            height={64}
            width={64}
            className="rounded-lg shadow-md object-contain"
          />
          <p className="mt-4 text-[#6c6c6c]">Loading system configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-[#140d0c]">
          System Configuration
        </h1>
        <button
          onClick={() => navigate("/admin/agents")}
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors flex items-center gap-1"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          Back to Agents
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-100 border border-red-300 text-red-700 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-6 p-4 bg-green-100 border border-green-300 text-green-700 rounded">
          {success}
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-medium mb-4 text-[#140d0c]">
          Voice Configuration
        </h2>
        <p className="text-[#6c6c6c] mb-6">
          Configure voice settings for each supported language.
        </p>

        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-[#e7e2d3]">
            <thead>
              <tr className="bg-[#f2efe3]">
                <th className="py-3 px-4 text-left border-b border-[#e7e2d3] text-[#140d0c]">
                  Language
                </th>
                <th className="py-3 px-4 text-left border-b border-[#e7e2d3] text-[#140d0c]">
                  Language Code
                </th>
                <th className="py-3 px-4 text-left border-b border-[#e7e2d3] text-[#140d0c]">
                  Voice Name
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(voiceConfig).map(([language, settings]) => (
                <tr
                  key={language}
                  className="border-b border-[#e7e2d3] hover:bg-[#f8f7f3]"
                >
                  <td className="py-3 px-4 text-[#140d0c]">{language}</td>
                  <td className="py-3 px-4">
                    <input
                      type="text"
                      value={settings.language_code}
                      onChange={(e) =>
                        handleVoiceConfigChange(
                          language,
                          "language_code",
                          e.target.value
                        )
                      }
                      className="w-full px-2 py-1 border border-[#e7e2d3] rounded"
                    />
                  </td>
                  <td className="py-3 px-4">
                    <input
                      type="text"
                      value={settings.voice_name}
                      onChange={(e) =>
                        handleVoiceConfigChange(
                          language,
                          "voice_name",
                          e.target.value
                        )
                      }
                      className="w-full px-2 py-1 border border-[#e7e2d3] rounded"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={handleSaveSettings}
            disabled={saving}
            className={`px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors flex items-center gap-1 ${
              saving ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            {saving ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemConfig;
