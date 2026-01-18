/**
 * 侧边栏组件 - 历史记录列表
 */
import { useState, useEffect } from 'react';
import { Search, Plus, MessageSquare, X } from 'lucide-react';
import { SidebarItem } from './SidebarItem';
import './Sidebar.css';

export const Sidebar = ({
  conversations,
  currentSessionId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onExportConversation,
  onSearch,
  isOpen,
  onToggle
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const searchTimer = setTimeout(async () => {
      if (searchQuery.trim()) {
        setIsSearching(true);
        const results = await onSearch(searchQuery);
        setSearchResults(results);
        setIsSearching(false);
      } else {
        setSearchResults([]);
      }
    }, 300);

    return () => clearTimeout(searchTimer);
  }, [searchQuery, onSearch]);

  const displayConversations = searchQuery.trim() ? searchResults : conversations;

  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onToggle} />

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={onNewChat}>
            <Plus size={20} />
            <span>新对话</span>
          </button>

          <button className="sidebar-close" onClick={onToggle}>
            <X size={20} />
          </button>
        </div>

        {/* Search Box */}
        <div className="sidebar-search">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="搜索对话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          {searchQuery && (
            <button
              className="search-clear"
              onClick={() => setSearchQuery('')}
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Conversations List */}
        <div className="sidebar-content">
          {isSearching ? (
            <div className="sidebar-loading">搜索中...</div>
          ) : displayConversations.length === 0 ? (
            <div className="sidebar-empty">
              <MessageSquare size={48} />
              <p>{searchQuery ? '未找到相关对话' : '暂无历史对话'}</p>
            </div>
          ) : (
            displayConversations.map((conv) => (
              <SidebarItem
                key={conv.session_id}
                conversation={conv}
                isActive={conv.session_id === currentSessionId}
                onClick={() => onSelectConversation(conv)}
                onDelete={() => onDeleteConversation(conv.session_id)}
                onExport={(format) => onExportConversation(conv.session_id, format)}
              />
            ))
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          <button className="sidebar-footer-btn" onClick={onNewChat}>
            <Plus size={16} />
            <span>新建对话</span>
          </button>
        </div>
      </aside>
    </>
  );
};
