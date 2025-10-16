import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Loader2, Maximize2 } from 'lucide-react';
import ReactFlow, { Background, BackgroundVariant, Controls, Node, Edge, Position, NodeProps, MarkerType, Handle, MiniMap, useNodesState, useEdgesState, addEdge, useReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import { api, getAuthToken, API_URL, GlobalMindMap, MindMapNode, MindMapResponse } from '@/lib/api';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/lib/auth-context';
import { useTheme } from '@/lib/theme-context';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
};

// Custom expandable node styled like the reference
const CustomMindMapNode: React.FC<NodeProps<{ title: string; description?: string; level: number; isExpanded: boolean; onToggle?: () => void; isDark?: boolean }>> = ({ data }) => {
  const { title, description, level, isExpanded, onToggle, isDark = false } = data;
  const MAX_DESC_HEIGHT = 220; // px, keep in sync with estimator below
  
  const getNodeColors = () => {
    if (isDark) {
      // Dark mode colors - teal/cyan gradient with better contrast
      return {
        background: level === 0 ? '#0891b2' : level === 1 ? '#06b6d4' : level === 2 ? '#14b8a6' : '#374151',
        border: level === 0 ? '#0e7490' : level === 1 ? '#0891b2' : level === 2 ? '#0d9488' : '#4b5563',
        textColor: 'white',
        descColor: level <= 2 ? 'text-white/90' : 'text-gray-200',
        iconColor: level <= 2 ? 'text-white/80' : 'text-gray-300',
      };
    } else {
      // Light mode colors - teal/cyan gradient with vibrant colors
      return {
        background: level === 0 ? '#0891b2' : level === 1 ? '#06b6d4' : level === 2 ? '#14b8a6' : '#f3f4f6',
        border: level === 0 ? '#0e7490' : level === 1 ? '#0891b2' : level === 2 ? '#0d9488' : '#d1d5db',
        textColor: level <= 2 ? 'white' : '#111827',
        descColor: level <= 2 ? 'text-white/90' : 'text-gray-700',
        iconColor: level <= 2 ? 'text-white/80' : 'text-gray-600',
      };
    }
  };
  
  const colors = getNodeColors();
  
  return (
    <div
      className={`p-3 cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-105 relative ${
        isExpanded ? 'ring-2 ring-violet-400 dark:ring-violet-500 ring-opacity-60' : ''
      } ${isExpanded && description ? 'block' : 'flex items-center'}`}
      onClick={(e) => {
        e.stopPropagation();
        if (description && onToggle) onToggle();
      }}
      style={{
        minWidth: isExpanded ? '320px' : '220px',
        maxWidth: isExpanded ? '420px' : '280px',
        minHeight: '64px',
        background: colors.background,
        color: colors.textColor,
        border: `2px solid ${colors.border}`,
        borderRadius: '12px',
        fontSize: '16px',
        boxShadow: isExpanded 
          ? (isDark ? '0 8px 16px rgba(0,0,0,0.4)' : '0 8px 16px rgba(0,0,0,0.15)')
          : (isDark ? '0 4px 8px rgba(0,0,0,0.3)' : '0 4px 8px rgba(0,0,0,0.1)'),
        overflow: 'hidden',
        wordWrap: 'break-word',
      }}
    >
      {/* connection handles */}
      <Handle type="target" position={Position.Left} style={{ background: 'transparent', border: 'none', width: 8, height: 8, left: -4 }} />
      <Handle type="source" position={Position.Right} style={{ background: 'transparent', border: 'none', width: 8, height: 8, right: -4 }} />

      {/* expand indicator */}
      {description && (
        <div className="absolute top-2 right-2 w-5 h-5 flex items-center justify-center">
          <svg
            className={`w-4 h-4 transition-transform duration-200 ${colors.iconColor} ${
              isExpanded ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      )}

      <div className="w-full text-center font-semibold text-base leading-tight break-words">
        {title}
      </div>

      {isExpanded && description && (
        <div
          className={`text-sm leading-relaxed mt-3 break-words text-justify ${colors.descColor}`}
          style={{ maxHeight: MAX_DESC_HEIGHT, overflowY: 'auto' }}
        >
          {description}
        </div>
      )}
    </div>
  );
};

const nodeTypes = { mindMapNode: CustomMindMapNode } as const;

export const MindMapModal: React.FC<Props> = ({ open, onOpenChange, threadId }) => {
  const { user } = useAuth();
  const { theme } = useTheme();
  const [initialFetch, setInitialFetch] = useState<MindMapResponse | null>(null);
  const [mapData, setMapData] = useState<GlobalMindMap | undefined>(undefined);
  const [status, setStatus] = useState<boolean | undefined>(undefined);
  const [message, setMessage] = useState<string>('');
  const [showMessage, setShowMessage] = useState<boolean>(true);
  // Using manual timeout loop to prevent overlapping requests
  const pollingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingActiveRef = useRef<boolean>(false);
  const socketRef = useRef<Socket | null>(null);
  const lastPayloadRef = useRef<string>('');

  type ProgressPayload = {
    message?: string;
    status?: boolean;
    data?: GlobalMindMap;
    completed?: boolean;
  };

  // React Flow nodes/edges state + expansion state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<any>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge<any>>([]);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  // Calculate bounding box for translate extent
  const translateExtent = useMemo(() => {
    if (!nodes.length) return undefined;
    const xs = nodes.map(n => n.position.x);
    const ys = nodes.map(n => n.position.y);
    const minX = Math.min(...xs) - 300;
    const maxX = Math.max(...xs) + 800;
    const minY = Math.min(...ys) - 300;
    const maxY = Math.max(...ys) + 300;
    return [[minX, minY], [maxX, maxY]] as [[number, number], [number, number]];
  }, [nodes]);

  // Convert GlobalMindMap into positioned nodes/edges using a bottom-up layout
  const convertMindMapToFlow = useCallback((mindMap: GlobalMindMap) => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];
    const isDark = theme === 'dark';

    // Estimate height based on expansion and description length to avoid overlap
    const estimateSelfHeight = (n: MindMapNode): number => {
      const baseCollapsed = 72; // closer to visual min height + padding
      const isExpanded = expandedNodes.has(n.id);
      if (!isExpanded || !n.description) return baseCollapsed;
      // Roughly estimate lines at ~70 chars per line for 420px width and xs font
      const charsPerLine = 80;
      const text = n.description || '';
      const lines = Math.ceil(text.length / charsPerLine);
      const lineHeight = 18; // px per line (approx for text-xs)
      const padding = 36; // top/bottom + gaps
      const SAFETY = 28; // extra safety to ensure no overlap
      const raw = baseCollapsed + padding + lines * lineHeight + SAFETY;
      const MAX_HEIGHT = baseCollapsed + padding + 220; // sync with MAX_DESC_HEIGHT
      return Math.min(raw, MAX_HEIGHT);
    };

    const calcHeight = (n: MindMapNode): number => {
      if (!n.children || n.children.length === 0) {
        const h = Math.max(100, estimateSelfHeight(n));
        (n as any)._requiredHeight = h;
        return h;
      }
      let total = 0;
      for (const c of n.children) total += calcHeight(c);
  const minGap = 48; // more space between siblings
      const self = estimateSelfHeight(n);
      const childrenSpace = Math.max(total + n.children.length * minGap, 100);
      const h = Math.max(self, childrenSpace);
      (n as any)._requiredHeight = h;
      return h;
    };

    (mindMap.roots || []).forEach(calcHeight);

  const horizontalSpacing = 520; // more spacing to avoid lateral overlap when expanded
    const baseX = 200;

    // Helpers to support collision resolution
    const levelMap = new Map<number, string[]>();
    const childrenMap = new Map<string, string[]>();
    const parentMap = new Map<string, string | null>();
    const idToMindNode = new Map<string, MindMapNode>();

    const add = (n: MindMapNode, parentId: string | null, level: number, allocatedY: number, allocatedH: number) => {
      const id = n.id; // keep original ids for stability
      const x = baseX + level * horizontalSpacing;
      const y = allocatedY + allocatedH / 2;
      const isExpanded = expandedNodes.has(id);

      idToMindNode.set(id, n);
      parentMap.set(id, parentId);
      childrenMap.set(id, (n.children || []).map((c) => c.id));
      if (!levelMap.has(level)) levelMap.set(level, []);
      levelMap.get(level)!.push(id);

      newNodes.push({
        id,
        type: 'mindMapNode',
        position: { x, y },
        data: {
          title: n.title || 'Untitled',
          description: n.description || '',
          level,
          isExpanded,
          isDark,
          onToggle: () => {
            setExpandedNodes((prev) => {
              const ns = new Set(prev);
              if (ns.has(id)) ns.delete(id); else ns.add(id);
              return ns;
            });
          },
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });

      if (parentId) {
        const stroke = isDark 
          ? (level === 1 ? '#22d3ee' : level === 2 ? '#2dd4bf' : level === 3 ? '#5eead4' : '#5eead4')
          : (level === 1 ? '#0891b2' : level === 2 ? '#06b6d4' : level === 3 ? '#14b8a6' : '#9ca3af');
        const width = level === 1 ? 3 : level === 2 ? 2.5 : 2;
        newEdges.push({
          id: `e-${parentId}-${id}`,
          source: parentId,
          target: id,
          type: 'bezier',
          animated: level === 1,
          style: { stroke, strokeWidth: width },
          markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15, color: stroke },
        });
      }

      if (n.children && n.children.length) {
        let childY = allocatedY;
        for (const c of n.children) {
          const h = (c as any)._requiredHeight || 100;
          add(c, id, level + 1, childY, h);
          childY += h;
        }
      }
    };

    // lay out each root one below another
    let rootY = 50;
    for (const r of mindMap.roots || []) {
      const rh = (r as any)._requiredHeight || 200;
      add(r, null, 0, rootY, rh);
      rootY += rh + 50;
    }

    // Post-process: avoid vertical overlap per column by pushing subtrees down
    const idToIndex = new Map<string, number>();
    newNodes.forEach((n, idx) => idToIndex.set(n.id, idx));

    const heightOf = (id: string) => {
      const m = idToMindNode.get(id);
      const est = m ? estimateSelfHeight(m) : 100;
      return Math.max(100, est);
    };

    const applyShiftRec = (id: string, dy: number) => {
      const idx = idToIndex.get(id);
      if (idx != null) {
        newNodes[idx] = {
          ...newNodes[idx],
          position: { ...newNodes[idx].position, y: newNodes[idx].position.y + dy },
        };
      }
      const kids = childrenMap.get(id) || [];
      for (const k of kids) applyShiftRec(k, dy);
    };

    const levels = Array.from(levelMap.keys()).sort((a, b) => a - b);
    const minVerticalGap = 52; // ensure spacing between boxes
    const runCollisionPass = () => {
      for (const lvl of levels) {
        const ids = (levelMap.get(lvl) || []).slice().sort((a, b) => {
          const ya = newNodes[idToIndex.get(a)!].position.y;
          const yb = newNodes[idToIndex.get(b)!].position.y;
          return ya - yb;
        });
        let prevBottom = -Infinity;
        for (const id of ids) {
          const idx = idToIndex.get(id)!;
          const h = heightOf(id);
          const y = newNodes[idx].position.y;
          let top = y - h / 2;
          const requiredTop = prevBottom + minVerticalGap;
          if (top < requiredTop) {
            const dy = requiredTop - top;
            applyShiftRec(id, dy);
            top += dy;
          }
          prevBottom = top + h;
        }
      }
    };

    // First collision pass (before parent centering)
    runCollisionPass();

    // Re-center parents based on children positions (bottom-up)
    const maxLevel = levels.length ? Math.max(...levels) : 0;
    for (let lvl = maxLevel - 1; lvl >= 0; lvl--) {
      const ids = levelMap.get(lvl) || [];
      for (const id of ids) {
        const kids = childrenMap.get(id) || [];
        if (kids.length) {
          const ys = kids.map((cid) => newNodes[idToIndex.get(cid)!].position.y);
          const avg = ys.reduce((a, b) => a + b, 0) / ys.length;
          const idx = idToIndex.get(id)!;
      newNodes[idx] = { ...newNodes[idx], position: { ...newNodes[idx].position, y: avg } };
        }
      }
    }

    // Second collision pass to fix any overlaps introduced by centering
    runCollisionPass();

    setNodes(newNodes);
    setEdges(newEdges);
  }, [expandedNodes, setNodes, setEdges, theme]);

  // Rebuild graph when fresh data arrives
  useEffect(() => {
    if (mapData) convertMindMapToFlow(mapData);
  }, [mapData, convertMindMapToFlow]);

  // Update nodes' expanded state efficiently
  useEffect(() => {
    // Rebuild layout to accommodate expanded heights and prevent overlaps
    if (mapData) {
      convertMindMapToFlow(mapData);
    } else {
      setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, isExpanded: expandedNodes.has(n.id) } })));
    }
  }, [expandedNodes, setNodes]);

  const closeEverything = useCallback(() => {
    // Stop polling loop FIRST
    pollingActiveRef.current = false;
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    // Disconnect socket
    if (socketRef.current) {
      try { 
        socketRef.current.off(); // Remove all listeners
        socketRef.current.disconnect(); 
      } catch (e) {
        if (import.meta.env.DEV) console.debug('socket disconnect error', e);
      }
      socketRef.current = null;
    }
    
    if (import.meta.env.DEV) console.debug('mind map cleanup: polling and socket stopped');
  }, []);

  // Kick off initial fetch when modal opens
  useEffect(() => {
    if (!open) {
      // Immediately stop polling when modal closes
      pollingActiveRef.current = false;
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
      // Disconnect socket
      if (socketRef.current) {
        try { 
          socketRef.current.off(); // Remove all listeners
          socketRef.current.disconnect(); 
        } catch (e) {
          if (import.meta.env.DEV) console.debug('socket disconnect error', e);
        }
        socketRef.current = null;
      }
      if (import.meta.env.DEV) console.debug('mind map modal closed: stopped all requests');
      return;
    }
    let cancelled = false;
    (async () => {
  const res = await api.getMindMap(threadId);
      if (cancelled) return;
      setInitialFetch(res);
      setMessage(res.message || '');
      if (res.mind_map) {
        setStatus(res.status);
        if (res.status && res.data) setMapData(res.data);

        // start socket.io subscription for mind map progress
        const token = getAuthToken();
        try {
          const socket = io(API_URL, {
            path: '/socket.io',
            transports: ['websocket'],
            auth: token ? { token } : undefined,
            query: { thread_id: threadId },
          });
          socketRef.current = socket;

          const onProgress = (data: ProgressPayload) => {
            // Only update message from WebSocket
            if (typeof data.message === 'string') {
              setMessage(data.message);
              setShowMessage(true); // Show message when received
            }
            
            // Check if completed, then stop everything
            if (data.completed === true) {
              if (import.meta.env.DEV) console.debug('mind map completed, stopping WebSocket and polling');
              
              // Stop polling
              pollingActiveRef.current = false;
              if (pollingTimeoutRef.current) {
                clearTimeout(pollingTimeoutRef.current);
                pollingTimeoutRef.current = null;
              }
              
              // Disconnect WebSocket
              if (socketRef.current) {
                socketRef.current.disconnect();
                socketRef.current = null;
              }
              
              // Hide message after completion
              setShowMessage(false);
            }
          };

          socket.on('connect', () => {
            if (import.meta.env.DEV) console.debug('mind map socket connected');
          });
          socket.on('connect_error', (err) => {
            if (import.meta.env.DEV) console.debug('mind map socket connect_error', err);
          });
          // Primary event name with user_id and thread_id
          const progressEvent = user?.userId ? `${user.userId}/${threadId}/mind_map/progress` : 'mind_map/progress';
          socket.on(progressEvent, onProgress);
          // Fallback aliases if backend uses different naming
          socket.on('mind_map_progress', onProgress);
          socket.on('progress', onProgress);
        } catch (e) {
          if (import.meta.env.DEV) console.debug('socket init error', e);
        }

        // start polling every 10 seconds to get status and data (not message)
        pollingActiveRef.current = true;
        const pollOnce = async () => {
          // Double-check that polling is still active before making request
          if (!pollingActiveRef.current) {
            if (import.meta.env.DEV) console.debug('polling stopped - skipping request');
            return;
          }
          try {
            const r = await api.getMindMap(threadId);
            // Check again after async operation completes
            if (!pollingActiveRef.current) {
              if (import.meta.env.DEV) console.debug('polling stopped during request - ignoring response');
              return;
            }
            const payload = JSON.stringify(r);
            if (payload !== lastPayloadRef.current) {
              lastPayloadRef.current = payload;
              // Only update status and data from polling, NOT message
              setStatus(r.status);
              if (r.status && r.data) setMapData(r.data);
            }
            if (!r.mind_map) {
              // stop polling if server reports no mind map flow
              pollingActiveRef.current = false;
              if (pollingTimeoutRef.current) {
                clearTimeout(pollingTimeoutRef.current);
                pollingTimeoutRef.current = null;
              }
              return;
            }
          } catch (e) {
            if (import.meta.env.DEV) console.debug('mind map poll error', e);
          }
          // schedule next run in 10 seconds only if still active
          if (pollingActiveRef.current) {
            pollingTimeoutRef.current = setTimeout(pollOnce, 10000);
          }
        };
        // kick off loop
        pollOnce();
      }
    })();
    return () => { 
      cancelled = true;
      // Cleanup on unmount or when dependencies change
      pollingActiveRef.current = false;
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
      if (socketRef.current) {
        try {
          socketRef.current.off();
          socketRef.current.disconnect();
        } catch (e) {
          if (import.meta.env.DEV) console.debug('socket cleanup error', e);
        }
        socketRef.current = null;
      }
    };
  }, [open, threadId]); // Removed closeEverything from dependencies to prevent re-runs

  // Keep showing messages until WebSocket sends completed: true
  // No auto-hide logic needed - messages will be hidden only when completed is received

  const body = useMemo(() => {
    const mm = initialFetch;
    if (!mm) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Loading…</span>
          </div>
        </div>
      );
    }

    if (!mm.mind_map) {
      return (
        <div className="p-4">
          <p className="text-sm whitespace-pre-wrap">{mm.message}</p>
        </div>
      );
    }

    // mind_map === true
    if (status) {
      // show map + messages below from websocket
      return (
        <div className="h-full grid grid-rows-[1fr_auto] gap-3">
          <div className="min-h-0 border rounded-md overflow-hidden bg-gray-50 dark:bg-gray-900">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              fitView
              fitViewOptions={{ padding: 0.05, maxZoom: 1.2, minZoom: 0.005 }}
              minZoom={0.05}
              maxZoom={1.5}
              defaultViewport={{ x: 0, y: 0, zoom: 0.3 }}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              panOnDrag={true}
              zoomOnScroll={true}
              zoomOnPinch={true}
              panOnScroll={false}
              preventScrolling={true}
              translateExtent={translateExtent}
              nodeExtent={undefined}
              onNodeClick={(_, node) => {
                setExpandedNodes((prev) => {
                  const ns = new Set(prev);
                  if (ns.has(node.id)) ns.delete(node.id); else ns.add(node.id);
                  return ns;
                });
              }}
            >
              <Controls position="bottom-left" showInteractive={false} showFitView={true} fitViewOptions={{ padding: 0.05, maxZoom: 1.2, minZoom: 0.005 }} />
              <MiniMap 
                position="bottom-right" 
                pannable
                zoomable
                className="!bg-white/95 dark:!bg-gray-800/90 !border-2 !border-gray-300 dark:!border-gray-600 !rounded-lg !shadow-lg" 
                nodeColor={(node) => {
                  const level = node.data.level;
                  if (theme === 'dark') {
                    return level === 0 ? '#0891b2' : level === 1 ? '#06b6d4' : level === 2 ? '#14b8a6' : '#374151';
                  }
                  return level === 0 ? '#0891b2' : level === 1 ? '#06b6d4' : level === 2 ? '#14b8a6' : '#d1d5db';
                }}
              />
              <Background 
                variant={BackgroundVariant.Dots} 
                gap={18} 
                size={1} 
                className="!bg-gray-50 dark:!bg-gray-900"
                color={theme === 'dark' ? '#4b5563' : '#d1d5db'} 
              />
            </ReactFlow>
          </div>
          {showMessage && message && (
            <div className="border rounded-md p-2 bg-muted/30">
              <p className="text-xs whitespace-pre-wrap">{message}</p>
            </div>
          )}
        </div>
      );
    }

    // status is false: center message with loading state (make text larger)
    return (
      <div className="h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-center">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <p className="text-2xl font-semibold whitespace-pre-wrap max-w-2xl">{message || 'Generating mind map…'}</p>
        </div>
      </div>
    );
  }, [initialFetch, status, nodes, edges, message, showMessage]);

  return (
    <Dialog open={open} onOpenChange={(v) => {
      if (!v) closeEverything();
      onOpenChange(v);
    }}>
      <DialogContent className="max-w-[98vw] w-[98vw] h-[98vh] max-h-[98vh] p-4 flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Mind Map</DialogTitle>
        </DialogHeader>
        <div className="flex-1 min-h-0 mt-2">
          {body}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MindMapModal;
