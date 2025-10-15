import { useEffect, useState } from 'react';
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

const Dashboard = () => {
  const { user, logout, isLoading } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
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
      <div className="flex-1 flex overflow-hidden">
        <ThreadSidebar 
          threads={user.threads || {}} 
          activeThreadId={activeThreadId}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
