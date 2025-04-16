import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import AgentSelector from "./AgentSelector";
import AudioAgent from "./AudioAgent";
import AnimatedLogo from "../Common/AnimatedLogo";
import { fetchAgentList } from "../../services/api";
import { API_BASE_URL } from "../../config/api";
import "./VoiceAgent.css";
import { IoArrowBack } from "react-icons/io5";
import { IconWrapper } from "./IconWrapper";
import { accessVoiceAgent } from "../../services/api";
import { getLanguageName } from "../../utils/languageUtils";

interface Agent {
  id: string;
  name: string;
  description: string;
  api_path: string;
  is_outbound: boolean;
  primary_language: string;
  tags: string[];
  auth_required: boolean;
  auth_type: string;
  connection_type: string;
}

interface AgentAccessInfo {
  is_outbound: boolean;
  limitations: string[];
  primary_language: string;
  supported_languages: string[];
}

const VoiceAgentPage: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [agentDetails, setAgentDetails] = useState<Agent | null>(null);
  const [agentAccessInfo, setAgentAccessInfo] =
    useState<AgentAccessInfo | null>(null);
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
              ? response.agents
              : [];
          const agent = agents.find((a: Agent) => a.id === agentId);
          if (agent) {
            setAgentDetails(agent);
            setSelectedAgent(agentId);

            // Get agent access info on initial load
            try {
              const accessResponse = await accessVoiceAgent(agentId);
              if (accessResponse.success && accessResponse.agent_info) {
                setAgentAccessInfo(accessResponse.agent_info);
              } else {
                throw new Error(
                  accessResponse.error || "Failed to get agent info"
                );
              }
            } catch (error) {
              console.error("Error fetching agent access info:", error);
            }
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
        setAgentAccessInfo(null);
      }
    };
    fetchAgent();
  }, [agentId, navigate]);

  const handleBackToSelection = () => {
    setSelectedAgent(null);
    setAgentDetails(null);
    setAgentAccessInfo(null);
    setIsConnected(false);
    navigate("/");
  };

  const handleConnectionChange = (connected: boolean) => {
    setIsConnected(connected);
  };

  const handleAgentAccessInfo = (accessInfo: AgentAccessInfo) => {
    setAgentAccessInfo(accessInfo);
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
          <AgentSelector onAgentAccessGranted={handleAgentAccessInfo} />
        </div>
      ) : (
        <div className="bg-[#1a1310] border border-[#382e1e] rounded-3xl p-8 shadow-lg">
          <button
            className="text-[#ffcc33] hover:text-[#ffcc33]/80 flex items-center gap-2 transition-colors mb-6 ml-4"
            onClick={handleBackToSelection}
          >
            <IconWrapper icon={IoArrowBack} />
            Back to Agents
          </button>

          <AudioAgent
            agentId={selectedAgent}
            apiPath={agentDetails?.api_path || ""}
            onBackToSelection={handleBackToSelection}
            onConnectionChange={handleConnectionChange}
          />

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Limitations */}
            {agentAccessInfo && (
              <div className="bg-[#2a2320] rounded-lg border border-[#382e1e] p-4">
                <h3 className="text-[#e7e2d3] font-medium text-lg mb-3">
                  Current limitations
                </h3>
                {agentAccessInfo.limitations.length > 0 ? (
                  <ul className="space-y-2">
                    {agentAccessInfo.limitations.map((limitation, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-[#ffcc33] text-lg leading-none">
                          •
                        </span>
                        <span className="text-[#a39e8f] -mt-1">
                          {limitation}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[#a39e8f] italic">
                    No limitations specified
                  </p>
                )}
              </div>
            )}

            {/* Instructions */}
            <div className="bg-[#2a2320] rounded-lg border border-[#382e1e] p-4">
              <h3 className="text-[#e7e2d3] font-medium text-lg mb-3">
                Important Instructions
              </h3>
              <ul className="space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-[#ffcc33] text-lg leading-none">•</span>
                  <span className="text-[#a39e8f] -mt-1">
                    Please mute yourself when not talking to prevent echo and
                    feedback.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#ffcc33] text-lg leading-none">•</span>
                  <span className="text-[#a39e8f] -mt-1">
                    This feature is still in development and may not provide the
                    most accurate results.
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#ffcc33] text-lg leading-none">•</span>
                  <span className="text-[#a39e8f] -mt-1">
                    For best results, speak clearly and in a quiet environment.
                  </span>
                </li>
              </ul>
              <p className="mt-3 text-sm">
                <span className="text-[#a39e8f]">
                  For any feedback, please contact us at{" "}
                </span>
                <a
                  href="mailto:hello@caw.tech"
                  className="text-[#ffcc33] hover:underline"
                >
                  hello@caw.tech
                </a>
              </p>
            </div>

            {/* Agent Info - Full Width Below */}
            {agentAccessInfo && (
              <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Agent Type */}
                <div className="bg-[#2a2320] rounded-lg border border-[#382e1e] p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[#a39e8f] text-sm">Agent Type:</span>
                    <span
                      className={`px-3 py-1 rounded-full text-sm ${
                        agentAccessInfo.is_outbound
                          ? "bg-blue-900/50 text-blue-200"
                          : "bg-purple-900/50 text-purple-200"
                      }`}
                    >
                      {agentAccessInfo.is_outbound ? "Outbound" : "Inbound"}
                    </span>
                  </div>
                </div>

                {/* Languages */}
                <div className="bg-[#2a2320] rounded-lg border border-[#382e1e] p-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[#a39e8f] text-sm">
                        Main Language:
                      </span>
                      <span className="text-[#e7e2d3] text-sm px-2 py-0.5 bg-[#382e1e] rounded">
                        {getLanguageName(agentAccessInfo.primary_language)}
                      </span>
                    </div>
                    <div>
                      <div className="flex flex-wrap gap-1.5 justify-between">
                        <span className="text-[#a39e8f] text-sm">
                          Also speaks:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {agentAccessInfo.supported_languages
                            .filter(
                              (lang) =>
                                lang !== agentAccessInfo.primary_language
                            )
                            .map((lang, index) => (
                              <span
                                key={index}
                                className="text-[#a39e8f] text-xs px-2 py-0.5 bg-[#382e1e] rounded"
                              >
                                {getLanguageName(lang)}
                              </span>
                            ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceAgentPage;
