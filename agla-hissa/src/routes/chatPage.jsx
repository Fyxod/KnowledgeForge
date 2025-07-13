import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import ChatWindow from '../components/ChatWindow';
import { uploadFiles, sendQuery, getUser, createEmptyThread, updateThreadName } from '../services/api';

export default function ChatPage({ userData, setUserData, onLogout }) {
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadingFiles, setUploadingFiles] = useState([]);

  // Load user data and threads on component mount
  useEffect(() => {
    const loadUserData = async () => {
      try {
        if (userData?.userId) {
          const response = await getUser(userData.userId);
          setUserData(response.user);
          
          // Convert threads object to array
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

  const refreshUserData = async () => {
    try {
      if (userData?.userId) {
        const response = await getUser(userData.userId);
        setUserData(response.user);
        
        // Update threads
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

    // Immediately add user message to the current thread in local state
    const userMessage = {
      type: 'user',
      content: text,
      timestamp: new Date().toISOString()
    };

    // Update local state to show user message immediately
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
      
      // Refresh user data to get the complete updated thread with AI response
      await refreshUserData();
      
      console.log('Query response:', response);
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('Failed to send message. Please try again.');
      
      // On error, refresh to get the accurate state from server
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
    setUploadingFiles(files); // Track which files are being uploaded
    setError(null);
    
    try {
      // If we have a selected thread, add files to it
      // If no thread is selected, create a new one
      const response = await uploadFiles(
        files, 
        selectedThreadId, // Pass the current thread ID (or null for new thread)
        selectedThreadId ? null : 'Document Chat' // Only set thread name for new threads
      );
      
      console.log('Upload response:', response);
      
      // If a new thread was created and no thread was previously selected, select it
      if (response.thread_id && !selectedThreadId) {
        console.log('Selecting new thread:', response.thread_id);
        setSelectedThreadId(response.thread_id);
      } else if (response.thread_id && selectedThreadId) {
        console.log('Files added to existing thread:', selectedThreadId);
      }
      
      // Refresh user data to show updated threads and documents
      await refreshUserData();
      
    } catch (error) {
      console.error('File upload failed:', error);
      setError('File upload failed. Please try again.');
      throw error; // Re-throw to let ChatInput handle the error display
    } finally {
      setIsUploading(false);
      setUploadingFiles([]); // Clear uploading files list
    }
  };

  const handleCreateThread = async () => {
    console.log('handleCreateThread called');
    try {
      const response = await createEmptyThread(`Chat ${new Date().toLocaleTimeString()}`);
      console.log('New thread created:', response);
      
      // Select the new thread
      if (response.thread_id) {
        console.log('Selecting new thread:', response.thread_id);
        setSelectedThreadId(response.thread_id);
      }
      
      // Refresh user data to show the new thread
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
      
      // Refresh user data to show the updated thread name
      await refreshUserData();
      
    } catch (error) {
      console.error('Failed to update thread name:', error);
      setError('Failed to update thread name. Please try again.');
      throw error;
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
    <div className="h-[calc(100vh-4rem)] bg-gray-50 flex">{/* Subtract navbar height */}
      {/* Error Toast */}
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
        onRefresh={refreshUserData}
        onCreateThread={handleCreateThread}
        onUpdateThreadName={handleUpdateThreadName}
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
  );
}
