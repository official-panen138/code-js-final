import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Code2, LayoutDashboard, FolderKanban, LogOut, ChevronLeft, ChevronRight, Settings } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Separator } from '../components/ui/separator';
import { useState } from 'react';

function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const links = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/projects', icon: FolderKanban, label: 'Projects' },
  ];

  return (
    <aside
      data-testid="sidebar"
      className={`flex flex-col h-screen border-r border-border bg-white transition-all duration-200 ${collapsed ? 'w-[68px]' : 'w-[240px]'}`}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-5">
        <div className="w-8 h-8 rounded-md bg-[#0F172A] flex items-center justify-center flex-shrink-0">
          <Code2 className="w-4 h-4 text-white" strokeWidth={2} />
        </div>
        {!collapsed && (
          <span className="text-lg font-semibold tracking-tight" style={{ fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            JSHost
          </span>
        )}
      </div>

      <Separator />

      {/* Nav Links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            data-testid={`nav-${link.label.toLowerCase()}`}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            <link.icon className="w-5 h-5 flex-shrink-0" strokeWidth={1.5} />
            {!collapsed && <span>{link.label}</span>}
          </NavLink>
        ))}
      </nav>

      <Separator />

      {/* User & Collapse */}
      <div className="px-3 py-4 space-y-3">
        {!collapsed && user && (
          <div className="px-3">
            <p className="text-sm font-medium text-foreground truncate">{user.email}</p>
            <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
          </div>
        )}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setCollapsed(!collapsed)}
            data-testid="sidebar-collapse-btn"
            className="flex-shrink-0"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </Button>
          {!collapsed && (
            <Button variant="ghost" size="sm" onClick={handleLogout} data-testid="logout-btn" className="text-muted-foreground hover:text-destructive">
              <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Logout
            </Button>
          )}
        </div>
      </div>
    </aside>
  );
}

export default function Layout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-[#FAFBFC]" data-testid="main-content">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
