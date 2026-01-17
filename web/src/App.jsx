/**
 * easyAgent Web App
 * 主应用组件
 */

import { useState } from 'react';
import { Chat } from './components/Chat';
import { Agents } from './components/Agents';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('chat'); // 'chat' or 'agents'

  return (
    <div className="app">
      {/* 导航栏 */}
      <nav className="navbar">
        <div className="nav-brand">
          <span className="logo">🤖</span>
          <span className="brand-name">easyAgent</span>
        </div>
        <div className="nav-links">
          <button
            className={`nav-link ${currentView === 'chat' ? 'active' : ''}`}
            onClick={() => setCurrentView('chat')}
          >
            💬 聊天
          </button>
          <button
            className={`nav-link ${currentView === 'agents' ? 'active' : ''}`}
            onClick={() => setCurrentView('agents')}
          >
            🔧 Agents
          </button>
        </div>
        <div className="nav-info">
          <span className="version">v0.2.0</span>
        </div>
      </nav>

      {/* 主内容区域 */}
      <main className="main-content">
        {currentView === 'chat' && <Chat />}
        {currentView === 'agents' && <Agents />}
      </main>

      {/* 页脚 */}
      <footer className="footer">
        <p>
          © 2026 easyAgent. Powered by{' '}
          <a href="https://fastapi.tiangolo.com" target="_blank" rel="noopener noreferrer">
            FastAPI
          </a>{' '}
          &{' '}
          <a href="https://react.dev" target="_blank" rel="noopener noreferrer">
            React
          </a>
        </p>
      </footer>
    </div>
  );
}

export default App;
