import React from 'react';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';

export default function ChatWindow({ thread, onSend, onFileUpload, isUploading, isSending, uploadingFiles = [] }) {
  if (!thread) {
    return (
      <div className="flex-1 flex flex-col bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md mx-auto p-8">
            <div className="w-16 h-16 mx-auto mb-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">
              Welcome to Samsung Prism
            </h2>
            <p className="text-gray-600 text-lg mb-6">
              Click "New Chat" in the sidebar to start a conversation, or upload files below to create a document-based thread.
            </p>
            <div className="bg-white p-4 rounded-lg shadow-md mb-6">
              <p className="text-sm text-gray-500">
                <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Tip: Upload PDFs, images, or documents to get AI-powered insights
              </p>
            </div>
          </div>
        </div>
        
        <div className="border-t bg-white">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 text-center">
              Or Upload Files to Create a New Thread
            </h3>
            <ChatInput 
              onSend={() => {}}
              onFileUpload={onFileUpload}
              isUploading={isUploading}
              disabled={true}
              placeholder="Upload files to get started..."
              hideTextInput={true}
              uploadingFiles={uploadingFiles}
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
    <div className="flex-1 flex flex-col h-full bg-white">
      <div className="p-6 border-b bg-gradient-to-r from-white to-gray-50 shadow-sm">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-1">{thread.thread_name}</h2>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {thread.documents?.length || 0} documents
              </span>
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                {thread.chats?.length || 0} messages
              </span>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                <span>AI Ready</span>
              </div>
            </div>
          </div>
          
          {thread.documents && thread.documents.length > 0 && (
            <div className="hidden md:flex items-center gap-2">
              <span className="text-xs text-gray-500">Documents:</span>
              <div className="flex gap-1">
                {thread.documents.slice(0, 5).map((doc, idx) => (
                  <div 
                    key={idx}
                    className="bg-gray-100 px-2 py-1 rounded text-xs flex items-center gap-1"
                    title={doc.title}
                  >
                    <span className="text-xs font-mono text-gray-600">{getFileIcon(doc.type)}</span>
                    <span className="max-w-20 truncate">{doc.title}</span>
                  </div>
                ))}
                {thread.documents.length > 5 && (
                  <div className="bg-gray-100 px-2 py-1 rounded text-xs">
                    +{thread.documents.length - 5}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-4xl mx-auto p-6">
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
                  timestamp: msg.timestamp || new Date().toISOString()
                };
                
                return <MessageBubble key={i} message={safeMessage} />;
              })}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">🚀</div>
              <h3 className="text-xl font-semibold text-gray-700 mb-2">
                Ready to start chatting!
              </h3>
              <p className="text-gray-500 mb-6">
                {thread.documents?.length > 0 
                  ? "Your documents are loaded. Ask me anything about them!"
                  : "Upload some documents or start asking questions."}
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

      <div className="border-t bg-white">
        <ChatInput 
          onSend={onSend} 
          onFileUpload={onFileUpload}
          isUploading={isUploading}
          disabled={isSending}
          uploadingFiles={uploadingFiles}
        />
      </div>
    </div>
  );
}
