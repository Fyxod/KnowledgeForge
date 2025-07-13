/**
 * ChatInput Component
 * 
 * Provides a comprehensive input interface for sending messages and uploading files.
 * Features include drag-and-drop file upload, message composition, and file management.
 * 
 * Props:
 * - onSend: Function to handle message sending
 * - onFileUpload: Function to handle file uploads
 * - isUploading: Boolean indicating upload in progress
 * - disabled: Boolean to disable input
 * - placeholder: Input placeholder text
 * - hideTextInput: Boolean to hide text input (file upload only mode)
 */

import { useState, useRef, useEffect } from 'react';

export default function ChatInput({ 
  onSend, 
  onFileUpload, 
  isUploading = false, 
  disabled = false, 
  placeholder = "Ask me anything about your documents...",
  hideTextInput = false,
  uploadingFiles = []
}) {
  // Component state
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  
  // Refs for DOM elements
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  /**
   * Auto-resize textarea based on content
   * Maintains maximum height of 120px to prevent excessive growth
   */
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [input]);

  /**
   * Handle message sending
   * Validates input and calls onSend callback
   */
  const handleSend = () => {
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput('');
  };

  /**
   * Handle keyboard shortcuts for sending messages
   * Enter sends message, Shift+Enter creates new line
   */

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);
  };

  const handleFileUpload = async () => {
    if (selectedFiles.length === 0) return;
    
    try {
      await onFileUpload(selectedFiles);
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('File upload failed:', error);
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(files => files.filter((_, i) => i !== index));
  };

  const getFileIcon = (file) => {
    const type = file.type.toLowerCase();
    if (type.includes('pdf')) return '📄';
    if (type.includes('image')) return '🖼️';
    if (type.includes('text')) return '📃';
    if (type.includes('word')) return '📝';
    return '📁';
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    setSelectedFiles(files);
  };

  return (
    <div className="p-6">
      {/* File Upload Area */}
      {selectedFiles.length > 0 && (
        <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm font-medium text-blue-800">
              📎 Selected Files ({selectedFiles.length})
            </span>
            <button
              onClick={handleFileUpload}
              disabled={isUploading}
              className="px-4 py-2 text-sm bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-lg hover:from-green-600 hover:to-emerald-600 disabled:opacity-50 transition-all duration-200 shadow-md"
            >
              {isUploading ? (
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Uploading...
                </div>
              ) : (
                'Upload Files'
              )}
            </button>
          </div>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex justify-between items-center bg-white p-3 rounded-lg shadow-sm">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-xl">{getFileIcon(file)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{file.name}</div>
                    <div className="text-xs text-gray-500">{formatFileSize(file.size)}</div>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="text-red-500 hover:text-red-700 ml-2 w-6 h-6 flex items-center justify-center rounded-full hover:bg-red-50 transition-colors"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div 
        className={`relative bg-white border-2 rounded-2xl shadow-lg transition-all duration-200 ${
          isDragging 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-200 hover:border-gray-300 focus-within:border-blue-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Drag overlay */}
        {isDragging && (
          <div className="absolute inset-0 bg-blue-100 border-2 border-dashed border-blue-400 rounded-2xl flex items-center justify-center z-10">
            <div className="text-center">
              <div className="text-3xl mb-2">📁</div>
              <p className="text-blue-700 font-medium">Drop files here to upload</p>
            </div>
          </div>
        )}

        <div className="flex items-end gap-3 p-4">
          {/* File Upload Button */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            multiple
            className="hidden"
            accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className={`${hideTextInput 
              ? 'p-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700 shadow-lg' 
              : 'p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50'
            } rounded-lg transition-all duration-200 flex-shrink-0`}
            title="Upload Files"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
            </svg>
            {hideTextInput && <span className="ml-2 font-medium text-sm">Upload Files</span>}
          </button>

          {/* Text Input */}
          {!hideTextInput && (
            <>
              <textarea
                ref={textareaRef}
                className="flex-1 resize-none border-0 outline-none bg-transparent text-gray-900 placeholder-gray-500 text-base leading-6 min-h-[24px] max-h-[120px]"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={placeholder}
                disabled={disabled}
                rows={1}
              />

              {/* Send Button */}
              <button
                onClick={handleSend}
                disabled={!input.trim() || disabled}
                className="p-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex-shrink-0 shadow-lg transform hover:scale-105"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </>
          )}
          
          {/* When hideTextInput is true, show upload prompt */}
          {hideTextInput && (
            <div className="flex-1 text-center py-4">
              <p className="text-gray-500">
                Click the attach button to upload files and start chatting
              </p>
            </div>
          )}
        </div>
      </div>

      {/* File type info */}
      <div className="mt-3 text-center">
        <p className="text-xs text-gray-500">
          💡 Supports PDF, Word, text files, and images. Drag and drop or click to upload.
        </p>
      </div>
    </div>
  );
}
