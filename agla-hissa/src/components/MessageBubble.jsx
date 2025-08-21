import React, { useState } from 'react';
import SafeMarkdownRenderer from './SafeMarkdownRenderer';
// import ReactMarkdown from 'react-markdown';
// import remarkGfm from 'remark-gfm';
// import '../styles/markdown.css'; // Temporarily commented out

export default function MessageBubble({ message }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showCitationDropdown, setShowCitationDropdown] = useState(false);
  const [markdownEnabled, setMarkdownEnabled] = useState(true); // Toggle for markdown
  
  if (!message || typeof message !== 'object') {
    console.warn('MessageBubble received invalid message:', message);
    return null;
  }
  
  const isUser = message.type === 'user';
  const content = message.content || 'No content available';
  const documentsUsed = message.documents_used || [];
  
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
      <div className={`w-full max-w-none sm:max-w-3xl ${isUser ? 'order-2' : 'order-1'}`}>
        <div className={`flex items-end gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ${
            isUser 
              ? 'bg-gradient-to-r from-blue-500 to-purple-500' 
              : 'bg-gradient-to-r from-emerald-500 to-teal-500'
          }`}>
            {isUser ? 'U' : 'AI'}
          </div>
          
          <div className={`px-4 py-3 rounded-lg shadow-sm w-full sm:max-w-2xl ${
            isUser 
              ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white' 
              : 'bg-gray-100 border border-gray-200 text-gray-800'
          }`}>
            <div className={`leading-relaxed ${
              isUser ? 'text-white' : 'text-gray-800'
            }`}>
              {isUser ? (
                // For user messages, display as plain text with line breaks
                <div className="whitespace-pre-wrap">
                  {displayContent}
                </div>
              ) : (
                // For AI messages, use safe markdown renderer
                <SafeMarkdownRenderer 
                  content={displayContent} 
                  enableMarkdown={markdownEnabled}
                />
              )}
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
            
            {/* Subtle citation or timestamp display */}
            <div className={`text-xs mt-2 ${
              isUser ? 'text-blue-100' : 'text-gray-500'
            }`}>
              {!isUser && documentsUsed.length > 0 ? (
                // Show document citation for AI messages with dropdown
                <div className="relative">
                  {(() => {
                    // Group citations by document
                    const docGroups = documentsUsed.reduce((groups, doc) => {
                      const docId = doc.metadata?.document_id;
                      const docName = doc.metadata?.title || doc.metadata?.file_name || 'Document';
                      const pageNo = doc.metadata?.page_no;
                      
                      if (!groups[docId]) {
                        groups[docId] = { name: docName, pages: [] };
                      }
                      if (pageNo && !groups[docId].pages.includes(pageNo)) {
                        groups[docId].pages.push(pageNo);
                      }
                      return groups;
                    }, {});
                    
                    const docEntries = Object.values(docGroups);
                    
                    if (docEntries.length === 1) {
                      // Single document case - no dropdown needed
                      const doc = docEntries[0];
                      if (doc.pages.length === 0) {
                        return <span>{doc.name}</span>;
                      } else if (doc.pages.length === 1) {
                        return <span>{doc.name} • Page {doc.pages[0]}</span>;
                      } else {
                        const sortedPages = doc.pages.sort((a, b) => a - b);
                        return <span>{doc.name} • Pages {sortedPages.join(', ')}</span>;
                      }
                    } else {
                      // Multiple documents case - show dropdown
                      const firstDoc = docEntries[0];
                      const restCount = docEntries.length - 1;
                      
                      return (
                        <>
                          <button
                            onClick={() => setShowCitationDropdown(!showCitationDropdown)}
                            className="hover:underline cursor-pointer flex items-center gap-1"
                          >
                            <span>
                              {firstDoc.pages.length === 0 
                                ? `${firstDoc.name} • +${restCount} more docs`
                                : firstDoc.pages.length === 1
                                  ? `${firstDoc.name} p.${firstDoc.pages[0]} • +${restCount} more`
                                  : `${firstDoc.name} p.${firstDoc.pages[0]}+ • +${restCount} more`
                              }
                            </span>
                            <svg 
                              className={`w-3 h-3 transition-transform ${showCitationDropdown ? 'rotate-180' : ''}`}
                              fill="none" 
                              stroke="currentColor" 
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                          
                          {showCitationDropdown && (
                            <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-48 max-w-80">
                              <div className="p-3">
                                <div className="text-xs font-medium text-gray-700 mb-2">Sources:</div>
                                <div className="space-y-2">
                                  {docEntries.map((doc, idx) => (
                                    <div key={idx} className="text-xs">
                                      <div className="font-medium text-gray-800">{doc.name}</div>
                                      {doc.pages.length > 0 && (
                                        <div className="text-gray-600 ml-2">
                                          {doc.pages.length === 1 
                                            ? `Page ${doc.pages[0]}`
                                            : `Pages ${doc.pages.sort((a, b) => a - b).join(', ')}`
                                          }
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          )}
                        </>
                      );
                    }
                  })()}
                </div>
              ) : message.timestamp ? (
                // Show timestamp for user messages or AI messages without citations
                formatTimestamp(message.timestamp)
              ) : null}
            </div>
          </div>
        </div>
        
        <div className={`mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 ${
          isUser ? 'text-right' : 'text-left'
        }`}>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigator.clipboard.writeText(content)}
              className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
              title="Copy message"
            >
              Copy
            </button>
            {!isUser && (
              <button
                onClick={() => setMarkdownEnabled(!markdownEnabled)}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  markdownEnabled 
                    ? 'text-blue-600 bg-blue-50 hover:bg-blue-100' 
                    : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                }`}
                title={markdownEnabled ? 'Disable formatting' : 'Enable formatting'}
              >
                {markdownEnabled ? 'MD' : 'TXT'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
