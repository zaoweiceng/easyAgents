/**
 * useChat Hook
 * 管理聊天状态和逻辑
 */

import { useState, useCallback } from 'react';
import { chatSync, chatStream } from '../services/api';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [streamContent, setStreamContent] = useState('');
  const [error, setError] = useState(null);

  /**
   * 发送消息（同步模式）
   */
  const sendSyncMessage = useCallback(async (query) => {
    setIsLoading(true);
    setError(null);
    setStreamContent('');

    // 添加用户消息
    const userMessage = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await chatSync(query);

      // 处理响应
      const responseMessages = response.response || [];
      const formattedMessages = responseMessages.map((msg) => ({
        role: msg.role,
        content: msg.content || msg.message || '',
        data: msg.data,
      }));

      setMessages((prev) => [...prev, ...formattedMessages]);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        { role: 'error', content: `错误: ${err.message}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * 发送消息（流式模式）
   */
  const sendStreamMessage = useCallback(async (query) => {
    setIsLoading(true);
    setError(null);
    setStreamContent('');
    setCurrentAgent(null);

    // 添加用户消息
    const userMessage = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMessage]);

    // 创建一个空的助手消息来累积流式内容
    let assistantMessage = { role: 'assistant', content: '', events: [] };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      await chatStream(
        query,
        {
          onDelta: (data) => {
            setStreamContent((prev) => prev + (data.content || ''));
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                lastMessage.content += data.content || '';
              }
              return newMessages;
            });
          },
          onAgentStart: (data) => {
            setCurrentAgent(data);
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                lastMessage.events = lastMessage.events || [];
                lastMessage.events.push({
                  type: 'agent_start',
                  data,
                });
              }
              return newMessages;
            });
          },
          onAgentEnd: (data) => {
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                lastMessage.events = lastMessage.events || [];
                lastMessage.events.push({
                  type: 'agent_end',
                  data,
                });
              }
              return newMessages;
            });
          },
          onMessage: (data) => {
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage && lastMessage.role === 'assistant') {
                lastMessage.data = data.message;
              }
              return newMessages;
            });
          },
          onError: (data) => {
            setError(data.error_message);
            setMessages((prev) => [
              ...prev,
              { role: 'error', content: `错误: ${data.error_message}` },
            ]);
          },
          onDone: () => {
            setIsLoading(false);
            setCurrentAgent(null);
            setStreamContent('');
          },
        },
        null
      );
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  }, []);

  /**
   * 清空聊天历史
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setStreamContent('');
    setCurrentAgent(null);
  }, []);

  return {
    messages,
    isLoading,
    currentAgent,
    streamContent,
    error,
    sendSyncMessage,
    sendStreamMessage,
    clearMessages,
  };
};
