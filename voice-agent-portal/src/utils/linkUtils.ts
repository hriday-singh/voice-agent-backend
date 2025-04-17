/**
 * Utility functions for generating direct agent navigation links
 */

/**
 * Generates a direct link to a specific agent that will redirect users after login
 *
 * @param agentId - The ID of the agent to navigate to after login
 * @param baseUrl - Optional base URL for the link (defaults to current origin)
 * @returns A complete URL for direct agent navigation
 */
export const generateDirectAgentLink = (
  agentId: string,
  baseUrl?: string
): string => {
  // Use the provided baseUrl or default to current origin
  const base = baseUrl || window.location.origin;
  return `${base}/login?agent=${encodeURIComponent(agentId)}`;
};

/**
 * Checks if a URL contains an agent redirect parameter
 *
 * @param url - The URL to check
 * @returns The agent ID if present, null otherwise
 */
export const getAgentFromUrl = (url: string): string | null => {
  try {
    const urlObj = new URL(url);
    return urlObj.searchParams.get("agent");
  } catch (error) {
    return null;
  }
};
