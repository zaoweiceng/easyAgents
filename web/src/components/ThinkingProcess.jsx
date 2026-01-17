/**
 * ThinkingProcess Component - 显示AI思考过程的可折叠组件
 */
import { useState } from 'react';
import { ChevronDown, ChevronRight, Bot } from 'lucide-react';
import './ThinkingProcess.css';

export const ThinkingProcess = ({ steps, isProcessing = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="thinking-process">
      <button
        className="thinking-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="thinking-title">
          {isProcessing ? (
            <>
              <div className="thinking-spinner"></div>
              <span>思考中...</span>
            </>
          ) : (
            <>
              <Bot size={16} />
              <span>已深度思考</span>
            </>
          )}
        </div>
        {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
      </button>

      {isExpanded && (
        <div className="thinking-content">
          {steps.map((step, index) => (
            <div key={index} className="thinking-step">
              <div className="step-agent">
                <span className="step-indicator">▶</span>
                <span className="step-agent-name">{step.agent_name}</span>
              </div>
              {step.reason && (
                <div className="step-reason">{step.reason}</div>
              )}
              {step.task && (
                <div className="step-task">任务: {step.task}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
