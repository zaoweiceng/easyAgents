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
 * 重载所有Agent插件（热插拔）
 */
export const reloadAgents = async () => {
  const response = await fetch(`${API_BASE_URL}/agents/reload`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('重载Agent失败');
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
 * @param {Function} callbacks.onPause - 暂停等待用户输入
 * @param {Function} callbacks.onMetadata - 接收元数据（包括session_id）
 * @param {string} sessionId - 会话ID
 * @param {Object} llmParams - LLM参数（可选）
 */
export const chatStream = async (query, callbacks, sessionId = null, llmParams = null) => {
  const {
    onDelta,
    onAgentStart,
    onAgentEnd,
    onError,
    onDone,
    onMessage,
    onPause,
    onMetadata,
  } = callbacks;

  try {
    const requestBody = {
      query,
      stream: true,
      session_id: sessionId,
    };

    // 如果提供了LLM参数，添加到请求中
    if (llmParams) {
      if (llmParams.temperature !== undefined) {
        requestBody.temperature = llmParams.temperature;
      }
      if (llmParams.top_p !== undefined) {
        requestBody.top_p = llmParams.top_p;
      }
      if (llmParams.top_k !== undefined) {
        requestBody.top_k = llmParams.top_k;
      }
    }

    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
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
          const data = line.slice(6).trim();

          if (data === '[DONE]') {
            onDone && onDone();
            return;
          }

          // 跳过空行
          if (!data) {
            continue;
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
              case 'pause':
                onPause && onPause(event.data);
                break;
              case 'error':
                onError && onError(event.data);
                break;
              case 'metadata':
                // 处理元数据（包括 session_id）
                onMetadata && onMetadata(event.data);
                break;
              default:
                console.log('未知事件类型:', event.type, event.data);
            }
          } catch (e) {
            console.error('解析事件失败:', e, data);
          }
        } else if (line.trim()) {
          // 忽略非 "data: " 开头的非空行（可能是后端直接输出的调试信息）
          console.debug('忽略非SSE格式数据:', line.trim());
        }
      }
    }
  } catch (error) {
    onError && onError({ error_message: error.message });
    throw error;
  }
};

/**
 * 恢复流式聊天（从暂停点继续）
 * @param {string} query - 用户提交的表单数据
 * @param {Object} callbacks - 回调函数集合
 * @param {string} sessionId - 会话ID（必须）
 * @param {Object} llmParams - LLM参数（可选）
 */
export const chatStreamResume = async (query, callbacks, sessionId, llmParams = null) => {
  const {
    onDelta,
    onAgentStart,
    onAgentEnd,
    onError,
    onDone,
    onMessage,
    onPause,
    onMetadata,
  } = callbacks;

  if (!sessionId) {
    throw new Error('恢复聊天必须提供 sessionId');
  }

  try {
    const requestBody = {
      query,
      stream: true,
      session_id: sessionId,
    };

    // 如果提供了LLM参数，添加到请求中
    if (llmParams) {
      if (llmParams.temperature !== undefined) {
        requestBody.temperature = llmParams.temperature;
      }
      if (llmParams.top_p !== undefined) {
        requestBody.top_p = llmParams.top_p;
      }
      if (llmParams.top_k !== undefined) {
        requestBody.top_k = llmParams.top_k;
      }
    }

    const response = await fetch(`${API_BASE_URL}/chat/stream/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error('恢复流式聊天请求失败');
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
          const data = line.slice(6).trim();

          if (data === '[DONE]') {
            onDone && onDone();
            return;
          }

          if (!data) {
            continue;
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
              case 'pause':
                onPause && onPause(event.data);
                break;
              case 'error':
                onError && onError(event.data);
                break;
              case 'metadata':
                onMetadata && onMetadata(event.data);
                break;
              default:
                console.log('未知事件类型:', event.type, event.data);
            }
          } catch (e) {
            console.error('解析事件失败:', e, data);
          }
        } else if (line.trim()) {
          console.debug('忽略非SSE格式数据:', line.trim());
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
  reloadAgents,
  chatSync,
  chatStream,
};

/**
 * ============================================================================
 * 文件管理API
 * ============================================================================
 */

/**
 * 上传文件
 * @param {File} file - 要上传的文件对象
 * @param {string} sessionId - 会话ID（可选）
 * @returns {Promise<Object>} 文件信息
 */
export const uploadFile = async (file, sessionId = null) => {
  const formData = new FormData();
  formData.append('file', file);

  let url = `${API_BASE_URL}/files/upload`;
  if (sessionId) {
    url += `?session_id=${encodeURIComponent(sessionId)}`;
  }

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '文件上传失败');
  }

  return response.json();
};

/**
 * 下载文件
 * @param {string} fileId - 文件ID
 * @returns {Promise<Blob>} 文件内容
 */
export const downloadFile = async (fileId) => {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`);

  if (!response.ok) {
    throw new Error('文件下载失败');
  }

  return response.blob();
};

/**
 * 获取文件列表
 * @param {string} sessionId - 会话ID（可选，用于过滤）
 * @param {number} limit - 最大返回数量
 * @returns {Promise<Object>} 文件列表
 */
export const getFiles = async (sessionId = null, limit = 100) => {
  let url = `${API_BASE_URL}/files?limit=${limit}`;
  if (sessionId) {
    url += `&session_id=${encodeURIComponent(sessionId)}`;
  }

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('获取文件列表失败');
  }

  return response.json();
};

/**
 * 获取文件信息
 * @param {string} fileId - 文件ID
 * @returns {Promise<Object>} 文件信息
 */
export const getFileInfo = async (fileId) => {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}/info`);

  if (!response.ok) {
    throw new Error('获取文件信息失败');
  }

  return response.json();
};

/**
 * 删除文件
 * @param {string} fileId - 文件ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteFile = async (fileId) => {
  const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('删除文件失败');
  }

  return response.json();
};

/**
 * 删除会话的所有文件
 * @param {string} sessionId - 会话ID
 * @returns {Promise<Object>} 删除结果
 */
export const deleteSessionFiles = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/files/session/${sessionId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('删除会话文件失败');
  }

  return response.json();
};
