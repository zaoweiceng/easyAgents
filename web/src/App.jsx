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
  } = useConversations();

  const handleNewChat = async () => {
    const sessionId = await createConversation('新对话');
    setSidebarOpen(false);
    setCurrentSessionId(sessionId);
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
      setConversations((prev) =>
        prev.map((conv) =>
          conv.session_id === titleUpdate.sessionId
            ? { ...conv, title: titleUpdate.newTitle }
            : conv
        )
      );
      console.log('已更新会话标题:', titleUpdate.newTitle);
    }
  }, [titleUpdate, setConversations]);

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
      />
    </div>
  );
}

export default App;
