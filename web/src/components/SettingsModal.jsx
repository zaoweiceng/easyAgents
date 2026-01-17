/**
 * 设置弹窗组件
 * 包含同步/流式模式切换、清除历史等设置
 */
import { useState } from 'react';
import './SettingsModal.css';

export const SettingsModal = ({ isOpen, onClose, settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState(settings);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave(localSettings);
    onClose();
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>设置</h2>
          <button className="settings-close" onClick={onClose}>×</button>
        </div>

        <div className="settings-content">
          {/* 聊天模式设置 */}
          <div className="settings-section">
            <h3>聊天模式</h3>
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

          {/* 其他设置 */}
          <div className="settings-section">
            <h3>数据管理</h3>
            <button
              className="settings-danger-btn"
              onClick={() => {
                if (confirm('确定要清除所有历史记录吗？此操作不可恢复。')) {
                  // 触发清除历史
                  onSave({ ...localSettings, clearAllHistory: true });
                  onClose();
                }
              }}
            >
              清除所有历史记录
            </button>
          </div>
        </div>

        <div className="settings-footer">
          <button className="settings-btn settings-btn-cancel" onClick={onClose}>
            取消
          </button>
          <button className="settings-btn settings-btn-save" onClick={handleSave}>
            保存
          </button>
        </div>
      </div>
    </div>
  );
};
