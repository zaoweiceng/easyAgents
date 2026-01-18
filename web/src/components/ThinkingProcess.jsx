/**
 * ThinkingProcess Component - 显示AI思考过程的可折叠组件
 */
import { useState, useRef } from 'react';
import { ChevronDown, ChevronRight, Bot } from 'lucide-react';
import { FormComponent } from './FormComponent';
import './ThinkingProcess.css';

export const ThinkingProcess = ({ steps, isProcessing = false, formConfig, onFormSubmit, isFormSubmitted = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const formSubmittedRef = useRef(isFormSubmitted);

  // 更新提交状态
  if (isFormSubmitted && !formSubmittedRef.current) {
    formSubmittedRef.current = true;
  }

  // 自动展开如果有表单
  const hasForm = formConfig && !formSubmittedRef.current;
  if (hasForm && !isExpanded) {
    setIsExpanded(true);
  }

  const handleFormSubmit = async (formData) => {
    formSubmittedRef.current = true;
    if (onFormSubmit) {
      await onFormSubmit(formData);
    }
  };

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

          {/* 表单作为思考过程的最后一步 */}
          {formConfig && (
            <div className="thinking-step thinking-form-step">
              <div className="step-agent">
                <span className="step-indicator">▶</span>
                <span className="step-agent-name">等待用户输入</span>
              </div>
              <div className="thinking-form-wrapper">
                <FormComponent
                  formConfig={formConfig}
                  onSubmit={handleFormSubmit}
                  disabled={formSubmittedRef.current}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
