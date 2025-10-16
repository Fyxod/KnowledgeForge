import { useEffect, useMemo, useRef, useState } from 'react';
import { Outlet, useNavigate, useMatch } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Brain, LogOut, User, Moon, Sun } from 'lucide-react';
import { ThreadSidebar } from '@/components/ThreadSidebar';
import { useAuth } from '@/lib/auth-context';
import { useTheme } from '@/lib/theme-context';
import { removeAuthToken, removeCurrentUser } from '@/lib/api';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';

const Dashboard = () => {
  const { user, logout, isLoading } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  // Persist sidebar width across sessions
  const storageKey = 'dashboard:sidebar:layout';
  const defaultLayout = useMemo(() => {
    const raw = localStorage.getItem(storageKey);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length === 2) return parsed as number[];
      } catch {}
    }
    return [22, 78] as number[]; // percentage widths
  }, []);
  const [layout, setLayout] = useState<number[]>(defaultLayout);
  const [groupKey, setGroupKey] = useState(0);
  const prevSidebarSizeRef = useRef<number>(layout[0]);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [collapsedPercent, setCollapsedPercent] = useState<number>(6);

  // Keep collapsed width ~64px regardless of screen size
  useEffect(() => {
    const updateCollapsedPercent = () => {
      const width = containerRef.current?.getBoundingClientRect().width || window.innerWidth || 1200;
      const px = 64; // match previous w-16 collapsed width
      const percent = Math.max(2, Math.min(20, (px / Math.max(1, width)) * 100));
      setCollapsedPercent(percent);
    };
    updateCollapsedPercent();
    window.addEventListener('resize', updateCollapsedPercent);
    return () => window.removeEventListener('resize', updateCollapsedPercent);
  }, []);
  const match = useMatch('/dashboard/threads/:threadId');
  const activeThreadId = match?.params.threadId;

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      navigate('/login');
    }
  }, [user, navigate, isLoading]);

  const handleLogout = () => {
    removeAuthToken();
    removeCurrentUser();
    logout();
    navigate('/');
  };

  if (isLoading) {
    return <div className="h-screen flex items-center justify-center">Loading…</div>;
  }
  if (!user) return null;

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-background">
        <div className="px-4 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Brain className="w-6 h-6 text-primary" />
            <h1 className="text-lg font-semibold">Knowledge Synthesis</h1>
          </div>
          
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={toggleTheme}>
              {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </Button>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <User className="w-5 h-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-2 border-b">
                  <p className="font-medium">{user.name}</p>
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                </div>
                <DropdownMenuItem onClick={() => navigate('/dashboard/profile')}>
                  <User className="w-4 h-4 mr-2" />
                  Profile
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div ref={containerRef} className="flex-1 flex overflow-hidden min-h-0 min-w-0">
        <ResizablePanelGroup
          key={groupKey}
          direction="horizontal"
          className="w-full min-h-0 min-w-0"
          onLayout={(sizes) => {
            // Save last known sizes; also keep ref updated
            prevSidebarSizeRef.current = sizes[0];
            setLayout(sizes);
            localStorage.setItem(storageKey, JSON.stringify(sizes));
          }}
        >
          <ResizablePanel
            defaultSize={sidebarCollapsed ? collapsedPercent : layout[0]}
            minSize={sidebarCollapsed ? collapsedPercent : 12}
            maxSize={sidebarCollapsed ? collapsedPercent : 40}
          >
            <div className="h-full min-h-0 min-w-0">
              <ThreadSidebar
                threads={user.threads || {}}
                activeThreadId={activeThreadId}
                collapsed={sidebarCollapsed}
                onToggleCollapse={() => {
                  setSidebarCollapsed((prev) => {
                    const next = !prev;
                    if (next) {
                      // collapsing: remember current size and snap to fixed collapsed width
                      const currentSize = layout[0];
                      if (currentSize) prevSidebarSizeRef.current = currentSize;
                      const nextLayout: number[] = [collapsedPercent, 100 - collapsedPercent];
                      setLayout(nextLayout);
                      localStorage.setItem(storageKey, JSON.stringify(nextLayout));
                      setGroupKey((k) => k + 1);
                    } else {
                      // expanding: restore previous size or default
                      const restoredRaw = prevSidebarSizeRef.current || defaultLayout[0];
                      const restored = Math.min(40, Math.max(12, restoredRaw));
                      const nextLayout: number[] = [restored, 100 - restored];
                      setLayout(nextLayout);
                      localStorage.setItem(storageKey, JSON.stringify(nextLayout));
                      setGroupKey((k) => k + 1);
                    }
                    return next;
                  });
                }}
              />
            </div>
          </ResizablePanel>
          {!sidebarCollapsed && <ResizableHandle withHandle />}
          <ResizablePanel defaultSize={sidebarCollapsed ? 100 - collapsedPercent : layout[1]} minSize={40}>
            <main className="h-full overflow-hidden min-h-0 min-w-0">
              <Outlet />
            </main>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
};

export default Dashboard;
