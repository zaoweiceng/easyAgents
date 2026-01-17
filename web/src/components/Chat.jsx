/**
 * Chat Component
 * 聊天界面组件
 */

import { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import './Chat.css';

export const Chat = () => {
  const [mode, setMode] = useState('stream'); // 'sync' or 'stream'
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const {
    messages,
    isLoading,
    currentAgent,
    error,
    sendSyncMessage,
    sendStreamMessage,
    clearMessages,
  } = useChat();

  /**
   * 自动滚动到底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentAgent]);

  /**
   * 发送消息
   */
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const query = input.trim();
    setInput('');

    if (mode === 'sync') {
      await sendSyncMessage(query);
    } else {
      await sendStreamMessage(query);
    }
  };

  /**
   * 按Enter发送
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      {/* 头部 */}
      <div className="chat-header">
        <h1>🤖 easyAgent Chat</h1>
        <div className="chat-controls">
          <button
            className={`mode-button ${mode === 'sync' ? 'active' : ''}`}
            onClick={() => setMode('sync')}
            disabled={isLoading}
          >
            同步模式
          </button>
          <button
            className={`mode-button ${mode === 'stream' ? 'active' : ''}`}
            onClick={() => setMode('stream')}
            disabled={isLoading}
          >
            流式模式
          </button>
          <button
            className="clear-button"
            onClick={clearMessages}
            disabled={isLoading || messages.length === 0}
          >
            清空
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="error-message">
          <strong>错误:</strong> {error}
        </div>
      )}

      {/* 当前Agent状态 */}
      {currentAgent && (
        <div className="agent-status">
          <span className="agent-indicator">▶</span>
          <span className="agent-name">{currentAgent.agent_name}</span>
          <span className="agent-desc">正在处理...</span>
        </div>
      )}

      {/* 消息列表 */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h2>欢迎使用 easyAgent</h2>
            <p>请输入您的问题，AI助手将为您解答</p>
            <div className="example-queries">
              <p>示例查询:</p>
              <button onClick={() => setInput('查询id为2的图书信息')}>
                查询id为2的图书信息
              </button>
              <button onClick={() => setInput('你好')}>
                打个招呼
              </button>
              <button onClick={() => setInput('有哪些可用的Agent？')}>
                有哪些可用的Agent？
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className={`message message-${msg.role}`}>
              <div className="message-header">
                <span className="message-role">
                  {msg.role === 'user' && '👤 用户'}
                  {msg.role === 'assistant' && '🤖 助手'}
                  {msg.role === 'system' && '⚙️ 系统'}
                  {msg.role === 'error' && '❌ 错误'}
                </span>
              </div>
              <div className="message-content">
                {typeof msg.content === 'string' ? (
                  <p>{msg.content}</p>
                ) : (
                  <pre>{JSON.stringify(msg.content, null, 2)}</pre>
                )}
              </div>

              {/* 显示事件 */}
              {msg.events && msg.events.length > 0 && (
                <div className="message-events">
                  {msg.events.map((event, eventIndex) => (
                    <div key={eventIndex} className={`event event-${event.type}`}>
                      {event.type === 'agent_start' && (
                        <span>
                          ▶ {event.data.agent_name} 开始处理
                        </span>
                      )}
                      {event.type === 'agent_end' && (
                        <span>
                          ✓ {event.data.agent_name} 完成
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* 显示数据 */}
              {msg.data && (
                <div className="message-data">
                  <details>
                    <summary>查看数据</summary>
                    <pre>{JSON.stringify(msg.data, null, 2)}</pre>
                  </details>
                </div>
              )}
            </div>
          ))
        )}
        {isLoading && !currentAgent && (
          <div className="message message-assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className="input-container">
        <textarea
          className="message-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入您的问题... (按Enter发送，Shift+Enter换行)"
          disabled={isLoading}
          rows={3}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? '发送中...' : '发送'}
        </button>
      </div>
    </div>
  );
};
