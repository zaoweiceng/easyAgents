/**
 * easyAgent Web App - ChatGPT风格主应用
 */
import { useState, useEffect } from 'react';
import { Chat } from './components/Chat';
import { Sidebar } from './components/Sidebar';
import { useConversations } from './hooks/useConversations';
import './App.css';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settings, setSettings] = useState({
    chatMode: 'stream', // 'sync' or 'stream'
  });
  const [titleUpdate, setTitleUpdate] = useState(null); // 保存标题更新信息
  const [isCurrentConversationEmpty, setIsCurrentConversationEmpty] = useState(true); // 当前会话是否为空

  const {
    conversations,
    currentSessionId,
    setCurrentSessionId,
    createConversation,
    fetchConversationDetail,
    deleteConversation,
    searchConversations,
    exportConversation,
    setConversations,
    fetchConversations,
  } = useConversations();

  const handleNewChat = async () => {
    // 如果当前会话为空，不创建新会话，只清空状态
    if (isCurrentConversationEmpty) {
      setCurrentSessionId(null);
      setSidebarOpen(false);
    } else {
      // 如果当前会话有内容，创建新会话
      const sessionId = await createConversation('新对话');
      setSidebarOpen(false);
      setCurrentSessionId(sessionId);
      setIsCurrentConversationEmpty(true);
    }
  };

  const handleSelectConversation = async (conv) => {
    setCurrentSessionId(conv.session_id);
    setSidebarOpen(false);
    // TODO: 加载会话的历史消息到Chat组件
  };

  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings);
  };

  // 监听titleUpdate变化，更新会话列表中的标题
  useEffect(() => {
    if (titleUpdate && titleUpdate.sessionId && titleUpdate.newTitle) {
      const finalTitle = titleUpdate.newTitle.trim() || '新对话';

      setConversations((prev) =>
        prev.map((conv) =>
          conv.session_id === titleUpdate.sessionId
            ? { ...conv, title: finalTitle }
            : conv
        )
      );
      console.log('已更新会话标题:', finalTitle);

      // 重新获取会话列表以确保同步
      fetchConversations();
    }
  }, [titleUpdate, setConversations, fetchConversations]);

  // 处理消息数量变化
  const handleMessageCountChange = (hasMessages) => {
    setIsCurrentConversationEmpty(!hasMessages);
  };

  // 获取当前会话的标题
  const getCurrentTitle = () => {
    if (!currentSessionId) return 'easyAgent';
    const currentConv = conversations.find(c => c.session_id === currentSessionId);
    if (currentConv && currentConv.title && currentConv.title !== '新对话') {
      return currentConv.title;
    }
    return 'easyAgent';
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentSessionId={currentSessionId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={deleteConversation}
        onExportConversation={(sessionId, format) => exportConversation(sessionId, format)}
        onSearch={searchConversations}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      <Chat
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onNewChat={handleNewChat}
        settings={settings}
        onSettingsChange={handleSettingsChange}
        currentSessionId={currentSessionId}
        onTitleUpdate={setTitleUpdate}
        onMessageCountChange={handleMessageCountChange}
        currentTitle={getCurrentTitle()}
      />
    </div>
  );
}

export default App;
