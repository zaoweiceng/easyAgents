/**
 * Agents Component
 * Agent列表和详情组件
 */

import { useState } from 'react';
import { useAgents } from '../hooks/useAgents';
import './Agents.css';

export const Agents = () => {
  const [showDetail, setShowDetail] = useState(false);
  const {
    agents,
    selectedAgent,
    isLoading,
    isReloading,
    error,
    successMessage,
    loadAgentDetail,
    reloadAgentsPlugin,
    setSelectedAgent,
    setSuccessMessage,
  } = useAgents();

  /**
   * 查看Agent详情
   */
  const handleViewDetail = async (agentName) => {
    await loadAgentDetail(agentName);
    setShowDetail(true);
  };

  /**
   * 关闭详情
   */
  const handleCloseDetail = () => {
    setShowDetail(false);
    setSelectedAgent(null);
  };

  /**
   * 重载Agent插件
   */
  const handleReload = async () => {
    try {
      await reloadAgentsPlugin();
      // 3秒后自动清除成功消息
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
    } catch (err) {
      console.error('重载失败:', err);
    }
  };

  return (
    <div className="agents-container">
      {/* 头部 */}
      <div className="agents-header">
        <div className="header-content">
          <div>
            <h1>🔧 Agent 管理器</h1>
            <p>查看和管理所有可用的AI Agent</p>
          </div>
          <button
            className={`reload-button ${isReloading ? 'loading' : ''}`}
            onClick={handleReload}
            disabled={isReloading}
          >
            {isReloading ? (
              <>
                <span className="spinner-small"></span>
                重载中...
              </>
            ) : (
              <>
                🔄 重载插件
              </>
            )}
          </button>
        </div>
      </div>

      {/* 成功提示 */}
      {successMessage && (
        <div className="success-message">
          <strong>✓ 成功:</strong> {successMessage}
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="error-message">
          <strong>错误:</strong> {error}
        </div>
      )}

      {/* 加载状态 */}
      {isLoading && agents.length === 0 ? (
        <div className="loading">
          <div className="spinner"></div>
          <p>加载中...</p>
        </div>
      ) : (
        <>
          {/* 统计信息 */}
          <div className="agents-stats">
            <div className="stat-card">
              <div className="stat-number">{agents.length}</div>
              <div className="stat-label">总Agent数</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">
                {agents.filter((a) => a.is_active).length}
              </div>
              <div className="stat-label">活跃Agent</div>
            </div>
          </div>

          {/* Agent列表 */}
          <div className="agents-grid">
            {agents.map((agent) => (
              <div key={agent.name} className="agent-card">
                <div className="agent-card-header">
                  <h3>{agent.name}</h3>
                  <span className={`status ${agent.is_active ? 'active' : 'inactive'}`}>
                    {agent.is_active ? '活跃' : '未激活'}
                  </span>
                </div>

                <div className="agent-card-body">
                  <p className="agent-description">{agent.description}</p>

                  {agent.handles && agent.handles.length > 0 && (
                    <div className="agent-handles">
                      <strong>处理能力:</strong>
                      <div className="handles-list">
                        {agent.handles.map((handle, index) => (
                          <span key={index} className="handle-tag">
                            {handle}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="agent-meta">
                    <span className="version">版本: {agent.version}</span>
                  </div>
                </div>

                <div className="agent-card-footer">
                  <button
                    className="detail-button"
                    onClick={() => handleViewDetail(agent.name)}
                  >
                    查看详情
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Agent详情弹窗 */}
      {showDetail && selectedAgent && (
        <div className="modal-overlay" onClick={handleCloseDetail}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedAgent.name}</h2>
              <button className="close-button" onClick={handleCloseDetail}>
                ×
              </button>
            </div>

            <div className="modal-body">
              <div className="detail-section">
                <h3>基本信息</h3>
                <div className="detail-row">
                  <span className="detail-label">名称:</span>
                  <span className="detail-value">{selectedAgent.name}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">版本:</span>
                  <span className="detail-value">{selectedAgent.version}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">状态:</span>
                  <span
                    className={`detail-value status ${
                      selectedAgent.is_active ? 'active' : 'inactive'
                    }`}
                  >
                    {selectedAgent.is_active ? '活跃' : '未激活'}
                  </span>
                </div>
              </div>

              <div className="detail-section">
                <h3>描述</h3>
                <p>{selectedAgent.description}</p>
              </div>

              {selectedAgent.handles && selectedAgent.handles.length > 0 && (
                <div className="detail-section">
                  <h3>处理能力</h3>
                  <div className="handles-list">
                    {selectedAgent.handles.map((handle, index) => (
                      <span key={index} className="handle-tag">
                        {handle}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedAgent.parameters && (
                <div className="detail-section">
                  <h3>参数</h3>
                  <pre>{JSON.stringify(selectedAgent.parameters, null, 2)}</pre>
                </div>
              )}

              {selectedAgent.supports_streaming !== undefined && (
                <div className="detail-section">
                  <h3>特性</h3>
                  <div className="feature-list">
                    <div className="feature-item">
                      <span className="feature-label">流式支持:</span>
                      <span className={`feature-value ${selectedAgent.supports_streaming ? 'yes' : 'no'}`}>
                        {selectedAgent.supports_streaming ? '✓ 支持' : '✗ 不支持'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button className="close-modal-button" onClick={handleCloseDetail}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
