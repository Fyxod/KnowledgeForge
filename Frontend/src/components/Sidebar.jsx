import React, { useState } from 'react';

export default function Sidebar({ 
  threads, 
  selectedId, 
  onSelect, 
  userData, 
  onCreateThread, 
  onUpdateThreadName,
  onDeleteThread
}) {
  const [isCreating, setIsCreating] = useState(false);
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [editingName, setEditingName] = useState('');
  
  const handleCreateNewThread = async () => {
    setIsCreating(true);
    try {
      await onCreateThread();
    } catch (error) {
      console.error('Failed to create thread:', error);
    } finally {
      setIsCreating(false);
    }
  };
  
  const formatDate = (dateStr) => {
    try {
      const date = typeof dateStr === 'string' ? new Date(dateStr) : new Date(dateStr.$date);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'Unknown date';
    }
  };

  const getFileIcon = (type) => {
    switch(type?.toLowerCase()) {
      case 'pdf': return 'PDF';
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif': return 'IMG';
      case 'doc':
      case 'docx': return 'DOC';
      case 'txt': return 'TXT';
      default: return 'FILE';
    }
  };

  const handleEditThreadName = (threadId, currentName) => {
    setEditingThreadId(threadId);
    setEditingName(currentName);
  };

  const handleSaveThreadName = async (threadId) => {
    if (!editingName.trim()) {
      setEditingThreadId(null);
      return;
    }

    try {
      await onUpdateThreadName(threadId, editingName.trim());
      setEditingThreadId(null);
      setEditingName('');
    } catch (error) {
      console.error('Failed to update thread name:', error);
    }
  };

  const handleCancelEdit = () => {
    setEditingThreadId(null);
    setEditingName('');
  };

  const handleKeyPress = (e, threadId) => {
    if (e.key === 'Enter') {
      handleSaveThreadName(threadId);
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div className="w-80 bg-gradient-to-b from-gray-900 to-gray-800 text-white flex flex-col h-full shadow-2xl">
      <div className="p-6 border-b border-gray-700 flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
            Chats
          </h1>
          <div className="flex items-center gap-2">
          </div>
        </div>
        <div className="space-y-3">
          <button
            onClick={handleCreateNewThread}
            disabled={isCreating}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 text-white px-3 py-2 rounded-lg flex items-center justify-center gap-2 transition-all duration-200 transform hover:scale-105 shadow-lg"
          >
            {isCreating ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <>
                <span className="text-base">+</span>
                <span className="font-medium text-sm">New Chat</span>
              </>
            )}
          </button>
          
          <div className="text-center text-gray-300">
            <p className="text-xs">Or upload files below to add documents</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-3">
        {threads.length === 0 ? (
          <div className="text-center text-gray-400 mt-12">
            <div className="w-12 h-12 mx-auto mb-4 bg-gray-600 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-base font-medium mb-2">No threads yet</p>
            <p className="text-xs">Upload files to create your first thread!</p>
          </div>
        ) : (
          threads
            .sort((a, b) => {
              const dateA = a.updatedAt || a.createdAt || a.created_at || new Date(0);
              const dateB = b.updatedAt || b.createdAt || b.created_at || new Date(0);
              
              const getTimestamp = (date) => {
                if (!date) return 0;
                if (typeof date === 'string') return new Date(date).getTime();
                if (date.$date) return new Date(date.$date).getTime();
                if (date instanceof Date) return date.getTime();
                return 0;
              };
              
              return getTimestamp(dateB) - getTimestamp(dateA);
            })
            .map(({ id, thread_name, updatedAt, documents, chats }) => (
            <div
              key={id}
              onClick={() => onSelect(id)}
              className={`p-4 rounded-xl cursor-pointer transition-all duration-200 transform hover:scale-102 ${
                id === selectedId 
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg' 
                  : 'bg-gray-800 hover:bg-gray-700 shadow-md'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                {editingThreadId === id ? (
                  <div className="flex-1 mr-2">
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onKeyDown={(e) => handleKeyPress(e, id)}
                      onBlur={() => handleSaveThreadName(id)}
                      className="w-full bg-white/10 text-white px-2 py-1 rounded text-sm border border-white/20 focus:border-white/40 focus:outline-none"
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                ) : (
                  <div className="flex-1">
                    <h3 
                      className="font-semibold truncate text-base cursor-pointer hover:text-blue-200 transition-colors"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditThreadName(id, thread_name);
                      }}
                      title="Click to edit thread name"
                    >
                      {thread_name}
                    </h3>
                  </div>
                )}
                
                <div className="flex items-center gap-2">
                  {id === selectedId && (
                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteThread(id);
                    }}
                    className="text-gray-400 hover:text-red-400 transition-colors p-1 rounded-full hover:bg-black/20"
                    title="Delete thread"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              
              {documents?.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {documents.slice(0, 3).map((doc, idx) => (
                    <span key={idx} className="text-xs bg-black/20 px-2 py-1 rounded-md flex items-center gap-1">
                      <span className="text-xs font-mono">{getFileIcon(doc.type)}</span>
                      {doc.title.length > 10 ? doc.title.substring(0, 10) + '...' : doc.title}
                    </span>
                  ))}
                  {documents.length > 3 && (
                    <span className="text-xs text-gray-300">+{documents.length - 3} more</span>
                  )}
                </div>
              )}
              
              <div className="flex justify-between items-center text-sm text-gray-300">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    {documents?.length || 0}
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    {chats?.length || 0}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  {formatDate(updatedAt)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="p-6 border-t border-gray-700 bg-gray-900/50 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
            {userData?.name?.charAt(0)?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">
              {userData?.name || 'User'}
            </div>
            <div className="text-xs text-gray-400 truncate">
              {userData?.email || 'user@example.com'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
