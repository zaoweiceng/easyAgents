/**
 * useAgents Hook
 * 管理Agent列表和详情
 */

import { useState, useEffect, useCallback } from 'react';
import { getAgents, getAgent } from '../services/api';

export const useAgents = () => {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * 加载所有Agent
   */
  const loadAgents = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getAgents();
      setAgents(response.agents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * 加载特定Agent详情
   */
  const loadAgentDetail = useCallback(async (agentName) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getAgent(agentName);
      setSelectedAgent(response.agent);
      return response.agent;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * 初始化时加载Agent列表
   */
  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  return {
    agents,
    selectedAgent,
    isLoading,
    error,
    loadAgents,
    loadAgentDetail,
    setSelectedAgent,
  };
};
