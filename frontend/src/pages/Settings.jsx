import { useState, useEffect, useRef, useMemo } from 'react';
import axios from 'axios';
import { debounce } from 'lodash';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Checkbox } from '../components/ui/checkbox';
import { Badge } from '../components/ui/badge';
import WhatsAppTemplateEditor from '../components/WhatsAppTemplateEditor';
import PrintNodeSettings from '../components/PrintNodeSettings';
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import { toast } from 'sonner';
import { 
  Building2, Save, Loader2, Calculator, Bell, Database, 
  Upload, Download, RefreshCw, Shield, Warehouse, DollarSign,
  Plus, Pencil, Trash2, AlertTriangle, FileSpreadsheet, Users, FileText, X, MessageSquare, Printer
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const API = `${window.location.origin}/api`;

// All available pages for permissions (scanner removed)
const allPages = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'parcel-intake', label: 'Parcel Intake' },
  { id: 'warehouse', label: 'Warehouse' },
  { id: 'clients', label: 'Clients' },
  { id: 'loading', label: 'Loading' },
  { id: 'trips', label: 'Trips' },
  { id: 'finance', label: 'Finance' },
  { id: 'fleet', label: 'Fleet' },
  { id: 'team', label: 'Team' },
  { id: 'settings', label: 'Settings' },
];

// All roles
const allRoles = [
  { id: 'owner', label: 'Owner', locked: true },
  { id: 'manager', label: 'Manager' },
  { id: 'warehouse', label: 'Warehouse' },
  { id: 'finance', label: 'Finance' },
  { id: 'driver', label: 'Driver' },
];

// Default permissions (owner gets all, scanner removed)
const defaultPermissions = {
  owner: allPages.map(p => p.id),
  manager: ['dashboard', 'parcel-intake', 'warehouse', 'clients', 'loading', 'trips', 'finance', 'fleet', 'team'],
  warehouse: ['dashboard', 'parcel-intake', 'warehouse', 'loading'],
  finance: ['dashboard', 'clients', 'finance'],
  driver: ['dashboard', 'trips'],
};

export function Settings() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('company');
  const fileInputRef = useRef(null);
  
  // Company Profile
  const [companyData, setCompanyData] = useState({
    company_name: '',
    logo_url: '',
    primary_color: '#6B633C',
    default_currency: 'ZAR',
    address: '',
    phone: '',
    email: '',
  });

  // Pricing & Calculations
  const [pricingData, setPricingData] = useState({
    volumetric_divisor: 5000,
    default_rate_type: 'per_kg',
    default_rate_value: 0,
    fuel_surcharge_percentage: 0,
  });

  // Notifications
  const [notificationData, setNotificationData] = useState({
    email_notifications: true,
    invoice_sent_email: true,
    trip_completed_email: true,
    overdue_invoice_email: true,
  });

  // Role Permissions
  const [permissions, setPermissions] = useState(defaultPermissions);

  // Warehouses
  const [warehouses, setWarehouses] = useState([]);
  const [warehouseModalOpen, setWarehouseModalOpen] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState(null);
  const [warehouseForm, setWarehouseForm] = useState({
    name: '',
    location: '',
    contact_person: '',
    phone: '',
    status: 'active'
  });

  // Currencies
  const [currencies, setCurrencies] = useState({ base_currency: 'ZAR', exchange_rates: [] });
  const [currencyModalOpen, setCurrencyModalOpen] = useState(false);
  const [currencyForm, setCurrencyForm] = useState({ code: '', name: '', rate_to_base: '' });

  // Data Management
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importWarehouseId, setImportWarehouseId] = useState('');
  const [importModalOpen, setImportModalOpen] = useState(false);
  
  // Client CSV Import/Export
  const [clientImportModalOpen, setClientImportModalOpen] = useState(false);
  const [clientImportData, setClientImportData] = useState(null);
  const [clientImporting, setClientImporting] = useState(false);
  const clientFileInputRef = useRef(null);
  
  // Parcel Import Preview
  const [parcelImportPreview, setParcelImportPreview] = useState(null);
  const [parcelImportModalOpen, setParcelImportModalOpen] = useState(false);
  const [parcelImporting, setParcelImporting] = useState(false);
  const parcelFileInputRef = useRef(null);

  // Audit Log
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadingAuditLogs, setLoadingAuditLogs] = useState(false);
  const [auditFilters, setAuditFilters] = useState({
    date_from: '',
    date_to: '',
    user_id: 'all',
    module: 'all'
  });
  const [users, setUsers] = useState([]);

  // Banking Details
  const [bankAccounts, setBankAccounts] = useState([]);
  const [savingBanking, setSavingBanking] = useState(false);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    await Promise.all([
      fetchTenant(),
      fetchPermissions(),
      fetchWarehouses(),
      fetchCurrencies()
    ]);
    setLoading(false);
  };

  const fetchTenant = async () => {
    try {
      const response = await axios.get(`${API}/tenant`, { withCredentials: true });
      setCompanyData({
        company_name: response.data.company_name || '',
        logo_url: response.data.logo_url || '',
        primary_color: response.data.primary_color || '#6B633C',
        default_currency: response.data.default_currency || 'ZAR',
        address: response.data.address || '',
        phone: response.data.phone || '',
        email: response.data.email || '',
      });
      setPricingData({
        volumetric_divisor: response.data.volumetric_divisor || 5000,
        default_rate_type: response.data.default_rate_type || 'per_kg',
        default_rate_value: response.data.default_rate_value || 0,
        fuel_surcharge_percentage: response.data.fuel_surcharge_percentage || 0,
      });
    } catch (error) {
      console.error('Failed to fetch tenant');
    }
  };

  const fetchPermissions = async () => {
    try {
      const response = await axios.get(`${API}/tenant/permissions`, { withCredentials: true });
      setPermissions(response.data);
    } catch (error) {
      console.error('Failed to fetch permissions');
    }
  };

  const fetchWarehouses = async () => {
    try {
      const response = await axios.get(`${API}/warehouses`, { withCredentials: true });
      setWarehouses(response.data);
    } catch (error) {
      console.error('Failed to fetch warehouses');
    }
  };

  const fetchCurrencies = async () => {
    try {
      const response = await axios.get(`${API}/tenant/currencies`, { withCredentials: true });
      setCurrencies(response.data);
    } catch (error) {
      console.error('Failed to fetch currencies');
    }
  };

  const fetchAuditLogs = async () => {
    setLoadingAuditLogs(true);
    try {
      const params = {};
      if (auditFilters.date_from) params.date_from = auditFilters.date_from;
      if (auditFilters.date_to) params.date_to = auditFilters.date_to;
      if (auditFilters.user_id !== 'all') params.user_id = auditFilters.user_id;
      if (auditFilters.module !== 'all') {
        // Map module to table_name
        const moduleMap = {
          'parcels': 'shipments',
          'invoices': 'invoices',
          'trips': 'trips'
        };
        params.table_name = moduleMap[auditFilters.module];
      }
      
      const response = await axios.get(`${API}/audit-logs`, { params, withCredentials: true });
      setAuditLogs(response.data);
    } catch (error) {
      toast.error('Failed to fetch audit logs');
    } finally {
      setLoadingAuditLogs(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`, { withCredentials: true });
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users');
    }
  };

  useEffect(() => {
    if (activeTab === 'audit') {
      fetchAuditLogs();
      if (users.length === 0) fetchUsers();
    } else if (activeTab === 'banking') {
      fetchBankingDetails();
    }
  }, [activeTab, auditFilters]);

  const fetchBankingDetails = async () => {
    try {
      const response = await axios.get(`${API}/settings/banking-details`, { withCredentials: true });
      setBankAccounts(response.data.accounts || []);
    } catch (error) {
      console.error('Failed to load banking details:', error);
      // Set default empty accounts on error
      setBankAccounts([
        { currency: 'ZAR', bank_name: '', account_name: '', account_number: '', branch_code: '', swift_code: '' },
        { currency: 'KES', bank_name: '', account_name: '', account_number: '', branch_code: '', swift_code: '' }
      ]);
    }
  };

  const saveBankingDetails = async () => {
    setSavingBanking(true);
    try {
      await axios.put(`${API}/settings/banking-details`, { accounts: bankAccounts }, { withCredentials: true });
      toast.success('Banking details saved');
    } catch (error) {
      toast.error('Failed to save banking details');
    } finally {
      setSavingBanking(false);
    }
  };

  const addBankAccount = () => {
    setBankAccounts([...bankAccounts, {
      currency: 'USD',
      bank_name: '',
      account_name: '',
      account_number: '',
      branch_code: '',
      swift_code: ''
    }]);
  };

  const updateBankAccount = (index, field, value) => {
    const updated = [...bankAccounts];
    updated[index][field] = value;
    setBankAccounts(updated);
  };

  const removeBankAccount = (index) => {
    setBankAccounts(bankAccounts.filter((_, i) => i !== index));
  };

  // Save handlers
  const handleSaveCompany = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/tenant`, companyData, { withCredentials: true });
      toast.success('Company profile updated');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePricing = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/tenant`, pricingData, { withCredentials: true });
      toast.success('Pricing settings updated');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePermissions = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/tenant/permissions`, permissions, { withCredentials: true });
      toast.success('Permissions updated');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const togglePermission = (role, pageId) => {
    if (role === 'owner') return;
    setPermissions(prev => {
      const rolePerms = prev[role] || [];
      if (rolePerms.includes(pageId)) {
        return { ...prev, [role]: rolePerms.filter(p => p !== pageId) };
      } else {
        return { ...prev, [role]: [...rolePerms, pageId] };
      }
    });
  };

  // Warehouse handlers
  const openWarehouseModal = (warehouse = null) => {
    if (warehouse) {
      setEditingWarehouse(warehouse);
      setWarehouseForm({
        name: warehouse.name || '',
        location: warehouse.location || '',
        contact_person: warehouse.contact_person || '',
        phone: warehouse.phone || '',
        status: warehouse.status || 'active'
      });
    } else {
      setEditingWarehouse(null);
      setWarehouseForm({ name: '', location: '', contact_person: '', phone: '', status: 'active' });
    }
    setWarehouseModalOpen(true);
  };

  const handleSaveWarehouse = async () => {
    if (!warehouseForm.name.trim()) {
      toast.error('Warehouse name is required');
      return;
    }
    setSaving(true);
    try {
      if (editingWarehouse) {
        await axios.put(`${API}/warehouses/${editingWarehouse.id}`, warehouseForm, { withCredentials: true });
        toast.success('Warehouse updated');
      } else {
        await axios.post(`${API}/warehouses`, warehouseForm, { withCredentials: true });
        toast.success('Warehouse created');
      }
      setWarehouseModalOpen(false);
      fetchWarehouses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save warehouse');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteWarehouse = async (warehouse) => {
    if (!confirm(`Delete warehouse "${warehouse.name}"?`)) return;
    try {
      await axios.delete(`${API}/warehouses/${warehouse.id}`, { withCredentials: true });
      toast.success('Warehouse deleted');
      fetchWarehouses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete warehouse');
    }
  };

  const handleCreateDefaultWarehouses = async () => {
    setSaving(true);
    try {
      const response = await axios.post(`${API}/warehouses/create-defaults`, {}, { withCredentials: true });
      toast.success(response.data.message);
      fetchWarehouses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create default warehouses');
    } finally {
      setSaving(false);
    }
  };

  // Currency handlers
  const openCurrencyModal = () => {
    setCurrencyForm({ code: '', name: '', rate_to_base: '' });
    setCurrencyModalOpen(true);
  };

  const handleAddCurrency = async () => {
    if (!currencyForm.code || !currencyForm.name || !currencyForm.rate_to_base) {
      toast.error('All fields are required');
      return;
    }
    setSaving(true);
    try {
      await axios.post(`${API}/tenant/currencies/add`, currencyForm, { withCredentials: true });
      toast.success(`Currency ${currencyForm.code} added`);
      setCurrencyModalOpen(false);
      fetchCurrencies();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add currency');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCurrency = async (code) => {
    if (!confirm(`Delete currency ${code}?`)) return;
    try {
      await axios.delete(`${API}/tenant/currencies/${code}`, { withCredentials: true });
      toast.success(`Currency ${code} deleted`);
      fetchCurrencies();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete currency');
    }
  };

  // Debounced exchange rate update (1 second delay)
  const debouncedUpdateExchangeRate = useMemo(
    () => debounce(async (code, newRate) => {
      const updatedRates = currencies.exchange_rates.map(r => 
        r.code === code ? { ...r, rate_to_base: parseFloat(newRate) } : r
      );
      try {
        await axios.put(`${API}/tenant/currencies`, { exchange_rates: updatedRates }, { withCredentials: true });
        setCurrencies(prev => ({ ...prev, exchange_rates: updatedRates }));
        toast.success(`Exchange rate for ${code} updated`);
      } catch (error) {
        toast.error('Failed to update exchange rate');
      }
    }, 1000),
    [currencies.exchange_rates]
  );

  const handleUpdateExchangeRate = (code, newRate) => {
    // Update UI immediately
    const updatedRates = currencies.exchange_rates.map(r => 
      r.code === code ? { ...r, rate_to_base: parseFloat(newRate) } : r
    );
    setCurrencies(prev => ({ ...prev, exchange_rates: updatedRates }));
    // Debounced API call
    debouncedUpdateExchangeRate(code, newRate);
  };

  // Data Management handlers
  const handleDataReset = async () => {
    setResetting(true);
    try {
      const response = await axios.post(`${API}/data/reset`, {}, { withCredentials: true });
      toast.success(response.data.summary);
      setResetDialogOpen(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset data');
    } finally {
      setResetting(false);
    }
  };

  const handleImportCSV = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Parse CSV for preview first
    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target.result;
      const lines = text.split('\n').filter(line => line.trim());
      
      if (lines.length === 0) {
        toast.error('Empty CSV file');
        return;
      }
      
      // Detect headers
      const firstLine = lines[0].toLowerCase();
      const hasHeaders = firstLine.includes('sent by') || firstLine.includes('description');
      
      const dataLines = hasHeaders ? lines.slice(1) : lines;
      const parcels = dataLines.map(line => {
        const parts = line.split(',').map(p => p.trim().replace(/^"|"$/g, ''));
        return {
          sent_by: parts[0] || '',
          primary_recipient: parts[1] || '',
          secondary_recipient: parts[2] || '',
          description: parts[3] || '',
          length: parseFloat(parts[4]) || 0,
          width: parseFloat(parts[5]) || 0,
          height: parseFloat(parts[6]) || 0,
          weight: parseFloat(parts[7]) || 0,
          qty: parseInt(parts[8]) || 1
        };
      }).filter(p => p.sent_by && p.weight > 0);
      
      // Calculate total parcels (accounting for QTY > 1)
      const totalParcels = parcels.reduce((sum, p) => sum + p.qty, 0);
      
      // Get unique client names to check for matches
      const clientNames = [...new Set(parcels.map(p => p.sent_by))];
      
      // Fetch existing clients to check matches
      try {
        const clientsRes = await axios.get(`${API}/clients`, { withCredentials: true });
        const existingClients = clientsRes.data || [];
        const existingClientNames = existingClients.map(c => c.name.toLowerCase());
        
        const clientMatches = clientNames.map(name => ({
          name,
          found: existingClients.find(c => c.name.toLowerCase() === name.toLowerCase()),
          isNew: !existingClientNames.includes(name.toLowerCase())
        }));
        
        setParcelImportPreview({
          file,
          parcels,
          hasHeaders,
          totalRows: parcels.length,
          totalParcels,
          clientMatches,
          newClients: clientMatches.filter(c => c.isNew).length
        });
        setParcelImportModalOpen(true);
      } catch (error) {
        toast.error('Failed to check client matches');
      }
    };
    reader.readAsText(file);
  };

  // Confirm parcel import
  const handleConfirmParcelImport = async () => {
    if (!parcelImportPreview?.file) return;
    
    setParcelImporting(true);
    const formData = new FormData();
    formData.append('file', parcelImportPreview.file);
    
    // Build URL with warehouse_id if selected
    let url = `${API}/import/parcels`;
    if (importWarehouseId) {
      url += `?warehouse_id=${importWarehouseId}`;
    }
    
    try {
      const response = await axios.post(url, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(response.data.summary, { duration: 10000 });
      setParcelImportModalOpen(false);
      setImportModalOpen(false);
      setParcelImportPreview(null);
      setImportWarehouseId('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import parcels');
    } finally {
      setParcelImporting(false);
      if (parcelFileInputRef.current) parcelFileInputRef.current.value = '';
    }
  };

  // Client CSV Import handler
  const handleClientCSVSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Parse CSV for preview
    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target.result;
      const lines = text.split('\n').filter(line => line.trim());
      
      if (lines.length === 0) {
        toast.error('Empty CSV file');
        return;
      }
      
      // Detect headers
      const firstLine = lines[0].toLowerCase();
      const hasHeaders = firstLine.includes('client name') || firstLine.includes('name');
      
      const dataLines = hasHeaders ? lines.slice(1) : lines;
      const clients = dataLines.map(line => {
        const parts = line.split(',').map(p => p.trim().replace(/^"|"$/g, ''));
        return {
          name: parts[0] || '',
          phone: parts[1] || '',
          email: parts[2] || '',
          vat_number: parts[3] || '',
          physical_address: parts[4] || '',
          billing_address: parts[5] || parts[4] || '',
          rate: parts[6] || ''
        };
      }).filter(c => c.name);
      
      setClientImportData({
        file,
        clients,
        hasHeaders,
        total: clients.length
      });
      setClientImportModalOpen(true);
    };
    reader.readAsText(file);
  };

  // Confirm client import
  const handleConfirmClientImport = async () => {
    if (!clientImportData?.file) return;
    
    setClientImporting(true);
    const formData = new FormData();
    formData.append('file', clientImportData.file);
    
    try {
      const response = await axios.post(`${API}/import/clients`, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(response.data.summary, { duration: 10000 });
      setClientImportModalOpen(false);
      setClientImportData(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import clients');
    } finally {
      setClientImporting(false);
      if (clientFileInputRef.current) clientFileInputRef.current.value = '';
    }
  };

  // Export clients to CSV
  const handleExportClients = async () => {
    try {
      const response = await axios.get(`${API}/export/clients`, {
        withCredentials: true,
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const date = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `Servex_Clients_Export_${date}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Clients exported successfully');
    } catch (error) {
      toast.error('Failed to export clients');
    }
  };

  // Download template CSVs
  const downloadClientTemplate = () => {
    const headers = 'Client Name,Phone,Email,VAT No,Physical Address,Billing Address,Rate';
    const example1 = 'Acme Corp,+254712345678,acme@example.com,VAT12345,123 Main St Johannesburg,Same as above,36.00';
    const example2 = 'Beta Ltd,+254798765432,beta@example.com,,456 Oak Ave Nairobi,,42.50';
    const content = [headers, example1, example2].join('\n');
    
    const blob = new Blob([content], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'Servex_Client_Import_Template.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
    toast.success('Template downloaded');
  };

  const downloadParcelTemplate = () => {
    const headers = 'Sent By,Primary Recipient,Secondary Recipient,Description,L,W,H,KG,QTY';
    const example1 = 'Acme Corp,John Doe,,Electronics - TV,120,80,20,25.5,1';
    const example2 = 'Acme Corp,Jane Smith,Mike Wilson,Wine bottles,40,30,50,12.0,3';
    const example3 = 'Beta Ltd,Beta Ltd,,Office furniture,200,100,120,85.0,1';
    const content = [headers, example1, example2, example3].join('\n');
    
    const blob = new Blob([content], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'Servex_Parcel_Import_Template.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
    toast.success('Template downloaded');
  };

  const isOwner = user?.role === 'owner';

  if (!isOwner) {
    return (
      <>
        <div className="flex items-center justify-center h-[60vh]">
          <div className="text-center">
            <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">Access Restricted</h2>
            <p className="text-muted-foreground">Only owners can access settings</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="space-y-6" data-testid="settings-page">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground mt-1">Manage your company settings and preferences</p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="bg-white border flex-wrap h-auto gap-1 p-1">
            <TabsTrigger value="company" data-testid="tab-company">
              <Building2 className="h-4 w-4 mr-2" />Company
            </TabsTrigger>
            <TabsTrigger value="pricing" data-testid="tab-pricing">
              <Calculator className="h-4 w-4 mr-2" />Pricing
            </TabsTrigger>
            <TabsTrigger value="warehouses" data-testid="tab-warehouses">
              <Warehouse className="h-4 w-4 mr-2" />Warehouses
            </TabsTrigger>
            <TabsTrigger value="currencies" data-testid="tab-currencies">
              <DollarSign className="h-4 w-4 mr-2" />Currencies
            </TabsTrigger>
            <TabsTrigger value="permissions" data-testid="tab-permissions">
              <Shield className="h-4 w-4 mr-2" />Permissions
            </TabsTrigger>
            <TabsTrigger value="notifications" data-testid="tab-notifications">
              <Bell className="h-4 w-4 mr-2" />Notifications
            </TabsTrigger>
            <TabsTrigger value="data" data-testid="tab-data">
              <Database className="h-4 w-4 mr-2" />Data
            </TabsTrigger>
            <TabsTrigger value="audit" data-testid="tab-audit">
              <FileText className="h-4 w-4 mr-2" />Audit Log
            </TabsTrigger>
            <TabsTrigger value="banking" data-testid="tab-banking">
              <DollarSign className="h-4 w-4 mr-2" />Banking
            </TabsTrigger>
            <TabsTrigger value="whatsapp" data-testid="tab-whatsapp">
              <MessageSquare className="h-4 w-4 mr-2" />WhatsApp
            </TabsTrigger>
            <TabsTrigger value="printnode" data-testid="tab-printnode">
              <Printer className="h-4 w-4 mr-2" />PrintNode
            </TabsTrigger>
          </TabsList>

          {/* Company Profile */}
          <TabsContent value="company" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Company Profile</CardTitle>
                <CardDescription>Your company information displayed on invoices and documents</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Company Name</Label>
                    <Input value={companyData.company_name} onChange={(e) => setCompanyData({ ...companyData, company_name: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Default Currency</Label>
                    <Input value={companyData.default_currency} onChange={(e) => setCompanyData({ ...companyData, default_currency: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Phone</Label>
                    <Input value={companyData.phone} onChange={(e) => setCompanyData({ ...companyData, phone: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input type="email" value={companyData.email} onChange={(e) => setCompanyData({ ...companyData, email: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Address</Label>
                  <Input value={companyData.address} onChange={(e) => setCompanyData({ ...companyData, address: e.target.value })} placeholder="123 Main St, City, Country" />
                </div>
                <div className="space-y-2">
                  <Label>Logo URL</Label>
                  <Input value={companyData.logo_url} onChange={(e) => setCompanyData({ ...companyData, logo_url: e.target.value })} placeholder="https://..." />
                </div>
                <div className="space-y-2">
                  <Label>Primary Color</Label>
                  <div className="flex items-center gap-2">
                    <Input type="color" value={companyData.primary_color} onChange={(e) => setCompanyData({ ...companyData, primary_color: e.target.value })} className="w-16 h-10 p-1" />
                    <Input value={companyData.primary_color} onChange={(e) => setCompanyData({ ...companyData, primary_color: e.target.value })} className="flex-1" />
                  </div>
                </div>
                <div className="pt-4">
                  <Button onClick={handleSaveCompany} disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Pricing */}
          <TabsContent value="pricing" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Pricing & Calculations</CardTitle>
                <CardDescription>Configure how rates and weights are calculated</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Volumetric Divisor</Label>
                    <Input type="number" value={pricingData.volumetric_divisor} onChange={(e) => setPricingData({ ...pricingData, volumetric_divisor: parseInt(e.target.value) || 5000 })} />
                    <p className="text-xs text-muted-foreground">Standard is 5000 for air freight</p>
                  </div>
                  <div className="space-y-2">
                    <Label>Default Rate Type</Label>
                    <select value={pricingData.default_rate_type} onChange={(e) => setPricingData({ ...pricingData, default_rate_type: e.target.value })} className="w-full h-10 px-3 border rounded-md">
                      <option value="per_kg">Per KG</option>
                      <option value="per_cbm">Per CBM</option>
                      <option value="flat_rate">Flat Rate</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label>Default Rate Value</Label>
                    <Input type="number" step="0.01" value={pricingData.default_rate_value} onChange={(e) => setPricingData({ ...pricingData, default_rate_value: parseFloat(e.target.value) || 0 })} />
                  </div>
                  <div className="space-y-2">
                    <Label>Fuel Surcharge (%)</Label>
                    <Input type="number" step="0.1" value={pricingData.fuel_surcharge_percentage} onChange={(e) => setPricingData({ ...pricingData, fuel_surcharge_percentage: parseFloat(e.target.value) || 0 })} />
                  </div>
                </div>
                <div className="pt-4">
                  <Button onClick={handleSavePricing} disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Warehouses */}
          <TabsContent value="warehouses" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Warehouse Management</CardTitle>
                    <CardDescription>Manage your warehouse locations</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={handleCreateDefaultWarehouses} disabled={saving}>
                      <RefreshCw className="h-4 w-4 mr-2" />Create Defaults
                    </Button>
                    <Button onClick={() => openWarehouseModal()}>
                      <Plus className="h-4 w-4 mr-2" />Add Warehouse
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Location</TableHead>
                      <TableHead>Contact Person</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {warehouses.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                          No warehouses configured. Click "Create Defaults" or "Add Warehouse" to get started.
                        </TableCell>
                      </TableRow>
                    ) : warehouses.map(warehouse => (
                      <TableRow key={warehouse.id}>
                        <TableCell className="font-medium">{warehouse.name}</TableCell>
                        <TableCell>{warehouse.location || '-'}</TableCell>
                        <TableCell>{warehouse.contact_person || '-'}</TableCell>
                        <TableCell>{warehouse.phone || '-'}</TableCell>
                        <TableCell>
                          <Badge variant={warehouse.status === 'active' ? 'default' : 'secondary'}>
                            {warehouse.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="icon" onClick={() => openWarehouseModal(warehouse)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteWarehouse(warehouse)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Currencies */}
          <TabsContent value="currencies" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Currency Management</CardTitle>
                    <CardDescription>Configure exchange rates (Base: {currencies.base_currency})</CardDescription>
                  </div>
                  <Button onClick={openCurrencyModal}>
                    <Plus className="h-4 w-4 mr-2" />Add Currency
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Code</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Rate to {currencies.base_currency}</TableHead>
                      <TableHead className="w-[100px]">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currencies.exchange_rates.map(rate => (
                      <TableRow key={rate.code}>
                        <TableCell className="font-medium">{rate.code}</TableCell>
                        <TableCell>{rate.name}</TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            step="0.01"
                            value={rate.rate_to_base}
                            onChange={(e) => handleUpdateExchangeRate(rate.code, e.target.value)}
                            className="w-32"
                            disabled={rate.code === currencies.base_currency}
                          />
                        </TableCell>
                        <TableCell>
                          {rate.code !== currencies.base_currency && (
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteCurrency(rate.code)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <p className="text-sm text-muted-foreground mt-4">
                  Formula: Amount in {currencies.base_currency} = Amount × Rate to {currencies.base_currency}
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Permissions */}
          <TabsContent value="permissions" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  Role-Based Page Visibility
                </CardTitle>
                <CardDescription>Control which pages each role can access.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-muted/50">
                        <th className="text-left p-3 font-medium">Page</th>
                        {allRoles.map(role => (
                          <th key={role.id} className="p-3 text-center font-medium">
                            {role.label}
                            {role.locked && <span className="block text-xs text-muted-foreground font-normal">(Locked)</span>}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {allPages.map(page => (
                        <tr key={page.id} className="border-b">
                          <td className="p-3 font-medium">{page.label}</td>
                          {allRoles.map(role => (
                            <td key={role.id} className="p-3 text-center">
                              <Checkbox
                                checked={(permissions[role.id] || []).includes(page.id)}
                                disabled={role.id === 'owner'}
                                onCheckedChange={() => togglePermission(role.id, page.id)}
                              />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pt-4 flex justify-between items-center">
                  <Button variant="outline" onClick={() => setPermissions(defaultPermissions)}>
                    <RefreshCw className="h-4 w-4 mr-2" />Reset to Defaults
                  </Button>
                  <Button onClick={handleSavePermissions} disabled={saving}>
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    Save Permissions
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notifications */}
          <TabsContent value="notifications" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>Configure how you receive notifications</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-sm text-muted-foreground">Receive important updates via email</p>
                  </div>
                  <Switch checked={notificationData.email_notifications} onCheckedChange={(checked) => setNotificationData({ ...notificationData, email_notifications: checked })} />
                </div>
                <Separator />
                <div className="space-y-4 pl-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm">Invoice sent confirmation</p>
                    <Switch checked={notificationData.invoice_sent_email} onCheckedChange={(checked) => setNotificationData({ ...notificationData, invoice_sent_email: checked })} disabled={!notificationData.email_notifications} />
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="text-sm">Trip completed notification</p>
                    <Switch checked={notificationData.trip_completed_email} onCheckedChange={(checked) => setNotificationData({ ...notificationData, trip_completed_email: checked })} disabled={!notificationData.email_notifications} />
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="text-sm">Overdue invoice reminders</p>
                    <Switch checked={notificationData.overdue_invoice_email} onCheckedChange={(checked) => setNotificationData({ ...notificationData, overdue_invoice_email: checked })} disabled={!notificationData.email_notifications} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Data */}
          <TabsContent value="data" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Data Management</CardTitle>
                <CardDescription>Import, export, and manage your data</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Client Import/Export Section */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <Users className="h-4 w-4" /> Client Data
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card className="border-dashed">
                      <CardContent className="p-6 text-center">
                        <Upload className="h-8 w-8 mx-auto mb-3 text-blue-600" />
                        <h3 className="font-medium mb-2">Import Clients</h3>
                        <p className="text-sm text-muted-foreground mb-2">
                          CSV: Name, Phone, Email, VAT, Address, Rate
                        </p>
                        <Button 
                          variant="link" 
                          size="sm" 
                          className="h-auto p-0 mb-3 text-[#6B633C]"
                          onClick={downloadClientTemplate}
                        >
                          <Download className="h-3 w-3 mr-1" /> Download Template
                        </Button>
                        <input 
                          ref={clientFileInputRef}
                          type="file" 
                          accept=".csv" 
                          onChange={handleClientCSVSelect} 
                          className="hidden" 
                          id="client-csv-input"
                        />
                        <Button variant="outline" className="w-full" onClick={() => clientFileInputRef.current?.click()}>
                          <Upload className="h-4 w-4 mr-2" />
                          Import Clients CSV
                        </Button>
                      </CardContent>
                    </Card>
                    <Card className="border-dashed">
                      <CardContent className="p-6 text-center">
                        <Download className="h-8 w-8 mx-auto mb-3 text-green-600" />
                        <h3 className="font-medium mb-2">Export Clients</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                          Download all clients as CSV
                        </p>
                        <Button variant="outline" className="w-full" onClick={handleExportClients}>
                          <Download className="h-4 w-4 mr-2" />
                          Export Clients CSV
                        </Button>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <Separator />

                {/* Parcel Import Section */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <FileSpreadsheet className="h-4 w-4" /> Parcel Data
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card className="border-dashed">
                      <CardContent className="p-6 text-center">
                        <FileSpreadsheet className="h-8 w-8 mx-auto mb-3 text-green-600" />
                        <h3 className="font-medium mb-2">Import Parcels from CSV</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                          Import parcels with client auto-matching
                        </p>
                        <Button variant="outline" className="w-full" onClick={() => setImportModalOpen(true)}>
                          <Upload className="h-4 w-4 mr-2" />
                          Import Parcels CSV
                        </Button>
                      </CardContent>
                    </Card>
                    <Card className="border-dashed">
                      <CardContent className="p-6 text-center">
                        <Download className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
                        <h3 className="font-medium mb-2">Export All Data</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                          Download all data as CSV (coming soon)
                        </p>
                        <Button variant="outline" className="w-full" disabled>
                          Export All Data
                        </Button>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <Separator />

                {/* Danger Zone */}
                <div>
                  <h3 className="font-medium mb-3 text-red-600 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" /> Danger Zone
                  </h3>
                  <Card className="border-dashed border-red-200">
                    <CardContent className="p-6 text-center">
                      <AlertTriangle className="h-8 w-8 mx-auto mb-3 text-red-500" />
                      <h3 className="font-medium mb-2 text-red-700">Reset All Data</h3>
                      <p className="text-sm text-muted-foreground mb-4">
                        Delete all clients, trips, parcels, invoices
                      </p>
                      <Button variant="destructive" className="w-full" onClick={() => setResetDialogOpen(true)}>
                        <Trash2 className="h-4 w-4 mr-2" />Reset Data
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Audit Log Tab */}
          <TabsContent value="audit" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Audit Log</CardTitle>
                <CardDescription>View all system changes and user actions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Filters */}
                <div className="flex flex-wrap gap-3">
                  <div className="flex flex-col gap-1">
                    <Label className="text-xs">From Date</Label>
                    <Input
                      type="date"
                      value={auditFilters.date_from}
                      onChange={(e) => setAuditFilters(prev => ({ ...prev, date_from: e.target.value }))}
                      className="w-[150px]"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <Label className="text-xs">To Date</Label>
                    <Input
                      type="date"
                      value={auditFilters.date_to}
                      onChange={(e) => setAuditFilters(prev => ({ ...prev, date_to: e.target.value }))}
                      className="w-[150px]"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <Label className="text-xs">User</Label>
                    <select
                      value={auditFilters.user_id}
                      onChange={(e) => setAuditFilters(prev => ({ ...prev, user_id: e.target.value }))}
                      className="h-10 w-[180px] rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="all">All Users</option>
                      {users.map(u => (
                        <option key={u.id} value={u.id}>{u.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex flex-col gap-1">
                    <Label className="text-xs">Module</Label>
                    <select
                      value={auditFilters.module}
                      onChange={(e) => setAuditFilters(prev => ({ ...prev, module: e.target.value }))}
                      className="h-10 w-[150px] rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="all">All Modules</option>
                      <option value="parcels">Parcels</option>
                      <option value="invoices">Invoices</option>
                      <option value="trips">Trips</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <Button onClick={fetchAuditLogs} disabled={loadingAuditLogs} variant="outline">
                      {loadingAuditLogs ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                      Refresh
                    </Button>
                  </div>
                </div>

                {/* Audit Log Table */}
                <div className="border rounded-lg">
                  {loadingAuditLogs ? (
                    <div className="p-8 text-center">
                      <Loader2 className="h-8 w-8 animate-spin mx-auto text-gray-400" />
                    </div>
                  ) : auditLogs.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                      No audit logs found for the selected filters
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[180px]">Timestamp</TableHead>
                          <TableHead>User</TableHead>
                          <TableHead>Action</TableHead>
                          <TableHead>Module</TableHead>
                          <TableHead>Record ID</TableHead>
                          <TableHead className="min-w-[300px]">Changes</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {auditLogs.map((log, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="text-sm font-mono">
                              {new Date(log.created_at).toLocaleString()}
                            </TableCell>
                            <TableCell className="text-sm">
                              {log.user_name || 'System'}
                            </TableCell>
                            <TableCell>
                              <Badge variant={
                                log.action === 'create' ? 'default' :
                                log.action === 'delete' ? 'destructive' :
                                log.action === 'status_change' ? 'secondary' : 'outline'
                              }>
                                {log.action}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm capitalize">
                              {log.table_name}
                            </TableCell>
                            <TableCell className="text-sm font-mono">
                              {log.record_id?.slice(0, 8)}...
                            </TableCell>
                            <TableCell className="text-xs">
                              {log.action === 'status_change' && log.old_value && log.new_value ? (
                                <span>
                                  <span className="text-red-600">{log.old_value.status || 'N/A'}</span>
                                  {' → '}
                                  <span className="text-green-600">{log.new_value.status || 'N/A'}</span>
                                </span>
                              ) : log.action === 'update' && log.old_value && log.new_value ? (
                                <div className="max-w-md">
                                  {Object.keys(log.new_value || {}).slice(0, 3).map(key => (
                                    <div key={key} className="text-xs">
                                      <span className="font-medium">{key}:</span>{' '}
                                      <span className="text-red-600">{JSON.stringify(log.old_value?.[key])?.slice(0, 30)}</span>
                                      {' → '}
                                      <span className="text-green-600">{JSON.stringify(log.new_value?.[key])?.slice(0, 30)}</span>
                                    </div>
                                  ))}
                                </div>
                              ) : log.action === 'create' ? (
                                <span className="text-green-600">Record created</span>
                              ) : log.action === 'delete' ? (
                                <span className="text-red-600">Record deleted</span>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Banking Details Tab */}
          <TabsContent value="banking" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Banking Details</CardTitle>
                <CardDescription>Manage bank accounts for different currencies. These will appear on quotes and invoices.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {bankAccounts.map((account, index) => (
                  <Card key={index} className="p-4 border-2">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-2">
                        <Badge>{account.currency}</Badge>
                        <span className="text-sm text-gray-500">
                          {account.currency === 'ZAR' && '(Default for non-KES)'}
                          {account.currency === 'KES' && '(Default for KES)'}
                        </span>
                      </div>
                      {!['ZAR', 'KES'].includes(account.currency) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeBankAccount(index)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Currency</Label>
                        <select
                          value={account.currency}
                          onChange={(e) => updateBankAccount(index, 'currency', e.target.value)}
                          className="w-full h-10 rounded-md border border-input bg-background px-3 py-2"
                          disabled={['ZAR', 'KES'].includes(account.currency)}
                        >
                          <option value="ZAR">ZAR (South African Rand)</option>
                          <option value="KES">KES (Kenyan Shilling)</option>
                          <option value="USD">USD (US Dollar)</option>
                          <option value="EUR">EUR (Euro)</option>
                          <option value="GBP">GBP (British Pound)</option>
                        </select>
                      </div>
                      <div>
                        <Label>Bank Name</Label>
                        <Input
                          value={account.bank_name}
                          onChange={(e) => updateBankAccount(index, 'bank_name', e.target.value)}
                          placeholder="e.g., FNB, Equity Bank"
                        />
                      </div>
                      <div>
                        <Label>Account Name</Label>
                        <Input
                          value={account.account_name}
                          onChange={(e) => updateBankAccount(index, 'account_name', e.target.value)}
                          placeholder="Account holder name"
                        />
                      </div>
                      <div>
                        <Label>Account Number</Label>
                        <Input
                          value={account.account_number}
                          onChange={(e) => updateBankAccount(index, 'account_number', e.target.value)}
                          placeholder="Account number"
                        />
                      </div>
                      <div>
                        <Label>Branch Code (Optional)</Label>
                        <Input
                          value={account.branch_code || ''}
                          onChange={(e) => updateBankAccount(index, 'branch_code', e.target.value)}
                          placeholder="Branch code"
                        />
                      </div>
                      <div>
                        <Label>SWIFT Code (Optional)</Label>
                        <Input
                          value={account.swift_code || ''}
                          onChange={(e) => updateBankAccount(index, 'swift_code', e.target.value)}
                          placeholder="SWIFT/BIC code"
                        />
                      </div>
                    </div>
                  </Card>
                ))}

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={addBankAccount}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Account for Other Currency
                  </Button>
                  <Button
                    onClick={saveBankingDetails}
                    disabled={savingBanking}
                    className="bg-[#6B633C] hover:bg-[#5a5332]"
                  >
                    {savingBanking ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    Save Banking Details
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* WhatsApp Templates - SESSION H */}
          <TabsContent value="whatsapp" className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold">WhatsApp Message Templates</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Customize WhatsApp messages sent to clients for invoices, statements, and collections
              </p>
            </div>
            <WhatsAppTemplateEditor />
          </TabsContent>

          {/* PrintNode Settings */}
          <TabsContent value="printnode" className="space-y-4">
            <PrintNodeSettings />
          </TabsContent>
        </Tabs>

        {/* CSV Import Modal */}
        <Dialog open={importModalOpen} onOpenChange={setImportModalOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Import Parcels from CSV</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {/* Format Documentation */}
              <div className="bg-gray-50 border rounded p-3 text-sm">
                <p className="font-medium mb-2">CSV Format (with or without headers):</p>
                <div className="space-y-1 text-xs text-gray-600">
                  <p>Column 1: <span className="font-medium">Sent By</span> (client name)</p>
                  <p>Column 2: <span className="font-medium">Primary Recipient</span></p>
                  <p>Column 3: <span className="font-medium">Secondary Recipient</span></p>
                  <p>Column 4: <span className="font-medium">Description</span> (required)</p>
                  <p>Column 5-7: <span className="font-medium">L, W, H</span> (dimensions in cm)</p>
                  <p>Column 8: <span className="font-medium">KG</span> (weight, required)</p>
                  <p>Column 9: <span className="font-medium">QTY</span> (default: 1)</p>
                </div>
                <div className="mt-2 pt-2 border-t">
                  <p className="text-xs text-amber-600">
                    <strong>Note:</strong> QTY &gt; 1 creates multiple parcels (e.g., QTY=5 creates 5 parcels numbered 1 of 5, 2 of 5...)
                  </p>
                </div>
                <Button 
                  variant="link" 
                  size="sm" 
                  className="h-auto p-0 mt-2 text-[#6B633C]"
                  onClick={downloadParcelTemplate}
                >
                  <Download className="h-3 w-3 mr-1" /> Download Template CSV
                </Button>
              </div>
              
              <div className="space-y-2">
                <Label>Target Warehouse (optional)</Label>
                <select 
                  value={importWarehouseId} 
                  onChange={(e) => setImportWarehouseId(e.target.value)}
                  className="w-full h-10 px-3 border rounded-md"
                >
                  <option value="">All warehouses (alternate)</option>
                  {warehouses.map(wh => (
                    <option key={wh.id} value={wh.id}>{wh.name}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label>CSV File</Label>
                <input ref={parcelFileInputRef} type="file" accept=".csv" onChange={handleImportCSV} className="w-full" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setImportModalOpen(false)}>Cancel</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Parcel Import Preview Modal */}
        <Dialog open={parcelImportModalOpen} onOpenChange={setParcelImportModalOpen}>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle>Import Parcels Preview</DialogTitle>
            </DialogHeader>
            {parcelImportPreview && (
              <div className="space-y-4 py-4">
                <p className="text-sm text-muted-foreground">
                  About to import <span className="font-semibold text-foreground">{parcelImportPreview.totalParcels}</span> parcels 
                  from <span className="font-semibold text-foreground">{parcelImportPreview.totalRows}</span> rows:
                </p>
                
                {/* Client Matching Section */}
                <div className="bg-blue-50 border border-blue-200 rounded p-3">
                  <h4 className="font-medium text-blue-800 mb-2">Client Matching:</h4>
                  <div className="max-h-[150px] overflow-auto space-y-1">
                    {parcelImportPreview.clientMatches.map((match, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <span className="text-gray-600">"{match.name}"</span>
                        <span className="text-gray-400">→</span>
                        {match.found ? (
                          <span className="text-green-600">Found: {match.found.name}</span>
                        ) : (
                          <span className="text-amber-600 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" /> NOT FOUND - will create new client
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* Parcel Preview Table */}
                <div className="max-h-[200px] overflow-auto border rounded">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50">
                        <TableHead className="w-[40px]">#</TableHead>
                        <TableHead>Sent By</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="text-right">L×W×H</TableHead>
                        <TableHead className="text-right">KG</TableHead>
                        <TableHead className="text-right">QTY</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {parcelImportPreview.parcels.slice(0, 10).map((parcel, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="text-muted-foreground">{idx + 1}</TableCell>
                          <TableCell className="font-medium">{parcel.sent_by}</TableCell>
                          <TableCell className="max-w-[200px] truncate">{parcel.description}</TableCell>
                          <TableCell className="text-right text-sm font-mono">{parcel.length}×{parcel.width}×{parcel.height}</TableCell>
                          <TableCell className="text-right font-mono">{parcel.weight.toFixed(2)}</TableCell>
                          <TableCell className="text-right font-mono">{parcel.qty}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                
                {parcelImportPreview.totalRows > 10 && (
                  <p className="text-sm text-muted-foreground text-center">
                    ... and {parcelImportPreview.totalRows - 10} more rows
                  </p>
                )}
                
                {/* Summary Info */}
                <div className="bg-green-50 p-3 rounded text-sm text-green-700">
                  <p><strong>Import Summary:</strong></p>
                  <ul className="list-disc ml-5 mt-1">
                    <li>Total parcels to create: {parcelImportPreview.totalParcels}</li>
                    {parcelImportPreview.newClients > 0 && (
                      <li className="text-amber-600">New clients to create: {parcelImportPreview.newClients}</li>
                    )}
                    <li>Status: warehouse (not assigned to any trip)</li>
                    <li>Warehouse: {importWarehouseId ? warehouses.find(w => w.id === importWarehouseId)?.name : 'Alternating between all'}</li>
                  </ul>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setParcelImportModalOpen(false)}>Cancel</Button>
              <Button onClick={handleConfirmParcelImport} disabled={parcelImporting} className="bg-[#6B633C] hover:bg-[#5a5332]">
                {parcelImporting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                {parcelImporting ? 'Importing...' : `Import ${parcelImportPreview?.totalParcels || 0} Parcels`}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Warehouse Modal */}
        <Dialog open={warehouseModalOpen} onOpenChange={setWarehouseModalOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingWarehouse ? 'Edit Warehouse' : 'Add Warehouse'}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Name *</Label>
                <Input value={warehouseForm.name} onChange={(e) => setWarehouseForm({ ...warehouseForm, name: e.target.value })} placeholder="Warehouse name" />
              </div>
              <div className="space-y-2">
                <Label>Location</Label>
                <Input value={warehouseForm.location} onChange={(e) => setWarehouseForm({ ...warehouseForm, location: e.target.value })} placeholder="City, Country" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Contact Person</Label>
                  <Input value={warehouseForm.contact_person} onChange={(e) => setWarehouseForm({ ...warehouseForm, contact_person: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input value={warehouseForm.phone} onChange={(e) => setWarehouseForm({ ...warehouseForm, phone: e.target.value })} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <select value={warehouseForm.status} onChange={(e) => setWarehouseForm({ ...warehouseForm, status: e.target.value })} className="w-full h-10 px-3 border rounded-md">
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setWarehouseModalOpen(false)}>Cancel</Button>
              <Button onClick={handleSaveWarehouse} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                {editingWarehouse ? 'Update' : 'Create'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Currency Modal */}
        <Dialog open={currencyModalOpen} onOpenChange={setCurrencyModalOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Currency</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Currency Code *</Label>
                <Input value={currencyForm.code} onChange={(e) => setCurrencyForm({ ...currencyForm, code: e.target.value.toUpperCase() })} placeholder="USD, EUR, KES..." maxLength={3} />
              </div>
              <div className="space-y-2">
                <Label>Currency Name *</Label>
                <Input value={currencyForm.name} onChange={(e) => setCurrencyForm({ ...currencyForm, name: e.target.value })} placeholder="US Dollar, Euro, Kenyan Shilling..." />
              </div>
              <div className="space-y-2">
                <Label>Rate to {currencies.base_currency} *</Label>
                <Input type="number" step="0.01" value={currencyForm.rate_to_base} onChange={(e) => setCurrencyForm({ ...currencyForm, rate_to_base: e.target.value })} placeholder="18.5" />
                <p className="text-xs text-muted-foreground">1 {currencyForm.code || 'XXX'} = X {currencies.base_currency}</p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCurrencyModalOpen(false)}>Cancel</Button>
              <Button onClick={handleAddCurrency} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
                Add Currency
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Reset Confirmation Dialog */}
        <AlertDialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="h-5 w-5" />
                Reset All Data?
              </AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete ALL:
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Clients and their rates</li>
                  <li>Parcels and shipments</li>
                  <li>Trips and routes</li>
                  <li>Invoices and payments</li>
                  <li>Expenses and notifications</li>
                </ul>
                <p className="mt-4 font-semibold">Users, warehouses, and settings will be preserved.</p>
                <p className="mt-2 text-red-600">This action cannot be undone!</p>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDataReset} disabled={resetting} className="bg-red-600 hover:bg-red-700">
                {resetting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
                {resetting ? 'Resetting...' : 'Yes, Reset Everything'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Client Import Preview Modal */}
        <Dialog open={clientImportModalOpen} onOpenChange={setClientImportModalOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Import Clients Preview</DialogTitle>
            </DialogHeader>
            {clientImportData && (
              <div className="space-y-4 py-4">
                <p className="text-sm text-muted-foreground">
                  About to import <span className="font-semibold text-foreground">{clientImportData.total}</span> clients:
                </p>
                
                <div className="max-h-[300px] overflow-auto border rounded">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50">
                        <TableHead className="w-[40px]">#</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Phone</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>VAT</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {clientImportData.clients.slice(0, 10).map((client, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="text-muted-foreground">{idx + 1}</TableCell>
                          <TableCell className="font-medium">{client.name}</TableCell>
                          <TableCell className="text-sm">{client.phone || '-'}</TableCell>
                          <TableCell className="text-sm">{client.email || '-'}</TableCell>
                          <TableCell className="text-sm">{client.vat_number || '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                
                {clientImportData.total > 10 && (
                  <p className="text-sm text-muted-foreground text-center">
                    ... and {clientImportData.total - 10} more clients
                  </p>
                )}
                
                <div className="bg-blue-50 p-3 rounded text-sm text-blue-700">
                  <p><strong>Default settings applied:</strong></p>
                  <ul className="list-disc ml-5 mt-1">
                    <li>Currency: ZAR</li>
                    <li>Rate type: Per KG</li>
                    <li>Rate value: R 36.00 (or tenant default)</li>
                  </ul>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setClientImportModalOpen(false)}>Cancel</Button>
              <Button onClick={handleConfirmClientImport} disabled={clientImporting} className="bg-[#6B633C] hover:bg-[#5a5332]">
                {clientImporting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                {clientImporting ? 'Importing...' : `Import ${clientImportData?.total || 0} Clients`}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}
