import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AgentSelector from "./AgentSelector";
import AudioAgent from "./AudioAgent";
import AnimatedLogo from "../Common/AnimatedLogo";
import { fetchAgentList } from "../../services/api";
import "./VoiceAgent.css";

interface Agent {
  id: string;
  name: string;
  description: string;
  api_path: string;
}

const VoiceAgentPage: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [agentDetails, setAgentDetails] = useState<Agent | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const navigate = useNavigate();
  const { agentId } = useParams<{ agentId: string }>();

  useEffect(() => {
    const fetchAgent = async () => {
      if (agentId) {
        try {
          const response = await fetchAgentList();
          const agents =
            response && Array.isArray(response)
              ? response
              : response && response.agents
              ? Object.values(response.agents)
              : [];
          const agent = agents.find((a: Agent) => a.id === agentId);
          if (agent) {
            setAgentDetails(agent);
            setSelectedAgent(agentId);
          } else {
            // If agent not found, redirect to home
            navigate("/");
          }
        } catch (error) {
          console.error("Error fetching agent details:", error);
          navigate("/");
        }
      } else {
        setSelectedAgent(null);
        setAgentDetails(null);
      }
    };
    fetchAgent();
  }, [agentId, navigate]);

  const handleBackToSelection = () => {
    setSelectedAgent(null);
    setAgentDetails(null);
    setIsConnected(false);
    navigate("/");
  };

  const handleConnectionChange = (connected: boolean) => {
    setIsConnected(connected);
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-5xl">
      <header className="page-header mb-8">
        {!selectedAgent && (
          <div className="flex items-center justify-center mb-6">
            <AnimatedLogo
              gifSrc="/assets/caw-tech-logo.svg"
              fallbackSrc="/assets/caw-tech-logo.svg"
              alt="CAW Tech Logo"
              height={100}
              width={100}
              className="object-contain cursor-pointer"
              onClick={handleBackToSelection}
            />
          </div>
        )}
        <h1 className="page-title text-[#140d0c] text-center text-3xl font-semibold">
          Voice Agent Portal
          {agentDetails && isConnected && (
            <span className="block text-lg mt-2 text-[#6c6c6c]">
              Connected to: {agentDetails.name}
            </span>
          )}
        </h1>
        {!selectedAgent && (
          <p className="mt-2 text-muted-foreground text-center text-[#6c6c6c]">
            Talk to our AI voice agents using your microphone. Choose an agent
            below to start a conversation.
          </p>
        )}
      </header>

      {!selectedAgent ? (
        <div className="bg-[#f8f7f3] rounded-3xl shadow-lg p-8">
          <AgentSelector />
        </div>
      ) : (
        <div className="bg-[#1a1310] border border-[#382e1e] rounded-3xl p-8 shadow-lg">
          <AudioAgent
            agentId={selectedAgent}
            apiPath={agentDetails?.api_path || ""}
            onBackToSelection={handleBackToSelection}
            onConnectionChange={handleConnectionChange}
          />
        </div>
      )}
    </div>
  );
};

export default VoiceAgentPage;
