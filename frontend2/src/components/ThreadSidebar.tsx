import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Thread } from '@/lib/api';
import { Plus, FileText, MessageSquare, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';

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
    <div className={`border-r bg-sidebar transition-all duration-300 ${collapsed ? 'w-16' : 'w-72'} flex flex-col`}>
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

          <ScrollArea className="flex-1">
            <div className="p-2 space-y-2">
              {sortedThreads.map(([id, thread]) => (
                <button
                  key={id}
                  onClick={() => navigate(`/dashboard/threads/${id}`)}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    activeThreadId === id 
                      ? 'bg-sidebar-accent text-sidebar-accent-foreground' 
                      : 'hover:bg-sidebar-accent/50'
                  }`}
                >
                  <div className="font-medium truncate mb-1">{thread.thread_name}</div>
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
                    {formatDistanceToNow(new Date(thread.updatedAt), { addSuffix: true })}
                  </div>
                </button>
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
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => navigate('/dashboard/new')}
          >
            <Plus className="w-5 h-5" />
          </Button>
        </div>
      )}
    </div>
  );
};
