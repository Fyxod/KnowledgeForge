import React, { useState } from 'react';

export default function MessageBubble({ message }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!message || typeof message !== 'object') {
    console.warn('MessageBubble received invalid message:', message);
    return null;
  }
  
  const isUser = message.type === 'user';
  const content = message.content || 'No content available';
  
  const formatTimestamp = (timestamp) => {
    try {
      const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp.$date);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const isLongMessage = content.length > 500;
  const displayContent = isLongMessage && !isExpanded 
    ? content.substring(0, 500) + '...' 
    : content;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} group`}>
      <div className={`max-w-3xl ${isUser ? 'order-2' : 'order-1'}`}>
        <div className={`flex items-end gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ${
            isUser 
              ? 'bg-gradient-to-r from-blue-500 to-purple-500' 
              : 'bg-gradient-to-r from-emerald-500 to-teal-500'
          }`}>
            {isUser ? 'U' : 'AI'}
          </div>
          
          <div className={`px-4 py-3 rounded-lg shadow-sm max-w-2xl ${
            isUser 
              ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white' 
              : 'bg-gray-100 border border-gray-200 text-gray-800'
          }`}>
            <div className={`whitespace-pre-wrap leading-relaxed ${
              isUser ? 'text-white' : 'text-gray-800'
            }`}>
              {displayContent}
            </div>
            
            {isLongMessage && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className={`mt-2 text-sm underline ${
                  isUser ? 'text-blue-100 hover:text-white' : 'text-blue-600 hover:text-blue-800'
                }`}
              >
                {isExpanded ? 'Show less' : 'Show more'}
              </button>
            )}
            
            {message.timestamp && (
              <div className={`text-xs mt-2 ${
                isUser ? 'text-blue-100' : 'text-gray-500'
              }`}>
                {formatTimestamp(message.timestamp)}
              </div>
            )}
          </div>
        </div>
        
        <div className={`mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 ${
          isUser ? 'text-right' : 'text-left'
        }`}>
          <button
            onClick={() => navigator.clipboard.writeText(content)}
            className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
            title="Copy message"
          >
            Copy
          </button>
        </div>
      </div>
    </div>
  );
}
