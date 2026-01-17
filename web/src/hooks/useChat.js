/**
 * useChat Hook
 * 管理聊天状态和逻辑
 */

import { useState, useCallback, useRef } from 'react';
import { flushSync } from 'react-dom';
import { chatSync, chatStream } from '../services/api';

// 辅助函数：从JSON对象中提取agent名称
function extractAgentName(jsonObj) {
  // 尝试从不同字段提取agent名称
  if (jsonObj.agent_name) return jsonObj.agent_name;
  if (jsonObj.next_agent && jsonObj.next_agent !== 'none') return jsonObj.next_agent;
  if (jsonObj.data && jsonObj.data.sql) return 'sql_agent';
  if (jsonObj.data && jsonObj.data.answer) return 'general_agent';
  return 'unknown_agent';
}

export const useChat = (initialSessionId = null) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(initialSessionId);
  const currentMessageRef = useRef(null);  // 引用当前正在累积的消息对象
  const thinkingStepsRef = useRef([]);  // 使用ref来始终获取最新的thinking steps

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
      const response = await chatSync(query, sessionId);

      // 更新session_id（如果后端返回了新的）
      if (response.session_id) {
        setSessionId(response.session_id);
      }

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
  }, [sessionId]);

  /**
   * 发送消息（流式模式）
   */
  const sendStreamMessage = useCallback(async (query) => {
    setIsLoading(true);
    setError(null);
    setCurrentAgent(null);
    thinkingStepsRef.current = [];  // 重置思考步骤

    // 用于累积general_agent的原始JSON内容
    const rawContentRef = { current: '' };

    // 添加用户消息
    const userMessage = { role: 'user', content: query };
    setMessages((prev) => {
      const newMessages = [...prev, userMessage];

      // 创建一个空的助手消息来累积流式内容
      const assistantMessage = {
        role: 'assistant',
        content: '',
        thinkingSteps: [],
        isThinkingComplete: false
      };
      currentMessageRef.current = assistantMessage;  // 保存引用到ref

      return [...newMessages, assistantMessage];
    });

    try {
      await chatStream(
        query,
        {
          onDelta: (data) => {
            // 只对最终输出（general_agent）的内容应用打字机效果
            if (data.content && typeof data.content === 'string') {
              if (data.is_final_output && currentMessageRef.current) {
                // 累积原始JSON内容
                rawContentRef.current += data.content;

                // 尝试从累积的内容中提取answer字段
                try {
                  const content = rawContentRef.current;

                  // 查找 "answer": 后面的内容
                  const answerKeyIndex = content.indexOf('"answer"');
                  if (answerKeyIndex !== -1) {
                    // 找到 "answer": 后面的冒号
                    const colonIndex = content.indexOf(':', answerKeyIndex);
                    if (colonIndex !== -1) {
                      // 找到answer值的开始引号
                      const firstQuoteIndex = content.indexOf('"', colonIndex);
                      if (firstQuoteIndex !== -1) {
                        // 从第一个引号后开始，提取内容直到遇到未转义的引号
                        let answerText = '';
                        let i = firstQuoteIndex + 1;
                        let inEscape = false;

                        while (i < content.length) {
                          const char = content[i];

                          if (inEscape) {
                            // 处理转义字符
                            if (char === 'n') {
                              answerText += '\n';
                            } else if (char === 't') {
                              answerText += '\t';
                            } else if (char === 'r') {
                              answerText += '\r';
                            } else if (char === '\\') {
                              answerText += '\\';
                            } else if (char === '"') {
                              answerText += '"';
                            } else {
                              answerText += char;
                            }
                            inEscape = false;
                          } else if (char === '\\') {
                            // 遇到转义符号
                            inEscape = true;
                          } else if (char === '"') {
                            // 遇到结束引号
                            break;
                          } else {
                            // 普通字符
                            answerText += char;
                          }
                          i++;
                        }

                        // 如果提取到了内容，更新显示
                        if (answerText || currentMessageRef.current.content) {
                          currentMessageRef.current.content = answerText;

                          flushSync(() => {
                            setMessages((prev) => [...prev]);
                          });
                        }
                      }
                    }
                  }
                } catch (e) {
                  // 解析失败，继续累积
                  console.debug('JSON解析中...', e.message);
                }
              }
              // 如果不是最终输出，忽略（这是思考过程，不显示）
            }
          },
          onAgentStart: (data) => {
            // 添加到思考步骤
            const step = {
              agent_name: data.agent_name,
              reason: null,  // 稍后更新
              task: null
            };
            thinkingStepsRef.current.push(step);

            // 更新消息的thinkingSteps
            if (currentMessageRef.current) {
              currentMessageRef.current.thinkingSteps = [...thinkingStepsRef.current];

              flushSync(() => {
                setMessages((prev) => [...prev]);
                setCurrentAgent(data);
              });
            }
          },
          onAgentEnd: (data) => {
            // 更新最后一个thinking step的reason和task
            const lastStep = thinkingStepsRef.current[thinkingStepsRef.current.length - 1];
            if (lastStep && lastStep.agent_name === data.agent_name) {
              if (data.agent_selection_reason) {
                lastStep.reason = data.agent_selection_reason;
              }
              if (data.task_list && data.task_list.length > 0) {
                lastStep.task = data.task_list[0];
              }

              // 更新消息的thinkingSteps
              if (currentMessageRef.current) {
                currentMessageRef.current.thinkingSteps = [...thinkingStepsRef.current];

                flushSync(() => {
                  setMessages((prev) => [...prev]);
                });
              }
            }
          },
          onMessage: (data) => {
            // onMessage收到的是完整的Message对象
            if (data.message) {
              const message = data.message;

              // 更新最后一个思考步骤的原因和任务
              const lastStep = thinkingStepsRef.current[thinkingStepsRef.current.length - 1];
              if (lastStep) {
                if (message.agent_selection_reason) {
                  lastStep.reason = message.agent_selection_reason;
                }
                if (message.task_list && message.task_list.length > 0) {
                  lastStep.task = message.task_list[0];
                }

                // 更新消息的thinkingSteps
                if (currentMessageRef.current) {
                  currentMessageRef.current.thinkingSteps = [...thinkingStepsRef.current];

                  flushSync(() => {
                    setMessages((prev) => [...prev]);
                  });
                }
              }
            }
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
            if (currentMessageRef.current) {
              currentMessageRef.current.isThinkingComplete = true;
            }
            // 不立即清空agent状态，让用户看到完整的agent信息
          },
        },
        sessionId
      );
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  }, [sessionId]);

  /**
   * 清空聊天历史
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setCurrentAgent(null);
    thinkingStepsRef.current = [];
    currentMessageRef.current = null;
  }, []);

  /**
   * 加载会话历史
   */
  const loadConversation = useCallback(async (sessionId) => {
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/conversations/${sessionId}`);

      if (!response.ok) {
        throw new Error('加载会话失败');
      }

      const data = await response.json();
      const conversationData = data.data;

      // 转换消息格式
      const formattedMessages = conversationData.messages.map((msg) => {
        let content = msg.content;
        let thinkingSteps = [];

        // 如果是assistant消息，尝试解析JSON并提取answer
        if (msg.role === 'assistant' && content) {
          try {
            // 尝试找到所有JSON对象（可能包含多个）
            const jsonMatches = content.match(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g) || [];

            if (jsonMatches.length > 0) {
              // 解析所有JSON对象
              const jsonObjects = jsonMatches.map(match => {
                try {
                  return JSON.parse(match);
                } catch (e) {
                  return null;
                }
              }).filter(obj => obj !== null);

              // 从最后一个JSON对象（通常是general_agent的响应）提取answer
              const lastJson = jsonObjects[jsonObjects.length - 1];
              if (lastJson && lastJson.data && lastJson.data.answer) {
                content = lastJson.data.answer;
              }

              // 从所有JSON对象构建thinkingSteps
              thinkingSteps = jsonObjects.map((jsonObj, index) => {
                // 跳过entrance_agent（通常是第一个）
                if (index === 0 && jsonObj.next_agent && jsonObj.next_agent !== 'none') {
                  return null; // 跳过entrance_agent的响应
                }

                // 只处理有实际工作的agent
                if (jsonObj.agent_selection_reason || jsonObj.data) {
                  return {
                    agent_name: extractAgentName(jsonObj),
                    reason: jsonObj.agent_selection_reason || null,
                    task: (jsonObj.task_list && jsonObj.task_list.length > 0) ? jsonObj.task_list[0] : null
                  };
                }
                return null;
              }).filter(step => step !== null);
            }
          } catch (e) {
            console.error('解析历史消息JSON失败:', e);
            // 如果解析失败，保持原样
          }
        }

        return {
          role: msg.role,
          content: content,
          data: msg.data,
          events: msg.events,
          thinkingSteps: thinkingSteps,
          isThinkingComplete: true, // 历史消息总是完成状态
        };
      });

      setMessages(formattedMessages);
      setSessionId(sessionId);
    } catch (err) {
      setError(err.message);
      console.error('加载会话失败:', err);
    }
  }, []);

  /**
   * 设置当前会话ID
   */
  const setSessionIdFromOutside = useCallback((newSessionId) => {
    setSessionId(newSessionId);
  }, []);

  return {
    messages,
    isLoading,
    currentAgent,
    error,
    sessionId,
    sendSyncMessage,
    sendStreamMessage,
    clearMessages,
    loadConversation,
    setSessionId: setSessionIdFromOutside,
  };
};
