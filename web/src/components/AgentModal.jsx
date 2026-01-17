/**
 * Agent Modal - 显示当前Agent信息
 */
import { useState, useEffect } from 'react';
import { Bot, Code, Settings, ChevronDown, ChevronRight } from 'lucide-react';
import { getAgents, getAgent } from '../services/api';
import './AgentModal.css';

export const AgentModal = ({ isOpen, onClose, currentAgentName }) => {
  const [agents, setAgents] = useState([]);
  const [agentDetails, setAgentDetails] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedAgents, setExpandedAgents] = useState({});

  useEffect(() => {
    if (isOpen) {
      fetchAgents();
    }
  }, [isOpen]);

  const fetchAgents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAgents();
      const agentsList = data.agents || [];
      setAgents(agentsList);

      // 获取每个Agent的详细信息
      const details = {};
      await Promise.all(
        agentsList.map(async (agent) => {
          try {
            const detailData = await getAgent(agent.name);
            details[agent.name] = detailData;
          } catch (err) {
            console.error(`Failed to fetch details for ${agent.name}:`, err);
            details[agent.name] = agent;
          }
        })
      );
      setAgentDetails(details);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (agentName) => {
    setExpandedAgents((prev) => ({
      ...prev,
      [agentName]: !prev[agentName],
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="agent-overlay" onClick={onClose}>
      <div className="agent-modal" onClick={(e) => e.stopPropagation()}>
        <div className="agent-header">
          <h2>Agent 列表</h2>
          <button className="agent-close" onClick={onClose}>×</button>
        </div>

        <div className="agent-content">
          {loading ? (
            <div className="agent-loading">加载中...</div>
          ) : error ? (
            <div className="agent-error">{error}</div>
          ) : agents.length === 0 ? (
            <div className="agent-empty">
              <Bot size={48} />
              <p>暂无可用Agent</p>
            </div>
          ) : (
            <div className="agent-list">
              {agents.map((agent) => {
                const detailData = agentDetails[agent.name] || {};
                const details = detailData.agent || {};
                const isExpanded = expandedAgents[agent.name];
                const isActive = agent.name === currentAgentName;

                return (
                  <div
                    key={agent.name}
                    className={`agent-item ${isActive ? 'active' : ''}`}
                  >
                    <div
                      className="agent-item-summary"
                      onClick={() => toggleExpand(agent.name)}
                    >
                      <div className="agent-item-left">
                        <div className="agent-item-icon">
                          <Bot size={20} />
                        </div>
                        <div className="agent-item-info">
                          <div className="agent-item-name">
                            {agent.name}
                            {isActive && (
                              <span className="agent-item-badge">当前使用</span>
                            )}
                          </div>
                          <div className="agent-item-description">
                            {agent.description || '暂无描述'}
                          </div>
                        </div>
                      </div>
                      <button className="agent-expand-btn">
                        {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                      </button>
                    </div>

                    {isExpanded && (
                      <div className="agent-item-details">
                        {/* Handles Section */}
                        {details.handles && details.handles.length > 0 && (
                          <div className="agent-detail-section">
                            <div className="agent-detail-header">
                              <Code size={16} />
                              <h4>处理能力</h4>
                            </div>
                            <div className="agent-handles-list">
                              {details.handles.map((handle, idx) => (
                                <div key={idx} className="agent-handle-tag">
                                  {handle}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Parameters Section */}
                        {details.parameters && Object.keys(details.parameters).length > 0 && (
                          <div className="agent-detail-section">
                            <div className="agent-detail-header">
                              <Settings size={16} />
                              <h4>配置参数</h4>
                            </div>
                            <div className="agent-params-list">
                              {Object.entries(details.parameters).map(([key, value]) => (
                                <div key={key} className="agent-param-item">
                                  <div className="agent-param-key">{key}</div>
                                  <div className="agent-param-value">
                                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* No additional info */}
                        {(!details.handles || details.handles.length === 0) &&
                         (!details.parameters || Object.keys(details.parameters).length === 0) && (
                          <div className="agent-no-details">
                            暂无详细信息
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
