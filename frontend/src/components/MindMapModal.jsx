import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { getMindMap, getGlobalMindMap } from '../services/api';
import { API_BASE_URL } from '../../url';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Position,
  Handle,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import io from 'socket.io-client';

// Custom node component that handles expansion state
const CustomMindMapNode = ({ data }) => {
  const { title, description, level, isExpanded, onToggle } = data;
  
  return (
    <div 
      className={`p-3 cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-105 relative ${
        isExpanded ? 'ring-2 ring-blue-300 ring-opacity-50' : ''
      }`}
      onClick={(e) => {
        e.stopPropagation();
        if (description && onToggle) {
          onToggle();
        }
      }}
      style={{ 
        minWidth: isExpanded ? '320px' : '220px',
        maxWidth: isExpanded ? '420px' : '280px',
        minHeight: '50px',
        background: level === 0 ? '#3b82f6' : level === 1 ? '#6366f1' : level === 2 ? '#8b5cf6' : '#e5e7eb',
        color: level <= 2 ? 'white' : 'black',
        border: `2px solid ${level === 0 ? '#1e40af' : level === 1 ? '#4338ca' : level === 2 ? '#7c3aed' : '#9ca3af'}`,
        borderRadius: '12px',
        fontSize: '12px',
        boxShadow: isExpanded ? '0 8px 16px rgba(0, 0, 0, 0.15)' : '0 4px 8px rgba(0, 0, 0, 0.1)',
        overflow: 'hidden',
        wordWrap: 'break-word',
      }}
    >
      {/* Connection handles */}
      <Handle 
        type="target" 
        position={Position.Left} 
        style={{ 
          background: 'transparent', 
          border: 'none',
          width: 8,
          height: 8,
          left: -4
        }} 
      />
      <Handle 
        type="source" 
        position={Position.Right} 
        style={{ 
          background: 'transparent', 
          border: 'none',
          width: 8,
          height: 8,
          right: -4
        }} 
      />
      
      {/* Expand/Collapse indicator */}
      {description && (
        <div className="absolute top-2 right-2 w-5 h-5 flex items-center justify-center">
          <svg 
            className={`w-4 h-4 transition-transform duration-200 ${
              level <= 2 ? 'text-white/80' : 'text-gray-500'
            } ${isExpanded ? 'rotate-180' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      )}

      <div className={`font-semibold text-sm leading-tight break-words ${
        description ? 'pr-8' : 'pr-2'
      } ${level <= 2 ? 'text-white' : 'text-gray-800'}`}>
        {title}
      </div>
      
      {isExpanded && description && (
        <div className={`text-xs leading-relaxed mt-3 break-words pr-8 ${
          level <= 2 ? 'text-white/90' : 'text-gray-600'
        }`}>
          {description}
        </div>
      )}
    </div>
  );
};

// Register the custom node type
const nodeTypes = {
  mindMapNode: CustomMindMapNode,
};

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
  const [expandedNodes, setExpandedNodes] = useState(new Set()); // Track expanded nodes
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Get current user ID from localStorage
  const userId = useMemo(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      try {
        const parsed = JSON.parse(userData);
        return parsed.userId;
      } catch (e) {
        console.error('Failed to parse user data:', e);
        return null;
      }
    }
    return null;
  }, []);

  // Initialize WebSocket hook
  const { isConnected, connectionStatus, subscribeToMindMapUpdates } = useWebSocket(userId);

  // Cleanup function for timeouts
  const clearAllTimeouts = () => {
    timeoutIds.forEach(id => clearTimeout(id));
    setTimeoutIds([]);
  };

  // Initialize Socket.IO connection
  // Clear all timeouts and reset states
  const resetAllStates = () => {
    clearAllTimeouts();
    setSocketHandledResult(false);
    setProgressInfo({ status: '', message: '', progress: 0 });
    setError(null);
    setLoading(false);
    setMindMapData(null);
    setNodes([]);
    setEdges([]);
  };

  useEffect(() => {
    if (isOpen) {
      const newSocket = io(API_BASE_URL);
      
      newSocket.on('connect', () => {
        console.log('[WebSocket] Socket connected:', newSocket.id);
        setSocket(newSocket);
      });
      
      newSocket.on('mindmap_progress', (data) => {
        console.log('[WebSocket] Received mindmap_progress event:', data);
        setProgressInfo(data);
        
        if (data.status === 'success') {
          console.log('[WebSocket] Socket reported success, setting socketHandledResult=true');
          setSocketHandledResult(true);
          
          // For success, we don't set loading to false here - let the API response handle it
          // because we need to process the mind map data
          
        } else if (data.status === 'error') {
          console.log('[WebSocket] Socket reported error:', data.message);
          setSocketHandledResult(true);
          setError(data.message || 'Unknown error occurred');
          
          // For errors, immediately set loading to false
          setLoading(false);
          
        } else if (data.status === 'not_found') {
          console.log('[WebSocket] Socket reported not_found');
          setSocketHandledResult(true);
          setError('Mind map not found. Please try another document or generate a new mind map.');
          
          // For not found, immediately set loading to false
          setLoading(false);
        }
      });
      
      newSocket.on('disconnect', () => {
        console.log('[WebSocket] Socket disconnected');
        setSocket(null);
      });
      
      newSocket.on('connect_error', (error) => {
        console.error('[WebSocket] Socket connection error:', error);
        // If there's a connection error, make sure we don't stay in loading state
        setLoading(false);
        setError('WebSocket connection error. Please refresh the page and try again.');
      });
      
      return () => {
        resetAllStates();
        newSocket.disconnect();
        setSocket(null);
      };
    } else {
      // Clear states when modal closes
      resetAllStates();
    }
  }, [isOpen]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearAllTimeouts();
    };
  }, []);

  // Subscribe to mind map updates
  useEffect(() => {
    if (!isOpen || !isConnected || !userId || !thread) return;
    
    // Extract thread ID
    const threadId = thread.thread_id || thread.id || thread.threadId || thread._id;
    if (!threadId) {
      console.warn('[MindMap] Cannot subscribe to mind map updates: No thread ID found');
      return;
    }

    console.log('[MindMap] 🔔 Setting up mind map WebSocket subscription for thread:', threadId);
    
    // Subscribe to mind map updates
    const unsubscribe = subscribeToMindMapUpdates(threadId, (data) => {
      console.log('[MindMap] 🔔 Received mind map update from WebSocket:', data);
      
      if (data.status) {
        // Mind map has been created, let's fetch it automatically
        if (selectedDocument && selectedDocument.id === 'global') {
          // If global mind map is already selected, refresh it
          console.log('[MindMap] Auto-refreshing global mind map');
          handleGlobalMindMap(threadId);
        } else if (selectedDocument) {
          // If a document-specific mind map is selected, refresh it
          console.log('[MindMap] Auto-refreshing document mind map for:', selectedDocument.id);
          handleDocumentSelect(selectedDocument.id, selectedDocument.title);
        } else {
          // If no mind map is selected, load the global one
          console.log('[MindMap] Auto-loading global mind map (no selection)');
          handleGlobalMindMap(threadId);
        }
      }
    });
    
    return () => {
      console.log('[MindMap] 🔕 Unsubscribing from mind map updates');
      unsubscribe();
    };
  }, [isOpen, isConnected, userId, thread, subscribeToMindMapUpdates, selectedDocument]);

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
      setExpandedNodes(new Set()); // Reset expanded nodes
      setNodes([]);
      setEdges([]);
    }
  }, [isOpen, setNodes, setEdges]);

  // Extract thread information and documents
  useEffect(() => {
    if (isOpen && thread) {
      // Look for thread ID in various possible field names
      const threadId = thread.thread_id || thread.id || thread.threadId || thread._id;
      
      // Extract documents from the thread object structure
      let threadDocuments = [];
      
      // Check various possible document locations in the thread object
      const possibleDocumentArrays = [
        thread.documents,
        thread.docs,
        thread.files,
        thread.document_list,
        thread.attachments
      ];
      
      // Find the first non-empty document array
      threadDocuments = possibleDocumentArrays.find(arr => Array.isArray(arr) && arr.length > 0) || [];
      
      if (threadDocuments.length > 0) {
        const processedDocs = threadDocuments.map((doc, index) => {
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
          
          const realDocId = possibleDocIds.find(id => id != null && id !== '' && id !== undefined);
          
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
          
          const realTitle = possibleTitles.find(title => title != null && title !== '' && title !== undefined) || `Document ${index + 1}`;
          
          
          return {
            document_id: realDocId || `MISSING_DOC_ID_${index}`,
            document_title: realTitle,
            originalDoc: doc,
            hasValidId: !!realDocId
          };
        });
        
        setDocuments(processedDocs);
      } else {
        setDocuments([]);
      }
    }
  }, [isOpen, thread]);

  // Convert mind map data to React Flow format
  const convertMindMapToFlow = useCallback((mindMap) => {
    console.log('Converting mind map to flow format:', mindMap);
    
    if (!mindMap || !mindMap.roots || !Array.isArray(mindMap.roots)) {
      console.error('Invalid mind map structure in convertMindMapToFlow:', mindMap);
      return;
    }

    const newNodes = [];
    const newEdges = [];
    const nodeIds = new Set(); // Track created node IDs
    let nodeCounter = 0;
    
    // BOTTOM-UP APPROACH: Calculate space requirements from leaf nodes upward
    const calculateNodeSpace = (node) => {
      if (!node.children || node.children.length === 0) {
        // Leaf node - needs minimal space
        node._requiredHeight = 100; // Base height for leaf nodes
        return node._requiredHeight;
      }
      
      // Parent node - calculate space needed for all children first
      let totalChildrenHeight = 0;
      node.children.forEach(child => {
        totalChildrenHeight += calculateNodeSpace(child); // Recursive bottom-up
      });
      
      // Parent needs at least as much space as its children, plus some padding
      const minSpacing = 20; // Minimum gap between children
      const paddingPerChild = node.children.length * minSpacing;
      node._requiredHeight = Math.max(100, totalChildrenHeight + paddingPerChild);
      
      return node._requiredHeight;
    };

    // Phase 1: Calculate space requirements bottom-up for all trees
    mindMap.roots.forEach(root => {
      calculateNodeSpace(root);
    });

    // Phase 2: Position nodes using the calculated space requirements
    const processNode = (node, parentId = null, level = 0, allocatedY = 0, allocatedHeight = null) => {
      const currentNodeId = `node-${nodeCounter++}`;
      nodeIds.add(currentNodeId); // Track this node ID
      
      // Use calculated height if not provided
      const height = allocatedHeight || node._requiredHeight;
      
      // Calculate position
      const horizontalSpacing = 450;
      
      let x, y;
      
      if (level === 0) {
        // Root node - center it
        x = 200;
        y = allocatedY + (height / 2);
      } else {
        // Child nodes - position relative to parent
        x = 200 + (level * horizontalSpacing);
        y = allocatedY + (height / 2); // Center in allocated space
      }

      const isExpanded = expandedNodes.has(currentNodeId);
      
      newNodes.push({
        id: currentNodeId,
        type: 'mindMapNode',
        position: { x, y },
        data: {
          title: node.title || 'Untitled',
          description: node.description || '',
          level: level,
          isExpanded: expandedNodes.has(currentNodeId),
          onToggle: () => {
            setExpandedNodes(prev => {
              const newSet = new Set(prev);
              if (newSet.has(currentNodeId)) {
                newSet.delete(currentNodeId);
              } else {
                newSet.add(currentNodeId);
              }
              return newSet;
            });
          }
        },
      });

      // Add edge from parent if exists - only if both nodes exist
      if (parentId && nodeIds.has(parentId) && nodeIds.has(currentNodeId)) {
        newEdges.push({
          id: `edge-${parentId}-${currentNodeId}`,
          source: parentId,
          target: currentNodeId,
          type: 'bezier',
          style: { 
            stroke: level === 0 ? '#3b82f6' : level === 1 ? '#6366f1' : '#8b5cf6',
            strokeWidth: level === 0 ? 3 : level === 1 ? 2.5 : 2,
          },
          animated: level === 0,
          markerEnd: {
            type: 'arrowclosed',
            width: 15,
            height: 15,
          },
          // Add curvature for more flowing lines
          pathOptions: {
            curvature: 0.6
          }
        });
      }

      // Process children using their pre-calculated space requirements
      if (node.children && Array.isArray(node.children) && node.children.length > 0) {
        let currentChildY = allocatedY;
        
        node.children.forEach((child, index) => {
          if (!child) return; // Skip null/undefined children
          
          const childHeight = child._requiredHeight || 100;
          
          // Position child in its allocated space
          processNode(child, currentNodeId, level + 1, currentChildY, childHeight);
          
          // Move to next child position
          currentChildY += childHeight;
        });
      }
    };

    // Phase 3: Process all root nodes using their calculated heights
    try {
      let currentRootY = 50; // Start with some top margin
      
      mindMap.roots.forEach((root, index) => {
        if (!root) return; // Skip null/undefined roots
        
        const rootHeight = root._requiredHeight || 200;
        processNode(root, null, 0, currentRootY, rootHeight);
        currentRootY += rootHeight + 50; // Add gap between root trees
      });
    } catch (error) {
      console.error('Error processing mind map:', error);
    }

    // Finish up
    setNodes(newNodes);
    setEdges(newEdges);
  }, [setNodes, setEdges, expandedNodes]);

  // Update nodes when expandedNodes changes
  useEffect(() => {
    if (mindMapData && nodes.length > 0) {
      setNodes(currentNodes => 
        currentNodes.map(node => ({
          ...node,
          data: {
            ...node.data,
            isExpanded: expandedNodes.has(node.id)
          }
        }))
      );
    }
  }, [expandedNodes, setNodes]);

  const handleGlobalMindMap = async (threadId) => {
    // Clear any previous states and timeouts
    clearAllTimeouts();
    setSelectedDocument({ id: 'global', title: 'Global Mind Map' });
    setLoading(true);
    setError(null);
    setMindMapData(null);
    setNodes([]);
    setEdges([]);
    setSocketHandledResult(false);
    setExpandedNodes(new Set()); // Reset expanded nodes for new global map
    setProgressInfo({ status: 'starting', message: 'Initializing global mind map request...', progress: 0 });
    
    try {
      // Extract thread ID if not provided
      const finalThreadId = threadId || thread.thread_id || thread.id || thread.threadId || thread._id;
      
      // Additional validation
      if (!finalThreadId) {
        throw new Error('Thread ID not found in thread object');
      }
      
      // Convert to string if needed (some APIs expect strings)
      const threadIdStr = String(finalThreadId);
      
      console.log('=== GLOBAL MIND MAP REQUEST ===');
      console.log('Thread ID:', threadIdStr, typeof threadIdStr);
      
      // Use the global mind map API service with socket ID for progress updates
      const response = await getGlobalMindMap(threadIdStr, socket?.id);
      
      console.log('=== GLOBAL MIND MAP RESPONSE ===');
      console.log('Response:', response);
      
      // If socket already handled the result (e.g. not_found or error), don't proceed
      if (socketHandledResult) {
        console.log('Socket already handled the result, not processing API response');
        return;
      }
      
      if (response && response.status) {
        // Check if this is a "not found" response
        if (response.not_found) {
          console.log('Mind map not found via API response');
          setError('Global mind map not found. Please try generating a new one.');
          setLoading(false);
          return;
        }
        
        console.log('Setting mind map data:', response.data);
        
        // Check if the mind map data has the expected structure
        if (!response.data || !response.data.roots || !Array.isArray(response.data.roots)) {
          console.error('Invalid mind map data structure:', response.data);
          setError('Invalid mind map data structure received from server.');
          setLoading(false);
          return;
        }
        
        // Set the mind map data and convert to flow format
        setMindMapData(response.data);
        convertMindMapToFlow(response.data);
        setProgressInfo({ status: 'complete', message: 'Global mind map loaded successfully!', progress: 100 });
        
        // Always force loading to false after data is processed
        setLoading(false);
      } else {
        // Handle unsuccessful response
        const errorMsg = response?.message || response?.error || 'Failed to fetch global mind map';
        console.error('Unsuccessful response:', errorMsg);
        setError(errorMsg);
        setLoading(false);
      }
    } catch (apiError) {
      console.error('=== HANDLE GLOBAL MIND MAP ERROR ===');
      console.error('Error:', apiError);
      
      // Only handle error if socket hasn't already handled it
      if (!socketHandledResult) {
        let errorMessage = 'Unable to fetch global mind map. ';
        
        if (apiError.response?.status === 401) {
          errorMessage += 'Authentication failed. Please log in again.';
        } else if (apiError.response?.status === 422) {
          errorMessage += 'Request format error. Check console for details.';
        } else {
          errorMessage += apiError.message || 'Unknown error occurred.';
        }
        
        setError(errorMessage);
        setLoading(false);
      }
    }
  };

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
    setExpandedNodes(new Set()); // Reset expanded nodes for new document
    setProgressInfo({ status: 'starting', message: 'Initializing mind map request...', progress: 0 });
    
    try {
      // Extract thread ID
      const threadId = thread.thread_id || thread.id || thread.threadId || thread._id;
      
      // Additional validation
      if (!threadId) {
        throw new Error('Thread ID not found in thread object');
      }
      
      if (!documentId) {
        throw new Error('Document ID is required');
      }
      
      // Convert to strings if needed (some APIs expect strings)
      const finalThreadId = String(threadId);
      const finalDocumentId = String(documentId);
      
      console.log('=== FINAL VALUES FOR API ===');
      console.log('Final Thread ID:', finalThreadId, typeof finalThreadId);
      console.log('Final Document ID:', finalDocumentId, typeof finalDocumentId);
      
      // Use the API service with socket ID for progress updates
      const response = await getMindMap(finalThreadId, finalDocumentId, socket?.id);
      
      if (response && response.status) {
        // Check if this is a "not found" response
        if (response.not_found) {
          // Socket.IO has already handled this case, don't override
          // The progress UI will transition to "not found" state via socket events
          return;
        }
        
        setMindMapData(response.data);
        convertMindMapToFlow(response.data);
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

  // Handle node clicks for expand/collapse
  const onNodeClick = useCallback((event, node) => {
    console.log('Node clicked:', node.id);
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(node.id)) {
        newSet.delete(node.id);
      } else {
        newSet.add(node.id);
      }
      return newSet;
    });
  }, []);

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
          <h2 className="text-xl font-semibold text-gray-800">
            {selectedDocument?.id === 'global' 
              ? '🌐 Global Mind Map (All Documents)' 
              : 'Mind Map Visualization'}
            {selectedDocument && selectedDocument.id !== 'global' && (
              <span className="ml-2 text-sm font-normal text-gray-500">
                - {selectedDocument.title}
              </span>
            )}
          </h2>
          <div className="flex items-center space-x-4">
            {/* Notification alert for new mind maps */}
            {progressInfo.status === 'new_mindmap_available' && (
              <div 
                className="animate-pulse flex items-center px-3 py-1 bg-green-100 text-green-800 rounded-full cursor-pointer hover:bg-green-200"
                onClick={() => handleGlobalMindMap(thread.thread_id || thread.id || thread.threadId || thread._id)}
              >
                <span className="text-lg mr-1">🆕</span>
                <span className="text-sm font-medium">New mind map available!</span>
              </div>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex h-[calc(100%-4rem)]">
          {/* Sidebar */}
          <div className="w-1/4 border-r border-gray-200 p-4 overflow-y-auto">
            <h3 className="font-medium text-gray-700 mb-3">Select Document</h3>
            
            {/* Global Mind Map Option */}
            <button
              onClick={() => handleGlobalMindMap(thread?.threadId)}
              className={`w-full text-left p-3 mb-4 rounded-lg border transition-colors bg-indigo-50 border-indigo-300 hover:bg-indigo-100 ${
                selectedDocument?.id === 'global' ? 'bg-indigo-100 border-indigo-400 text-indigo-700' : 'text-indigo-600'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="font-medium text-sm">
                  🌐 Global Mind Map (All Documents)
                </div>
              </div>
              <div className="text-xs mt-1 text-indigo-500">
                Create a mind map from all documents in this thread
              </div>
            </button>
            
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center">
                <span className="px-2 bg-white text-sm text-gray-500">OR SELECT DOCUMENT</span>
              </div>
            </div>
            
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

            {/* Instructions Panel */}
            {documents.length > 0 && (
              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-medium text-blue-800 mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  How to Use
                </h4>
                <div className="text-xs text-blue-700 space-y-1">
                  <p>• Click <strong>Global Mind Map</strong> to see a mind map of all documents</p>
                  <p>• Or click any document to load its specific mind map</p>
                  <p>• Click nodes to expand/collapse descriptions</p>
                  <p>• Use mouse wheel to zoom in/out</p>
                  <p>• Drag to pan around the mind map</p>
                  <p>• Use controls (top-left) for fit view</p>
                </div>
              </div>
            )}
          </div>

          {/* Mind Map Area */}
          <div className="flex-1 relative">
            {(loading || error || (selectedDocument && !mindMapData)) && (
              <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center z-10">
                <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full mx-4">
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                    
                    <h3 className="text-lg font-semibold text-gray-800 mb-2">
                      Loading Mind Map
                    </h3>
                    
                    
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
                    
                    
                  </div>
                </div>
              </div>
            )}

            {!selectedDocument && !loading && !error && !mindMapData && (
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

            {mindMapData && nodes.length > 0 && (
              <div className="w-full h-full">
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  nodeTypes={nodeTypes}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onNodeClick={onNodeClick}
                  fitView
                  fitViewOptions={{
                    padding: 0.3, // Add padding around the mind map
                    maxZoom: 0.8, // Start more zoomed out
                    minZoom: 0.1,
                    duration: 800 // Smooth transition
                  }}
                  defaultViewport={{ x: 0, y: 0, zoom: 0.6 }} // Default zoom level
                  className="bg-gradient-to-br from-slate-50 to-blue-50"
                  nodesDraggable={false} // Disable dragging to ensure clicks work
                  nodesConnectable={false}
                  elementsSelectable={false} // Disable selection to ensure clicks work
                >
                  <Controls position="top-left" showInteractive={false} />
                  <MiniMap 
                    position="bottom-right"
                    nodeColor={(node) => {
                      if (!node) return '#e5e7eb';
                      const level = node.id ? parseInt(node.id.split('-')[1] || '0') : 0;
                      return level === 0 ? '#3b82f6' : level === 1 ? '#6366f1' : level === 2 ? '#8b5cf6' : '#e5e7eb';
                    }}
                    maskColor="rgba(255, 255, 255, 0.8)"
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.9)',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px'
                    }}
                  />
                  <Background 
                    variant="dots" 
                    gap={20} 
                    size={1.5} 
                    color="#cbd5e1" 
                  />
                </ReactFlow>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MindMapModal;
