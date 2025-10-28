import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Thread, api } from '@/lib/api';
import { Plus, FileText, MessageSquare, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import { formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { toast } from '@/components/ui/use-toast';
import { useAuth } from '@/lib/auth-context';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ThreadSidebarProps {
  threads: Record<string, Thread>;
  activeThreadId?: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

type SortOption = 'updatedAt' | 'createdAt' | 'alphabetically';

export const ThreadSidebar = ({ threads, activeThreadId, collapsed, onToggleCollapse }: ThreadSidebarProps) => {
  const [sortBy, setSortBy] = useState<SortOption>('updatedAt');
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);

  // Helper: parse timestamp by appending 'Z' (interpret as UTC); fall back to current time if invalid
  const parseTimestampAsUTC = (ts?: string) => {
    try {
      const parsed = new Date(String(ts ?? '') + 'Z');
      if (isNaN(parsed.getTime())) return new Date();
      return parsed;
    } catch {
      return new Date();
    }
  };

  const handleDelete = async (threadId: string, threadName: string) => {
    try {
      
      const prevUser = user;
      if (!prevUser) return;
      const updatedThreads = { ...prevUser.threads };
      delete updatedThreads[threadId];
      setUser({ ...prevUser, threads: updatedThreads });

      const res = await api.deleteThread(threadId);
      if (!res.status) {
        setUser(prevUser);
        toast({ title: 'Failed to delete thread', description: `"${threadName}" could not be deleted.`, variant: 'destructive' as any });
        return;
      }

      if (activeThreadId === threadId) {
        navigate('/dashboard');
      }
      toast({ title: 'Thread deleted', description: `"${threadName}" was removed.` });
    } catch (e) {
      toast({ title: 'Error deleting thread', description: (e as Error).message, variant: 'destructive' as any });
    }
  };

  const sortedThreads = useMemo(() => {
    const threadEntries = Object.entries(threads);
    
    return threadEntries.sort(([, a], [, b]) => {
      switch (sortBy) {
        case 'alphabetically':
          return a.thread_name.localeCompare(b.thread_name);
        case 'createdAt':
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'updatedAt':
        default:
          return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      }
    });
  }, [threads, sortBy]);

  return (
    <div className={`border-r bg-sidebar transition-all duration-300 flex flex-col w-full min-w-16 min-h-0 h-full`}>
      <div className="p-4 border-b flex items-center justify-between">
        {!collapsed && <h2 className="font-semibold">Threads</h2>}
        <Button variant="ghost" size="icon" onClick={onToggleCollapse}>
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </Button>
      </div>

      {!collapsed && (
        <>
          <div className="p-4 border-b space-y-3">
            <Button 
              className="w-full bg-gradient-primary" 
              onClick={() => navigate('/dashboard/new')}
            >
              <Plus className="w-4 h-4 mr-2" />
              New Thread
            </Button>
            
            <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortOption)}>
              <SelectTrigger>
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="updatedAt">Last Updated</SelectItem>
                <SelectItem value="createdAt">Date Created</SelectItem>
                <SelectItem value="alphabetically">Alphabetically</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <ScrollArea className="flex-1 min-h-0">
            <div className="p-2 space-y-2">
              {sortedThreads.map(([id, thread]) => (
                <div
                  key={id}
                  className={`group relative rounded-lg overflow-hidden min-w-0 ${
                    activeThreadId === id ? 'bg-sidebar-accent text-sidebar-accent-foreground ring-1 ring-primary/20' : ''
                  }`}
                  aria-current={activeThreadId === id ? 'page' : undefined}
                >
                  {/* Selected indicator bar */}
                  <div
                    className={`absolute left-0 top-0 h-full w-1 rounded-r ${
                      activeThreadId === id ? 'bg-primary' : 'bg-transparent'
                    }`}
                    aria-hidden
                  />
                  <button
                    onClick={() => navigate(`/dashboard/threads/${id}`)}
                    className={`w-full text-left p-3 pl-4 rounded-lg transition-colors min-w-0 ${
                      activeThreadId === id 
                        ? 'bg-transparent' 
                        : 'hover:bg-sidebar-accent/50'
                    }`}
                  >
                    <div className="font-medium whitespace-normal break-words mb-1 pr-8">
                      {thread.thread_name}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <FileText className="w-3 h-3" />
                        {thread.documents?.length || 0}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" />
                        {thread.chats?.length || 0}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {formatDistanceToNow(parseTimestampAsUTC(thread.updatedAt), { addSuffix: true })}
                    </div>
                  </button>
                  <button
                    aria-label="Delete thread"
                    className="absolute top-2 right-2 z-10 flex items-center justify-center w-5 h-5 rounded hover:bg-destructive/10 text-muted-foreground/80 hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPendingDelete({ id, name: thread.thread_name });
                      setConfirmOpen(true);
                    }}
                    title="Delete"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              
              {sortedThreads.length === 0 && (
                <div className="text-center text-muted-foreground py-8 text-sm">
                  No threads yet
                </div>
              )}
            </div>
          </ScrollArea>
        </>
      )}

      {collapsed && (
        <div className="flex-1 flex flex-col items-center py-4 gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/dashboard/new')}
                aria-label="New thread"
              >
                <Plus className="w-5 h-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right" align="center">New thread</TooltipContent>
          </Tooltip>
        </div>
      )}

      {/* Delete confirmation dialog */}
      <AlertDialog open={confirmOpen} onOpenChange={(open) => {
        if (!open) {
          setConfirmOpen(false);
        } else {
          setConfirmOpen(true);
        }
      }}>
        <AlertDialogContent onClick={(e) => e.stopPropagation()}>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this thread?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete?.name ? (
                <>
                  You’re about to delete “{pendingDelete.name}”. This action cannot be undone.
                </>
              ) : (
                'This action cannot be undone.'
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setConfirmOpen(false);
              setPendingDelete(null);
            }}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={async () => {
                if (pendingDelete) {
                  await handleDelete(pendingDelete.id, pendingDelete.name);
                }
                setConfirmOpen(false);
                setPendingDelete(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
