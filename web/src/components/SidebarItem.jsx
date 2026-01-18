/**
 * 单个历史记录项组件
 */
import { useState } from 'react';
import { Trash2, MessageSquare, Clock, Download, ChevronDown } from 'lucide-react';
import { ConfirmDialog } from './ConfirmDialog';
import './SidebarItem.css';

export const SidebarItem = ({ conversation, isActive, onClick, onDelete, onExport }) => {
  const [showDelete, setShowDelete] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return '今天';
    } else if (diffDays === 1) {
      return '昨天';
    } else if (diffDays < 7) {
      return `${diffDays} 天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  };

  const handleExport = (format) => {
    setShowExportMenu(false);
    onExport(format);
  };

  return (
    <div
      className={`sidebar-item ${isActive ? 'active' : ''}`}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => {
        setShowDelete(false);
        setShowExportMenu(false);
      }}
    >
      <button className="sidebar-item-content" onClick={onClick}>
        <MessageSquare size={16} className="item-icon" />
        <div className="item-info">
          <div className="item-title">{conversation.title}</div>
          <div className="item-meta">
            <Clock size={12} />
            <span>{formatDate(conversation.updated_at)}</span>
            <span>·</span>
            <span>{conversation.message_count} 条消息</span>
          </div>
        </div>
      </button>

      {showDelete && (
        <>
          <div style={{ position: 'absolute', right: '48px', top: '50%', transform: 'translateY(-50%)', zIndex: 11 }}>
            <div
              className="sidebar-item-export"
              onClick={(e) => {
                e.stopPropagation();
                setShowExportMenu(!showExportMenu);
              }}
              title="导出对话"
              style={{ position: 'relative', cursor: 'pointer', padding: '6px', borderRadius: '6px', background: '#e0f2fe', color: '#0284c7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#bae6fd'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#e0f2fe'}
            >
              <Download size={16} />
              {showExportMenu && (
                <div className="export-menu" onClick={(e) => e.stopPropagation()}>
                  <div
                    className="export-menu-item"
                    onClick={() => handleExport('json')}
                  >
                    导出为 JSON
                  </div>
                  <div
                    className="export-menu-item"
                    onClick={() => handleExport('pdf')}
                  >
                    导出为 PDF
                  </div>
                </div>
              )}
            </div>
          </div>

          <button
            className="sidebar-item-delete"
            onClick={(e) => {
              e.stopPropagation();
              setShowConfirm(true);
            }}
          >
            <Trash2 size={16} />
          </button>
        </>
      )}

      {/* 确认对话框 */}
      <ConfirmDialog
        isOpen={showConfirm}
        title="删除对话"
        message={`确定要删除对话"${conversation.title}"吗？此操作不可恢复。`}
        onConfirm={() => {
          setShowConfirm(false);
          onDelete();
        }}
        onCancel={() => setShowConfirm(false)}
      />
    </div>
  );
};
