/**
 * 单个历史记录项组件
 */
import { useState } from 'react';
import { Trash2, MessageSquare, Clock, Download } from 'lucide-react';
import './SidebarItem.css';

export const SidebarItem = ({ conversation, isActive, onClick, onDelete, onExport }) => {
  const [showDelete, setShowDelete] = useState(false);

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

  return (
    <div
      className={`sidebar-item ${isActive ? 'active' : ''}`}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
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
          <button
            className="sidebar-item-export"
            onClick={(e) => {
              e.stopPropagation();
              onExport();
            }}
            title="导出对话"
          >
            <Download size={16} />
          </button>
          <button
            className="sidebar-item-delete"
            onClick={(e) => {
              e.stopPropagation();
              if (confirm('确定要删除这个对话吗？')) {
                onDelete();
              }
            }}
          >
            <Trash2 size={16} />
          </button>
        </>
      )}
    </div>
  );
};
