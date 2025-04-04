import React, { useState, useEffect } from "react";
import {
  fetchAllAgents,
  getSystemConfig,
  updateSystemConfig,
  createAgent,
  updateAgent,
  deleteAgent,
  enableAgent,
  disableAgent,
  getAgentUsage,
  getAgentTraffic,
  clearAgentUsage,
  clearAgentTraffic,
  AgentData,
} from "../../services/api";
import AnimatedLogo from "../Common/AnimatedLogo";
import "./Admin.css";

interface Agent {
  id: string;
  name: string;
  description: string;
  startup_message: string;
  prompt: string;
  api_path: string;
  prompt_file: string;
  enabled: boolean;
}

interface SystemConfig {
  language_codes: Record<string, string>;
  model_config: {
    name: string;
    temperature: number;
  };
  audio_options: {
    audio_chunk_duration: number;
    started_talking_threshold: number;
    speech_threshold: number;
  };
  default_messages: Record<string, string>;
}

interface UsageRecord {
  id: number;
  otp_id: number;
  agent_type: string;
  timestamp: string;
}

interface TrafficRecord {
  id: number;
  agent_type: string;
  session_count: number;
  last_activity: string;
  is_active: boolean;
}

interface PaginationState {
  currentPage: number;
  totalPages: number;
  limit: number;
}

type ActiveTab = "agents" | "system" | "usage" | "traffic";

const AgentConfiguration: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("agents");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [usageStats, setUsageStats] = useState<UsageRecord[]>([]);
  const [trafficStats, setTrafficStats] = useState<TrafficRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<boolean>(false);
  const [newAgent, setNewAgent] = useState<AgentData>({
    id: "",
    name: "",
    description: "",
    startup_message:
      "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Welcome message</prosody></speak>",
    prompt: "System prompt that defines agent behavior",
  });
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [editingSystemConfig, setEditingSystemConfig] =
    useState<boolean>(false);
  const [usagePagination, setUsagePagination] = useState<PaginationState>({
    currentPage: 1,
    totalPages: 1,
    limit: 10,
  });
  const [trafficPagination, setTrafficPagination] = useState<PaginationState>({
    currentPage: 1,
    totalPages: 1,
    limit: 10,
  });

  useEffect(() => {
    if (activeTab === "agents") {
      fetchAgents();
    } else if (activeTab === "system") {
      fetchSystemConfigData();
    } else if (activeTab === "usage") {
      fetchUsageStatsData();
    } else if (activeTab === "traffic") {
      fetchTrafficStatsData();
    }
  }, [activeTab]);

  // Load initial data when component mounts
  useEffect(() => {
    // Only load agents data initially to avoid multiple API calls
    fetchAgents();

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const response = await fetchAllAgents();

      // Convert the response to the expected format
      let agentsArray: Agent[] = [];
      if (response && response.agents) {
        agentsArray = Object.entries(response.agents).map(
          ([id, agentData]: [string, any]) => ({
            id,
            name: agentData.name,
            description: agentData.description,
            startup_message: agentData.startup_message,
            prompt: agentData.prompt,
            api_path: agentData.api_path,
            prompt_file: agentData.prompt_file,
            enabled: agentData.enabled !== false,
          })
        );
      }

      setAgents(agentsArray);
      setError(null);
    } catch (err: any) {
      console.error("Error fetching agents:", err);
      setError(err.message || "Failed to fetch agents");
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemConfigData = async () => {
    try {
      setLoading(true);
      const response = await getSystemConfig();
      setSystemConfig(response);
      setError(null);
    } catch (err: any) {
      console.error("Error fetching system config:", err);
      setError(err.message || "Failed to fetch system configuration");
    } finally {
      setLoading(false);
    }
  };

  const fetchUsageStatsData = async (page = 1) => {
    try {
      setLoading(true);
      const offset = (page - 1) * usagePagination.limit;
      const response = await getAgentUsage({
        limit: usagePagination.limit,
        offset: offset,
      });
      setUsageStats(response.data.data || []);
      setUsagePagination((prev) => ({
        ...prev,
        currentPage: page,
        totalPages: Math.ceil(response.data.total / prev.limit),
      }));
      setError(null);
    } catch (err: any) {
      console.error("Error fetching usage stats:", err);
      setError(err.message || "Failed to fetch agent usage statistics");
    } finally {
      setLoading(false);
    }
  };

  const fetchTrafficStatsData = async (page = 1) => {
    try {
      setLoading(true);
      const offset = (page - 1) * trafficPagination.limit;
      const response = await getAgentTraffic({
        limit: trafficPagination.limit,
        offset: offset,
      });
      setTrafficStats(response.data.data || []);
      setTrafficPagination((prev) => ({
        ...prev,
        currentPage: page,
        totalPages: Math.ceil(response.data.total / prev.limit),
      }));
      setError(null);
    } catch (err: any) {
      console.error("Error fetching traffic stats:", err);
      setError(err.message || "Failed to fetch agent traffic statistics");
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;

    if (selectedAgentId) {
      // Edit existing agent
      setAgents((prevAgents) =>
        prevAgents.map((agent) =>
          agent.id === selectedAgentId
            ? {
                ...agent,
                [name]: value,
              }
            : agent
        )
      );
    } else {
      // New agent
      setNewAgent((prev) => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  const handleSystemConfigChange = (
    section: keyof SystemConfig,
    key: string,
    value: any
  ) => {
    if (!systemConfig) return;

    setSystemConfig({
      ...systemConfig,
      [section]: {
        ...systemConfig[section],
        [key]: value,
      },
    });
  };

  const handleAddLanguage = () => {
    if (!systemConfig) return;

    const languageName = prompt("Enter language name (e.g., english):");
    if (!languageName) return;

    const languageCode = prompt("Enter language code (e.g., en-IN):");
    if (!languageCode) return;

    setSystemConfig({
      ...systemConfig,
      language_codes: {
        ...systemConfig.language_codes,
        [languageName.toLowerCase()]: languageCode,
      },
    });
  };

  const handleRemoveLanguage = (language: string) => {
    if (!systemConfig) return;

    if (window.confirm(`Are you sure you want to remove ${language}?`)) {
      const newLanguageCodes = { ...systemConfig.language_codes };
      delete newLanguageCodes[language];

      setSystemConfig({
        ...systemConfig,
        language_codes: newLanguageCodes,
      });
    }
  };

  const handleAddDefaultMessage = () => {
    if (!systemConfig) return;

    const messageName = prompt(
      "Enter message type (e.g., error, unclear_audio):"
    );
    if (!messageName) return;

    const messageContent = prompt("Enter SSML message content:");
    if (!messageContent) return;

    setSystemConfig({
      ...systemConfig,
      default_messages: {
        ...systemConfig.default_messages,
        [messageName.toLowerCase()]: messageContent,
      },
    });
  };

  const handleRemoveDefaultMessage = (messageType: string) => {
    if (!systemConfig) return;

    if (
      window.confirm(`Are you sure you want to remove ${messageType} message?`)
    ) {
      const newMessages = { ...systemConfig.default_messages };
      delete newMessages[messageType];

      setSystemConfig({
        ...systemConfig,
        default_messages: newMessages,
      });
    }
  };

  const handleAddAgent = async () => {
    try {
      setLoading(true);
      setError(null);

      // Validate agent ID format
      if (newAgent.id && !/^[a-z0-9_]+$/.test(newAgent.id)) {
        setError(
          "Agent ID must contain only lowercase letters, numbers, and underscores"
        );
        return;
      }

      const response = await createAgent(newAgent);

      // Update the agents list with the new agent
      const newAgentWithPrompt = {
        ...response.agent,
        prompt: newAgent.prompt, // Add the prompt from the form
      };
      setAgents((prev) => [...prev, newAgentWithPrompt]);

      // Reset the form
      setNewAgent({
        id: "",
        name: "",
        description: "",
        startup_message:
          "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Welcome message</prosody></speak>",
        prompt: "System prompt that defines agent behavior",
      });

      setEditMode(false);
    } catch (err: any) {
      console.error("Error adding agent:", err);
      setError(err.message || "Failed to add agent");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateAgent = async () => {
    if (!selectedAgentId) return;

    try {
      setLoading(true);
      setError(null);

      const agentToUpdate = agents.find((a) => a.id === selectedAgentId);
      if (!agentToUpdate) {
        throw new Error("Agent not found");
      }

      const response = await updateAgent(selectedAgentId, {
        name: agentToUpdate.name,
        description: agentToUpdate.description,
        startup_message: agentToUpdate.startup_message,
        prompt: agentToUpdate.prompt,
      });

      // Update the agents list with the updated agent
      const updatedAgentWithPrompt = {
        ...response.agent,
        prompt: agentToUpdate.prompt, // Keep the prompt from the form
      };
      setAgents((prev) =>
        prev.map((agent) =>
          agent.id === selectedAgentId ? updatedAgentWithPrompt : agent
        )
      );

      setSelectedAgentId(null);
      setEditMode(false);
    } catch (err: any) {
      console.error("Error updating agent:", err);
      setError(err.message || "Failed to update agent");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAgent = async (agentId: string, enabled: boolean) => {
    try {
      setLoading(true);
      setError(null);

      const response = enabled
        ? await enableAgent(agentId)
        : await disableAgent(agentId);

      // Update the agents list with the updated enabled status
      setAgents((prev) =>
        prev.map((agent) =>
          agent.id === agentId ? { ...agent, enabled } : agent
        )
      );
    } catch (err: any) {
      console.error("Error toggling agent:", err);
      setError(
        err.message || `Failed to ${enabled ? "enable" : "disable"} agent`
      );
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!window.confirm("Are you sure you want to delete this agent?")) {
      return;
    }

    try {
      setLoading(true);
      await deleteAgent(agentId);
      fetchAgents(); // Refresh the list
    } catch (err) {
      console.error("Error deleting agent:", err);
      setError("Failed to delete agent");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateSystemConfig = async () => {
    if (!systemConfig) return;

    try {
      setLoading(true);
      const response = await updateSystemConfig(systemConfig);
      setEditingSystemConfig(false);
    } catch (err) {
      console.error("Error updating system config:", err);
      setError("Failed to update system configuration");
    } finally {
      setLoading(false);
    }
  };

  const cancelSystemConfigEdit = () => {
    setEditingSystemConfig(false);
    fetchSystemConfigData();
  };

  // Format timestamp to a readable format
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const clearUsageStats = async () => {
    if (
      !window.confirm(
        "Are you sure you want to clear all agent usage records? This cannot be undone."
      )
    ) {
      return;
    }

    try {
      setLoading(true);
      await clearAgentUsage();
      fetchUsageStatsData(); // Refresh after clearing
      setError(null);
    } catch (err: any) {
      console.error("Error clearing usage stats:", err);
      setError(err.message || "Failed to clear agent usage statistics");
    } finally {
      setLoading(false);
    }
  };

  const clearTrafficStats = async () => {
    if (
      !window.confirm(
        "Are you sure you want to clear all agent traffic statistics? This cannot be undone."
      )
    ) {
      return;
    }

    try {
      setLoading(true);
      await clearAgentTraffic();
      fetchTrafficStatsData(); // Refresh after clearing
      setError(null);
    } catch (err: any) {
      console.error("Error clearing traffic stats:", err);
      setError(err.message || "Failed to clear agent traffic statistics");
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (tab: "usage" | "traffic", page: number) => {
    if (tab === "usage") {
      fetchUsageStatsData(page);
    } else {
      fetchTrafficStatsData(page);
    }
  };

  const handleRefreshUsage = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    fetchUsageStatsData(1);
  };

  const handleRefreshTraffic = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    fetchTrafficStatsData(1);
  };

  // Add pagination component
  const Pagination: React.FC<{
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
  }> = ({ currentPage, totalPages, onPageChange }) => {
    const handlePrevClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.preventDefault();
      if (currentPage > 1) {
        onPageChange(currentPage - 1);
      }
    };

    const handleNextClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.preventDefault();
      if (currentPage < totalPages) {
        onPageChange(currentPage + 1);
      }
    };

    return (
      <div className="flex justify-center items-center space-x-2 mt-4">
        <button
          onClick={handlePrevClick}
          disabled={currentPage === 1}
          className="px-3 py-1 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          Previous
        </button>
        <span className="text-sm text-[#6c6c6c]">
          Page {currentPage} of {totalPages}
        </span>
        <button
          onClick={handleNextClick}
          disabled={currentPage === totalPages}
          className="px-3 py-1 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          Next
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center">
          <AnimatedLogo
            gifSrc="/assets/caw-tech-logo.gif"
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
          <h2 className="text-2xl font-bold text-[#140d0c]">
            Agent Configuration
          </h2>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        <div className="mb-6">
          <nav className="flex space-x-4 border-b border-[#e7e2d3]">
            {["agents", "system", "usage", "traffic"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab as ActiveTab)}
                className={`px-4 py-2 font-medium transition-colors relative ${
                  activeTab === tab
                    ? "text-[#ffcc33] after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-[#ffcc33]"
                    : "text-[#6c6c6c] hover:text-[#ffcc33]"
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === "agents" && (
          <div className="space-y-6">
            {editMode && (
              <div className="bg-[#f2efe3] p-6 rounded-lg border border-[#e7e2d3]">
                <h3 className="text-lg font-medium mb-4">
                  {selectedAgentId ? "Edit Agent" : "Add New Agent"}
                </h3>
                <div className="space-y-4">
                  {!selectedAgentId && (
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Agent ID
                      </label>
                      <input
                        type="text"
                        name="id"
                        value={newAgent.id}
                        onChange={handleInputChange}
                        placeholder="lowercase_with_underscores"
                        className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                      />
                      <p className="text-xs text-[#6c6c6c] mt-1">
                        Must contain only lowercase letters, numbers, and
                        underscores
                      </p>
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={
                        selectedAgentId
                          ? agents.find((a) => a.id === selectedAgentId)?.name
                          : newAgent.name
                      }
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Description
                    </label>
                    <textarea
                      name="description"
                      value={
                        selectedAgentId
                          ? agents.find((a) => a.id === selectedAgentId)
                              ?.description
                          : newAgent.description
                      }
                      onChange={handleInputChange}
                      rows={3}
                      className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Startup Message (SSML)
                    </label>
                    <textarea
                      name="startup_message"
                      value={
                        selectedAgentId
                          ? agents.find((a) => a.id === selectedAgentId)
                              ?.startup_message
                          : newAgent.startup_message
                      }
                      onChange={handleInputChange}
                      rows={4}
                      className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md font-mono text-sm"
                    />
                    <p className="text-xs text-[#6c6c6c] mt-1">
                      Use SSML format with language and prosody tags
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      System Prompt
                    </label>
                    <textarea
                      name="prompt"
                      value={
                        selectedAgentId
                          ? agents.find((a) => a.id === selectedAgentId)?.prompt
                          : newAgent.prompt
                      }
                      onChange={handleInputChange}
                      rows={6}
                      className="w-full px-3 py-2 border border-[#e7e2d3] rounded-md"
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={() => {
                        setEditMode(false);
                        setSelectedAgentId(null);
                        setNewAgent({
                          id: "",
                          name: "",
                          description: "",
                          startup_message:
                            "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>Welcome message</prosody></speak>",
                          prompt: "System prompt that defines agent behavior",
                        });
                      }}
                      className="px-4 py-2 bg-gray-200 text-[#140d0c] rounded hover:bg-gray-300 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={
                        selectedAgentId ? handleUpdateAgent : handleAddAgent
                      }
                      className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors"
                    >
                      {selectedAgentId ? "Update Agent" : "Create Agent"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className="bg-white rounded-lg shadow-md p-6 flex flex-col border border-[#e7e2d3] hover:shadow-lg transition-all duration-300"
                >
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <h3 className="text-lg font-medium text-[#140d0c]">
                      {agent.name}
                    </h3>
                    <button
                      onClick={() =>
                        handleToggleAgent(agent.id, !agent.enabled)
                      }
                      className={`px-2 py-1 text-xs rounded-full ${
                        agent.enabled
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {agent.enabled ? "Enabled" : "Disabled"}
                    </button>
                  </div>

                  <p className="text-[#6c6c6c] mb-4">{agent.description}</p>

                  <div className="text-xs text-[#6c6c6c] mb-4">
                    <p>ID: {agent.id}</p>
                    <p>API Path: {agent.api_path}</p>
                  </div>

                  <div className="flex justify-end space-x-2 mt-auto pt-4 border-t border-[#e7e2d3]">
                    <button
                      onClick={() => {
                        setEditMode(true);
                        setSelectedAgentId(agent.id);
                      }}
                      className="px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteAgent(agent.id)}
                      className="px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition-colors text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "system" && systemConfig && (
          <div className="space-y-6">
            <div className="flex justify-between items-center mb-6">
              {!editingSystemConfig ? (
                <button
                  className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors font-medium"
                  onClick={() => setEditingSystemConfig(true)}
                >
                  Edit System Configuration
                </button>
              ) : (
                <div className="space-x-2">
                  <button
                    className="px-4 py-2 bg-gray-200 text-[#140d0c] rounded hover:bg-gray-300 transition-colors font-medium"
                    onClick={cancelSystemConfigEdit}
                  >
                    Cancel
                  </button>
                  <button
                    className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors font-medium"
                    onClick={handleUpdateSystemConfig}
                  >
                    Save Configuration
                  </button>
                </div>
              )}
            </div>

            <div className="config-section">
              <h3>Language Codes</h3>
              {editingSystemConfig && (
                <button className="small-button" onClick={handleAddLanguage}>
                  + Add Language
                </button>
              )}
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Language</th>
                    <th>Code</th>
                    {editingSystemConfig && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(systemConfig.language_codes).map(
                    ([language, code]) => (
                      <tr key={language}>
                        <td>{language}</td>
                        <td>
                          {editingSystemConfig ? (
                            <input
                              type="text"
                              value={code}
                              onChange={(e) =>
                                handleSystemConfigChange(
                                  "language_codes",
                                  language,
                                  e.target.value
                                )
                              }
                            />
                          ) : (
                            code
                          )}
                        </td>
                        {editingSystemConfig && (
                          <td>
                            <button
                              className="delete-button small"
                              onClick={() => handleRemoveLanguage(language)}
                            >
                              Remove
                            </button>
                          </td>
                        )}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>

            <div className="config-section">
              <h3>Model Configuration</h3>
              <table className="data-table">
                <tbody>
                  <tr>
                    <td>Model Name</td>
                    <td>
                      {editingSystemConfig ? (
                        <input
                          type="text"
                          value={systemConfig.model_config.name}
                          onChange={(e) =>
                            handleSystemConfigChange(
                              "model_config",
                              "name",
                              e.target.value
                            )
                          }
                        />
                      ) : (
                        systemConfig.model_config.name
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Temperature</td>
                    <td>
                      {editingSystemConfig ? (
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step="0.1"
                          value={systemConfig.model_config.temperature}
                          onChange={(e) =>
                            handleSystemConfigChange(
                              "model_config",
                              "temperature",
                              parseFloat(e.target.value)
                            )
                          }
                        />
                      ) : (
                        systemConfig.model_config.temperature
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="config-section">
              <h3>Audio Options</h3>
              <table className="data-table">
                <tbody>
                  <tr>
                    <td>Audio Chunk Duration</td>
                    <td>
                      {editingSystemConfig ? (
                        <input
                          type="number"
                          min="0.1"
                          step="0.1"
                          value={
                            systemConfig.audio_options.audio_chunk_duration
                          }
                          onChange={(e) =>
                            handleSystemConfigChange(
                              "audio_options",
                              "audio_chunk_duration",
                              parseFloat(e.target.value)
                            )
                          }
                        />
                      ) : (
                        systemConfig.audio_options.audio_chunk_duration
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Started Talking Threshold</td>
                    <td>
                      {editingSystemConfig ? (
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step="0.05"
                          value={
                            systemConfig.audio_options.started_talking_threshold
                          }
                          onChange={(e) =>
                            handleSystemConfigChange(
                              "audio_options",
                              "started_talking_threshold",
                              parseFloat(e.target.value)
                            )
                          }
                        />
                      ) : (
                        systemConfig.audio_options.started_talking_threshold
                      )}
                    </td>
                  </tr>
                  <tr>
                    <td>Speech Threshold</td>
                    <td>
                      {editingSystemConfig ? (
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step="0.05"
                          value={systemConfig.audio_options.speech_threshold}
                          onChange={(e) =>
                            handleSystemConfigChange(
                              "audio_options",
                              "speech_threshold",
                              parseFloat(e.target.value)
                            )
                          }
                        />
                      ) : (
                        systemConfig.audio_options.speech_threshold
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="config-section">
              <h3>Default Messages</h3>
              {editingSystemConfig && (
                <button
                  className="small-button"
                  onClick={handleAddDefaultMessage}
                >
                  + Add Message
                </button>
              )}
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>SSML Message</th>
                    {editingSystemConfig && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(systemConfig.default_messages).map(
                    ([type, message]) => (
                      <tr key={type}>
                        <td>{type}</td>
                        <td>
                          {editingSystemConfig ? (
                            <textarea
                              rows={3}
                              value={message}
                              onChange={(e) =>
                                handleSystemConfigChange(
                                  "default_messages",
                                  type,
                                  e.target.value
                                )
                              }
                            />
                          ) : (
                            <div className="message-preview">{message}</div>
                          )}
                        </td>
                        {editingSystemConfig && (
                          <td>
                            <button
                              className="delete-button small"
                              onClick={() => handleRemoveDefaultMessage(type)}
                            >
                              Remove
                            </button>
                          </td>
                        )}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "usage" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-[#140d0c]">
                Agent Usage Statistics
              </h3>
              <div className="space-x-2">
                <button
                  onClick={handleRefreshUsage}
                  className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors font-medium"
                >
                  Refresh Data
                </button>
                <button
                  onClick={clearUsageStats}
                  className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors font-medium"
                >
                  Clear Data
                </button>
              </div>
            </div>

            {usageStats.length === 0 ? (
              <div className="text-center py-8 text-[#6c6c6c]">
                No usage data available
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-[#e7e2d3]">
                    <thead>
                      <tr className="bg-[#f2efe3]">
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          ID
                        </th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          OTP ID
                        </th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          Agent Type
                        </th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          Timestamp
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-[#e7e2d3]">
                      {usageStats.map((record) => (
                        <tr key={record.id} className="hover:bg-[#f2efe3]/50">
                          <td className="px-4 py-3 text-sm">{record.id}</td>
                          <td className="px-4 py-3 text-sm">{record.otp_id}</td>
                          <td className="px-4 py-3 text-sm">
                            {record.agent_type}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {formatTimestamp(record.timestamp)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <Pagination
                  currentPage={usagePagination.currentPage}
                  totalPages={usagePagination.totalPages}
                  onPageChange={(page) => handlePageChange("usage", page)}
                />
              </>
            )}
          </div>
        )}

        {activeTab === "traffic" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-[#140d0c]">
                Agent Traffic Statistics
              </h3>
              <div className="space-x-2">
                <button
                  onClick={handleRefreshTraffic}
                  className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors font-medium"
                >
                  Refresh Data
                </button>
                <button
                  onClick={clearTrafficStats}
                  className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors font-medium"
                >
                  Clear Data
                </button>
              </div>
            </div>

            {trafficStats.length === 0 ? (
              <div className="text-center py-8 text-[#6c6c6c]">
                No traffic data available
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-[#e7e2d3]">
                    <thead>
                      <tr className="bg-[#f2efe3]">
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          ID
                        </th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          Agent Type
                        </th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          Session Count
                        </th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          Last Activity
                        </th>
                        <th className="px-4 py-2 text-left text-sm font-medium text-[#140d0c]">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-[#e7e2d3]">
                      {trafficStats.map((record) => (
                        <tr key={record.id} className="hover:bg-[#f2efe3]/50">
                          <td className="px-4 py-3 text-sm">{record.id}</td>
                          <td className="px-4 py-3 text-sm">
                            {record.agent_type}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {record.session_count}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {formatTimestamp(record.last_activity)}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            <span
                              className={`inline-block px-2 py-1 rounded-full text-xs ${
                                record.is_active
                                  ? "bg-green-100 text-green-800"
                                  : "bg-red-100 text-red-800"
                              }`}
                            >
                              {record.is_active ? "Active" : "Inactive"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <Pagination
                  currentPage={trafficPagination.currentPage}
                  totalPages={trafficPagination.totalPages}
                  onPageChange={(page) => handlePageChange("traffic", page)}
                />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentConfiguration;
