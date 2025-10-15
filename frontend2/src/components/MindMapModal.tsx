import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Loader2, Maximize2 } from 'lucide-react';
import ReactFlow, { Background, BackgroundVariant, Controls, Node, Edge, Position, NodeProps, MarkerType, Handle, MiniMap, useNodesState, useEdgesState, addEdge, useReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import { api, getAuthToken, API_URL, GlobalMindMap, MindMapNode, MindMapResponse } from '@/lib/api';
import { io, Socket } from 'socket.io-client';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
};

// Custom expandable node styled like the reference
const CustomMindMapNode: React.FC<NodeProps<{ title: string; description?: string; level: number; isExpanded: boolean; onToggle?: () => void }>> = ({ data }) => {
  const { title, description, level, isExpanded, onToggle } = data;
  const MAX_DESC_HEIGHT = 220; // px, keep in sync with estimator below
  return (
    <div
      className={`p-3 cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-105 relative ${
        isExpanded ? 'ring-2 ring-violet-300 ring-opacity-60' : ''
      } ${isExpanded && description ? 'block' : 'flex items-center'}`}
      onClick={(e) => {
        e.stopPropagation();
        if (description && onToggle) onToggle();
      }}
      style={{
        minWidth: isExpanded ? '320px' : '220px',
        maxWidth: isExpanded ? '420px' : '280px',
  minHeight: '64px',
        background:
          level === 0 ? '#3b82f6' : level === 1 ? '#6366f1' : level === 2 ? '#8b5cf6' : '#e5e7eb',
        color: level <= 2 ? 'white' : 'black',
        border: `2px solid ${level === 0 ? '#1e40af' : level === 1 ? '#4338ca' : level === 2 ? '#7c3aed' : '#9ca3af'}`,
        borderRadius: '12px',
        fontSize: '16px',
        boxShadow: isExpanded ? '0 8px 16px rgba(0,0,0,0.15)' : '0 4px 8px rgba(0,0,0,0.1)',
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
            className={`w-4 h-4 transition-transform duration-200 ${level <= 2 ? 'text-white/80' : 'text-gray-500'} ${
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

      <div className={`w-full text-center font-semibold text-base leading-tight break-words ${
        level <= 2 ? 'text-white' : 'text-gray-800'
      }`}>
        {title}
      </div>

      {isExpanded && description && (
        <div
          className={`text-sm leading-relaxed mt-3 break-words text-justify ${level <= 2 ? 'text-white/90' : 'text-gray-600'}`}
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
  const messageTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  type ProgressPayload = {
    message?: string;
    status?: boolean;
    data?: GlobalMindMap;
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
        const stroke = level === 1 ? '#3b82f6' : level === 2 ? '#6366f1' : level === 3 ? '#8b5cf6' : '#8b5cf6';
        const width = level === 1 ? 3 : level === 2 ? 2.5 : 2;
        newEdges.push({
          id: `e-${parentId}-${id}`,
          source: parentId,
          target: id,
          type: 'bezier',
          animated: level === 1,
          style: { stroke, strokeWidth: width },
          markerEnd: { type: MarkerType.ArrowClosed, width: 15, height: 15 },
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
  }, [expandedNodes, setNodes, setEdges]);

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
    // Stop polling loop
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
    }
    pollingTimeoutRef.current = null;
    pollingActiveRef.current = false;

    // Clear message timeout
    if (messageTimeoutRef.current) {
      clearTimeout(messageTimeoutRef.current);
    }
    messageTimeoutRef.current = null;

    // Disconnect socket
    if (socketRef.current) {
      try { socketRef.current.disconnect(); } catch (e) {
        if (import.meta.env.DEV) console.debug('socket disconnect error', e);
      }
    }
    socketRef.current = null;
  }, []);

  // Kick off initial fetch when modal opens
  useEffect(() => {
    if (!open) {
      closeEverything();
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
            // data expected to be same shape as previous ws payload
            if (typeof data.message === 'string') setMessage(data.message);
            if (typeof data.status === 'boolean') setStatus(data.status);
            if (data.status && data.data) setMapData(data.data);
          };

          socket.on('connect', () => {
            if (import.meta.env.DEV) console.debug('mind map socket connected');
          });
          socket.on('connect_error', (err) => {
            if (import.meta.env.DEV) console.debug('mind map socket connect_error', err);
          });
          // Primary event name
          socket.on('mind_map/progress', onProgress);
          // Fallback aliases if backend uses different naming
          socket.on('mind_map_progress', onProgress);
          socket.on('progress', onProgress);
        } catch (e) {
          if (import.meta.env.DEV) console.debug('socket init error', e);
        }

        // start polling every 5 seconds while mind_map is true, without overlapping
        pollingActiveRef.current = true;
        const pollOnce = async () => {
          if (!pollingActiveRef.current) return;
          try {
            const r = await api.getMindMap(threadId);
            const payload = JSON.stringify(r);
            if (payload !== lastPayloadRef.current) {
              lastPayloadRef.current = payload;
              setMessage(r.message || '');
              setStatus(r.status);
              if (r.status && r.data) setMapData(r.data);
            }
            if (!r.mind_map) {
              // stop polling if server reports no mind map flow
              pollingActiveRef.current = false;
              if (pollingTimeoutRef.current) clearTimeout(pollingTimeoutRef.current);
              pollingTimeoutRef.current = null;
              return;
            }
          } catch (e) {
            if (import.meta.env.DEV) console.debug('mind map poll error', e);
          }
          // schedule next run in 5 seconds
          if (pollingActiveRef.current) {
            pollingTimeoutRef.current = setTimeout(pollOnce, 5000);
          }
        };
        // kick off loop
        pollOnce();
      }
    })();
    return () => { cancelled = true; };
  }, [open, threadId, closeEverything]);

  // Cleanup when closing modal
  useEffect(() => {
    if (!open) {
      closeEverything();
    }
  }, [open, closeEverything]);

  // Hide message after 5 seconds when mind_map is true and status is true
  useEffect(() => {
    if (initialFetch?.mind_map && status) {
      // Show message initially
      setShowMessage(true);
      
      // Clear any existing timeout
      if (messageTimeoutRef.current) {
        clearTimeout(messageTimeoutRef.current);
      }
      
      // Set timeout to hide message after 5 seconds
      messageTimeoutRef.current = setTimeout(() => {
        setShowMessage(false);
      }, 5000);
      
      // Cleanup on unmount or when dependencies change
      return () => {
        if (messageTimeoutRef.current) {
          clearTimeout(messageTimeoutRef.current);
        }
      };
    } else {
      // Always show message when conditions don't match
      setShowMessage(true);
    }
  }, [initialFetch?.mind_map, status, message]);

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
          <div className="min-h-0 border rounded-md overflow-hidden">
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
              <MiniMap position="bottom-right" style={{ backgroundColor: 'rgba(255,255,255,0.9)', border: '1px solid #e2e8f0', borderRadius: 8 }} />
              <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="#bdbdbd" />
            </ReactFlow>
          </div>
          {showMessage && (
            <div className="border rounded-md p-2 bg-muted/30">
              <p className="text-xs whitespace-pre-wrap">{message}</p>
            </div>
          )}
        </div>
      );
    }

    // status is false: center message with loading state
    return (
      <div className="h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-2 text-center">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <p className="text-sm whitespace-pre-wrap max-w-xl">{message || 'Generating mind map…'}</p>
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
