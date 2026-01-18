/**
 * Chat Component - 聊天界面组件（ChatGPT风格）
 */
import { useState, useRef, useEffect } from 'react';
import { Menu, Settings, Send, Bot, Plus, Paperclip, X } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { SettingsModal } from './SettingsModal';
import { AgentModal } from './AgentModal';
import { ThinkingProcess } from './ThinkingProcess';
import { MarkdownRenderer } from './MarkdownRenderer';
import { uploadFile } from '../services/api';
import './Chat.css';

export const Chat = ({
  sidebarOpen,
  onToggleSidebar,
  settings,
  onSettingsChange,
  currentSessionId,
  onTitleUpdate,
  onNewChat,
  onMessageCountChange,
  currentTitle
}) => {
  const [input, setInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [showAgent, setShowAgent] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const {
    messages,
    isLoading,
    currentAgent,
    error,
    sessionId,
    titleUpdate,
    sendSyncMessage,
    sendStreamMessage,
    submitFormAndResume,
    clearMessages,
    loadConversation,
    setSessionId,
  } = useChat(currentSessionId, settings);

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

  // 监听titleUpdate，通知父组件
  useEffect(() => {
    if (titleUpdate && onTitleUpdate) {
      onTitleUpdate(titleUpdate);
    }
  }, [titleUpdate, onTitleUpdate]);

  // 监听messages数量变化，通知父组件
  useEffect(() => {
    if (onMessageCountChange) {
      const hasMessages = messages.length > 0;
      onMessageCountChange(hasMessages);
    }
  }, [messages.length, onMessageCountChange]);

  const handleSend = async () => {
    if ((!input.trim() && attachedFiles.length === 0) || isLoading) return;

    const query = input.trim();
    setInput('');

    // 如果有附件，在消息中包含文件信息
    let message = query;
    if (attachedFiles.length > 0) {
      const fileInfos = attachedFiles.map(f => `[文件: ${f.original_filename}, ID: ${f.file_id}]`).join('\n');
      message = query ? `${query}\n\n${fileInfos}` : fileInfos;
    }

    if (settings.chatMode === 'sync') {
      await sendSyncMessage(message);
    } else {
      await sendStreamMessage(message);
    }

    // 清空附件
    setAttachedFiles([]);
  };

  // 处理文件选择
  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setUploading(true);

    try {
      for (const file of files) {
        const result = await uploadFile(file, sessionId);
        setAttachedFiles(prev => [...prev, result.file]);
      }
    } catch (error) {
      console.error('文件上传失败:', error);
      alert(`文件上传失败: ${error.message}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // 移除附件
  const removeAttachment = (fileId) => {
    setAttachedFiles(prev => prev.filter(f => f.file_id !== fileId));
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
          <button className="icon-btn new-chat-btn" onClick={onNewChat} title="新建对话">
            <Plus size={20} />
          </button>
          <h1>{currentTitle || 'easyAgent'}</h1>
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
          messages.map((msg, index) => {
            // 如果消息是用户提交的表单数据（内部消息），不显示
            if (msg.role === 'user' && msg.content && msg.content.startsWith('{"type":"form_submission"')) {
              return null;
            }

            return (
              <div key={index} className={`message message-${msg.role}`}>
                {/* Thinking Process - 只在assistant消息且有thinkingSteps时显示 */}
                {msg.role === 'assistant' && msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                  <ThinkingProcess
                    steps={msg.thinkingSteps}
                    isProcessing={!msg.isThinkingComplete && isLoading}
                    formConfig={msg.data?.form_config}
                    onFormSubmit={async (formData) => {
                      const formDataWithDemand = {
                        type: 'form_submission',
                        form_values: formData,
                        original_demand: msg.data?.user_demand || ''
                      };
                      await submitFormAndResume(formDataWithDemand);
                    }}
                    isFormSubmitted={msg.isFormSubmitted}
                  />
                )}

                {/* Message Content */}
                {msg.content && (
                  <div className="message-content">
                    <MarkdownRenderer content={msg.content} />
                  </div>
                )}
              </div>
            );
          })
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
        {/* 附件列表 */}
        {attachedFiles.length > 0 && (
          <div className="attachments-list">
            {attachedFiles.map(file => (
              <div key={file.file_id} className="attachment-item">
                <Paperclip size={16} />
                <span className="attachment-name">{file.original_filename}</span>
                <button
                  className="attachment-remove"
                  onClick={() => removeAttachment(file.file_id)}
                  title="移除"
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="input-wrapper">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <button
            className="attach-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            title="上传文件"
          >
            <Paperclip size={20} />
          </button>
          <textarea
            ref={textareaRef}
            className="message-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="输入您的问题... (按Enter发送，Shift+Enter换行)"
            disabled={isLoading || uploading}
            rows={1}
          />
          <button
            className="send-button"
            onClick={handleSend}
            disabled={isLoading || uploading || (!input.trim() && attachedFiles.length === 0)}
          >
            {uploading ? '上传中...' : <Send size={20} />}
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
