import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { Button } from './ui/button';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import {
  LayoutDashboard,
  Package,
  PackageCheck,
  Users,
  Truck,
  Settings,
  LogOut,
  Moon,
  Sun,
  Menu,
  ChevronLeft,
  Building2,
  UserCircle,
  Receipt,
  Car,
  Warehouse
} from 'lucide-react';
import { cn } from '../lib/utils';
import { NotificationBell } from './NotificationBell';
import { PackagePlus } from 'lucide-react';

const API = `${window.location.origin}/api`;

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard', pageId: 'dashboard' },
  { icon: PackagePlus, label: 'Parcel Intake', href: '/parcels/intake', pageId: 'parcel-intake' },
  { icon: Warehouse, label: 'Warehouse', href: '/warehouse', pageId: 'warehouse' },
  { icon: Receipt, label: 'Finance', href: '/finance', pageId: 'finance' },
  { icon: Truck, label: 'Trips', href: '/trips', pageId: 'trips' },
  { icon: PackageCheck, label: 'Loading', href: '/loading', pageId: 'loading' },
  { icon: Users, label: 'Clients', href: '/clients', pageId: 'clients' },
  { icon: Car, label: 'Fleet', href: '/fleet', pageId: 'fleet' },
  { icon: UserCircle, label: 'Team', href: '/team', pageId: 'team' },
  { icon: Settings, label: 'Settings', href: '/settings', pageId: 'settings' },
];

// Default permissions (scanner removed)
const defaultPermissions = {
  owner: ['dashboard', 'parcel-intake', 'warehouse', 'clients', 'loading', 'trips', 'finance', 'fleet', 'team', 'settings'],
  manager: ['dashboard', 'parcel-intake', 'warehouse', 'clients', 'loading', 'trips', 'finance', 'fleet', 'team'],
  warehouse: ['dashboard', 'parcel-intake', 'warehouse', 'loading'],
  finance: ['dashboard', 'clients', 'finance'],
  driver: ['dashboard', 'trips'],
};

// Helper function to check if a nav item should be active
const isNavItemActive = (pathname, href) => {
  // Exact match
  if (pathname === href) return true;
  
  // Check if current path starts with the nav href (for child routes)
  // e.g., /trips/123 should highlight /trips
  // But /parcels/intake should not highlight /parcels
  const pathSegments = pathname.split('/').filter(Boolean);
  const hrefSegments = href.split('/').filter(Boolean);
  
  // For multi-segment hrefs like /parcels/intake, require exact match
  if (hrefSegments.length > 1) {
    return pathname === href || pathname.startsWith(href + '/');
  }
  
  // For single-segment hrefs, check if path starts with it
  return pathSegments[0] === hrefSegments[0];
};

export function Layout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [permissions, setPermissions] = useState(defaultPermissions);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  // Fetch role permissions on mount
  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        const response = await axios.get(`${API}/tenant/permissions`, { withCredentials: true });
        setPermissions(response.data);
      } catch (error) {
        console.error('Failed to fetch permissions, using defaults');
      }
    };
    fetchPermissions();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  // Filter nav items based on user's role, custom_permissions, and tenant permissions
  const filteredNavItems = navItems.filter(item => {
    if (!user?.role) return true;
    
    // Owners always have full access
    if (user.role === 'owner') return true;
    
    // Check user's custom_permissions first (takes priority)
    if (user.custom_permissions?.pages) {
      return user.custom_permissions.pages[item.pageId] === true;
    }
    
    // Fall back to tenant-level role permissions
    const rolePerms = permissions[user.role] || defaultPermissions[user.role] || [];
    return rolePerms.includes(item.pageId);
  });

  const NavContent = ({ mobile = false }) => (
    <nav className="flex flex-col gap-1 p-2">
      {filteredNavItems.map((item) => {
        const isActive = isNavItemActive(location.pathname, item.href);
        return (
          <Link
            key={item.href}
            to={item.href}
            onClick={() => mobile && setMobileOpen(false)}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-md transition-all duration-200',
              isActive 
                ? 'bg-[#E8DC88] text-[#3C3F42] font-semibold' 
                : 'text-white/80 hover:bg-[#6B633C] hover:text-white'
            )}
            data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <item.icon className="h-5 w-5 flex-shrink-0" />
            {(!sidebarCollapsed || mobile) && (
              <span className="font-medium">{item.label}</span>
            )}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen bg-[#3C3F42] transition-all duration-300 hidden lg:block border-r-2 border-[#6B633C]',
          sidebarCollapsed ? 'w-16' : 'w-64'
        )}
      >
        {/* Logo Box - White background for visibility */}
        <div className="bg-white border-b border-gray-200">
          <div className={cn(
            "flex items-center justify-center",
            sidebarCollapsed ? "h-16 px-2" : "h-[100px] px-4"
          )}>
            <Link to="/dashboard" className="flex items-center justify-center">
              <img 
                src="/servex-logo-full.png" 
                alt="Servex Holdings" 
                className={cn(
                  "object-contain transition-all duration-300",
                  sidebarCollapsed ? "h-8 w-8" : "w-[120px] h-auto"
                )}
                style={{ imageRendering: 'auto' }}
              />
            </Link>
          </div>
          {/* Collapse button */}
          <div className="absolute top-2 right-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="h-7 w-7 text-gray-500 hover:bg-gray-100"
              data-testid="sidebar-toggle"
            >
              <ChevronLeft className={cn('h-4 w-4 transition-transform', sidebarCollapsed && 'rotate-180')} />
            </Button>
          </div>
        </div>

        {/* Nav Items */}
        <NavContent />

        {/* Tenant Info */}
        {!sidebarCollapsed && user?.tenant_name && (
          <div className="absolute bottom-16 left-0 right-0 px-4 py-3 border-t border-white/10">
            <div className="flex items-center gap-2 text-sm text-white/60">
              <Building2 className="h-4 w-4" />
              <span className="truncate">{user.tenant_name}</span>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <div className={cn('transition-all duration-300', sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64')}>
        {/* Header */}
        <header className="sticky top-0 z-30 h-16 border-b border-[#D4CFC0] bg-white">
          <div className="flex items-center justify-between h-full px-4">
            {/* Mobile Menu */}
            <div className="flex items-center gap-2 lg:hidden">
              <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="text-[#3C3F42]" data-testid="mobile-menu-toggle">
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-64 p-0 bg-[#3C3F42]">
                  <div className="bg-white border-b border-gray-200">
                    <div className="flex items-center justify-center h-[100px] px-4">
                      <img 
                        src="/servex-logo-full.png" 
                        alt="Servex Holdings" 
                        className="w-[120px] h-auto object-contain"
                        loading="eager"
                        decoding="async"
                      />
                    </div>
                  </div>
                  <NavContent mobile />
                </SheetContent>
              </Sheet>
              <Link to="/dashboard" className="lg:hidden">
                <img 
                  src="/servex-logo-full.png" 
                  alt="Servex Holdings" 
                  className="h-8 w-auto max-w-[100px] object-contain"
                  loading="eager"
                  decoding="async"
                />
              </Link>
            </div>

            {/* Page Title (hidden on mobile) */}
            <div className="hidden lg:block">
              <h1 className="font-heading font-semibold text-lg capitalize text-[#3C3F42]">
                {location.pathname.split('/')[1] || 'Dashboard'}
              </h1>
            </div>

            {/* Right Side */}
            <div className="flex items-center gap-2">
              {/* Notification Bell */}
              <NotificationBell />
              
              {/* Theme Toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className="h-9 w-9 text-[#3C3F42]"
                data-testid="theme-toggle"
              >
                {theme === 'dark' ? (
                  <Sun className="h-5 w-5" />
                ) : (
                  <Moon className="h-5 w-5" />
                )}
              </Button>

              {/* User Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="h-9 gap-2 px-2" data-testid="user-menu-trigger">
                    <Avatar className="h-7 w-7">
                      <AvatarImage src={user?.picture} alt={user?.name} />
                      <AvatarFallback className="text-xs bg-[#6B633C] text-white">
                        {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                      </AvatarFallback>
                    </Avatar>
                    <span className="hidden sm:inline text-sm font-medium max-w-[100px] truncate text-[#3C3F42]">
                      {user?.name}
                    </span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <div className="px-2 py-1.5">
                    <p className="text-sm font-medium">{user?.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate('/settings')} data-testid="menu-settings">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-destructive" data-testid="menu-logout">
                    <LogOut className="mr-2 h-4 w-4" />
                    Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
