import React, { useState, useEffect, useCallback } from 'react';
import { getMindMap } from '../services/api';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import io from 'socket.io-client';

const MindMapModal = ({ isOpen, onClose, thread }) => {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [mindMapData, setMindMapData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progressInfo, setProgressInfo] = useState({ status: '', message: '', progress: 0 });
  const [socket, setSocket] = useState(null);
  const [timeoutIds, setTimeoutIds] = useState([]); // Track timeouts for cleanup
  const [socketHandledResult, setSocketHandledResult] = useState(false); // Track if socket handled the result
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Cleanup function for timeouts
  const clearAllTimeouts = () => {
    timeoutIds.forEach(id => clearTimeout(id));
    setTimeoutIds([]);
  };

  // Initialize Socket.IO connection
  useEffect(() => {
    if (isOpen) {
      const newSocket = io('http://127.0.0.1:8000');
      
      newSocket.on('connect', () => {
        console.log('Socket connected:', newSocket.id);
        setSocket(newSocket);
      });
      
      newSocket.on('mindmap_progress', (data) => {
        console.log('Mind map progress:', data);
        setProgressInfo(data);
        
        if (data.status === 'success') {
          setSocketHandledResult(true);
          const timeoutId = setTimeout(() => {
            setLoading(false);
          }, 500);
          setTimeoutIds(prev => [...prev, timeoutId]);
        } else if (data.status === 'error') {
          setSocketHandledResult(true);
          setError(data.message);
          const timeoutId = setTimeout(() => {
            setLoading(false);
          }, 1000);
          setTimeoutIds(prev => [...prev, timeoutId]);
        } else if (data.status === 'not_found') {
          setSocketHandledResult(true);
          // Don't set this as an error, handle it as a special case
          const timeoutId = setTimeout(() => {
            setLoading(false);
          }, 2000); // Show longer to read the message
          setTimeoutIds(prev => [...prev, timeoutId]);
        }
      });
      
      newSocket.on('disconnect', () => {
        console.log('Socket disconnected');
        setSocket(null);
      });
      
      return () => {
        clearAllTimeouts();
        newSocket.disconnect();
        setSocket(null);
      };
    } else {
      // Clear states when modal closes
      clearAllTimeouts();
      setSocketHandledResult(false);
      setProgressInfo({ status: '', message: '', progress: 0 });
      setError(null);
      setLoading(false);
    }
  }, [isOpen]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearAllTimeouts();
    };
  }, []);

  // Reset states when modal closes
  useEffect(() => {
    if (!isOpen) {
      clearAllTimeouts();
      setSocketHandledResult(false);
      setProgressInfo({ status: '', message: '', progress: 0 });
      setError(null);
      setLoading(false);
      setSelectedDocument(null);
      setMindMapData(null);
      setNodes([]);
      setEdges([]);
    }
  }, [isOpen, setNodes, setEdges]);

  // Extract thread information and documents
  useEffect(() => {
    if (isOpen && thread) {
      console.log('=== COMPLETE THREAD DATA ANALYSIS ===');
      console.log('Full thread object:', thread);
      console.log('Thread keys:', Object.keys(thread));
      console.log('Thread type:', typeof thread);
      
      // Look for thread ID in various possible field names (same as we extract thread_id)
      const threadId = thread.thread_id || thread.id || thread.threadId || thread._id;
      console.log('Extracted thread ID:', threadId);
      
      // Extract documents from the SAME thread object structure
      // Try multiple possible document array locations
      let threadDocuments = [];
      
      // Check various possible document locations in the thread object
      const possibleDocumentArrays = [
        thread.documents,
        thread.docs,
        thread.files,
        thread.document_list,
        thread.attachments
      ];
      
      console.log('=== SEARCHING FOR DOCUMENTS IN THREAD ===');
      possibleDocumentArrays.forEach((docArray, index) => {
        console.log(`Possible document array ${index}:`, docArray);
      });
      
      // Find the first non-empty document array
      threadDocuments = possibleDocumentArrays.find(arr => Array.isArray(arr) && arr.length > 0) || [];
      
      console.log('Selected thread documents array:', threadDocuments);
      console.log('Number of documents found:', threadDocuments.length);
      
      if (threadDocuments.length > 0) {
        const processedDocs = threadDocuments.map((doc, index) => {
          console.log(`=== DOCUMENT ${index} ANALYSIS ===`);
          console.log(`Document object:`, doc);
          console.log(`Document keys:`, Object.keys(doc || {}));
          console.log(`Document values:`, doc);
          
          // Use the exact MongoDB structure - the real document ID is in "docId" field
          const possibleDocIds = [
            doc.docId,        // ← This is the real field from MongoDB!
            doc.id,           
            doc.document_id,
            doc.file_id,
            doc._id,
            doc.uuid,
            doc.doc_id,
            doc.documentId,
            doc.fileId
          ];
          
          console.log(`Possible document IDs:`, possibleDocIds);
          
          // Find the first non-null, non-undefined value (same logic as thread_id)
          const realDocId = possibleDocIds.find(id => id != null && id !== '' && id !== undefined);
          
          console.log(`Selected document ID:`, realDocId);
          console.log(`Document ID type:`, typeof realDocId);
          
          // Use exact MongoDB field names for title
          const possibleTitles = [
            doc.title,        // ← This is the field from MongoDB
            doc.file_name,    // ← Also available in MongoDB
            doc.name,
            doc.filename,
            doc.original_name,
            doc.display_name,
            doc.document_title,
            doc.document_name
          ];
          
          console.log(`Possible titles:`, possibleTitles);
          
          const realTitle = possibleTitles.find(title => title != null && title !== '' && title !== undefined) || `Document ${index + 1}`;
          
          console.log(`Selected title:`, realTitle);
          
          if (!realDocId) {
            console.error(`⚠️  NO VALID DOCUMENT ID FOUND FOR DOCUMENT ${index}`);
            console.error(`Document object:`, doc);
            console.error(`This document will not work with the mind map API`);
            console.error(`Available fields:`, Object.keys(doc || {}));
          } else {
            console.log(`✅ Valid document found: ID="${realDocId}" Title="${realTitle}"`);
          }
          
          return {
            document_id: realDocId || `MISSING_DOC_ID_${index}`,
            document_title: realTitle,
            originalDoc: doc,
            hasValidId: !!realDocId
          };
        });
        
        console.log('=== PROCESSED DOCUMENTS SUMMARY ===');
        processedDocs.forEach((doc, index) => {
          console.log(`Doc ${index}: ID="${doc.document_id}" Title="${doc.document_title}" Valid=${doc.hasValidId}`);
        });
        
        setDocuments(processedDocs);
      } else {
        console.log('=== NO DOCUMENTS FOUND ===');
        console.log('Thread object keys:', Object.keys(thread));
        console.log('Checked document arrays:', possibleDocumentArrays);
        setDocuments([]);
      }
    }
  }, [isOpen, thread]);

  // Convert mind map data to React Flow format
  const convertMindMapToFlow = useCallback((mindMap) => {
    console.log('=== CONVERTING MIND MAP TO FLOW ===');
    console.log('Mind map data:', mindMap);
    
    if (!mindMap || !mindMap.roots || !Array.isArray(mindMap.roots)) {
      console.error('Invalid mind map structure:', mindMap);
      return;
    }

    const newNodes = [];
    const newEdges = [];
    let nodeCounter = 0;

    const processNode = (node, parentId = null, level = 0, index = 0) => {
      const currentNodeId = `node-${nodeCounter++}`;
      
      // Calculate position with better spacing
      const x = level * 350;
      const y = index * 120 + level * 60;

      newNodes.push({
        id: currentNodeId,
        type: 'default',
        position: { x, y },
        data: {
          label: (
            <div className="p-4 min-w-[250px] max-w-[350px]">
              <div className="font-semibold text-sm mb-2 text-gray-800">{node.title}</div>
              {node.description && (
                <div className="text-xs text-gray-600 leading-relaxed">
                  {node.description.length > 150 
                    ? `${node.description.substring(0, 150)}...` 
                    : node.description}
                </div>
              )}
            </div>
          ),
        },
        style: {
          background: level === 0 ? '#3b82f6' : level === 1 ? '#6366f1' : '#e5e7eb',
          color: level <= 1 ? 'white' : 'black',
          border: `2px solid ${level === 0 ? '#1e40af' : level === 1 ? '#4338ca' : '#9ca3af'}`,
          borderRadius: '12px',
          fontSize: '12px',
          boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });

      // Add edge from parent if exists
      if (parentId) {
        newEdges.push({
          id: `edge-${parentId}-${currentNodeId}`,
          source: parentId,
          target: currentNodeId,
          type: 'smoothstep',
          style: { 
            stroke: level <= 1 ? '#4338ca' : '#6b7280', 
            strokeWidth: level === 0 ? 3 : 2 
          },
          animated: level === 0,
        });
      }

      // Process children recursively
      if (node.children && Array.isArray(node.children) && node.children.length > 0) {
        node.children.forEach((child, childIndex) => {
          processNode(child, currentNodeId, level + 1, childIndex);
        });
      }
    };

    // Process all root nodes
    mindMap.roots.forEach((root, rootIndex) => {
      processNode(root, null, 0, rootIndex);
    });

    console.log(`Created ${newNodes.length} nodes and ${newEdges.length} edges`);
    setNodes(newNodes);
    setEdges(newEdges);
  }, [setNodes, setEdges]);

  const handleDocumentSelect = async (documentId, documentTitle) => {
    // Clear any previous states and timeouts
    clearAllTimeouts();
    setSelectedDocument({ id: documentId, title: documentTitle });
    setLoading(true);
    setError(null);
    setMindMapData(null);
    setNodes([]);
    setEdges([]);
    setSocketHandledResult(false);
    setProgressInfo({ status: 'starting', message: 'Initializing mind map request...', progress: 0 });
    
    try {
      // Extract thread ID
      const threadId = thread.thread_id || thread.id || thread.threadId || thread._id;
      
      console.log('=== PRE-API CALL VALIDATION ===');
      console.log('Thread Object Keys:', Object.keys(thread));
      console.log('Thread Object:', thread);
      console.log('Extracted Thread ID:', threadId, typeof threadId);
      console.log('Selected Document ID:', documentId, typeof documentId);
      console.log('Document Title:', documentTitle);
      console.log('Socket ID:', socket?.id);
      
      // Additional validation
      if (!threadId) {
        console.error('=== THREAD ID EXTRACTION FAILED ===');
        console.error('Available thread fields:', Object.keys(thread));
        console.error('Thread values:', thread);
        throw new Error('Thread ID not found in thread object');
      }
      
      if (!documentId) {
        console.error('=== DOCUMENT ID MISSING ===');
        throw new Error('Document ID is required');
      }
      
      // Type validation
      console.log('=== TYPE VALIDATION ===');
      console.log('Thread ID type:', typeof threadId, 'value:', threadId);
      console.log('Document ID type:', typeof documentId, 'value:', documentId);
      
      // Convert to strings if needed (some APIs expect strings)
      const finalThreadId = String(threadId);
      const finalDocumentId = String(documentId);
      
      console.log('=== FINAL VALUES FOR API ===');
      console.log('Final Thread ID:', finalThreadId, typeof finalThreadId);
      console.log('Final Document ID:', finalDocumentId, typeof finalDocumentId);
      
      // Use the API service with socket ID for progress updates
      const response = await getMindMap(finalThreadId, finalDocumentId, socket?.id);
      
      console.log('=== API SUCCESS ===');
      console.log('Response:', response);
      
      if (response && response.status) {
        // Check if this is a "not found" response
        if (response.not_found) {
          console.log('Mind map not found - handled by Socket.IO');
          // Socket.IO has already handled this case, don't override
          // The progress UI will transition to "not found" state via socket events
          return;
        }
        
        console.log('Mind map fetched successfully!');
        setMindMapData(response.mind_map);
        convertMindMapToFlow(response.mind_map);
        setProgressInfo({ status: 'complete', message: 'Mind map loaded successfully!', progress: 100 });
        
        // Only control loading if socket hasn't handled it
        if (!socketHandledResult) {
          const timeoutId = setTimeout(() => {
            setLoading(false);
          }, 800);
          setTimeoutIds(prev => [...prev, timeoutId]);
        }
      } else {
        const errorMsg = response?.message || response?.error || 'Failed to fetch mind map';
        throw new Error(errorMsg);
      }
    } catch (apiError) {
      console.error('=== HANDLE DOCUMENT SELECT ERROR ===');
      console.error('Error:', apiError);
      
      // Only handle error if socket hasn't already handled it
      if (!socketHandledResult) {
        const timeoutId = setTimeout(() => {
          let errorMessage = 'Unable to fetch mind map. ';
          
          if (apiError.response?.status === 401) {
            errorMessage += 'Authentication failed. Please log in again.';
          } else if (apiError.response?.status === 422) {
            errorMessage += 'Request format error. Check console for details.';
            console.error('422 Error - likely thread_id or document_id format issue');
          } else if (apiError.response?.status === 404) {
            errorMessage += 'Mind map not found for this document.';
          } else {
            errorMessage += apiError.message || 'Please try again.';
          }
          
          setError(errorMessage);
          setProgressInfo({ status: 'error', message: errorMessage, progress: 0 });
          setLoading(false);
        }, 500); // Shorter delay for API-only errors
        setTimeoutIds(prev => [...prev, timeoutId]);
      }
    }
  };

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-[90vw] h-[90vh] bg-white rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">Mind Map Visualization</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex h-[calc(100%-4rem)]">
          {/* Sidebar */}
          <div className="w-1/4 border-r border-gray-200 p-4 overflow-y-auto">
            <h3 className="font-medium text-gray-700 mb-3">Select Document</h3>
            
            {/* Test Button */}
            <button
              onClick={() => {
                const mockMindMap = {
                  "user_id": "test_user",
                  "thread_id": "test_thread",
                  "document_id": "test_doc",
                  "roots": [
                    {
                      "id": "1",
                      "title": "Certificate of Completion",
                      "description": "A certificate of completion is a document that confirms an individual has successfully finished a training program.",
                      "parent_id": null,
                      "children": [
                        {
                          "id": "2",
                          "title": "Recipient",
                          "description": "The recipient is the individual to whom a certificate is awarded.",
                          "parent_id": "1",
                          "children": []
                        },
                        {
                          "id": "3",
                          "title": "Issuing Organization", 
                          "description": "The entity responsible for providing the certificate.",
                          "parent_id": "1",
                          "children": []
                        }
                      ]
                    }
                  ]
                };
                setSelectedDocument({ id: 'test_doc', title: 'Test Document' });
                setMindMapData(mockMindMap);
                convertMindMapToFlow(mockMindMap);
                setError(null);
              }}
              className="w-full mb-4 p-3 bg-green-50 border border-green-300 text-green-700 rounded-lg hover:bg-green-100 transition-colors text-sm"
            >
              🧪 Test Visualization
            </button>
            
            {documents.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-gray-400 mb-3">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-sm text-gray-500 mb-2">No documents found</p>
                <p className="text-xs text-gray-400">Upload documents to generate mind maps</p>
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc, index) => (
                  <button
                    key={doc.document_id || index}
                    onClick={() => {
                      if (!doc.hasValidId) {
                        console.error('Cannot generate mind map: Invalid document ID');
                        setError(`Cannot generate mind map for "${doc.document_title}": No valid document ID found`);
                        return;
                      }
                      handleDocumentSelect(doc.document_id, doc.document_title);
                    }}
                    disabled={!doc.hasValidId}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      !doc.hasValidId 
                        ? 'bg-red-50 border-red-200 text-red-400 cursor-not-allowed'
                        : selectedDocument?.id === doc.document_id
                        ? 'bg-blue-50 border-blue-300 text-blue-700'
                        : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium text-sm truncate" title={doc.document_title}>
                        {doc.document_title}
                      </div>
                      {!doc.hasValidId && (
                        <div className="text-red-400 text-xs ml-2">⚠️</div>
                      )}
                    </div>
                    <div className="text-xs mt-1">
                      {doc.hasValidId ? (
                        <>
                          <span className="text-gray-500">Click to generate mind map</span>
                          <br />
                          <span className="text-gray-400 font-mono">ID: {doc.document_id}</span>
                        </>
                      ) : (
                        <span className="text-red-400">No valid document ID found</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mind Map Area */}
          <div className="flex-1 relative">
            {loading && (
              <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center z-10">
                <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                    
                    <h3 className="text-lg font-semibold text-gray-800 mb-2">
                      Loading Mind Map
                    </h3>
                    
                    <div className="mb-4">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
                          style={{ width: `${progressInfo.progress}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>{progressInfo.progress}%</span>
                        <span>{progressInfo.status}</span>
                      </div>
                    </div>
                    
                    <p className="text-gray-600 text-sm">
                      {progressInfo.message || 'Searching for mind map...'}
                    </p>
                    
                    {progressInfo.status === 'searching' && (
                      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p className="text-xs text-blue-700">
                          🔍 Searching for existing mind map...
                        </p>
                      </div>
                    )}
                    
                    {progressInfo.status === 'checking' && (
                      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p className="text-xs text-blue-700">
                          📋 Checking available mind maps...
                        </p>
                      </div>
                    )}
                    
                    {progressInfo.status === 'loading' && (
                      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p className="text-xs text-blue-700">
                          📄 Loading mind map data...
                        </p>
                      </div>
                    )}
                    
                    {progressInfo.status === 'not_found' && (
                      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                        <p className="text-xs text-blue-700">
                          📄 Mind map not available for this document
                        </p>
                        <p className="text-xs text-blue-500 mt-1">
                          Mind maps are generated during document processing
                        </p>
                      </div>
                    )}
                    
                    {progressInfo.status === 'error' && (
                      <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-xs text-red-700">
                          ❌ {progressInfo.message}
                        </p>
                        <p className="text-xs text-red-500 mt-1">
                          Please try again or contact support
                        </p>
                      </div>
                    )}
                    
                    {progressInfo.status === 'complete' && (
                      <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                        <p className="text-xs text-green-700">
                          ✅ Mind map loaded successfully!
                        </p>
                      </div>
                    )}
                    
                    {socket?.connected && (
                      <div className="mt-4 flex items-center justify-center text-xs text-green-600">
                        <div className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></div>
                        Real-time updates connected
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="absolute inset-0 flex items-center justify-center p-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-red-700 max-w-md text-center">
                  <h4 className="font-medium mb-2">Unable to Load Mind Map</h4>
                  <p className="text-sm mb-4">{error}</p>
                  <button 
                    onClick={() => {
                      setError(null);
                      setSelectedDocument(null);
                    }}
                    className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md text-sm transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            )}

            {!selectedDocument && !loading && !error && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" />
                  </svg>
                  <p className="text-lg font-medium">Mind Map Viewer</p>
                  <p className="text-sm mt-1">
                    {documents.length > 0 
                      ? "Select a document to generate and view its mind map"
                      : "No documents available. Upload documents to create mind maps."}
                  </p>
                </div>
              </div>
            )}

            {selectedDocument && !loading && !error && !mindMapData && progressInfo.status === 'not_found' && (
              <div className="absolute inset-0 flex items-center justify-center p-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-blue-700 max-w-md text-center">
                  <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h4 className="font-medium mb-2">Mind Map Not Available</h4>
                  <p className="text-sm mb-4">
                    No mind map found for "{selectedDocument.title}". Mind maps are generated during document processing.
                  </p>
                  <button 
                    onClick={() => {
                      setSelectedDocument(null);
                      setProgressInfo({ status: '', message: '', progress: 0 });
                    }}
                    className="px-4 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-md text-sm transition-colors"
                  >
                    Select Another Document
                  </button>
                </div>
              </div>
            )}

            {mindMapData && nodes.length > 0 && (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                fitView
                className="bg-gray-50"
              >
                <Controls position="top-left" />
                <MiniMap 
                  position="bottom-right"
                  nodeColor="#3b82f6"
                  maskColor="rgba(255, 255, 255, 0.7)"
                />
                <Background variant="dots" gap={12} size={1} />
              </ReactFlow>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MindMapModal;
