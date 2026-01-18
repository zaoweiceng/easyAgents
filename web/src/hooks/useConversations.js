/**
 * useConversations Hook
 * 管理历史对话记录
 */
import { useState, useEffect, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useConversations = () => {
  const [conversations, setConversations] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * 获取所有会话列表
   */
  const fetchConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/conversations`);
      if (!response.ok) {
        throw new Error('获取会话列表失败');
      }

      const data = await response.json();
      setConversations(data.conversations);
    } catch (err) {
      setError(err.message);
      console.error('获取会话列表失败:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * 创建新会话
   */
  const createConversation = useCallback(async (title, modelName = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title,
          model_name: modelName,
        }),
      });

      if (!response.ok) {
        throw new Error('创建会话失败');
      }

      const data = await response.json();
      const newConv = data.data.conversation;

      setConversations((prev) => [newConv, ...prev]);
      setCurrentSessionId(newConv.session_id);

      return newConv.session_id;
    } catch (err) {
      console.error('创建会话失败:', err);
      throw err;
    }
  }, []);

  /**
   * 获取会话详情（包括消息）
   */
  const fetchConversationDetail = useCallback(async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${sessionId}`);

      if (!response.ok) {
        throw new Error('获取会话详情失败');
      }

      const data = await response.json();
      return data.data;
    } catch (err) {
      console.error('获取会话详情失败:', err);
      throw err;
    }
  }, []);

  /**
   * 删除会话
   */
  const deleteConversation = useCallback(async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${sessionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('删除会话失败');
      }

      setConversations((prev) =>
        prev.filter((conv) => conv.session_id !== sessionId)
      );

      // 如果删除的是当前会话，清空当前会话ID
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }
    } catch (err) {
      console.error('删除会话失败:', err);
      throw err;
    }
  }, [currentSessionId]);

  /**
   * 更新会话标题
   */
  const updateConversationTitle = useCallback(async (sessionId, title) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/conversations/${sessionId}/title`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ title }),
        }
      );

      if (!response.ok) {
        throw new Error('更新标题失败');
      }

      setConversations((prev) =>
        prev.map((conv) =>
          conv.session_id === sessionId
            ? { ...conv, title }
            : conv
        )
      );
    } catch (err) {
      console.error('更新标题失败:', err);
      throw err;
    }
  }, []);

  /**
   * 搜索会话
   */
  const searchConversations = useCallback(async (query) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/conversations/search/${encodeURIComponent(query)}`
      );

      if (!response.ok) {
        throw new Error('搜索失败');
      }

      const data = await response.json();
      return data.conversations;
    } catch (err) {
      console.error('搜索失败:', err);
      return [];
    }
  }, []);

  /**
   * 导出会话
   * @param {string} sessionId - 会话ID
   * @param {string} format - 导出格式: 'json' 或 'pdf' (默认: 'json')
   */
  const exportConversation = useCallback(async (sessionId, format = 'json') => {
    try {
      const endpoint = format === 'pdf'
        ? `${API_BASE_URL}/conversations/${sessionId}/export/pdf`
        : `${API_BASE_URL}/conversations/${sessionId}/export`;

      const response = await fetch(endpoint);

      if (!response.ok) {
        throw new Error('导出失败');
      }

      if (format === 'pdf') {
        // PDF格式：直接下载二进制文件
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation-${sessionId}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        // JSON格式：解析后再下载
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversation-${sessionId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('导出失败:', err);
      throw err;
    }
  }, []);

  // 初始化时加载会话列表
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  return {
    conversations,
    setConversations,
    currentSessionId,
    isLoading,
    error,
    setCurrentSessionId,
    fetchConversations,
    createConversation,
    fetchConversationDetail,
    deleteConversation,
    updateConversationTitle,
    searchConversations,
    exportConversation,
  };
};
