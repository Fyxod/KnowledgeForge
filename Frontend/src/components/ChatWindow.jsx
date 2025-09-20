import React, { useState } from 'react';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import MindMapModal from './MindMapModal';
import WordCloudModal from './WordCloudModal';
import ModeToggle from './ModeToggle';

export default function ChatWindow({ thread, onSend, onFileUpload, isUploading, isSending, uploadingFiles = [] }) {
  const [isDraggingOverWindow, setIsDraggingOverWindow] = useState(false);
  const [showMindMap, setShowMindMap] = useState(false);
  const [showWordCloud, setShowWordCloud] = useState(false);
  
  // Drag and drop handlers for the entire chat window (works even without thread)
  const handleWindowDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('ChatWindow: dragOver event');
    setIsDraggingOverWindow(true);
  };

  const handleWindowDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('ChatWindow: dragLeave event', e.target, e.relatedTarget);
    
    // Use a timeout to prevent flickering when moving between child elements
    setTimeout(() => {
      // Check if we're still dragging by seeing if another dragOver hasn't happened
      const rect = e.currentTarget.getBoundingClientRect();
      const isOutside = e.clientX < rect.left || e.clientX > rect.right || 
                       e.clientY < rect.top || e.clientY > rect.bottom;
      
      if (isOutside || !e.currentTarget.contains(e.relatedTarget)) {
        setIsDraggingOverWindow(false);
      }
    }, 50);
  };

  const handleWindowDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('ChatWindow: dragEnter event');
    setIsDraggingOverWindow(true);
  };

  const handleWindowDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('ChatWindow: drop event', e.dataTransfer.files);
    setIsDraggingOverWindow(false);
    
    try {
      const files = Array.from(e.dataTransfer?.files || []);
      console.log('ChatWindow: Processing files', files);
      if (files.length > 0) {
        // Validate file types
        const allowedTypes = ['.pdf', '.doc', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.gif'];
        const validFiles = files.filter(file => {
          const extension = '.' + file.name.split('.').pop().toLowerCase();
          return allowedTypes.includes(extension);
        });
        
        console.log('ChatWindow: Valid files', validFiles);
        if (validFiles.length > 0) {
          onFileUpload(validFiles);
        } else {
          console.warn('No valid files dropped. Allowed types:', allowedTypes);
        }
      }
    } catch (error) {
      console.error('Error handling file drop:', error);
      setIsDraggingOverWindow(false);
    }
  };

  if (!thread) {
    return (
      <div 
        className="flex-1 flex flex-col bg-gradient-to-br from-blue-50 to-indigo-100 relative h-full"
        onDragEnter={handleWindowDragEnter}
        onDragOver={handleWindowDragOver}
        onDragLeave={handleWindowDragLeave}
        onDrop={handleWindowDrop}
      >
        {/* Full window drag overlay for welcome screen */}
        {isDraggingOverWindow && (
          <div className="absolute inset-0 bg-blue-100/90 border-4 border-dashed border-blue-400 z-50 flex items-center justify-center pointer-events-none">
            <div className="text-center bg-white rounded-xl p-4 sm:p-8 shadow-2xl pointer-events-none max-w-sm mx-4">
              <div className="text-4xl sm:text-6xl mb-2 sm:mb-4">📁</div>
              <h3 className="text-lg sm:text-2xl font-bold text-blue-700 mb-1 sm:mb-2">Drop files to get started</h3>
              <p className="text-sm sm:text-base text-blue-600">Upload documents to create a new conversation</p>
              <p className="text-xs sm:text-sm text-gray-500 mt-1 sm:mt-2">
                Supports: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, GIF
              </p>
            </div>
          </div>
        )}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-4">
          <div className="min-h-full flex items-center justify-center">
            <div className="text-center max-w-sm sm:max-w-md mx-auto my-8">
              <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-4 sm:mb-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 sm:w-8 sm:h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h2 className="text-lg sm:text-2xl font-bold text-gray-800 mb-2 sm:mb-4">
                Welcome to Knowledge Synthesis Platform
              </h2>
              <p className="text-sm sm:text-lg text-gray-600 mb-4 sm:mb-6">
                Click "New Chat" in the sidebar to start a conversation, or upload files below to create a document-based thread.
              </p>
              <div className="bg-white p-3 sm:p-4 rounded-lg shadow-md mb-4 sm:mb-6">
                <p className="text-xs sm:text-sm text-gray-500">
                  <svg className="w-3 h-3 sm:w-4 sm:h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Tip: Upload PDFs, images, or documents to get AI-powered insights
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="border-t bg-white flex-shrink-0">
          <div className="p-4 sm:p-6">
            <h3 className="text-base sm:text-lg font-semibold text-gray-800 mb-3 sm:mb-4 text-center">
              Or Upload Files to Create a New Thread
            </h3>
            <ChatInput 
              onSend={() => {}}
              onFileUpload={onFileUpload}
              isUploading={isUploading}
              disabled={true}
              placeholder="Upload files to get started..."
              hideTextInput={true}
            />
          </div>
        </div>
      </div>
    );
  }

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

  return (
    <div 
      className="flex-1 flex flex-col bg-white relative h-full"
      onDragEnter={handleWindowDragEnter}
      onDragOver={handleWindowDragOver}
      onDragLeave={handleWindowDragLeave}
      onDrop={handleWindowDrop}
    >
      {/* Full window drag overlay */}
      {isDraggingOverWindow && (
        <div className="absolute inset-0 bg-blue-100/90 border-4 border-dashed border-blue-400 z-50 flex items-center justify-center pointer-events-none">
          <div className="text-center bg-white rounded-xl p-8 shadow-2xl pointer-events-none">
            <div className="text-6xl mb-4">📁</div>
            <h3 className="text-2xl font-bold text-blue-700 mb-2">Drop files anywhere</h3>
            <p className="text-blue-600">Upload documents to enhance this conversation</p>
            <p className="text-sm text-gray-500 mt-2">
              Supports: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, GIF
            </p>
          </div>
        </div>
      )}
      
      <div 
        className="p-4 border-b bg-white shadow-sm flex-shrink-0"
        onDragEnter={handleWindowDragEnter}
        onDragOver={handleWindowDragOver}
        onDragLeave={handleWindowDragLeave}
        onDrop={handleWindowDrop}
      >
        <div className="flex justify-between items-center">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">{thread.thread_name}</h2>
            {thread.documents && thread.documents.length > 0 && (
              <div className="flex items-center gap-2 mt-1">
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-sm text-gray-600">
                  {thread.documents.length} document{thread.documents.length > 1 ? 's' : ''} loaded
                </span>
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-3">
            {/* Mode Toggle */}
            <ModeToggle />
            
            {/* Mind Map Button */}
            {thread.documents && thread.documents.length > 0 && (
              <button
                onClick={() => setShowMindMap(true)}
                className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                title="Generate Mind Map"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="hidden sm:inline">Mind Map</span>
              </button>
            )}
            
            {/* Word Cloud Button */}
            {thread.documents && thread.documents.length > 0 && (
              <button
                onClick={() => setShowWordCloud(true)}
                className="flex items-center gap-2 px-3 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 transition-colors"
                title="Generate Word Cloud"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                <span className="hidden sm:inline">Word Cloud</span>
              </button>
            )}
          </div>
        </div>
      </div>

      <div 
        className="flex-1 overflow-y-auto overflow-x-hidden bg-white"
        onDragEnter={handleWindowDragEnter}
        onDragOver={handleWindowDragOver}
        onDragLeave={handleWindowDragLeave}
        onDrop={handleWindowDrop}
      >
        <div className="w-full max-w-none px-4 sm:px-6 lg:max-w-4xl lg:mx-auto">
          {thread.chats && thread.chats.length > 0 ? (
            <div className="space-y-6">
              {thread.chats.map((msg, i) => {
                if (!msg || typeof msg !== 'object') {
                  console.warn('Invalid message object:', msg);
                  return null;
                }
                
                const safeMessage = {
                  type: msg.type || 'user',
                  content: msg.content || msg.query || msg.result || 'No content',
                  timestamp: msg.timestamp || new Date().toISOString(),
                  documents_used: msg.documents_used || []  // Include citations
                };
                
                return <MessageBubble key={i} message={safeMessage} />;
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="text-3xl mb-3">�</div>
              <h3 className="text-lg font-medium text-gray-700 mb-1">
                Start a conversation
              </h3>
              <p className="text-gray-500 text-sm">
                {thread.documents?.length > 0 
                  ? "Ask questions about your documents"
                  : "Upload documents or ask questions"}
              </p>
            </div>
          )}
          
          {isUploading && uploadingFiles.length > 0 && (
            <div className="flex justify-start mb-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 max-w-md">
                <div className="flex items-center gap-3 mb-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  <span className="text-sm font-medium text-blue-800">
                    Uploading {uploadingFiles.length} file{uploadingFiles.length > 1 ? 's' : ''}...
                  </span>
                </div>
                <div className="space-y-1">
                  {uploadingFiles.slice(0, 3).map((file, index) => (
                    <div key={index} className="text-xs text-blue-600 flex items-center gap-2">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                      </svg>
                      <span className="truncate">{file.name}</span>
                    </div>
                  ))}
                  {uploadingFiles.length > 3 && (
                    <div className="text-xs text-blue-500">
                      +{uploadingFiles.length - 3} more files
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {isSending && (
            <div className="flex justify-start mb-4">
              <div className="bg-gray-200 rounded-lg px-4 py-3 max-w-xs">
                <div className="flex space-x-1 items-center">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t bg-white flex-shrink-0">
        <ChatInput 
          onSend={onSend} 
          onFileUpload={onFileUpload}
          isUploading={isUploading}
          disabled={isSending}
          disableDragDrop={true}  // Disable ChatInput drag/drop since ChatWindow handles it
        />
      </div>

      {/* Mind Map Modal */}
      <MindMapModal 
        isOpen={showMindMap}
        onClose={() => setShowMindMap(false)}
        thread={thread}
      />

      {/* Word Cloud Modal */}
      <WordCloudModal 
        isOpen={showWordCloud}
        onClose={() => setShowWordCloud(false)}
        threadId={thread?.id}
        availableDocuments={thread?.documents || []}
      />
    </div>
  );
}
