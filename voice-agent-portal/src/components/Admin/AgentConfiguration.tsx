import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchAllAgents,
  enableAgent,
  disableAgent,
  deleteAgent,
  Agent,
} from "../../services/api";
import AnimatedLogo from "../Common/AnimatedLogo";
import "./Admin.css";

const AgentConfiguration: React.FC = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const response = await fetchAllAgents();
      setAgents(response);
    } catch (err: any) {
      console.error("Error fetching agents:", err);
      setError(err.message || "Failed to fetch agents");
      setAgents([]);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAgent = async (agentId: number, enabled: boolean) => {
    try {
      setLoading(true);
      const response = enabled
        ? await enableAgent(agentId.toString())
        : await disableAgent(agentId.toString());

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

  const handleDeleteAgent = async (agentId: number) => {
    if (!window.confirm("Are you sure you want to delete this agent?")) {
      return;
    }

    try {
      setLoading(true);
      await deleteAgent(agentId.toString());
      fetchAgents(); // Refresh the list
    } catch (err: any) {
      console.error("Error deleting agent:", err);
      setError(err.message || "Failed to delete agent");
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
          <h2 className="text-2xl font-bold text-[#140d0c]">
            Agent Configuration
          </h2>
          <button
            onClick={() => navigate("/admin/agents/new")}
            className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors flex items-center gap-1"
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
                d="M12 4v16m8-8H4"
              />
            </svg>
            Add New Agent
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm mb-4">
            {error}
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
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      agent.is_outbound
                        ? "bg-blue-100 text-blue-800"
                        : "bg-purple-100 text-purple-800"
                    }`}
                  >
                    {agent.is_outbound ? "Outbound" : "Inbound"}
                  </span>
                  <button
                    onClick={() => handleToggleAgent(agent.id, !agent.enabled)}
                    className={`px-2 py-1 text-xs rounded-full ${
                      agent.enabled
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {agent.enabled ? "Enabled" : "Disabled"}
                  </button>
                </div>
              </div>

              <p className="text-[#6c6c6c] mb-4">{agent.description}</p>

              <div className="text-xs text-[#6c6c6c] mb-4">
                <p>ID: {agent.id}</p>
                <p>Type: {agent.agent_type}</p>
                {agent.tags && agent.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {agent.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end space-x-2 mt-auto pt-4 border-t border-[#e7e2d3]">
                <button
                  onClick={() => navigate(`/admin/agents/${agent.id}`)}
                  className="px-3 py-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors text-sm flex items-center gap-1"
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
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                    />
                  </svg>
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteAgent(agent.id)}
                  className="px-3 py-1.5 bg-red-500 text-white rounded hover:bg-red-600 transition-colors text-sm flex items-center gap-1"
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
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AgentConfiguration;
