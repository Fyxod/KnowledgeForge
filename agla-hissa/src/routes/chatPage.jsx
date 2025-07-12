// pages/ChatPage.js
import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import ChatWindow from '../components/ChatWindow';

export default function ChatPage({ userData }) {
  const [selectedThreadId, setSelectedThreadId] = useState(null);

  const threads = Object.entries(userData.threads || {}).map(([id, data]) => ({
    id,
    ...data,
  }));

  const currentThread = threads.find(t => t.id === selectedThreadId);

  const handleSendMessage = (text) => {
    // append to currentThread.chats
    // call API or update state
  };

  return (
    <div className="flex h-screen">
      <Sidebar
        threads={threads}
        selectedId={selectedThreadId}
        onSelect={setSelectedThreadId}
      />
      <ChatWindow thread={currentThread} onSend={handleSendMessage} />
    </div>
  );
}
