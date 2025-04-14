import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getAgent,
  fetchLLMModelsList,
  getLanguageCodes,
  AgentDetail,
  LLMModelList,
  LanguageCodes,
} from "../../services/api";
import { updateExistingAgent } from "../../utils/agentOperations";
import AnimatedLogo from "../Common/AnimatedLogo";

const defaultAgent: Partial<AgentDetail> = {
  id: undefined,
  name: "",
  description: "",
  api_path: "",
  startup_message:
    "<speak>Welcome to our service. How may I help you today?</speak>",
  system_prompt: "You are a helpful assistant...",
  can_interrupt: false,
  voice_name: "en-IN-Wavenet-E",
  limitations: [],
  llm_model_id: undefined,
  temperature: 0.7,
  languages: {
    primary: "en-IN",
    supported: ["en-IN"],
  },
  error_messages: {
    error:
      "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I apologize, I couldn't understand. Please try again.</prosody></speak>",
    unclear_audio:
      "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I couldn't hear you clearly. Could you please repeat?</prosody></speak>",
    unsupported_language:
      "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I'm sorry, but that language isn't supported. Please try another language.</prosody></speak>",
  },
  speech_context: [],
  agent_type: "",
  is_outbound: false,
  enabled: true,
  tags: [],
};

const AgentEdit: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [llmModels, setLLMModels] = useState<LLMModelList[]>([]);
  const [languageCodes, setLanguageCodes] = useState<LanguageCodes>({});

  const [agent, setAgent] = useState<Partial<AgentDetail>>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [modelsData, langCodesData] = await Promise.all([
          fetchLLMModelsList(),
          getLanguageCodes(),
        ]);
        setLLMModels(modelsData);
        setLanguageCodes(langCodesData);

        if (id) {
          const agentData = await getAgent(id);
          setAgent(agentData);
        } else {
          // Redirect to agent list if no ID provided
          navigate("/admin/agents");
        }
      } catch (err: any) {
        console.error("Error fetching data:", err);
        setError(err.message || "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, navigate]);

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setAgent((prev) => {
      const updates = { ...prev, [name]: value };

      // Update api_path automatically when agent_type changes
      if (name === "agent_type") {
        updates.api_path = `/voice-agents/${value}`;
      }

      return updates;
    });
  };

  const handleLanguagesChange = (key: string, value: any) => {
    setAgent((prev) => {
      const updatedLanguages = {
        ...prev.languages,
        [key]: value,
      };
      return {
        ...prev,
        languages: updatedLanguages as AgentDetail["languages"],
      };
    });
  };

  const handleErrorMessageChange = (key: string, value: string) => {
    setAgent((prev) => {
      const updatedErrorMessages = {
        ...prev.error_messages,
        [key]: value,
      };
      return {
        ...prev,
        error_messages: updatedErrorMessages as AgentDetail["error_messages"],
      };
    });
  };

  const handleAddSupportedLanguage = () => {
    // Create a simple dropdown in a modal
    const modal = document.createElement("div");
    modal.style.position = "fixed";
    modal.style.top = "0";
    modal.style.left = "0";
    modal.style.width = "100%";
    modal.style.height = "100%";
    modal.style.backgroundColor = "rgba(0,0,0,0.5)";
    modal.style.display = "flex";
    modal.style.justifyContent = "center";
    modal.style.alignItems = "center";
    modal.style.zIndex = "1000";

    const content = document.createElement("div");
    content.style.backgroundColor = "white";
    content.style.padding = "20px";
    content.style.borderRadius = "5px";
    content.style.width = "300px";

    const header = document.createElement("h3");
    header.textContent = "Add Supported Language";
    header.style.marginBottom = "15px";

    // Get current supported languages
    const currentSupported = agent.languages?.supported || [];

    // Create select element
    const select = document.createElement("select");
    select.style.width = "100%";
    select.style.padding = "8px";
    select.style.marginBottom = "15px";
    select.style.borderRadius = "4px";
    select.style.border = "1px solid #ccc";

    if (languageCodes) {
      Object.entries(languageCodes).forEach(([name, code]) => {
        if (!currentSupported.includes(code)) {
          const option = document.createElement("option");
          option.value = code;
          option.textContent = `${name} (${code})`;
          select.appendChild(option);
        }
      });
    }

    // Buttons
    const buttonContainer = document.createElement("div");
    buttonContainer.style.display = "flex";
    buttonContainer.style.justifyContent = "flex-end";
    buttonContainer.style.gap = "10px";

    const cancelButton = document.createElement("button");
    cancelButton.textContent = "Cancel";
    cancelButton.style.padding = "8px 16px";
    cancelButton.style.backgroundColor = "#f1f1f1";
    cancelButton.style.border = "none";
    cancelButton.style.borderRadius = "4px";
    cancelButton.style.cursor = "pointer";

    const addButton = document.createElement("button");
    addButton.textContent = "Add";
    addButton.style.padding = "8px 16px";
    addButton.style.backgroundColor = "#ffcc33";
    addButton.style.color = "#140d0c";
    addButton.style.border = "none";
    addButton.style.borderRadius = "4px";
    addButton.style.cursor = "pointer";

    // Add event listeners
    cancelButton.onclick = () => {
      document.body.removeChild(modal);
    };

    addButton.onclick = () => {
      const selectedLanguage = select.value as string;
      if (selectedLanguage) {
        setAgent((prev) => {
          const currentSupported = prev.languages?.supported || [];
          return {
            ...prev,
            languages: {
              ...prev.languages,
              supported: [...currentSupported, selectedLanguage],
            } as AgentDetail["languages"],
          };
        });
      }
      document.body.removeChild(modal);
    };

    // Assemble the modal
    buttonContainer.appendChild(cancelButton);
    buttonContainer.appendChild(addButton);

    content.appendChild(header);
    content.appendChild(select);
    content.appendChild(buttonContainer);

    modal.appendChild(content);

    document.body.appendChild(modal);
  };

  const handleRemoveSupportedLanguage = (language: string) => {
    setAgent((prev) => {
      const currentSupported = prev.languages?.supported || [];
      return {
        ...prev,
        languages: {
          ...prev.languages,
          supported: currentSupported.filter((lang) => lang !== language),
        } as AgentDetail["languages"],
      };
    });
  };

  const handleAddLimitation = () => {
    setAgent((prev) => ({
      ...prev,
      limitations: [...(prev.limitations || []), ""],
    }));
  };

  const handleLimitationChange = (index: number, value: string) => {
    setAgent((prev) => {
      const updatedLimitations = [...(prev.limitations || [])];
      updatedLimitations[index] = value;
      return {
        ...prev,
        limitations: updatedLimitations,
      };
    });
  };

  const handleRemoveLimitation = (index: number) => {
    setAgent((prev) => ({
      ...prev,
      limitations: prev.limitations?.filter((_, i) => i !== index) || [],
    }));
  };

  const handleTemperatureChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const temperature = parseFloat(e.target.value);
    setAgent((prev) => ({
      ...prev,
      temperature,
    }));
  };

  const handleLLMModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const modelId = e.target.value ? parseInt(e.target.value, 10) : undefined;
    setAgent((prev) => ({
      ...prev,
      llm_model_id: modelId,
    }));
  };

  const handleAddTag = () => {
    setAgent((prev) => ({
      ...prev,
      tags: [...(prev.tags || []), ""],
    }));
  };

  const handleTagChange = (index: number, value: string) => {
    setAgent((prev) => {
      const updatedTags = [...(prev.tags || [])];
      updatedTags[index] = value;
      return {
        ...prev,
        tags: updatedTags,
      };
    });
  };

  const handleRemoveTag = (index: number) => {
    setAgent((prev) => ({
      ...prev,
      tags: prev.tags?.filter((_, i) => i !== index) || [],
    }));
  };

  const handleAddSpeechContext = () => {
    setAgent((prev) => ({
      ...prev,
      speech_context: ["", ...(prev.speech_context || [])],
    }));
  };

  const handleSpeechContextChange = (index: number, value: string) => {
    setAgent((prev) => {
      const updatedContext = [...(prev.speech_context || [])];
      updatedContext[index] = value;
      return {
        ...prev,
        speech_context: updatedContext,
      };
    });
  };

  const handleRemoveSpeechContext = (index: number) => {
    setAgent((prev) => ({
      ...prev,
      speech_context: prev.speech_context?.filter((_, i) => i !== index) || [],
    }));
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);

      if (
        !agent.name ||
        !agent.description ||
        !agent.startup_message ||
        !agent.system_prompt ||
        !agent.agent_type
      ) {
        setError("Please fill in all required fields");
        return;
      }

      if (id) {
        await updateExistingAgent(id, agent);
        navigate("/admin/agents");
      }
    } catch (err: any) {
      console.error("Error updating agent:", err);
      setError(err.message || "Failed to update agent");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center">
          <AnimatedLogo
            gifSrc="/assets/caw-tech-logo.svg"
            fallbackSrc="/assets/caw-tech-logo.svg"
            alt="Loading..."
            height={64}
            width={64}
            className="rounded-lg shadow-md object-contain"
          />
          <p className="mt-4 text-[#6c6c6c]">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="bg-white shadow-md rounded-lg p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-[#140d0c]">Edit Agent</h2>
          <button
            onClick={() => navigate("/admin/agents")}
            className="px-4 py-2 bg-gray-200 text-[#140d0c] rounded hover:bg-gray-300 transition-colors flex items-center gap-1"
          >
            <svg
              className="w-4 h-4"
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
            Back to List
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        <div className="space-y-6">
          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">Basic Information</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  name="name"
                  value={agent.name}
                  onChange={handleInputChange}
                  placeholder="Agent Name"
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Description
                </label>
                <textarea
                  name="description"
                  value={agent.description}
                  onChange={handleInputChange}
                  placeholder="Agent Description"
                  rows={2}
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Agent Type
                </label>
                <input
                  type="text"
                  name="agent_type"
                  value={agent.agent_type}
                  onChange={handleInputChange}
                  placeholder="Agent Type"
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  API Path
                </label>
                <div className="flex items-center w-full px-3 py-2 border border-[#e7e2d3] bg-gray-50 rounded-md text-gray-500">
                  {agent.api_path ||
                    `/voice-agents/${agent.agent_type || "[agent-type]"}`}
                </div>
                <p className="text-xs text-[#6c6c6c] mt-1">
                  Path is automatically generated from Agent Type
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white p-4 rounded-lg border border-[#e7e2d3]">
                  <div className="flex justify-between items-start">
                    <div>
                      <label className="text-sm font-medium">
                        Outbound Agent
                      </label>
                      <p className="text-xs text-[#6c6c6c] mt-1">
                        Enable if this agent should initiate outbound calls
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={agent.is_outbound}
                        onChange={(e) =>
                          setAgent((prev) => ({
                            ...prev,
                            is_outbound: e.target.checked,
                          }))
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[#ffcc33]/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#ffcc33]"></div>
                    </label>
                  </div>
                </div>

                <div className="bg-white p-4 rounded-lg border border-[#e7e2d3]">
                  <div className="flex justify-between items-start">
                    <div>
                      <label className="text-sm font-medium">
                        Can Interrupt
                      </label>
                      <p className="text-xs text-[#6c6c6c] mt-1">
                        Allow users to interrupt the agent while speaking
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={agent.can_interrupt}
                        onChange={(e) =>
                          setAgent((prev) => ({
                            ...prev,
                            can_interrupt: e.target.checked,
                          }))
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-[#ffcc33]/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#ffcc33]"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">Messages</h3>
            <div className="space-y-4">
              <div className={`${!agent.is_outbound ? "opacity-50" : ""}`}>
                <div className="flex items-center gap-2 mb-1">
                  <label className="block text-sm font-medium">
                    Startup Message
                  </label>
                  {!agent.is_outbound && (
                    <span className="bg-amber-100 text-amber-800 text-xs px-2 py-1 rounded-full">
                      Requires Outbound Agent
                    </span>
                  )}
                </div>
                <textarea
                  name="startup_message"
                  value={agent.startup_message}
                  onChange={handleInputChange}
                  disabled={!agent.is_outbound}
                  rows={4}
                  className={`w-full px-3 py-2 border border-[#e7e2d3] rounded-md font-mono text-sm ${
                    !agent.is_outbound ? "bg-gray-50 cursor-not-allowed" : ""
                  }`}
                />
                <p className="text-xs text-[#6c6c6c] mt-1">
                  {agent.is_outbound
                    ? "Use SSML format with language and prosody tags"
                    : "Startup message is only available for outbound agents who initiate calls"}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  System Prompt
                </label>
                <textarea
                  name="system_prompt"
                  value={agent.system_prompt}
                  onChange={handleInputChange}
                  rows={6}
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                />
                <p className="text-xs text-[#6c6c6c] mt-1">
                  Defines the agent's behavior and capabilities
                </p>
              </div>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">Voice Configuration</h3>
            <div>
              <label className="block text-sm font-medium mb-1">
                Voice Name
              </label>
              <input
                type="text"
                name="voice_name"
                value={agent.voice_name}
                onChange={handleInputChange}
                placeholder="e.g., en-US-Wavenet-F"
                className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
              />
              <p className="text-xs text-[#6c6c6c] mt-1">
                Specify the TTS voice name to use
              </p>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">
              Languages Configuration
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Primary Language
                </label>
                <select
                  value={agent.languages?.primary || "en-IN"}
                  onChange={(e) =>
                    handleLanguagesChange("primary", e.target.value)
                  }
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                >
                  {agent.languages?.supported.map((code) => (
                    <option key={code} value={code}>
                      {Object.entries(languageCodes).find(
                        ([_, c]) => c === code
                      )?.[0] || code}{" "}
                      ({code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Supported Languages
                </label>
                <div className="flex items-center gap-2">
                  <div className="flex-1 flex flex-wrap gap-2">
                    {agent.languages?.supported.map((lang) => (
                      <div
                        key={lang}
                        className="bg-gray-100 px-2 py-1 rounded-full flex items-center"
                      >
                        <span className="text-sm mr-1">
                          {Object.entries(languageCodes).find(
                            ([_, c]) => c === lang
                          )?.[0] || lang}{" "}
                          ({lang})
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveSupportedLanguage(lang)}
                          className="text-red-500 hover:text-red-700"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={handleAddSupportedLanguage}
                    className="px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors flex items-center gap-1"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                    Add
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">Error Messages</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  General Error
                </label>
                <textarea
                  value={agent.error_messages?.error || ""}
                  onChange={(e) =>
                    handleErrorMessageChange("error", e.target.value)
                  }
                  rows={2}
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md font-mono text-sm"
                  placeholder="<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Error message</prosody></speak>"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Unclear Audio
                </label>
                <textarea
                  value={agent.error_messages?.unclear_audio || ""}
                  onChange={(e) =>
                    handleErrorMessageChange("unclear_audio", e.target.value)
                  }
                  rows={2}
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md font-mono text-sm"
                  placeholder="<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Unclear audio message</prosody></speak>"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Unsupported Language
                </label>
                <textarea
                  value={agent.error_messages?.unsupported_language || ""}
                  onChange={(e) =>
                    handleErrorMessageChange(
                      "unsupported_language",
                      e.target.value
                    )
                  }
                  rows={2}
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md font-mono text-sm"
                  placeholder="<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Unsupported language message</prosody></speak>"
                />
              </div>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">Model Configuration</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  LLM Model
                </label>
                <select
                  value={agent.llm_model_id?.toString() || ""}
                  onChange={handleLLMModelChange}
                  className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                >
                  <option value="">-- Select LLM Model --</option>
                  {llmModels.map((model) => (
                    <option key={model.id} value={model.id.toString()}>
                      {model.display_name} ({model.provider_name})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Temperature
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={agent.temperature || 0.7}
                  onChange={handleTemperatureChange}
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-[#6c6c6c]">
                  <span>0.0 (Precise)</span>
                  <span>{agent.temperature || 0.7}</span>
                  <span>1.0 (Creative)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">Tags</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                {agent.tags?.map((tag, index) => (
                  <div key={index} className="flex items-center">
                    <input
                      type="text"
                      value={tag}
                      onChange={(e) => handleTagChange(index, e.target.value)}
                      placeholder="Enter a tag"
                      className="flex-1 px-3 py-2 border border-[#e7e2d3] rounded-md mr-2"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(index)}
                      className="px-2 py-1 text-red-500 hover:text-red-700"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={handleAddTag}
                  className="px-3 py-2 text-sm text-blue-500 border border-dashed border-blue-300 rounded-md hover:bg-blue-50 w-full"
                >
                  + Add Tag
                </button>
              </div>
              <p className="text-sm text-[#6c6c6c]">
                Add tags to categorize and filter agents
              </p>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <h3 className="text-lg font-medium mb-4">Limitations</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                {agent.limitations?.map((limitation, index) => (
                  <div key={index} className="flex items-center">
                    <input
                      type="text"
                      value={limitation}
                      onChange={(e) =>
                        handleLimitationChange(index, e.target.value)
                      }
                      placeholder="Enter a limitation"
                      className="flex-1 px-3 py-2 border border-[#e7e2d3] rounded-md mr-2"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveLimitation(index)}
                      className="px-2 py-1 text-red-500 hover:text-red-700"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={handleAddLimitation}
                  className="px-3 py-2 text-sm text-blue-500 border border-dashed border-blue-300 rounded-md hover:bg-blue-50 w-full"
                >
                  + Add Limitation
                </button>
              </div>
              <p className="text-sm text-[#6c6c6c]">
                Add limitations or known issues with this agent
              </p>
            </div>
          </div>

          <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Speech Context</h3>
              <button
                type="button"
                onClick={handleAddSpeechContext}
                className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                + Add
              </button>
            </div>
            <div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                {agent.speech_context?.map((context, index) => (
                  <div
                    key={index}
                    className="flex items-center bg-white rounded-md border border-[#e7e2d3] px-2 py-1 gap-1"
                  >
                    <input
                      type="text"
                      value={context}
                      onChange={(e) =>
                        handleSpeechContextChange(index, e.target.value)
                      }
                      placeholder="Add phrase"
                      className="flex-1 text-sm border-none focus:outline-none focus:ring-1 focus:ring-[#ffcc33] min-w-0"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveSpeechContext(index)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <p className="text-xs text-[#6c6c6c] mt-2">
                Add phrases or words that the agent should recognize more
                accurately
              </p>
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={() => navigate("/admin/agents")}
              className="px-4 py-2 bg-gray-200 text-[#140d0c] rounded hover:bg-gray-300 transition-colors flex items-center gap-1"
            >
              <svg
                className="w-4 h-4"
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
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors flex items-center gap-1"
            >
              <svg
                className="w-4 h-4"
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
              Update Agent
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentEdit;
