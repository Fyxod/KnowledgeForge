import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import { api, getAuthToken, API_URL, GlobalMindMap, MindMapNode, MindMapResponse } from '@/lib/api';
import { io, Socket } from 'socket.io-client';

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  threadId: string;
};

// Convert hierarchical nodes to React Flow nodes/edges with simple top-down layout
const useFlowGraph = (data?: GlobalMindMap) => {
  return useMemo(() => {
    if (!data) return { nodes: [] as Node[], edges: [] as Edge[] };

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // simple DFS with coordinates
    const xSpacing = 260;
    const ySpacing = 140;

  const nextXByDepth: Record<number, number> = {};

    const ensureDepthX = (depth: number) => {
      if (nextXByDepth[depth] == null) nextXByDepth[depth] = 0;
      return nextXByDepth[depth];
    };

    const addNode = (n: MindMapNode, depth: number) => {
      const x = ensureDepthX(depth);
      const y = depth * ySpacing;
      const id = n.id;
      nodes.push({
        id,
        position: { x, y },
        data: { label: (
          <div className="px-3 py-2 rounded-md border bg-background shadow-sm max-w-[220px]">
            <p className="font-medium text-sm leading-tight">{n.title}</p>
            {n.description && (
              <p className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap">
                {n.description}
              </p>
            )}
          </div>
        ) },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
        type: 'default',
      });

      // increment X for this depth for siblings
      nextXByDepth[depth] = x + xSpacing;

      for (const child of n.children || []) {
        edges.push({ id: `${id}-${child.id}`, source: id, target: child.id, animated: false });
        addNode(child, depth + 1);
      }
    };

    for (const root of data.roots || []) addNode(root, 0);

    return { nodes, edges };
  }, [data]);
};

export const MindMapModal: React.FC<Props> = ({ open, onOpenChange, threadId }) => {
  const [initialFetch, setInitialFetch] = useState<MindMapResponse | null>(null);
  const [mapData, setMapData] = useState<GlobalMindMap | undefined>(undefined);
  const [status, setStatus] = useState<boolean | undefined>(undefined);
  const [message, setMessage] = useState<string>('');
  // Using manual timeout loop to prevent overlapping requests
  const pollingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingActiveRef = useRef<boolean>(false);
  const socketRef = useRef<Socket | null>(null);
  const lastPayloadRef = useRef<string>('');

  type ProgressPayload = {
    message?: string;
    status?: boolean;
    data?: GlobalMindMap;
  };

  const { nodes, edges } = useFlowGraph(mapData);

  const closeEverything = useCallback(() => {
    // Stop polling loop
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
    }
    pollingTimeoutRef.current = null;
    pollingActiveRef.current = false;

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
        <div className="h-[70vh] grid grid-rows-[1fr_auto] gap-3">
          <div className="min-h-0 border rounded-md overflow-hidden">
            <ReactFlow nodes={nodes} edges={edges} fitView>
              <MiniMap pannable zoomable />
              <Controls />
              <Background gap={16} />
            </ReactFlow>
          </div>
          <div className="border rounded-md p-3 bg-muted/30">
            <p className="text-sm whitespace-pre-wrap">{message}</p>
          </div>
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
  }, [initialFetch, status, nodes, edges, message]);

  return (
    <Dialog open={open} onOpenChange={(v) => {
      if (!v) closeEverything();
      onOpenChange(v);
    }}>
      <DialogContent className="max-w-5xl w-[90vw]">
        <DialogHeader>
          <DialogTitle>Mind Map</DialogTitle>
        </DialogHeader>
        <div className="mt-2">
          {body}
        </div>
        <div className="mt-4 flex justify-end">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MindMapModal;
