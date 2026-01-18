/**
 * 设置弹窗组件
 * 包含同步/流式模式切换、模型配置、清除历史等设置
 */
import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Eye, EyeOff } from 'lucide-react';
import { ConfirmDialog } from './ConfirmDialog';
import './SettingsModal.css';

export const SettingsModal = ({ isOpen, onClose, settings, onSave }) => {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'model' | 'data'
  const [localSettings, setLocalSettings] = useState(settings);
  const [modelConfig, setModelConfig] = useState({
    baseUrl: '',
    modelName: '',
    apiKey: ''
  });
  const [showKey, setShowKey] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  // 加载当前模型配置
  useEffect(() => {
    if (isOpen) {
      loadModelConfig();
    }
  }, [isOpen]);

  const loadModelConfig = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/config/model');
      if (response.ok) {
        const data = await response.json();
        setModelConfig({
          baseUrl: data.base_url || '',
          modelName: data.model_name || '',
          apiKey: '' // 不返回key
        });
      }
    } catch (error) {
      console.error('加载模型配置失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveModelConfig = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/config/model', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: modelConfig.baseUrl,
          model_name: modelConfig.modelName,
          api_key: modelConfig.apiKey
        })
      });

      if (response.ok) {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 2000);
      } else {
        alert('保存失败，请检查输入');
      }
    } catch (error) {
      console.error('保存模型配置失败:', error);
      alert('保存失败，请检查网络连接');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleSave = () => {
    onSave(localSettings);
    onClose();
  };

  return createPortal(
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>设置</h2>
          <button className="settings-close" onClick={onClose}>×</button>
        </div>

        {/* 选项卡导航 */}
        <div className="settings-tabs">
          <button
            className={`settings-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            聊天模式
          </button>
          <button
            className={`settings-tab ${activeTab === 'model' ? 'active' : ''}`}
            onClick={() => setActiveTab('model')}
          >
            模型配置
          </button>
          <button
            className={`settings-tab ${activeTab === 'data' ? 'active' : ''}`}
            onClick={() => setActiveTab('data')}
          >
            数据管理
          </button>
        </div>

        <div className="settings-content">
          {/* 聊天模式设置 */}
          {activeTab === 'chat' && (
            <div className="settings-section">
              <div className="settings-option">
                <label>
                  <input
                    type="radio"
                    name="chatMode"
                    value="sync"
                    checked={localSettings.chatMode === 'sync'}
                    onChange={(e) => setLocalSettings({
                      ...localSettings,
                      chatMode: e.target.value
                    })}
                  />
                  <span>同步模式</span>
                </label>
                <p className="option-desc">
                  等待完整响应后显示，适合复杂查询
                </p>
              </div>

              <div className="settings-option">
                <label>
                  <input
                    type="radio"
                    name="chatMode"
                    value="stream"
                    checked={localSettings.chatMode === 'stream'}
                    onChange={(e) => setLocalSettings({
                      ...localSettings,
                      chatMode: e.target.value
                    })}
                  />
                  <span>流式模式</span>
                </label>
                <p className="option-desc">
                  实时显示响应内容，更流畅的体验
                </p>
              </div>
            </div>
          )}

          {/* 模型配置设置 */}
          {activeTab === 'model' && (
            <div className="settings-section">
              {isLoading && <p className="loading-text">加载配置中...</p>}

              <div className="model-config-form">
                <div className="form-group">
                  <label>Base URL</label>
                  <input
                    type="text"
                    placeholder="例如: https://api.openai.com/v1"
                    value={modelConfig.baseUrl}
                    onChange={(e) => setModelConfig({ ...modelConfig, baseUrl: e.target.value })}
                    disabled={isLoading}
                  />
                </div>

                <div className="form-group">
                  <label>模型名称</label>
                  <input
                    type="text"
                    placeholder="例如: gpt-4"
                    value={modelConfig.modelName}
                    onChange={(e) => setModelConfig({ ...modelConfig, modelName: e.target.value })}
                    disabled={isLoading}
                  />
                </div>

                <div className="form-group">
                  <label>API Key</label>
                  <div className="input-with-toggle">
                    <input
                      type={showKey ? 'text' : 'password'}
                      placeholder="输入API密钥"
                      value={modelConfig.apiKey}
                      onChange={(e) => setModelConfig({ ...modelConfig, apiKey: e.target.value })}
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="toggle-visibility"
                      onClick={() => setShowKey(!showKey)}
                    >
                      {showKey ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                {saveSuccess && (
                  <p className="success-message">✓ 配置已保存到.env文件</p>
                )}

                <button
                  className="settings-btn settings-btn-primary"
                  onClick={handleSaveModelConfig}
                  disabled={isLoading || !modelConfig.baseUrl || !modelConfig.modelName}
                >
                  {isLoading ? '保存中...' : '保存配置'}
                </button>
              </div>
            </div>
          )}

          {/* 数据管理设置 */}
          {activeTab === 'data' && (
            <div className="settings-section">
              <div className="data-management">
                <h3>清除历史记录</h3>
                <p className="option-desc">删除所有历史对话记录，此操作不可恢复。</p>
                <button
                  className="settings-danger-btn"
                  onClick={() => {
                    setShowClearConfirm(true);
                  }}
                >
                  清除所有历史记录
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="settings-footer">
          <button className="settings-btn settings-btn-cancel" onClick={onClose}>
            关闭
          </button>
          {activeTab === 'chat' && (
            <button className="settings-btn settings-btn-save" onClick={handleSave}>
              保存
            </button>
          )}
        </div>
      </div>

      {/* 确认清除历史对话框 */}
      <ConfirmDialog
        isOpen={showClearConfirm}
        title="清除历史记录"
        message="确定要清除所有历史记录吗？此操作不可恢复。"
        onConfirm={() => {
          setShowClearConfirm(false);
          onSave({ ...localSettings, clearAllHistory: true });
          onClose();
        }}
        onCancel={() => setShowClearConfirm(false)}
      />
    </div>,
    document.body
  );
};
