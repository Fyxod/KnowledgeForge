import React, { useState, useEffect } from 'react';
import { getWordCloud } from '../services/api';

export default function WordCloudModal({ 
  isOpen, 
  onClose, 
  threadId, 
  availableDocuments = [] 
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDocuments, setSelectedDocuments] = useState(new Set());
  const [maxWords, setMaxWords] = useState(1000);
  const [wordCloudData, setWordCloudData] = useState(null);
  const [error, setError] = useState(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedDocuments(new Set());
      setWordCloudData(null);
      setError(null);
    }
  }, [isOpen]);

  const handleDocumentToggle = (docId) => {
    const newSelected = new Set(selectedDocuments);
    if (newSelected.has(docId)) {
      newSelected.delete(docId);
    } else {
      newSelected.add(docId);
    }
    setSelectedDocuments(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedDocuments.size === availableDocuments.length) {
      setSelectedDocuments(new Set());
    } else {
      setSelectedDocuments(new Set(availableDocuments.map(doc => doc.docId)));
    }
  };

  const handleGenerateWordCloud = async () => {
    if (selectedDocuments.size === 0) {
      setError('Please select at least one document');
      return;
    }

    setIsLoading(true);
    setError(null);
    setWordCloudData(null);

    try {
      const documentIdsArray = Array.from(selectedDocuments);
      console.log('=== WORD CLOUD GENERATION ===');
      console.log('Thread ID:', threadId);
      console.log('Selected Document IDs:', documentIdsArray);
      console.log('Available Documents:', availableDocuments);
      console.log('Max Words:', maxWords);
      
      // Log details about each selected document
      documentIdsArray.forEach(docId => {
        const doc = availableDocuments.find(d => d.docId === docId);
        console.log(`Document ${docId}:`, {
          docId: doc?.docId,
          fileName: doc?.file_name,
          title: doc?.title,
          fullDoc: doc
        });
      });

      // Add timeout for word cloud generation (30 seconds)
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Word cloud generation timed out. Please try again.')), 30000);
      });

      const response = await Promise.race([
        getWordCloud(threadId, documentIdsArray, maxWords),
        timeoutPromise
      ]);

      console.log('Word cloud response:', response);

      if (response.status && response.imageUrl) {
        // Verify the blob URL is valid
        console.log('Image URL created:', response.imageUrl);
        console.log('Blob size:', response.blob?.size, 'bytes');
        console.log('Blob type:', response.blob?.type);
        
        setWordCloudData(response);
      } else {
        setError('Failed to generate word cloud - invalid response');
      }
    } catch (error) {
      console.error('Word cloud generation failed:', error);
      setError(error.message || 'Failed to generate word cloud');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (wordCloudData?.imageUrl) {
      const link = document.createElement('a');
      link.href = wordCloudData.imageUrl;
      link.download = `wordcloud_${threadId}_${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-7xl max-h-[95vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">Word Cloud Generator</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close word cloud modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Left Panel - Document Selection */}
          <div className="w-2/5 border-r border-gray-200 p-6 overflow-y-auto">
            <h3 className="text-lg font-medium text-gray-800 mb-4">Select Documents</h3>
            
            {/* Select All/None */}
            <div className="mb-4">
              <button
                onClick={handleSelectAll}
                className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
              >
                {selectedDocuments.size === availableDocuments.length ? 'Deselect All' : 'Select All'}
              </button>
              <span className="text-sm text-gray-500 ml-2">
                ({selectedDocuments.size} of {availableDocuments.length} selected)
              </span>
            </div>

            {/* Document List */}
            <div className="space-y-2">
              {availableDocuments.map((doc) => (
                <label
                  key={doc.docId}
                  className="flex items-start space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedDocuments.has(doc.docId)}
                    onChange={() => handleDocumentToggle(doc.docId)}
                    className="mt-0.5 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {doc.file_name || doc.title || 'Untitled Document'}
                    </p>
                    {doc.title && doc.file_name && doc.title !== doc.file_name && (
                      <p className="text-xs text-gray-500 truncate">
                        {doc.title}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      ID: {doc.docId}
                    </p>
                  </div>
                </label>
              ))}
              
              {availableDocuments.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <p>No documents available in this thread</p>
                  <p className="text-sm mt-1">Upload some documents first</p>
                </div>
              )}
            </div>

            {/* Settings */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Maximum Words
              </label>
              <input
                type="number"
                min="100"
                max="2000"
                step="100"
                value={maxWords}
                onChange={(e) => setMaxWords(parseInt(e.target.value) || 1000)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerateWordCloud}
              disabled={isLoading || selectedDocuments.size === 0}
              className={`w-full mt-4 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                isLoading || selectedDocuments.size === 0
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Generating Word Cloud...
                </div>
              ) : (
                'Generate Word Cloud'
              )}
            </button>
            
            {isLoading && (
              <div className="mt-3 text-xs text-gray-500 text-center">
                <p>⏳ This may take 10-30 seconds...</p>
                <p>Processing documents and creating visualization</p>
              </div>
            )}
          </div>

          {/* Right Panel - Word Cloud Display */}
          <div className="flex-1 p-6 overflow-y-auto flex flex-col">
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
                <div className="flex">
                  <svg className="w-5 h-5 text-red-400 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <h4 className="text-sm font-medium text-red-800">Error</h4>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {!wordCloudData && !isLoading && !error && (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <p className="text-lg">No word cloud generated yet</p>
                  <p className="text-sm mt-1">Select documents and click "Generate Word Cloud" to begin</p>
                </div>
              </div>
            )}

            {wordCloudData && (
              <div className="flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-800">Generated Word Cloud</h3>
                  <button
                    onClick={handleDownload}
                    className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                  >
                    Download PNG
                  </button>
                </div>
                
                <div className="flex-1 flex items-center justify-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-200 p-4">
                  <img
                    src={wordCloudData.imageUrl}
                    alt="Generated Word Cloud"
                    className="max-w-full max-h-full object-contain"
                    style={{ maxHeight: 'calc(100vh - 300px)' }}
                    onLoad={(e) => {
                      console.log('Image loaded successfully:', {
                        naturalWidth: e.target.naturalWidth,
                        naturalHeight: e.target.naturalHeight,
                        src: e.target.src.substring(0, 50) + '...'
                      });
                    }}
                    onError={(e) => {
                      console.error('Image failed to load:', {
                        src: e.target.src.substring(0, 50) + '...',
                        error: e
                      });
                      setError('Failed to display word cloud image. Try downloading it instead.');
                    }}
                  />
                </div>
                
                {/* Debug info */}
                <div className="mt-2 text-xs text-gray-500">
                  <p>Blob size: {wordCloudData.blob?.size || 0} bytes</p>
                  <p>Blob type: {wordCloudData.blob?.type || 'unknown'}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
