import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent } from '../components/ui/card';
import { LoginForm } from '../components/LoginForm';
import { Truck, Package, MapPin, Users, BarChart3, Shield, Moon, Sun, Check } from 'lucide-react';

export function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated, loading } = useAuth();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [loading, isAuthenticated, navigate]);

  const features = [
    {
      icon: Package,
      title: 'Shipment Tracking',
      description: 'Track every piece with barcode scanning and real-time status updates.'
    },
    {
      icon: Users,
      title: 'Client Management',
      description: 'Manage clients, rates, and payment terms all in one place.'
    },
    {
      icon: Truck,
      title: 'Trip Planning',
      description: 'Organize shipments into trips with automated barcode generation.'
    },
    {
      icon: MapPin,
      title: 'Multi-Destination',
      description: 'Handle complex routes across Africa with ease.'
    },
    {
      icon: BarChart3,
      title: 'Real-time Analytics',
      description: 'Get insights into your operations with comprehensive dashboards.'
    },
    {
      icon: Shield,
      title: 'Multi-Tenant Security',
      description: 'Your data is isolated and secure with subdomain-based tenancy.'
    }
  ];

  const benefits = [
    'Reduce shipment tracking errors by 90%',
    'Speed up warehouse operations with barcode scanning',
    'Manage unlimited clients and shipments',
    'Role-based access for your entire team'
  ];

  return (
    <div className="min-h-screen bg-[#9B9B9D]">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-[#D4CFC0]">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-lg bg-[#6B633C] flex items-center justify-center">
              <Truck className="h-5 w-5 text-white" />
            </div>
            <span className="font-heading font-bold text-xl text-[#3C3F42]">Servex Holdings</span>
          </div>
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-gray-100 text-[#3C3F42]"
            data-testid="landing-theme-toggle"
          >
            {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </div>
      </header>

      {/* Hero Section with Login Form */}
      <section className="relative pt-24 pb-16 px-4 overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div 
            className="absolute inset-0 bg-cover bg-center opacity-10"
            style={{ backgroundImage: `url(https://images.unsplash.com/photo-1766561994067-dbd575e1cff2?q=80&w=2400&auto=format&fit=crop)` }}
          />
          <div className="absolute inset-0 bg-gradient-to-b from-[#E8DC88]/20 via-[#9B9B9D] to-[#9B9B9D]" />
        </div>

        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            {/* Left: Info Section */}
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white text-sm text-[#3C3F42] border border-[#D4CFC0]">
                <span className="h-2 w-2 rounded-full bg-[#6B633C] animate-pulse" />
                Built for African Freight Companies
              </div>
              
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#3C3F42]">
                Logistics Management
                <span className="text-[#6B633C] block">Made Simple</span>
              </h1>
              
              <p className="text-lg text-[#3C3F42]/80 max-w-lg">
                A powerful multi-tenant SaaS platform designed for African freight companies. 
                Track shipments, manage clients, and optimize your operations.
              </p>

              <div className="space-y-3">
                {benefits.map((benefit, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-[#3C3F42]/80">
                    <Check className="h-4 w-4 text-[#6B633C] flex-shrink-0" />
                    {benefit}
                  </div>
                ))}
              </div>

              {/* Stats Card - Desktop Only */}
              <div className="hidden lg:block">
                <Card className="bg-white shadow-lg">
                  <CardContent className="p-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <p className="text-sm text-[#938878]">Today's Shipments</p>
                          <p className="text-3xl font-bold font-mono text-[#3C3F42]">1,247</p>
                        </div>
                        <div className="h-12 w-12 rounded-lg bg-[#6B633C]/10 flex items-center justify-center">
                          <Package className="h-6 w-6 text-[#6B633C]" />
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-[#D4CFC0]">
                        <div>
                          <p className="text-xs text-[#938878]">Warehouse</p>
                          <p className="text-lg font-semibold font-mono text-[#3C3F42]">423</p>
                        </div>
                        <div>
                          <p className="text-xs text-[#938878]">In Transit</p>
                          <p className="text-lg font-semibold font-mono text-[#3C3F42]">512</p>
                        </div>
                        <div>
                          <p className="text-xs text-[#938878]">Delivered</p>
                          <p className="text-lg font-semibold font-mono text-[#3C3F42]">312</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Right: Login Form */}
            <div className="lg:sticky lg:top-24">
              <LoginForm />
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-[#E8E4D0]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="font-heading text-3xl sm:text-4xl font-bold text-[#3C3F42]">
              Everything You Need
            </h2>
            <p className="mt-3 text-[#938878] max-w-2xl mx-auto">
              A complete logistics management solution built for the unique needs of African freight operations.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <Card key={i} className="group hover:shadow-md transition-shadow bg-white">
                <CardContent className="p-6">
                  <div className="h-12 w-12 rounded-lg bg-[#6B633C]/10 flex items-center justify-center mb-4 group-hover:bg-[#6B633C]/20 transition-colors">
                    <feature.icon className="h-6 w-6 text-[#6B633C]" />
                  </div>
                  <h3 className="font-heading font-semibold text-lg mb-2 text-[#3C3F42]">{feature.title}</h3>
                  <p className="text-sm text-[#938878]">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#D4CFC0] py-8 px-4 bg-white">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-[#6B633C] flex items-center justify-center">
              <Truck className="h-4 w-4 text-white" />
            </div>
            <span className="font-heading font-bold text-[#3C3F42]">Servex Holdings</span>
          </div>
          <p className="text-sm text-[#938878]">
            &copy; {new Date().getFullYear()} Servex Holdings. Built for African businesses.
          </p>
        </div>
      </footer>
    </div>
  );
}
