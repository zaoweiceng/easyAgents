/**
 * useChat Hook
 * 管理聊天状态和逻辑
 */

import { useState, useCallback, useRef } from 'react';
import { flushSync } from 'react-dom';
import { chatSync, chatStream, chatStreamResume, deleteMessage as deleteMessageApi } from '../services/api';

// 辅助函数：从JSON对象中提取agent名称
function extractAgentName(jsonObj) {
  // 尝试从不同字段提取agent名称
  if (jsonObj.agent_name) return jsonObj.agent_name;
  if (jsonObj.next_agent && jsonObj.next_agent !== 'none') return jsonObj.next_agent;
  if (jsonObj.data && jsonObj.data.sql) return 'sql_agent';
  if (jsonObj.data && jsonObj.data.answer) return 'general_agent';
  return 'unknown_agent';
}

export const useChat = (initialSessionId = null, settings = null) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(initialSessionId);
  const [isPaused, setIsPaused] = useState(false);  // 标记是否处于暂停状态
  const currentMessageRef = useRef(null);  // 引用当前正在累积的消息对象
  const thinkingStepsRef = useRef([]);  // 使用ref来始终获取最新的thinking steps
  const [titleUpdate, setTitleUpdate] = useState(null);  // 保存标题更新信息

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
      const formattedMessages = responseMessages.map((msg) => {
        // 如果消息包含 form_config，不显示 content（因为它是 JSON 格式）
        const hasFormConfig = msg.data && msg.data.form_config;

        return {
          role: msg.role,
          content: hasFormConfig ? '' : (msg.content || msg.message || ''),
          data: msg.data,
          thinkingSteps: [],
          isThinkingComplete: true
        };
      });

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
    setIsPaused(false);  // 重置暂停状态
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

                // 更新消息的thinkingSteps 和 data
                if (currentMessageRef.current) {
                  currentMessageRef.current.thinkingSteps = [...thinkingStepsRef.current];

                  // 处理包含 form_config 的消息
                  const hasFormConfig = message.data && message.data.form_config;
                  if (hasFormConfig) {
                    // 如果包含表单，清空 content（避免显示 JSON），设置 data
                    currentMessageRef.current.content = '';
                    currentMessageRef.current.data = message.data;
                  } else if (message.data && message.data.answer) {
                    // 如果是最终答案，提取并显示
                    currentMessageRef.current.data = message.data;
                  }

                  flushSync(() => {
                    setMessages((prev) => [...prev]);
                  });
                }
              }
            }
          },
          onPause: (data) => {
            // 处理暂停事件
            console.log('收到暂停事件:', data);
            setIsPaused(true);
            setIsLoading(false);
            if (currentMessageRef.current) {
              currentMessageRef.current.isThinkingComplete = true;
              currentMessageRef.current.pausedContext = data;  // 保存暂停上下文

              // 从暂停上下文中提取表单配置
              // 暂停上下文中包含了整个 context，我们需要找到最后一条包含 form_config 的消息
              if (data.context && data.context.length > 0) {
                for (let i = data.context.length - 1; i >= 0; i--) {
                  const msg = data.context[i];
                  if (msg.data && msg.data.form_config) {
                    currentMessageRef.current.data = msg.data;
                    break;
                  }
                }
              }
            }
          },
          onMetadata: (data) => {
            // 处理元数据，包括 session_id
            if (data.session_id && !sessionId) {
              console.log('收到 session_id:', data.session_id);
              setSessionId(data.session_id);
            }
            // 处理标题更新
            if (data.title_updated && data.new_title) {
              console.log('收到标题更新:', data.new_title);
              setTitleUpdate({
                sessionId: data.session_id,
                newTitle: data.new_title
              });
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
        sessionId,
        settings?.llmParams
      );
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  }, [sessionId]);

  /**
   * 提交表单并恢复执行（从暂停点继续）
   */
  const submitFormAndResume = useCallback(async (formData) => {
    if (!sessionId) {
      setError('无法恢复执行：缺少会话ID');
      return;
    }

    setIsLoading(true);
    setError(null);
    setIsPaused(false);  // 重置暂停状态

    // 用于累积general_agent的原始JSON内容
    const rawContentRef = { current: '' };

    // 不添加新的用户消息，直接继续当前消息
    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (lastMessage && lastMessage.role === 'assistant') {
        // 标记表单为已提交，继续更新当前消息
        const updatedMessage = {
          ...lastMessage,
          isFormSubmitted: true,
          isThinkingComplete: false  // 继续思考
        };
        currentMessageRef.current = updatedMessage;
        return [...prev.slice(0, -1), updatedMessage];
      }
      return prev;
    });

    try {
      await chatStreamResume(
        JSON.stringify(formData),
        {
          onDelta: (data) => {
            // 与 sendStreamMessage 相同的处理逻辑
            if (data.content && typeof data.content === 'string') {
              if (data.is_final_output && currentMessageRef.current) {
                rawContentRef.current += data.content;

                try {
                  const content = rawContentRef.current;
                  const answerKeyIndex = content.indexOf('"answer"');
                  if (answerKeyIndex !== -1) {
                    const colonIndex = content.indexOf(':', answerKeyIndex);
                    if (colonIndex !== -1) {
                      const firstQuoteIndex = content.indexOf('"', colonIndex);
                      if (firstQuoteIndex !== -1) {
                        let answerText = '';
                        let i = firstQuoteIndex + 1;
                        let inEscape = false;

                        while (i < content.length) {
                          const char = content[i];
                          if (inEscape) {
                            if (char === 'n') answerText += '\n';
                            else if (char === 't') answerText += '\t';
                            else if (char === 'r') answerText += '\r';
                            else if (char === '\\') answerText += '\\';
                            else if (char === '"') answerText += '"';
                            else answerText += char;
                            inEscape = false;
                          } else if (char === '\\') {
                            inEscape = true;
                          } else if (char === '"') {
                            break;
                          } else {
                            answerText += char;
                          }
                          i++;
                        }

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
                  console.debug('JSON解析中...', e.message);
                }
              }
            }
          },
          onAgentStart: (data) => {
            // 添加到思考步骤
            const step = {
              agent_name: data.agent_name,
              reason: null,
              task: null
            };
            thinkingStepsRef.current.push(step);

            if (currentMessageRef.current) {
              currentMessageRef.current.thinkingSteps = [...thinkingStepsRef.current];
              flushSync(() => {
                setMessages((prev) => [...prev]);
                setCurrentAgent(data);
              });
            }
          },
          onAgentEnd: (data) => {
            const lastStep = thinkingStepsRef.current[thinkingStepsRef.current.length - 1];
            if (lastStep && lastStep.agent_name === data.agent_name) {
              if (data.agent_selection_reason) {
                lastStep.reason = data.agent_selection_reason;
              }
              if (data.task_list && data.task_list.length > 0) {
                lastStep.task = data.task_list[0];
              }

              if (currentMessageRef.current) {
                currentMessageRef.current.thinkingSteps = [...thinkingStepsRef.current];
                flushSync(() => {
                  setMessages((prev) => [...prev]);
                });
              }
            }
          },
          onMessage: (data) => {
            if (data.message) {
              const message = data.message;
              const lastStep = thinkingStepsRef.current[thinkingStepsRef.current.length - 1];
              if (lastStep) {
                if (message.agent_selection_reason) {
                  lastStep.reason = message.agent_selection_reason;
                }
                if (message.task_list && message.task_list.length > 0) {
                  lastStep.task = message.task_list[0];
                }

                if (currentMessageRef.current) {
                  currentMessageRef.current.thinkingSteps = [...thinkingStepsRef.current];

                  const hasFormConfig = message.data && message.data.form_config;
                  if (hasFormConfig) {
                    currentMessageRef.current.content = '';
                    currentMessageRef.current.data = message.data;
                  } else if (message.data && message.data.answer) {
                    currentMessageRef.current.data = message.data;
                  }

                  flushSync(() => {
                    setMessages((prev) => [...prev]);
                  });
                }
              }
            }
          },
          onPause: (data) => {
            console.log('再次收到暂停事件:', data);
            setIsPaused(true);
            setIsLoading(false);
            if (currentMessageRef.current) {
              currentMessageRef.current.isThinkingComplete = true;
              currentMessageRef.current.pausedContext = data;
              // 更新表单配置
              if (data.context && data.context.length > 0) {
                const lastMsg = data.context[data.context.length - 1];
                if (lastMsg.data && lastMsg.data.form_config) {
                  currentMessageRef.current.data = lastMsg.data;
                  currentMessageRef.current.isFormSubmitted = false;
                }
              }
            }
          },
          onMetadata: (data) => {
            // 处理标题更新
            if (data.title_updated && data.new_title) {
              console.log('收到标题更新:', data.new_title);
              setTitleUpdate({
                sessionId: data.session_id,
                newTitle: data.new_title
              });
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
          },
        },
        sessionId,
        settings?.llmParams
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
        let msgData = msg.data;
        let isFormSubmitted = false;

        // 首先检查是否包含 form_config
        const hasFormConfig = msgData && (
          msgData.form_config ||
          (msgData.data && msgData.data.form_config) ||
          (typeof msgData === 'object' && JSON.stringify(msgData).includes('"form_config"'))
        );

        // 如果包含表单配置，从 msgData 中提取
        if (hasFormConfig) {
          // 如果 msgData 本身就是表单配置
          if (msgData.form_config) {
            // 已经是正确的格式
          } else if (msgData.data && msgData.data.form_config) {
            msgData = msgData.data;
          }
        }

        // 优先从 msgData.data.answer 中提取答案（general_agent 的答案）
        if (msgData && msgData.data && msgData.data.answer && typeof msgData.data.answer === 'string') {
          content = msgData.data.answer;
        }
        // 尝试从 msgData.answer 中提取
        else if (msgData && msgData.answer && typeof msgData.answer === 'string') {
          content = msgData.answer;
        }
        // 如果包含 form_config，清空 content
        else if (hasFormConfig) {
          content = '';
        }
        // 如果 msgData 中没有 answer 且没有表单，尝试从 content 中解析
        else if (msg.role === 'assistant' && content && typeof content === 'string') {
          // 检查 content 是否是 JSON 格式（包含 "status" 等字段）
          if (content.includes('"status"') || content.includes('"form_config"')) {
            // 是原始 JSON，应该清空
            content = '';
          } else {
            try {
              // 尝试解析为 JSON
              const jsonObj = JSON.parse(content);
              if (jsonObj.data && jsonObj.data.answer) {
                content = jsonObj.data.answer;
              } else if (jsonObj.answer) {
                content = jsonObj.answer;
              } else {
                content = '';
              }
            } catch (e) {
              // 不是 JSON，保持原样
            }
          }
        }

        // 从 events 中提取 thinking steps
        if (msg.events && Array.isArray(msg.events) && msg.events.length > 0) {
          thinkingSteps = [];

          for (let i = 0; i < msg.events.length; i++) {
            const event = msg.events[i];
            if (event.type === 'agent_end') {
              thinkingSteps.push({
                agent_name: event.data.agent_name,
                reason: event.data.agent_selection_reason,
                task: event.data.task_list && event.data.task_list.length > 0
                  ? event.data.task_list[0]
                  : null
              });
            }
          }

          // 过滤掉 general_agent（它是最终输出），显示其他agent包括entrance_agent
          thinkingSteps = thinkingSteps.filter(step =>
            step.agent_name !== 'general_agent'
          );
        }

        return {
          id: msg.id,  // 保留数据库 ID，用于删除操作
          role: msg.role,
          content: content,
          data: msgData,
          events: msg.events,
          thinkingSteps: thinkingSteps,
          isThinkingComplete: true,
          isFormSubmitted: isFormSubmitted
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

  /**
   * 删除指定消息
   */
  const deleteMessage = useCallback(async (messageIndex) => {
    const messageToDelete = messages[messageIndex];

    if (!messageToDelete) {
      console.error('消息不存在:', messageIndex);
      return false;
    }

    try {
      // 如果消息有 id（从数据库加载的），则调用 API 删除
      if (messageToDelete.id && sessionId) {
        await deleteMessageApi(sessionId, messageToDelete.id);
      }

      // 从本地状态中删除消息
      setMessages((prev) => prev.filter((_, idx) => idx !== messageIndex));

      return true;
    } catch (error) {
      console.error('删除消息失败:', error);
      setError(error.message);
      return false;
    }
  }, [messages, sessionId]);

  return {
    messages,
    isLoading,
    currentAgent,
    error,
    sessionId,
    isPaused,
    titleUpdate,
    sendSyncMessage,
    sendStreamMessage,
    submitFormAndResume,
    clearMessages,
    loadConversation,
    deleteMessage,
    setSessionId: setSessionIdFromOutside,
  };
};
