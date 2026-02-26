import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Switch } from '../components/ui/switch';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../components/ui/table';
import {
  LineChart, Line, ResponsiveContainer, Tooltip
} from 'recharts';
import {
  Package, Users, Truck, Warehouse, ArrowRight, PackagePlus,
  TrendingUp, TrendingDown, DollarSign, AlertTriangle, Clock, BarChart2
} from 'lucide-react';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;
const DEFAULT_KES = 6.67;

const statusColors = {
  warehouse: 'bg-blue-100 text-blue-700',
  in_transit: 'bg-amber-100 text-amber-700',
  delivered: 'bg-green-100 text-green-700',
  arrived: 'bg-purple-100 text-purple-700'
};

const fmtAmt = (v, currency = 'ZAR', rate = DEFAULT_KES) => {
  const n = parseFloat(v) || 0;
  if (currency === 'KES') return 'KES ' + (n * rate).toLocaleString('en-ZA', { maximumFractionDigits: 0 });
  return 'R ' + n.toLocaleString('en-ZA', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

function Sparkline({ data }) {
  if (!data || data.length === 0) return null;
  const pts = data.map((v, i) => ({ i, v }));
  return (
    <ResponsiveContainer width="100%" height={32}>
      <LineChart data={pts}>
        <Line type="monotone" dataKey="v" stroke="#2D6A4F" strokeWidth={2} dot={false} />
        <Tooltip
          formatter={(v) => [`R ${v.toLocaleString()}`, 'Revenue']}
          labelFormatter={() => ''}
          contentStyle={{ fontSize: '11px', padding: '2px 6px' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function KpiTile({ label, value, sub, changePct, sparkline, isLoading, redBorder, href, icon: Icon }) {
  const up = changePct >= 0;
  const content = (
    <Card className={cn(
      "rounded-xl shadow-sm border hover:shadow-md transition-shadow min-h-[120px] flex flex-col justify-between",
      redBorder && "border-red-400"
    )}>
      <CardContent className="p-3 flex flex-col h-full">
        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-28" />
            <Skeleton className="h-3 w-16" />
          </div>
        ) : (
          <>
            <div>
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{label}</p>
                {Icon && <Icon className="h-3 w-3 text-muted-foreground" />}
              </div>
              <p className="text-xl font-bold text-[#3C3F42] leading-none mb-1">{value}</p>
              <div className="flex items-center gap-2 flex-wrap">
                {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
                {changePct !== undefined && (
                  <Badge className={cn(
                    "text-xs px-1.5 py-0",
                    up ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                  )}>
                    {up ? <TrendingUp className="h-3 w-3 inline mr-0.5" /> : <TrendingDown className="h-3 w-3 inline mr-0.5" />}
                    {Math.abs(changePct)}%
                  </Badge>
                )}
              </div>
            </div>
            {/* Sparkline or placeholder for equal height */}
            <div className="mt-2 h-[28px]">
              {sparkline && sparkline.length > 0
                ? <Sparkline data={sparkline} />
                : null
              }
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
  if (href) return <Link to={href}>{content}</Link>;
  return content;
}

export function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('mtd');
  const [currency, setCurrency] = useState('ZAR');
  const [kesRate, setKesRate] = useState(DEFAULT_KES);

  useEffect(() => {
    const fetchRate = async () => {
      try {
        const r = await axios.get(`${API}/settings/currencies`, { withCredentials: true });
        const kes = r.data?.currencies?.find(c => c.code === 'KES');
        if (kes?.exchange_rate) setKesRate(kes.exchange_rate);
      } catch {}
    };
    fetchRate();
  }, []);

  useEffect(() => {
    fetchStats();
  }, [period]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/dashboard/stats?period=${period}`, { withCredentials: true });
      setStats(r.data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const fmt = (v) => fmtAmt(v, currency, kesRate);
  const fin = stats?.financial || {};
  const ops = stats?.operations || {};

  return (
    <>
      <div className="space-y-5" data-testid="dashboard-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="font-heading text-xl sm:text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground text-sm mt-0.5">Logistics & Financial Overview</p>
          </div>
          {/* Filter Bar */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Period Toggle */}
            <div className="flex items-center bg-gray-100 rounded-lg p-0.5 gap-0.5" data-testid="period-toggle">
              {['mtd', 'last_month', '3m', 'all'].map(p => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={cn(
                    "px-2 py-1 rounded-md text-xs font-medium transition-colors",
                    period === p ? "bg-white text-[#6B633C] shadow-sm font-semibold" : "text-gray-500 hover:text-gray-700"
                  )}
                  data-testid={`period-${p}`}
                >
                  {p === 'mtd' ? 'MTD' : p === 'last_month' ? 'Last Mo.' : p === '3m' ? '3M' : 'All'}
                </button>
              ))}
            </div>
            {/* ZAR / KES Toggle */}
            <div className="flex items-center gap-2 bg-white border rounded-lg px-2 py-1" data-testid="currency-toggle-dashboard">
              <span className={cn("text-xs font-medium", currency === 'ZAR' ? "text-[#6B633C]" : "text-gray-400")}>ZAR</span>
              <Switch
                checked={currency === 'KES'}
                onCheckedChange={(c) => setCurrency(c ? 'KES' : 'ZAR')}
                data-testid="currency-switch-dashboard"
              />
              <span className={cn("text-xs font-medium", currency === 'KES' ? "text-[#6B633C]" : "text-gray-400")}>KES</span>
            </div>
            <div className="flex gap-2">
              <Button asChild variant="outline" size="sm" className="h-8 text-xs">
                <Link to="/scanner">Quick Scan</Link>
              </Button>
              <Button asChild size="sm" className="bg-[#6B633C] hover:bg-[#6B633C]/90 h-8 text-xs">
                <Link to="/parcels/intake">
                  <PackagePlus className="h-3 w-3 mr-1" /> Add Parcel
                </Link>
              </Button>
            </div>
          </div>
        </div>

        {/* Quick Actions — just below filter bar */}
        <div className="flex gap-2 flex-wrap">
          {[
            { to: '/clients/new', icon: Users, label: 'Add Client' },
            { to: '/trips/new', icon: Truck, label: 'Create Trip' },
          ].map(({ to, icon: Icon, label }) => (
            <Button key={to} variant="outline" size="sm" asChild className="h-8 text-xs">
              <Link to={to}>
                <Icon className="h-3 w-3 mr-1" />
                {label}
              </Link>
            </Button>
          ))}
        </div>

        {/* Row 1: Revenue */}
        <div className="bg-yellow-50 bg-opacity-30 p-4 rounded-lg border border-yellow-100">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Revenue</p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiTile
              label="Revenue (Period)"
              value={fmt(fin.revenue_mtd)}
              sub={`vs ${fmt(fin.revenue_last_month)} last`}
              changePct={fin.revenue_change_pct}
              sparkline={fin.revenue_sparkline}
              isLoading={loading}
              icon={TrendingUp}
            />
            <KpiTile 
              label="Accounts Receivable" 
              value={fmt(fin.accounts_receivable)} 
              sub="Total open invoices" 
              sparkline={fin.receivables_sparkline}
              isLoading={loading} 
              icon={DollarSign} 
              href="/finance" 
            />
            <KpiTile 
              label="Overdue Amount" 
              value={fmt(fin.overdue_amount)} 
              sub="Past due date" 
              sparkline={fin.overdue_sparkline}
              redBorder={fin.overdue_amount > 0} 
              isLoading={loading} 
              icon={AlertTriangle} 
              href="/finance" 
            />
            <KpiTile 
              label="Collection Rate" 
              value={`${fin.collection_rate ?? 0}%`} 
              sub="Of total invoiced" 
              sparkline={fin.collection_rate_sparkline}
              isLoading={loading} 
              icon={BarChart2} 
            />
          </div>
        </div>

        {/* Row 2: Operations */}
        <div className="bg-green-50 bg-opacity-30 p-4 rounded-lg border border-green-100">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Operations</p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiTile 
              label="In Warehouse" 
              value={(ops.warehouse ?? 0).toLocaleString()} 
              sub="parcels" 
              isLoading={loading} 
              icon={Warehouse} 
              href="/warehouse" 
            />
            <KpiTile 
              label="In Transit" 
              value={(ops.in_transit ?? 0).toLocaleString()} 
              sub="shipments" 
              isLoading={loading} 
              icon={Truck} 
              href="/trips" 
            />
            <KpiTile 
              label="Awaiting Collection" 
              value={(ops.awaiting_collection ?? 0).toLocaleString()} 
              sub="arrived parcels" 
              isLoading={loading} 
              icon={Clock} 
              href="/warehouse" 
            />
            <KpiTile 
              label="Uninvoiced Parcels" 
              value={(ops.uninvoiced_parcels ?? 0).toLocaleString()} 
              sub="no invoice attached" 
              isLoading={loading} 
              icon={Package} 
              redBorder={ops.uninvoiced_parcels > 0} 
              href="/finance" 
            />
          </div>
        </div>

        {/* Row 3: Summary */}
        <div className="bg-slate-50 bg-opacity-30 p-4 rounded-lg border border-slate-100">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">Summary</p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiTile 
              label="Active Clients" 
              value={(stats?.total_clients ?? 0).toLocaleString()} 
              isLoading={loading} 
              icon={Users} 
              href="/clients" 
            />
            <KpiTile 
              label="Total Trips" 
              value={(stats?.total_trips ?? 0).toLocaleString()} 
              isLoading={loading} 
              icon={Truck} 
              href="/trips" 
            />
            <KpiTile 
              label="Total Shipments" 
              value={(stats?.total_shipments ?? 0).toLocaleString()} 
              isLoading={loading} 
              icon={Package} 
              href="/shipments" 
            />
            <KpiTile 
              label="Delivered" 
              value={(ops.delivered ?? 0).toLocaleString()} 
              sub="all time" 
              isLoading={loading} 
              icon={TrendingUp} 
            />
          </div>
        </div>
      </div>
    </>
  );
}
