import { createAgent, updateAgent, AgentDetail } from "../services/api";

/**
 * Creates a new agent with the given agent data
 * @param agentData - The agent data to create
 * @returns A promise that resolves when the agent is created
 */
export const createNewAgent = async (
  agentData: Partial<AgentDetail>
): Promise<AgentDetail> => {
  console.log("Creating new agent:", agentData);

  // Ensure the API path is set correctly and remove any id field
  const agentToSave = {
    agent_type: agentData.agent_type || "",
    name: agentData.name || "",
    description: agentData.description || "",
    startup_message:
      agentData.startup_message ||
      "<speak>Welcome to our service. How may I help you today?</speak>",
    system_prompt: agentData.system_prompt || "You are a helpful assistant...",
    enabled: agentData.enabled !== undefined ? agentData.enabled : true,
    voice_name: agentData.voice_name || "en-IN-Wavenet-E",
    can_interrupt: agentData.can_interrupt || false,
    is_outbound: agentData.is_outbound || false,
    languages: {
      primary: agentData.languages?.primary || "en-IN",
      supported: agentData.languages?.supported || ["en-IN"],
    },
    speech_context: agentData.speech_context || [],
    limitations: agentData.limitations || [],
    llm_model_id: agentData.llm_model_id,
    temperature: agentData.temperature || 0.7,
    error_messages: {
      error:
        agentData.error_messages?.error ||
        "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I apologize, I couldn't understand. Please try again.</prosody></speak>",
      unclear_audio:
        agentData.error_messages?.unclear_audio ||
        "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I couldn't hear you clearly. Could you please repeat?</prosody></speak>",
      unsupported_language:
        agentData.error_messages?.unsupported_language ||
        "<speak xml:lang='en-IN'><prosody rate='medium' pitch='0%'>I'm sorry, but that language isn't supported. Please try another language.</prosody></speak>",
    },
    tags: agentData.tags || [],
  };

  try {
    const result = await createAgent(agentToSave as AgentDetail);
    return result;
  } catch (error: any) {
    console.error("Agent creation failed:", error);
    console.error("Error details:", error.response?.data || error.message);
    throw error;
  }
};

/**
 * Updates an existing agent with the given ID and agent data
 * @param agentId - The ID of the agent to update
 * @param agentData - The updated agent data
 * @returns A promise that resolves when the agent is updated
 */
export const updateExistingAgent = async (
  agentId: string,
  agentData: Partial<AgentDetail>
): Promise<AgentDetail> => {
  console.log("Updating agent:", agentData);

  try {
    const result = await updateAgent(agentId, agentData);
    return result;
  } catch (error: any) {
    console.error("Agent update failed:", error);
    console.error("Error details:", error.response?.data || error.message);
    throw error;
  }
};
