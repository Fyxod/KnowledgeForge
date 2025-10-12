import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import ChatWindow from '../components/ChatWindow';
import { uploadFiles, sendQuery, getUser, createEmptyThread, updateThreadName, deleteThread } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { useMode } from '../contexts/ModeContext';

export default function ChatPage({ userData, setUserData }) {
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadingFiles, setUploadingFiles] = useState([]);

  const { isConnected, connectionStatus, subscribeToThreadUpdates } = useWebSocket(
    userData?.userId, 
    !!userData?.userId
  );

  const { getCurrentModeConfig } = useMode();
  const currentModeConfig = getCurrentModeConfig();

  useEffect(() => {
    const loadUserData = async () => {
      try {
        if (userData?.userId) {
          const response = await getUser(userData.userId);
          setUserData(response.user);
          
          const threadsArray = Object.entries(response.user.threads || {}).map(([id, data]) => ({
            id,
            ...data,
          }));
          setThreads(threadsArray);
        }
      } catch (error) {
        console.error('Failed to load user data:', error);
        setError('Failed to load data. Please refresh the page.');
      } finally {
        setLoading(false);
      }
    };

    loadUserData();
  }, [userData?.userId, setUserData]);

  useEffect(() => {
    if (!isConnected || !userData?.userId) {
      return;
    }

    console.log('[WebSocket] Setting up thread update subscription');

    const unsubscribe = subscribeToThreadUpdates((data) => {
      console.log('[WebSocket] Received thread update:', data);
      
      if (data.threadId && data.newTitle) {
        setThreads(prevThreads => 
          prevThreads.map(thread => 
            thread.id === data.threadId 
              ? { ...thread, thread_name: data.newTitle, updatedAt: new Date().toISOString() }
              : thread
          )
        );
        
        console.log(`[WebSocket] Updated thread ${data.threadId} name to: ${data.newTitle}`);
      }
    });

    return () => {
      console.log('[WebSocket] Cleaning up thread update subscription');
      unsubscribe();
    };
  }, [isConnected, userData?.userId, subscribeToThreadUpdates]);

  const refreshUserData = async () => {
    try {
      if (userData?.userId) {
        const response = await getUser(userData.userId);
        setUserData(response.user);
        
        const threadsArray = Object.entries(response.user.threads || {}).map(([id, data]) => ({
          id,
          ...data,
        }));
        setThreads(threadsArray);
      }
    } catch (error) {
      console.error('Failed to refresh user data:', error);
    }
  };

  const handleSendMessage = async (text) => {
    if (!selectedThreadId || isSending) return;

    const userMessage = {
      type: 'user',
      content: text,
      timestamp: new Date().toISOString()
    };

    setThreads(prevThreads => 
      prevThreads.map(thread => {
        if (thread.id === selectedThreadId) {
          return {
            ...thread,
            chats: [...(thread.chats || []), userMessage],
            updatedAt: new Date().toISOString()
          };
        }
        return thread;
      })
    );

    setIsSending(true);
    try {
      const response = await sendQuery(selectedThreadId, text);
      
      console.log('Query response:', response);
      console.log('Documents used in response:', response.documents_used);
      console.log('Mode used:', currentModeConfig.name);
      
      await refreshUserData();
      
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('Failed to send message. Please try again.');
      
      await refreshUserData();
    } finally {
      setIsSending(false);
    }
  };

  const handleFileUpload = async (files) => {
    console.log('handleFileUpload called:', { 
      filesCount: files.length, 
      selectedThreadId,
      selectedThreadName: currentThread?.thread_name 
    });
    
    setIsUploading(true);
    setUploadingFiles(files);
    setError(null);
    
    try {
      const response = await uploadFiles(
        files, 
        selectedThreadId,
        selectedThreadId ? null : 'Document Chat'
      );
      
      console.log('Upload response:', response);
      
      if (response.thread_id && !selectedThreadId) {
        console.log('Selecting new thread:', response.thread_id);
        setSelectedThreadId(response.thread_id);
      } else if (response.thread_id && selectedThreadId) {
        console.log('Files added to existing thread:', selectedThreadId);
      }
      
      await refreshUserData();
      
    } catch (error) {
      console.error('File upload failed:', error);
      setError('File upload failed. Please try again.');
      throw error;
    } finally {
      setIsUploading(false);
      setUploadingFiles([]);
    }
  };

  const handleCreateThread = async () => {
    console.log('handleCreateThread called');
    try {
      const response = await createEmptyThread(`Chat ${new Date().toLocaleTimeString()}`);
      console.log('New thread created:', response);
      
      if (response.thread_id) {
        console.log('Selecting new thread:', response.thread_id);
        setSelectedThreadId(response.thread_id);
      }
      
      await refreshUserData();
      
    } catch (error) {
      console.error('Failed to create thread:', error);
      setError('Failed to create new thread. Please try again.');
      throw error;
    }
  };

  const handleUpdateThreadName = async (threadId, newName) => {
    console.log('handleUpdateThreadName called:', { threadId, newName });
    try {
      const response = await updateThreadName(threadId, newName);
      console.log('Thread name updated:', response);
      
      await refreshUserData();
      
    } catch (error) {
      console.error('Failed to update thread name:', error);
      setError('Failed to update thread name. Please try again.');
      throw error;
    }
  };
  
  const handleDeleteThread = async (threadId) => {
    console.log('handleDeleteThread called:', threadId);
    try {
      if (confirm('Are you sure you want to delete this thread? This action cannot be undone.')) {
        const response = await deleteThread(threadId);
        console.log('Thread deleted:', response);
        
        if (threadId === selectedThreadId) {
          setSelectedThreadId(null);
        }
        
        setThreads(prevThreads => prevThreads.filter(thread => thread.id !== threadId));
      }
    } catch (error) {
      console.error('Failed to delete thread:', error);
      const errorMessage = error.response?.data?.error || 'Failed to delete thread. Please try again.';
      setError(errorMessage);
    }
  };

  const currentThread = threads.find(t => t.id === selectedThreadId);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="text-gray-600">Loading your data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
      <div className="flex-1 flex overflow-hidden">
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-4 text-white hover:text-gray-200"
            >
              ×
            </button>
          </div>
        </div>
      )}

      <Sidebar
        threads={threads}
        selectedId={selectedThreadId}
        onSelect={setSelectedThreadId}
        userData={userData}
        onCreateThread={handleCreateThread}
        onUpdateThreadName={handleUpdateThreadName}
        onDeleteThread={handleDeleteThread}
      />
      
      <ChatWindow 
        thread={currentThread} 
        onSend={handleSendMessage}
        onFileUpload={handleFileUpload}
        isUploading={isUploading}
        isSending={isSending}
        onUpdateThreadName={handleUpdateThreadName}
        uploadingFiles={uploadingFiles}
      />
      </div>
    </div>
  );
}
