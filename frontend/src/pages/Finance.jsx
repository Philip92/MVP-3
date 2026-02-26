import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { InvoiceEditor } from '../components/InvoiceEditor';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { Switch } from '../components/ui/switch';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import { 
  Search, Mail, Download, ChevronDown, ChevronRight, MoreVertical,
  FileText, Users, AlertTriangle, Receipt, CheckCircle, Clock,
  AlertCircle, Send, Loader2, X, MessageCircle, RefreshCw, Filter
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

// Default exchange rates
const DEFAULT_RATES = { KES: 6.67, USD: 0.054, EUR: 0.050, GBP: 0.043 };

// Format currency with conversion
const formatCurrency = (amount, currency = 'ZAR', rates = DEFAULT_RATES) => {
  const num = parseFloat(amount) || 0;
  if (currency !== 'ZAR' && rates[currency]) {
    const converted = num * rates[currency];
    const prefix = currency === 'KES' ? 'KES ' : currency === 'USD' ? '$ ' : currency === 'EUR' ? '\u20AC ' : currency === 'GBP' ? '\u00A3 ' : currency + ' ';
    return prefix + converted.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return 'R ' + num.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// Status badge config
const statusConfig = {
  draft: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Unpaid' },
  sent: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Unpaid' },
  paid: { bg: 'bg-green-100', text: 'text-green-700', label: 'Paid ✓' },
  partial: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Partial' },
  overdue: { bg: 'bg-red-100', text: 'text-red-700', label: 'Overdue' }
};

// Row color based on status
const getRowColor = (status) => {
  switch (status) {
    case 'paid': return 'bg-green-50/50';
    case 'partial': return 'bg-yellow-50/50';
    case 'overdue': return 'bg-red-50/50';
    default: return '';
  }
};

// Overdue row color based on days
const getOverdueColor = (days) => {
  if (days > 30) return 'bg-red-100';
  if (days > 14) return 'bg-orange-100';
  return 'bg-yellow-50';
};

// InlineComment - auto-saves on blur
function InlineComment({ invoiceId, initialComment }) {
  const [val, setVal] = React.useState(initialComment || '');
  const [saving, setSaving] = React.useState(false);

  const handleBlur = async () => {
    if (val === initialComment) return;
    setSaving(true);
    try {
      await axios.patch(`${API}/invoices/${invoiceId}`, { comment: val }, { withCredentials: true });
    } catch {
      toast.error('Comment save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <input
      className="w-full text-xs border-0 border-b border-transparent hover:border-gray-300 focus:border-[#6B633C] focus:outline-none bg-transparent py-0.5 px-0"
      value={val}
      onChange={(e) => setVal(e.target.value)}
      onBlur={handleBlur}
      placeholder={saving ? 'Saving…' : 'Add note…'}
    />
  );
}

export function Finance() {
  const [activeTab, setActiveTab] = useState('statements');
  const [loading, setLoading] = useState(true);
  
  // Currency display
  const [displayCurrency, setDisplayCurrency] = useState('ZAR');
  const [exchangeRates, setExchangeRates] = useState(DEFAULT_RATES);
  const [exchangeRate, setExchangeRate] = useState(6.67);
  
  // Client Statements state
  const [statements, setStatements] = useState([]);
  const [tripColumns, setTripColumns] = useState([]);
  const [statementsSummary, setStatementsSummary] = useState({});
  const [statementsSearch, setStatementsSearch] = useState('');
  const [expandedClients, setExpandedClients] = useState({});
  const [clientInvoices, setClientInvoices] = useState({});
  const [statementSortBy, setStatementSortBy] = useState('outstanding_desc');
  const [statementShowPaid, setStatementShowPaid] = useState(false);
  
  // Trip Worksheets state
  const [trips, setTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState('');
  const [worksheetData, setWorksheetData] = useState(null);
  const [selectedInvoices, setSelectedInvoices] = useState([]);
  
  // Overdue state
  const [overdueData, setOverdueData] = useState({ invoices: [], total_overdue: 0, count: 0 });
  const [selectedOverdue, setSelectedOverdue] = useState([]);
  const [overdueTripFilter, setOverdueTripFilter] = useState('all');
  const [overdueSortBy, setOverdueSortBy] = useState('days_overdue');
  
  // Client Debt state
  const [clientDebtData, setClientDebtData] = useState([]);
  const [selectedClients, setSelectedClients] = useState([]);
  const [loadingDebt, setLoadingDebt] = useState(false);
  
  // Email modal state
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [emailData, setEmailData] = useState({
    to: '',
    subject: '',
    body: '',
    invoiceId: null,
    invoiceNumber: ''
  });
  const [sendingEmail, setSendingEmail] = useState(false);
  
  // WhatsApp sending state
  const [whatsappSending, setWhatsappSending] = useState(false);
  const [whatsappQueue, setWhatsappQueue] = useState([]);

  // Fetch exchange rates from settings
  useEffect(() => {
    const fetchExchangeRate = async () => {
      try {
        const response = await axios.get(`${API}/settings/currencies`, { withCredentials: true });
        if (response.data?.currencies) {
          const kesCurrency = response.data.currencies.find(c => c.code === 'KES');
          if (kesCurrency?.exchange_rate) {
            setExchangeRate(kesCurrency.exchange_rate);
          }
        }
      } catch (error) {
        console.error('Failed to fetch exchange rates:', error);
      }
    };
    fetchExchangeRate();
  }, []);

  // Helper for currency formatting with current toggle
  const fmtCurrency = (amount) => formatCurrency(amount, displayCurrency, exchangeRate);

  // Fetch data on mount
  useEffect(() => {
    fetchTrips();
    fetchStatements();
    fetchOverdue();
  }, []);

  // Refetch overdue when filters change
  useEffect(() => {
    if (activeTab === 'overdue') {
      fetchOverdue();
    }
  }, [overdueTripFilter, overdueSortBy]);

  // Fetch trips list
  const fetchTrips = async () => {
    try {
      const response = await axios.get(`${API}/trips`, { withCredentials: true });
      setTrips(response.data || []);
      if (response.data?.length > 0) {
        setSelectedTripId(response.data[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch trips:', error);
    }
  };

  // Fetch client statements
  const fetchStatements = async (sortBy = statementSortBy, showPaid = statementShowPaid) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${API}/finance/client-statements?sort_by=${sortBy}&show_paid=${showPaid}`,
        { withCredentials: true }
      );
      setStatements(response.data.statements || []);
      setTripColumns(response.data.trip_columns || []);
      setStatementsSummary(response.data.summary || {});
    } catch (error) {
      console.error('Failed to fetch statements:', error);
      toast.error('Failed to load client statements');
    } finally {
      setLoading(false);
    }
  };

  // Fetch worksheet for selected trip
  const fetchWorksheet = useCallback(async (tripId) => {
    if (!tripId) return;
    try {
      const response = await axios.get(`${API}/finance/trip-worksheet/${tripId}`, { withCredentials: true });
      setWorksheetData(response.data);
      setSelectedInvoices([]);
    } catch (error) {
      console.error('Failed to fetch worksheet:', error);
      toast.error('Failed to load trip worksheet');
    }
  }, []);

  // Fetch overdue invoices
  const fetchOverdue = async () => {
    try {
      const params = {};
      if (overdueTripFilter && overdueTripFilter !== 'all') {
        params.trip_id = overdueTripFilter;
      }
      if (overdueSortBy) {
        params.sort_by = overdueSortBy;
      }
      const response = await axios.get(`${API}/finance/overdue`, { params, withCredentials: true });
      setOverdueData(response.data);
    } catch (error) {
      console.error('Failed to fetch overdue:', error);
    }
  };

  const fetchClientDebt = async () => {
    setLoadingDebt(true);
    try {
      const response = await axios.get(`${API}/finance/client-debt-summary`, { withCredentials: true });
      setClientDebtData(response.data);
    } catch (error) {
      console.error('Failed to fetch client debt:', error);
      toast.error('Failed to load client debt data');
    } finally {
      setLoadingDebt(false);
    }
  };

  const downloadClientStatement = async (clientId, clientName) => {
    try {
      const response = await axios.get(`${API}/finance/client-statement/${clientId}`, { 
        withCredentials: true,
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `statement_${clientName.replace(/\s/g, '_')}_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Statement downloaded');
    } catch (error) {
      console.error('Failed to download statement:', error);
      toast.error('Failed to download statement');
    }
  };

  const sendPaymentReminders = async () => {
    if (selectedClients.length === 0) {
      toast.error('Please select at least one client');
      return;
    }

    try {
      const response = await axios.post(
        `${API}/finance/send-payment-reminders`,
        { client_ids: selectedClients },
        { withCredentials: true }
      );
      toast.success(response.data.message);
      setSelectedClients([]);
    } catch (error) {
      console.error('Failed to send reminders:', error);
      toast.error('Failed to send reminders');
    }
  };

  // Fetch worksheet when trip changes
  useEffect(() => {
    if (selectedTripId && activeTab === 'worksheets') {
      fetchWorksheet(selectedTripId);
    }
  }, [selectedTripId, activeTab, fetchWorksheet]);

  // Fetch client debt when tab is active
  useEffect(() => {
    if (activeTab === 'debt') {
      fetchClientDebt();
    }
  }, [activeTab]);

  // Toggle client row expansion
  const toggleClientExpand = async (clientId) => {
    if (expandedClients[clientId]) {
      setExpandedClients(prev => ({ ...prev, [clientId]: false }));
    } else {
      // Fetch invoices for this client if not cached
      if (!clientInvoices[clientId]) {
        try {
          const response = await axios.get(
            `${API}/finance/client-statements/${clientId}/invoices`,
            { withCredentials: true }
          );
          setClientInvoices(prev => ({ ...prev, [clientId]: response.data }));
        } catch (error) {
          console.error('Failed to fetch client invoices:', error);
        }
      }
      setExpandedClients(prev => ({ ...prev, [clientId]: true }));
    }
  };

  // Handle invoice selection for batch actions
  const toggleInvoiceSelection = (invoiceId) => {
    setSelectedInvoices(prev => 
      prev.includes(invoiceId) 
        ? prev.filter(id => id !== invoiceId)
        : [...prev, invoiceId]
    );
  };

  const toggleAllInvoices = () => {
    if (!worksheetData?.invoices) return;
    if (selectedInvoices.length === worksheetData.invoices.length) {
      setSelectedInvoices([]);
    } else {
      setSelectedInvoices(worksheetData.invoices.map(inv => inv.id));
    }
  };

  // Open email modal
  const openEmailModal = (invoice, isReminder = false) => {
    const subject = isReminder 
      ? `REMINDER: Invoice ${invoice.invoice_number || invoice.invoiceNumber} is overdue`
      : `Invoice ${invoice.invoice_number || invoice.invoiceNumber} from Servex Holdings`;
    
    const body = isReminder
      ? `Dear ${invoice.client_name},

REMINDER: Invoice ${invoice.invoice_number || invoice.invoiceNumber} is ${invoice.days_overdue || 0} days overdue.

Original due date: ${invoice.due_date ? format(new Date(invoice.due_date), 'dd MMM yyyy') : 'N/A'}
Amount outstanding: ${fmtCurrency(invoice.outstanding)}

Please remit payment urgently.

Payment Details:
FNB Account: 63112859666
Reference: ${invoice.invoice_number || invoice.invoiceNumber}

Thank you,
Servex Holdings`
      : `Dear ${invoice.client_name},

Please find attached Invoice ${invoice.invoice_number || invoice.invoiceNumber} for ${fmtCurrency(invoice.total_amount || invoice.total)}.

Due Date: ${invoice.due_date ? format(new Date(invoice.due_date), 'dd MMM yyyy') : 'N/A'}
Amount Outstanding: ${fmtCurrency(invoice.outstanding)}

Payment Details:
FNB Account: 63112859666
Reference: ${invoice.invoice_number || invoice.invoiceNumber}

Thank you,
Servex Holdings`;

    setEmailData({
      to: invoice.client_email || '',
      subject,
      body,
      invoiceId: invoice.id,
      invoiceNumber: invoice.invoice_number || invoice.invoiceNumber
    });
    setEmailModalOpen(true);
  };

  // Send email
  const handleSendEmail = async () => {
    if (!emailData.to || !emailData.invoiceId) {
      toast.error('Email address is required');
      return;
    }

    setSendingEmail(true);
    try {
      await axios.post(
        `${API}/invoices/${emailData.invoiceId}/send-email`,
        {
          to: emailData.to,
          subject: emailData.subject,
          body: emailData.body,
          attach_pdf: true
        },
        { withCredentials: true }
      );
      toast.success(`Email logged for ${emailData.to}`);
      setEmailModalOpen(false);
    } catch (error) {
      toast.error('Failed to send email');
    } finally {
      setSendingEmail(false);
    }
  };

  // WhatsApp bulk send - queue messages sequentially
  const handleWhatsAppBulkSend = async (invoices, messageType = 'overdue') => {
    // Filter invoices with WhatsApp numbers
    const withWhatsApp = invoices.filter(inv => {
      const whatsapp = inv.client_whatsapp || inv.whatsapp;
      return whatsapp && whatsapp.trim();
    });
    
    const withoutWhatsApp = invoices.filter(inv => {
      const whatsapp = inv.client_whatsapp || inv.whatsapp;
      return !whatsapp || !whatsapp.trim();
    });

    if (withoutWhatsApp.length > 0) {
      const names = withoutWhatsApp.map(inv => inv.client_name).slice(0, 3).join(', ');
      const more = withoutWhatsApp.length > 3 ? ` and ${withoutWhatsApp.length - 3} more` : '';
      toast.warning(`No WhatsApp number for: ${names}${more}`);
    }

    if (withWhatsApp.length === 0) {
      toast.error('No clients with WhatsApp numbers selected');
      return;
    }

    setWhatsappSending(true);
    toast.info(`Sending ${withWhatsApp.length} WhatsApp message(s)...`);

    // Process sequentially with a delay
    for (let i = 0; i < withWhatsApp.length; i++) {
      const inv = withWhatsApp[i];
      const whatsapp = (inv.client_whatsapp || inv.whatsapp || '').replace(/[^\d+]/g, '');
      
      let message;
      if (messageType === 'overdue') {
        message = `Hi ${inv.client_name}, your invoice ${inv.invoice_number} for ${fmtCurrency(inv.outstanding || inv.total_amount)} is overdue. Please arrange payment.`;
      } else {
        message = `Hi ${inv.client_name}, your trip ${inv.trip_number || ''} worksheet totaling ${fmtCurrency(inv.total_amount || inv.outstanding)} is ready. Please review.`;
      }

      // Open WhatsApp Web
      const url = `https://wa.me/${whatsapp}?text=${encodeURIComponent(message)}`;
      window.open(url, '_blank');

      // Log the WhatsApp send
      try {
        await axios.post(`${API}/invoices/${inv.id}/log-whatsapp`, {
          to_number: whatsapp,
          message: message
        }, { withCredentials: true });
      } catch (error) {
        console.error('Failed to log WhatsApp:', error);
      }

      // Wait 2 seconds between each to allow user to send
      if (i < withWhatsApp.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }

    setWhatsappSending(false);
    toast.success(`Opened ${withWhatsApp.length} WhatsApp conversation(s)`);
  };

  // Download PDF
  const handleDownloadPdf = async (invoiceId, type = 'type1') => {
    try {
      const url = type === 'type2' 
        ? `${API}/invoices/${invoiceId}/pdf/type2`
        : `${API}/invoices/${invoiceId}/pdf`;
      const response = await axios.get(url, {
        withCredentials: true,
        responseType: 'blob'
      });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', `invoice_${invoiceId}_${type}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  // Filter statements by search
  const filteredStatements = statements.filter(s => 
    s.client_name.toLowerCase().includes(statementsSearch.toLowerCase())
  );

  return (
    <>
      <div className="space-y-4" data-testid="finance-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-[#3C3F42]">Finance</h1>
            <p className="text-gray-500 text-sm">Manage invoices, statements, and payments</p>
          </div>
          
          {/* Currency Dropdown - Global for all tabs */}
          <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-1.5" data-testid="currency-toggle">
            <span className="text-xs text-muted-foreground mr-1">Currency:</span>
            <Select value={displayCurrency} onValueChange={setDisplayCurrency}>
              <SelectTrigger className="h-7 text-xs w-[100px] border-0 shadow-none" data-testid="currency-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ZAR">ZAR</SelectItem>
                <SelectItem value="KES">KES</SelectItem>
                <SelectItem value="USD">USD</SelectItem>
                <SelectItem value="EUR">EUR</SelectItem>
                <SelectItem value="GBP">GBP</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-xs text-muted-foreground ml-1">
              {displayCurrency !== 'ZAR' ? `(1 ZAR = ${exchangeRate} ${displayCurrency})` : ''}
            </span>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList style={{ backgroundColor: '#3C3F42' }} className="grid w-full grid-cols-4 gap-2 p-2 rounded-lg h-auto">
            <TabsTrigger 
              value="statements" 
              className="data-[state=active]:bg-[#E8DC88] data-[state=active]:text-[#3C3F42] data-[state=active]:font-semibold data-[state=active]:shadow-sm text-white/80 hover:text-white whitespace-nowrap px-4 py-3 text-sm transition-colors"
              data-testid="tab-statements"
            >
              <Users className="h-4 w-4 mr-2 shrink-0" />
              <span>Client Statements</span>
            </TabsTrigger>
            <TabsTrigger 
              value="worksheets"
              className="data-[state=active]:bg-[#E8DC88] data-[state=active]:text-[#3C3F42] data-[state=active]:font-semibold data-[state=active]:shadow-sm text-white/80 hover:text-white whitespace-nowrap px-4 py-3 text-sm transition-colors"
              data-testid="tab-worksheets"
            >
              <FileText className="h-4 w-4 mr-2 shrink-0" />
              <span>Trip Worksheets</span>
            </TabsTrigger>
            <TabsTrigger 
              value="overdue"
              className="data-[state=active]:bg-[#E8DC88] data-[state=active]:text-[#3C3F42] data-[state=active]:font-semibold data-[state=active]:shadow-sm text-white/80 hover:text-white whitespace-nowrap px-4 py-3 text-sm transition-colors"
              data-testid="tab-overdue"
            >
              <AlertTriangle className="h-4 w-4 mr-2 shrink-0" />
              <span>Overdue ({overdueData.count})</span>
            </TabsTrigger>
            <TabsTrigger 
              value="invoices"
              className="data-[state=active]:bg-[#E8DC88] data-[state=active]:text-[#3C3F42] data-[state=active]:font-semibold data-[state=active]:shadow-sm text-white/80 hover:text-white whitespace-nowrap px-4 py-3 text-sm transition-colors"
              data-testid="tab-invoices"
            >
              <Receipt className="h-4 w-4 mr-2 shrink-0" />
              <span>Invoice Details</span>
            </TabsTrigger>
          </TabsList>

          {/* ========== TAB 1: CLIENT STATEMENTS ========== */}
          <TabsContent value="statements" className="mt-6">
            {/* Summary + Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-4 flex-wrap">
                <div className="text-sm">
                  <span className="text-muted-foreground">Outstanding: </span>
                  <span className="font-bold text-[#3C3F42]">{fmtCurrency(statementsSummary.total_outstanding || 0)}</span>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">Overdue: </span>
                  <span className="font-bold text-red-600">{fmtCurrency(statementsSummary.overdue_amount || 0)}</span>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">Clients: </span>
                  <span className="font-bold">{statementsSummary.clients_with_debt || 0}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                  <Input
                    placeholder="Search clients..."
                    value={statementsSearch}
                    onChange={(e) => setStatementsSearch(e.target.value)}
                    className="pl-8 h-8 text-xs w-48"
                    data-testid="statements-search"
                  />
                </div>
                <Select value={statementSortBy} onValueChange={(v) => { setStatementSortBy(v); fetchStatements(v, statementShowPaid); }}>
                  <SelectTrigger className="h-8 text-xs w-40">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="outstanding_desc">Outstanding (High)</SelectItem>
                    <SelectItem value="outstanding_asc">Outstanding (Low)</SelectItem>
                    <SelectItem value="name_asc">Name A-Z</SelectItem>
                    <SelectItem value="name_desc">Name Z-A</SelectItem>
                  </SelectContent>
                </Select>
                <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={statementShowPaid}
                    onChange={(e) => { setStatementShowPaid(e.target.checked); fetchStatements(statementSortBy, e.target.checked); }}
                    className="rounded"
                  />
                  Show paid
                </label>
              </div>
            </div>

            {/* Matrix Table */}
            <div className="relative">
              <div className="overflow-x-auto rounded-lg border border-gray-200 h-[calc(100vh-350px)] sticky-scrollbar" style={{ maxHeight: '70vh' }}>
                <table className="w-full text-xs border-collapse" style={{ minWidth: `${Math.max(800, 280 + tripColumns.length * 120)}px` }}>
                <thead>
                  <tr className="bg-[#6B633C] text-white">
                    {/* Frozen cols */}
                    <th className="sticky left-0 z-10 bg-[#6B633C] px-2 py-2 text-left w-8 font-semibold">#</th>
                    <th className="sticky left-8 z-10 bg-[#6B633C] px-3 py-2 text-left min-w-[160px] font-semibold">Client</th>
                    <th className="sticky left-[208px] z-10 bg-[#6B633C] px-3 py-2 text-right min-w-[110px] font-semibold">Total Invoiced</th>
                    <th className="sticky left-[318px] z-10 bg-[#6B633C] px-3 py-2 text-right min-w-[110px] font-semibold">Outstanding</th>
                    {/* Trip sub-headers */}
                    {tripColumns.map(trip => (
                      <th key={trip} colSpan={2} className="px-1 py-2 text-center min-w-[120px] font-semibold border-l border-white/20">
                        {trip}
                      </th>
                    ))}
                  </tr>
                  <tr className="bg-[#5a5332] text-white/80">
                    <th className="sticky left-0 z-10 bg-[#5a5332]" />
                    <th className="sticky left-8 z-10 bg-[#5a5332]" />
                    <th className="sticky left-[208px] z-10 bg-[#5a5332]" />
                    <th className="sticky left-[318px] z-10 bg-[#5a5332]" />
                    {tripColumns.map(trip => (
                      <React.Fragment key={trip}>
                        <th className="px-1 py-1 text-right border-l border-white/20 text-[10px]">INV</th>
                        <th className="px-1 py-1 text-right text-[10px]">OUT</th>
                      </React.Fragment>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan={4 + tripColumns.length * 2} className="py-8 text-center text-muted-foreground">
                      <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                    </td></tr>
                  ) : filteredStatements.length === 0 ? (
                    <tr><td colSpan={4 + tripColumns.length * 2} className="py-8 text-center text-muted-foreground">
                      No data found
                    </td></tr>
                  ) : filteredStatements.map((s, idx) => (
                    <React.Fragment key={s.client_id}>
                      <tr
                        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                        onClick={() => toggleClientExpand(s.client_id)}
                      >
                        <td className="sticky left-0 z-10 bg-white px-2 py-2 text-muted-foreground text-center">{idx + 1}</td>
                        <td className="sticky left-8 z-10 bg-white px-3 py-2 font-medium">
                          <div className="flex items-center gap-1">
                            {expandedClients[s.client_id] ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
                            {s.client_name}
                          </div>
                        </td>
                        <td className="sticky left-[208px] z-10 bg-white px-3 py-2 text-right font-mono">{fmtCurrency(s.total_invoiced)}</td>
                        <td className={cn("sticky left-[318px] z-10 bg-white px-3 py-2 text-right font-mono font-bold", s.total_outstanding > 0 ? "text-red-600" : "text-green-600")}>
                          {s.total_outstanding > 0 ? fmtCurrency(s.total_outstanding) : '—'}
                        </td>
                        {tripColumns.map(trip => {
                          const ta = s.trip_amounts?.[trip];
                          const inv = ta?.invoiced || 0;
                          const out = ta?.outstanding || 0;
                          const status = ta?.status || null;
                          return (
                            <React.Fragment key={trip}>
                              <td className={cn(
                                "border-l border-gray-100 px-1 py-2 text-right font-mono",
                                inv > 0 && out === 0 ? "bg-green-50" : out > 0 ? "bg-amber-50" : ""
                              )}>
                                {inv > 0 ? fmtCurrency(inv) : '—'}
                              </td>
                              <td className={cn(
                                "px-1 py-2 text-right font-mono",
                                status === 'overdue' ? "text-red-600 bg-red-50" : out > 0 ? "text-amber-700" : "text-green-600"
                              )}>
                                {out > 0 ? fmtCurrency(out) : inv > 0 ? '✓' : '—'}
                              </td>
                            </React.Fragment>
                          );
                        })}
                      </tr>
                      {expandedClients[s.client_id] && (
                        <tr key={`${s.client_id}-exp`} className="bg-gray-50">
                          <td colSpan={4 + tripColumns.length * 2} className="p-0">
                            <div className="p-3 border-t border-gray-200">
                              <p className="text-xs font-semibold mb-2">Invoices for {s.client_name}</p>
                              <table className="w-full text-xs">
                                <thead>
                                  <tr className="bg-gray-100 text-gray-600">
                                    <th className="px-2 py-1 text-left">INV #</th>
                                    <th className="px-2 py-1 text-left">Trip</th>
                                    <th className="px-2 py-1 text-right">Amount</th>
                                    <th className="px-2 py-1 text-right">Outstanding</th>
                                    <th className="px-2 py-1 text-left">Due</th>
                                    <th className="px-2 py-1">Status</th>
                                    <th />
                                  </tr>
                                </thead>
                                <tbody>
                                  {(clientInvoices[s.client_id] || []).map(inv => (
                                    <tr key={inv.id} className="border-b border-gray-100">
                                      <td className="px-2 py-1 font-mono">{inv.invoice_number}</td>
                                      <td className="px-2 py-1">{inv.trip_number}</td>
                                      <td className="px-2 py-1 text-right font-mono">{fmtCurrency(inv.total_amount)}</td>
                                      <td className={cn("px-2 py-1 text-right font-mono", inv.outstanding > 0 ? "text-red-600" : "text-green-600")}>
                                        {inv.outstanding > 0 ? fmtCurrency(inv.outstanding) : '—'}
                                      </td>
                                      <td className="px-2 py-1">{inv.due_date ? format(new Date(inv.due_date), 'dd MMM yy') : '—'}</td>
                                      <td className="px-2 py-1">
                                        <Badge className={cn("text-xs px-1", statusConfig[inv.status]?.bg, statusConfig[inv.status]?.text)}>
                                          {statusConfig[inv.status]?.label || inv.status}
                                        </Badge>
                                      </td>
                                      <td className="px-2 py-1">
                                        <div className="flex items-center gap-1">
                                          <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={() => openEmailModal({ ...inv, client_name: s.client_name, client_email: s.client_email })} title="Send Email">
                                            <Mail className="h-3 w-3" />
                                          </Button>
                                          <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                              <Button variant="ghost" size="sm" className="h-5 w-5 p-0" title="Download PDF">
                                                <Download className="h-3 w-3" />
                                              </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                              <DropdownMenuItem onClick={() => handleDownloadPdf(inv.id, 'type1')} data-testid={`download-pdf-type1-${inv.id}`}>
                                                <Download className="h-3 w-3 mr-2" /> PDF Type 1 (Standard)
                                              </DropdownMenuItem>
                                              <DropdownMenuItem onClick={() => handleDownloadPdf(inv.id, 'type2')} data-testid={`download-pdf-type2-${inv.id}`}>
                                                <Download className="h-3 w-3 mr-2" /> PDF Type 2 (Servex Branded)
                                              </DropdownMenuItem>
                                            </DropdownMenuContent>
                                          </DropdownMenu>
                                        </div>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          </TabsContent>



          {/* ========== TAB 2: TRIP WORKSHEETS ========== */}
          <TabsContent value="worksheets" className="mt-6">
            {/* Trip Selector */}
            <div className="flex items-center gap-4 mb-4">
              <Select value={selectedTripId} onValueChange={setSelectedTripId}>
                <SelectTrigger className="w-[300px]" data-testid="trip-selector">
                  <SelectValue placeholder="Select Trip" />
                </SelectTrigger>
                <SelectContent>
                  {trips.map(trip => (
                    <SelectItem key={trip.id} value={trip.id}>
                      {trip.trip_number} — {trip.route?.join(' → ') || 'No route'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {worksheetData && (
              <>
                {/* Row 1: Capacity Stats */}
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3">
                  {[
                    { label: 'Capacity KG', val: worksheetData.trip.capacity_kg ? `${worksheetData.trip.capacity_kg} kg` : '—' },
                    { label: 'Used KG', val: worksheetData.summary.used_kg ? `${worksheetData.summary.used_kg} kg (${worksheetData.trip.capacity_kg ? Math.round(worksheetData.summary.used_kg / worksheetData.trip.capacity_kg * 100) : '?'}%)` : '0 kg' },
                    { label: 'Remaining KG', val: worksheetData.summary.remaining_kg ? `${worksheetData.summary.remaining_kg} kg` : '—' },
                    { label: 'Capacity CBM', val: worksheetData.trip.capacity_cbm ? `${worksheetData.trip.capacity_cbm} m³` : '—' },
                    { label: 'Used CBM', val: worksheetData.summary.used_cbm ? `${worksheetData.summary.used_cbm.toFixed(3)} m³` : '0' },
                    { label: 'Remaining CBM', val: worksheetData.summary.remaining_cbm ? `${worksheetData.summary.remaining_cbm.toFixed(3)} m³` : '—' }
                  ].map(({ label, val }) => (
                    <Card key={label} className="border rounded-lg shadow-none">
                      <CardContent className="p-3">
                        <p className="text-xs text-muted-foreground">{label}</p>
                        <p className="text-sm font-bold text-[#3C3F42] mt-0.5">{val}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Row 2: Revenue Stats */}
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-5">
                  {[
                    { label: 'Gross Revenue', val: fmtCurrency(worksheetData.summary.total_revenue) },
                    { label: 'Total Collected', val: fmtCurrency(worksheetData.summary.total_collected) },
                    { label: 'Outstanding', val: fmtCurrency(worksheetData.summary.total_outstanding) },
                    { label: 'Rev / Ton', val: worksheetData.summary.revenue_per_ton ? fmtCurrency(worksheetData.summary.revenue_per_ton) : '—' },
                    { label: 'Rev / KG', val: worksheetData.summary.revenue_per_kg ? fmtCurrency(worksheetData.summary.revenue_per_kg) : '—' },
                    { label: 'Paid', val: `${worksheetData.summary.invoices_paid} of ${worksheetData.summary.invoices_total}` }
                  ].map(({ label, val }) => (
                    <Card key={label} className="border rounded-lg shadow-none">
                      <CardContent className="p-3">
                        <p className="text-xs text-muted-foreground">{label}</p>
                        <p className="text-sm font-bold text-[#3C3F42] mt-0.5">{val}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Invoice Table */}
                <Card className="border border-gray-200">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-[#6B633C]">
                          <TableHead className="w-[40px]">
                            <Checkbox
                              checked={selectedInvoices.length === worksheetData.invoices.length && worksheetData.invoices.length > 0}
                              onCheckedChange={toggleAllInvoices}
                              className="border-white"
                            />
                          </TableHead>
                          <TableHead className="text-white font-semibold text-xs">Sender</TableHead>
                          <TableHead className="text-white font-semibold text-xs">INV No</TableHead>
                          <TableHead className="text-white font-semibold text-xs">Recipient</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-right">KG</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-right">Ship KG</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-right">CBM</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-right">Rate</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-right">ZAR</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-right">KSH</TableHead>
                          <TableHead className="text-white font-semibold text-xs">Comment</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-center">Status</TableHead>
                          <TableHead className="text-white font-semibold text-xs text-right">Outstanding</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {worksheetData.invoices.map((inv) => (
                          <TableRow
                            key={inv.id}
                            className={cn(
                              "border-b border-gray-100 text-sm",
                              inv.status === 'paid' ? 'bg-green-50' :
                              inv.status === 'partial' ? 'bg-amber-50' :
                              inv.status === 'overdue' ? 'bg-red-50' : ''
                            )}
                          >
                            <TableCell>
                              <Checkbox
                                checked={selectedInvoices.includes(inv.id)}
                                onCheckedChange={() => toggleInvoiceSelection(inv.id)}
                              />
                            </TableCell>
                            <TableCell className="font-medium text-xs">{inv.client_name}</TableCell>
                            <TableCell className="font-mono text-xs">{inv.invoice_number}</TableCell>
                            <TableCell className="text-xs">{inv.recipient}</TableCell>
                            <TableCell className="text-right font-mono text-xs">{inv.weight_kg > 0 ? inv.weight_kg.toFixed(1) : '—'}</TableCell>
                            <TableCell className="text-right font-mono text-xs">{inv.shipping_weight > 0 ? inv.shipping_weight.toFixed(1) : '—'}</TableCell>
                            <TableCell className="text-right font-mono text-xs">{inv.cbm > 0 ? inv.cbm.toFixed(3) : '—'}</TableCell>
                            <TableCell className="text-right font-mono text-xs">{inv.effective_rate > 0 ? `R${inv.effective_rate.toFixed(2)}` : '—'}</TableCell>
                            <TableCell className="text-right font-mono text-xs">{fmtCurrency(inv.total_amount)}</TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              {displayCurrency === 'KES'
                                ? `KES ${(inv.total_amount * exchangeRate).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`
                                : `KES ${(inv.total_amount * exchangeRate).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}`
                              }
                            </TableCell>
                            <TableCell className="min-w-[120px]">
                              <InlineComment invoiceId={inv.id} initialComment={inv.comment || ''} />
                            </TableCell>
                            <TableCell className="text-center">
                              <Badge className={cn(
                                "text-xs px-1.5",
                                statusConfig[inv.status]?.bg,
                                statusConfig[inv.status]?.text
                              )}>
                                {statusConfig[inv.status]?.label || inv.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs font-medium text-red-600">
                              {inv.outstanding > 0 ? fmtCurrency(inv.outstanding) : '—'}
                            </TableCell>
                          </TableRow>
                        ))}
                        {/* Totals Footer */}
                        {worksheetData.invoices.length > 0 && (
                          <TableRow className="bg-gray-50 font-bold border-t-2">
                            <TableCell colSpan={4} className="text-xs font-bold pl-4">TOTALS</TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              {worksheetData.invoices.reduce((s, i) => s + i.weight_kg, 0).toFixed(1)}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              {worksheetData.invoices.reduce((s, i) => s + i.shipping_weight, 0).toFixed(1)}
                            </TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              {worksheetData.invoices.reduce((s, i) => s + i.cbm, 0).toFixed(3)}
                            </TableCell>
                            <TableCell />
                            <TableCell className="text-right font-mono text-xs">{fmtCurrency(worksheetData.summary.total_revenue)}</TableCell>
                            <TableCell className="text-right font-mono text-xs">
                              KES {(worksheetData.summary.total_revenue * exchangeRate).toLocaleString('en-ZA', { maximumFractionDigits: 0 })}
                            </TableCell>
                            <TableCell colSpan={2} />
                            <TableCell className="text-right font-mono text-xs text-red-600">{fmtCurrency(worksheetData.summary.total_outstanding)}</TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </Card>

                {/* Batch Actions */}
                {selectedInvoices.length > 0 && (
                  <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-[#3C3F42] text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-4 z-50">
                    <span className="text-sm">{selectedInvoices.length} selected</span>
                    <Button variant="secondary" size="sm" onClick={() => { const sel = worksheetData.invoices.filter(i => selectedInvoices.includes(i.id)); handleWhatsAppBulkSend(sel, 'worksheet'); }} disabled={whatsappSending}>
                      <MessageCircle className="h-4 w-4 mr-2" /> WhatsApp
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => toast.info('Batch email coming soon')}>
                      <Send className="h-4 w-4 mr-2" /> Email
                    </Button>
                  </div>
                )}
              </>
            )}
          </TabsContent>

          {/* ========== TAB 3: OVERDUE ========== */}
          <TabsContent value="overdue" className="mt-6">
            {/* Filters and Sort */}
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <Select value={overdueTripFilter} onValueChange={setOverdueTripFilter}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Filter by Trip" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Trips</SelectItem>
                  {trips.map(trip => (
                    <SelectItem key={trip.id} value={trip.id}>
                      {trip.trip_number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Select value={overdueSortBy} onValueChange={setOverdueSortBy}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="days_overdue">Days Overdue</SelectItem>
                  <SelectItem value="amount_desc">Amount (High → Low)</SelectItem>
                  <SelectItem value="amount_asc">Amount (Low → High)</SelectItem>
                  <SelectItem value="client_asc">Client A-Z</SelectItem>
                  <SelectItem value="client_desc">Client Z-A</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Summary */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-[#3C3F42]">
                  {overdueData.count} Overdue Invoice{overdueData.count !== 1 ? 's' : ''}
                </h2>
                <p className="text-sm text-gray-500">
                  Total outstanding: {fmtCurrency(overdueData.total_overdue)}
                </p>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline"
                  onClick={() => {
                    const selected = overdueData.invoices.filter(inv => selectedOverdue.includes(inv.id));
                    if (selected.length === 0) {
                      toast.error('Please select invoices to send WhatsApp');
                      return;
                    }
                    handleWhatsAppBulkSend(selected, 'overdue');
                  }}
                  disabled={selectedOverdue.length === 0 || whatsappSending}
                  data-testid="bulk-whatsapp-btn"
                >
                  {whatsappSending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <MessageCircle className="h-4 w-4 mr-2" />}
                  WhatsApp Selected ({selectedOverdue.length})
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => {
                    if (overdueData.invoices.length === 0) return;
                    handleWhatsAppBulkSend(overdueData.invoices, 'overdue');
                  }}
                  disabled={overdueData.invoices.length === 0 || whatsappSending}
                >
                  <Send className="h-4 w-4 mr-2" /> Send All Reminders
                </Button>
              </div>
            </div>

            {/* Overdue Table */}
            <Card className="border border-gray-200">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-[#6B633C]">
                      <TableHead className="w-[40px]">
                        <Checkbox 
                          checked={selectedOverdue.length === overdueData.invoices.length && overdueData.invoices.length > 0}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedOverdue(overdueData.invoices.map(inv => inv.id));
                            } else {
                              setSelectedOverdue([]);
                            }
                          }}
                          className="border-white"
                        />
                      </TableHead>
                      <TableHead className="text-white font-semibold">Client Name</TableHead>
                      <TableHead className="text-white font-semibold">Invoice #</TableHead>
                      <TableHead className="text-white font-semibold">Trip</TableHead>
                      <TableHead className="text-white font-semibold">Due Date</TableHead>
                      <TableHead className="text-white font-semibold text-center">Days Overdue</TableHead>
                      <TableHead className="text-white font-semibold text-right">Outstanding</TableHead>
                      <TableHead className="text-white font-semibold w-[140px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overdueData.invoices.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                          <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                          No overdue invoices!
                        </TableCell>
                      </TableRow>
                    ) : (
                      overdueData.invoices.map((inv) => (
                        <TableRow 
                          key={inv.id}
                          className={cn("border-b border-gray-100", getOverdueColor(inv.days_overdue))}
                        >
                          <TableCell>
                            <Checkbox 
                              checked={selectedOverdue.includes(inv.id)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedOverdue([...selectedOverdue, inv.id]);
                                } else {
                                  setSelectedOverdue(selectedOverdue.filter(id => id !== inv.id));
                                }
                              }}
                            />
                          </TableCell>
                          <TableCell className="font-medium">{inv.client_name}</TableCell>
                          <TableCell className="font-mono text-sm">{inv.invoice_number}</TableCell>
                          <TableCell>{inv.trip_number}</TableCell>
                          <TableCell>
                            {inv.due_date ? format(new Date(inv.due_date), 'dd MMM yyyy') : '-'}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge className={cn(
                              "text-xs",
                              inv.days_overdue > 30 ? "bg-red-600 text-white" :
                              inv.days_overdue > 14 ? "bg-orange-500 text-white" :
                              "bg-yellow-500 text-white"
                            )}>
                              {inv.days_overdue} days
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono font-bold text-red-600">
                            {fmtCurrency(inv.outstanding)}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={() => openEmailModal(inv, true)}
                                disabled={!inv.client_email}
                              >
                                <Mail className="h-3 w-3" />
                              </Button>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="outline" size="sm" title="Download PDF">
                                    <Download className="h-3 w-3" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem onClick={() => handleDownloadPdf(inv.id, 'type1')}>
                                    <Download className="h-3 w-3 mr-2" /> PDF Type 1
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => handleDownloadPdf(inv.id, 'type2')}>
                                    <Download className="h-3 w-3 mr-2" /> PDF Type 2 (Servex)
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                              <Button 
                                variant="outline" 
                                size="sm"
                                onClick={() => handleWhatsAppBulkSend([inv], 'overdue')}
                                disabled={!inv.client_whatsapp}
                                title={inv.client_whatsapp ? 'Send WhatsApp' : 'No WhatsApp number'}
                              >
                                <MessageCircle className="h-3 w-3" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </Card>
          </TabsContent>

          {/* ========== TAB 4: INVOICE DETAILS ========== */}
          <TabsContent value="invoices" className="mt-6">
            <InvoiceEditor />
          </TabsContent>
        </Tabs>

        {/* Email Modal */}
        <Dialog open={emailModalOpen} onOpenChange={setEmailModalOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5" />
                Send Invoice Email
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <label className="text-sm font-medium">To:</label>
                <Input
                  value={emailData.to}
                  onChange={(e) => setEmailData(prev => ({ ...prev, to: e.target.value }))}
                  placeholder="client@email.com"
                  className="mt-1"
                />
                {!emailData.to && (
                  <p className="text-xs text-amber-600 mt-1">
                    ⚠️ No email on file for this client
                  </p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium">Subject:</label>
                <Input
                  value={emailData.subject}
                  onChange={(e) => setEmailData(prev => ({ ...prev, subject: e.target.value }))}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Message:</label>
                <Textarea
                  value={emailData.body}
                  onChange={(e) => setEmailData(prev => ({ ...prev, body: e.target.value }))}
                  rows={10}
                  className="mt-1 font-mono text-sm"
                />
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="text-sm text-gray-600">
                  📎 Attachment: Invoice_{emailData.invoiceNumber}.pdf
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEmailModalOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleSendEmail}
                disabled={sendingEmail || !emailData.to}
                className="bg-[#6B633C] hover:bg-[#5a5332]"
              >
                {sendingEmail ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Sending...</>
                ) : (
                  <><Send className="h-4 w-4 mr-2" /> Send Email</>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}

export default Finance;
