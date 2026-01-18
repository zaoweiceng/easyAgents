/**
 * 确认对话框组件
 */
import { createPortal } from 'react-dom';
import './ConfirmDialog.css';

export const ConfirmDialog = ({ isOpen, title, message, onConfirm, onCancel }) => {
  if (!isOpen) return null;

  return createPortal(
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-header">
          <h3>{title}</h3>
        </div>

        <div className="confirm-body">
          <p>{message}</p>
        </div>

        <div className="confirm-footer">
          <button className="confirm-btn confirm-btn-cancel" onClick={onCancel}>
            取消
          </button>
          <button className="confirm-btn confirm-btn-danger" onClick={onConfirm}>
            确定删除
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};
