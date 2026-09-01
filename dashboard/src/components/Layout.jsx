import { Outlet, Navigate, NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Package, 
  ShoppingCart, 
  AlertTriangle, 
  Tags, 
  MessageSquare,
  LogOut,
  Bell
} from 'lucide-react';
import { useSSE } from '../hooks/useSSE';
import { useEffect, useState } from 'react';

export default function Layout() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const sellerData = JSON.parse(localStorage.getItem('seller') || '{}');
  
  const { lastEvent } = useSSE();
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    if (lastEvent) {
      setNotifications(prev => [lastEvent, ...prev].slice(0, 10));
      
      // Optionally show a toast here
    }
  }, [lastEvent]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('seller');
    navigate('/login');
  };

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Analytics' },
    { path: '/orders', icon: ShoppingCart, label: 'Orders' },
    { path: '/escalations', icon: AlertTriangle, label: 'Escalations' },
    { path: '/inventory', icon: Package, label: 'Inventory' },
    { path: '/conversations', icon: MessageSquare, label: 'Conversations' },
    { path: '/policies', icon: Tags, label: 'Policies' },
  ];

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)' }}>
          <h2 style={{ fontSize: '1.25rem', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.5rem' }}>⚡</span> Antigravity
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '4px' }}>
            {sellerData.business_name || 'Commerce Platform'}
          </p>
        </div>

        <nav style={{ flex: 1, padding: '20px 0' }}>
          <ul style={{ listStyle: 'none' }}>
            {navItems.map((item) => (
              <li key={item.path} style={{ margin: '4px 16px' }}>
                <NavLink
                  to={item.path}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    backgroundColor: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                    textDecoration: 'none',
                    fontWeight: isActive ? 600 : 500,
                    transition: 'all var(--transition-fast)',
                    border: isActive ? '1px solid rgba(59, 130, 246, 0.2)' : '1px solid transparent',
                  })}
                >
                  <item.icon size={20} color={window.location.pathname === item.path ? 'var(--accent-primary)' : 'currentColor'} />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div style={{ padding: '20px 16px', borderTop: '1px solid var(--border-color)' }}>
          <button 
            onClick={handleLogout}
            className="btn btn-secondary" 
            style={{ width: '100%', justifyContent: 'flex-start', color: 'var(--text-muted)' }}
          >
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Top Header */}
        <header style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '32px' }}>
          <div style={{ position: 'relative' }}>
            <button 
              className="btn btn-secondary"
              style={{ borderRadius: '50%', padding: '10px', width: '40px', height: '40px' }}
              onClick={() => setShowNotifications(!showNotifications)}
            >
              <Bell size={20} />
              {notifications.length > 0 && (
                <span style={{ 
                  position: 'absolute', top: '0', right: '0', 
                  width: '10px', height: '10px', borderRadius: '50%', 
                  background: 'var(--danger)', border: '2px solid var(--bg-primary)'
                }} />
              )}
            </button>
            
            {showNotifications && (
              <div className="glass-panel" style={{ 
                position: 'absolute', top: '50px', right: '0', 
                width: '320px', zIndex: 50, padding: '16px',
                maxHeight: '400px', overflowY: 'auto'
              }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                  Live Updates
                </h3>
                {notifications.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', padding: '20px 0' }}>
                    No recent events
                  </p>
                ) : (
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {notifications.map((n, i) => (
                      <li key={i} style={{ fontSize: '0.85rem', padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                        <strong style={{ color: 'var(--accent-primary)', display: 'block', marginBottom: '4px' }}>
                          {n.event.replace('_', ' ').toUpperCase()}
                        </strong>
                        <span style={{ color: 'var(--text-secondary)' }}>
                          {JSON.stringify(n.data).substring(0, 100)}...
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </header>
        
        {/* Page Content */}
        <div className="animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
