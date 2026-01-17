/**
 * easyAgent API Service
 * 用于与后端API通信
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * 健康检查
 */
export const healthCheck = async () => {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error('健康检查失败');
  }
  return response.json();
};

/**
 * 获取所有Agent列表
 */
export const getAgents = async () => {
  const response = await fetch(`${API_BASE_URL}/agents`);
  if (!response.ok) {
    throw new Error('获取Agent列表失败');
  }
  return response.json();
};

/**
 * 获取特定Agent详情
 */
export const getAgent = async (agentName) => {
  const response = await fetch(`${API_BASE_URL}/agents/${agentName}`);
  if (!response.ok) {
    throw new Error('获取Agent详情失败');
  }
  return response.json();
};

/**
 * 同步聊天
 */
export const chatSync = async (query, sessionId = null) => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      stream: false,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error('聊天请求失败');
  }

  return response.json();
};

/**
 * 流式聊天
 * @param {string} query - 用户查询
 * @param {Object} callbacks - 回调函数集合
 * @param {Function} callbacks.onDelta - 接收增量内容
 * @param {Function} callbacks.onAgentStart - Agent开始
 * @param {Function} callbacks.onAgentEnd - Agent结束
 * @param {Function} callbacks.onError - 错误处理
 * @param {Function} callbacks.onDone - 完成
 * @param {Function} callbacks.onMessage - 接收完整消息
 * @param {string} sessionId - 会话ID
 */
export const chatStream = async (query, callbacks, sessionId = null) => {
  const {
    onDelta,
    onAgentStart,
    onAgentEnd,
    onError,
    onDone,
    onMessage,
  } = callbacks;

  try {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        stream: true,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error('流式聊天请求失败');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            onDone && onDone();
            return;
          }

          try {
            const event = JSON.parse(data);

            switch (event.type) {
              case 'delta':
                onDelta && onDelta(event.data);
                break;
              case 'agent_start':
                onAgentStart && onAgentStart(event.data);
                break;
              case 'agent_end':
                onAgentEnd && onAgentEnd(event.data);
                break;
              case 'message':
                onMessage && onMessage(event.data);
                break;
              case 'error':
                onError && onError(event.data);
                break;
              case 'metadata':
                // 可以处理元数据
                break;
              default:
                console.log('未知事件类型:', event.type);
            }
          } catch (e) {
            console.error('解析事件失败:', e, data);
          }
        }
      }
    }
  } catch (error) {
    onError && onError({ error_message: error.message });
    throw error;
  }
};

export default {
  healthCheck,
  getAgents,
  getAgent,
  chatSync,
  chatStream,
};
