import React, { useState, useEffect } from "react";
import { AGENT_ENDPOINTS } from "../../config/api";
import api from "../../services/api";
import { HiOutlineChat } from "react-icons/hi";
import { IconWrapper } from "./IconWrapper";
import { useNavigate } from "react-router-dom";
import AnimatedLogo from "../Common/AnimatedLogo";

interface Agent {
  id: string;
  name: string;
  description: string;
  api_path: string;
}

const AgentSelector: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        setLoading(true);
        const response = await api.get(AGENT_ENDPOINTS.LIST);
        const agentsData =
          response.data && Array.isArray(response.data)
            ? response.data
            : response.data && response.data.agents
            ? Object.values(response.data.agents)
            : [];

        setAgents(agentsData);
        setLoading(false);
      } catch (err: any) {
        setError("Credits exhausted. Please contact hello@caw.tech");
        setLoading(false);
      }
    };

    fetchAgents();
  }, []);

  const handleAgentSelect = async (agent: Agent) => {
    try {
      await api.post(AGENT_ENDPOINTS.ACCESS, {
        agent_type: agent.id,
      });
      // Navigate to the agent page
      navigate(`/agent/${agent.id}`);
    } catch (err: any) {
      setError("Credits exhausted. Please contact hello@caw.tech");
    }
  };

  // Demo agents if no real agents are available
  const demoAgents: Agent[] = [
    {
      id: "general",
      name: "General Assistant",
      description:
        "A general-purpose voice assistant that can answer a wide range of questions and perform various tasks.",
      api_path: "/agents/general",
    },
    {
      id: "customer-service",
      name: "Customer Service",
      description:
        "Specialized in handling customer inquiries, complaints, and providing product information.",
      api_path: "/agents/customer-service",
    },
  ];

  // Use demo agents if none available
  const agentsToDisplay = agents.length === 0 ? demoAgents : agents;

  return (
    <div className="min-h-screen bg-[#f8f7f3] py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-[#140d0c] mb-8 text-center">
          Select Your Voice Assistant
        </h1>
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {loading ? (
            <div className="col-span-2 flex justify-center items-center py-12">
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
          ) : error ? (
            <div className="col-span-2 flex justify-center items-center py-12">
              <div className="bg-red-50 border border-red-200 text-red-600 rounded-md p-6 text-center max-w-md w-full mx-4">
                <div className="mb-4">{error}</div>
                <a
                  href="mailto:hello@caw.tech"
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                >
                  Contact Support
                </a>
              </div>
            </div>
          ) : (
            agentsToDisplay.map((agent) => (
              <div
                key={agent.id}
                className="bg-white rounded-lg shadow-md p-6 flex flex-col h-[300px] border border-[#e7e2d3] hover:shadow-lg transition-all duration-300"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-[#ffcc33]/20 flex items-center justify-center text-[#ffcc33]">
                    <IconWrapper icon={HiOutlineChat} size={20} />
                  </div>
                  <h3 className="text-lg font-medium text-[#140d0c]">
                    {agent.name}
                  </h3>
                </div>

                <p className="text-[#6c6c6c] mb-6 flex-grow line-clamp-4">
                  {agent.description}
                </p>

                <div className="flex justify-between items-center mt-auto pt-4 border-t border-[#e7e2d3]">
                  <span className="text-xs font-medium text-[#6c6c6c] px-2 py-1 bg-[#f2efe3] rounded-full">
                    {agent.id}
                  </span>
                  <button
                    onClick={() => handleAgentSelect(agent)}
                    className="px-4 py-2 bg-[#ffcc33] text-[#140d0c] rounded hover:bg-[#ffcc33]/90 transition-colors font-medium"
                  >
                    Start Chat
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentSelector;
