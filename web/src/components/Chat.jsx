/**
 * Chat Component - 聊天界面组件（ChatGPT风格）
 */
import { useState, useRef, useEffect } from 'react';
import { Menu, Settings, Send, Bot } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { SettingsModal } from './SettingsModal';
import { AgentModal } from './AgentModal';
import { ThinkingProcess } from './ThinkingProcess';
import { MarkdownRenderer } from './MarkdownRenderer';
import './Chat.css';

export const Chat = ({
  sidebarOpen,
  onToggleSidebar,
  settings,
  onSettingsChange,
  currentSessionId
}) => {
  const [input, setInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [showAgent, setShowAgent] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const {
    messages,
    isLoading,
    currentAgent,
    error,
    sessionId,
    sendSyncMessage,
    sendStreamMessage,
    clearMessages,
    loadConversation,
    setSessionId,
  } = useChat(currentSessionId);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentAgent]);

  // 自动调整文本框高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  // 当session_id改变时，加载会话历史
  useEffect(() => {
    if (currentSessionId) {
      loadConversation(currentSessionId);
    } else {
      clearMessages();
    }
  }, [currentSessionId, loadConversation, clearMessages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const query = input.trim();
    setInput('');

    if (settings.chatMode === 'sync') {
      await sendSyncMessage(query);
    } else {
      await sendStreamMessage(query);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <button className="icon-btn" onClick={onToggleSidebar}>
            <Menu size={24} />
          </button>
          <h1>easyAgent</h1>
        </div>

        <div className="header-right">
          <button className="icon-btn" onClick={() => setShowAgent(true)} title="Agent列表">
            <Bot size={20} />
          </button>
          <button className="icon-btn" onClick={() => setShowSettings(true)} title="设置">
            <Settings size={20} />
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <strong>错误:</strong> {error}
        </div>
      )}

      {/* Messages Container */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h2>欢迎使用 easyAgent</h2>
            <p>请输入您的问题，AI助手将为您解答</p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className={`message message-${msg.role}`}>
              {/* Thinking Process - 只在assistant消息且有thinkingSteps时显示 */}
              {msg.role === 'assistant' && msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                <ThinkingProcess
                  steps={msg.thinkingSteps}
                  isProcessing={!msg.isThinkingComplete && isLoading}
                />
              )}

              {/* Message Content */}
              {msg.content && (
                <div className="message-content">
                  <MarkdownRenderer content={msg.content} />
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

      {/* Input Container */}
      <div className="input-container">
        <div className="input-wrapper">
          <textarea
            ref={textareaRef}
            className="message-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="输入您的问题... (按Enter发送，Shift+Enter换行)"
            disabled={isLoading}
            rows={1}
          />
          <button
            className="send-button"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
          >
            <Send size={20} />
          </button>
        </div>
        <div className="input-footer">
          <span>AI生成的内容可能不准确，请核实重要信息。</span>
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        settings={settings}
        onSave={onSettingsChange}
      />

      {/* Agent Modal */}
      <AgentModal
        isOpen={showAgent}
        onClose={() => setShowAgent(false)}
        currentAgentName={currentAgent?.agent_name || null}
      />
    </div>
  );
};
