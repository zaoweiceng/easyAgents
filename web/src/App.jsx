/**
 * easyAgent Web App - ChatGPT风格主应用
 */
import { useState } from 'react';
import { Chat } from './components/Chat';
import { Sidebar } from './components/Sidebar';
import { useConversations } from './hooks/useConversations';
import './App.css';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settings, setSettings] = useState({
    chatMode: 'stream', // 'sync' or 'stream'
  });

  const {
    conversations,
    currentSessionId,
    setCurrentSessionId,
    createConversation,
    fetchConversationDetail,
    deleteConversation,
    searchConversations,
    exportConversation,
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

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentSessionId={currentSessionId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={deleteConversation}
        onExportConversation={exportConversation}
        onSearch={searchConversations}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      <Chat
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        settings={settings}
        onSettingsChange={handleSettingsChange}
        currentSessionId={currentSessionId}
      />
    </div>
  );
}

export default App;
