/**
 * useAgents Hook
 * 管理Agent列表和详情
 */

import { useState, useEffect, useCallback } from 'react';
import { getAgents, getAgent, reloadAgents } from '../services/api';

export const useAgents = () => {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isReloading, setIsReloading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

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
   * 重载Agent插件（热插拔）
   */
  const reloadAgentsPlugin = useCallback(async () => {
    setIsReloading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await reloadAgents();

      // 显示成功消息
      setSuccessMessage(response.message);

      // 重新加载Agent列表
      await loadAgents();

      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsReloading(false);
    }
  }, [loadAgents]);

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
    isReloading,
    error,
    successMessage,
    loadAgents,
    loadAgentDetail,
    reloadAgentsPlugin,
    setSelectedAgent,
    setSuccessMessage,
  };
};
