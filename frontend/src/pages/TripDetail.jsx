import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Checkbox } from '../components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableFooter,
} from '../components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
import { toast } from 'sonner';
import { 
  ArrowLeft, Package, Weight, Users, DollarSign, Truck, User,
  Calendar, MapPin, Edit, Lock, FileText, Plus, Trash2,
  MoreVertical, Upload, Receipt, Clock, CheckCircle, XCircle,
  AlertCircle, Fuel, Building2, Wrench, Utensils, MoreHorizontal,
  CircleDollarSign, Send, Download, RefreshCw, MessageSquare,
  Copy, FileUp, Eye, Search, Check, X
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { useAuth } from '../contexts/AuthContext';

const API = `${window.location.origin}/api`;

const statusConfig = {
  planning: { bg: 'bg-[#D4CFC0]', text: 'text-[#3C3F42]', label: 'Planning' },
  loading: { bg: 'bg-[#E8DC88]', text: 'text-[#3C3F42]', label: 'Loading' },
  in_transit: { bg: 'bg-[#6B633C]', text: 'text-white', label: 'In Transit' },
  delivered: { bg: 'bg-[#5A8F3B]', text: 'text-white', label: 'Delivered' },
  closed: { bg: 'bg-[#3C3F42]', text: 'text-white', label: 'Closed' }
};

const parcelStatusConfig = {
  warehouse: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'In Warehouse' },
  staged: { bg: 'bg-[#E8DC88]', text: 'text-[#3C3F42]', label: 'Ready to Load' },
  loaded: { bg: 'bg-[#6B633C]', text: 'text-white', label: 'Loaded' },
  in_transit: { bg: 'bg-blue-500', text: 'text-white', label: 'In Transit' },
  arrived: { bg: 'bg-purple-500', text: 'text-white', label: 'Awaiting Collection' },
  delivered: { bg: 'bg-[#5A8F3B]', text: 'text-white', label: 'Delivered' }
};

const expenseCategoryConfig = {
  fuel: { icon: Fuel, label: 'Fuel', color: '#EF4444' },
  tolls: { icon: CircleDollarSign, label: 'Tolls', color: '#F59E0B' },
  border_fees: { icon: Building2, label: 'Border Fees', color: '#8B5CF6' },
  repairs: { icon: Wrench, label: 'Repairs', color: '#3B82F6' },
  food: { icon: Utensils, label: 'Food', color: '#10B981' },
  accommodation: { icon: Building2, label: 'Accommodation', color: '#6366F1' },
  other: { icon: MoreHorizontal, label: 'Other', color: '#6B7280' }
};

const invoiceStatusConfig = {
  draft: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Draft' },
  sent: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Sent' },
  paid: { bg: 'bg-green-100', text: 'text-green-700', label: 'Paid' },
  overdue: { bg: 'bg-red-100', text: 'text-red-700', label: 'Overdue' }
};

const reviewStatusConfig = {
  not_reviewed: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Not Reviewed' },
  reviewed: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Reviewed' },
  approved: { bg: 'bg-green-100', text: 'text-green-700', label: 'Approved' }
};

const documentCategories = ['Driver Doc', 'Border Permit', 'Receipt', 'Other'];

export function TripDetail() {
  const { tripId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [tripData, setTripData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Tab data states
  const [parcels, setParcels] = useState([]);
  const [parcelFilter, setParcelFilter] = useState('all');
  const [parcelSearch, setParcelSearch] = useState('');
  const [selectedParcels, setSelectedParcels] = useState(new Set());
  const [clientsSummary, setClientsSummary] = useState({ clients: [], totals: {} });
  const [expenses, setExpenses] = useState([]);
  const [history, setHistory] = useState([]);
  const [historyFilter, setHistoryFilter] = useState('all');
  const [documents, setDocuments] = useState([]);
  const [packingList, setPackingList] = useState([]);
  const [packingListSearch, setPackingListSearch] = useState('');
  const [packingListSort, setPackingListSort] = useState('az');
  
  // Vehicles and drivers for assignment
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  
  // Team members for mentions
  const [teamMembers, setTeamMembers] = useState([]);
  
  // Dialog states
  const [editRouteOpen, setEditRouteOpen] = useState(false);
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const [expenseDialogOpen, setExpenseDialogOpen] = useState(false);
  const [confirmCloseOpen, setConfirmCloseOpen] = useState(false);
  const [uploadDocOpen, setUploadDocOpen] = useState(false);
  const [commentPopoverOpen, setCommentPopoverOpen] = useState(null);
  const [statusChangeOpen, setStatusChangeOpen] = useState(false);
  
  // Form states
  const [routeStops, setRouteStops] = useState([]);
  const [routeInput, setRouteInput] = useState('');
  const [selectedVehicle, setSelectedVehicle] = useState('');
  const [selectedDriver, setSelectedDriver] = useState('');
  const [expenseForm, setExpenseForm] = useState({
    category: 'fuel',
    amount: '',
    currency: 'ZAR',
    expense_date: new Date().toISOString().split('T')[0],
    description: '',
    supplier: '',
    receipt_url: ''
  });
  const [docForm, setDocForm] = useState({
    file_name: '',
    file_type: '',
    file_data: '',
    category: 'Other'
  });
  const [newStatus, setNewStatus] = useState('');
  const [commentText, setCommentText] = useState('');
  const [mentionSearch, setMentionSearch] = useState('');
  const [selectedMentions, setSelectedMentions] = useState([]);
  
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  const fetchTripData = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/trips/${tripId}/summary`, { withCredentials: true });
      setTripData(response.data);
      setRouteStops(response.data.trip.route || []);
      setSelectedVehicle(response.data.trip.vehicle_id || '');
      setSelectedDriver(response.data.trip.driver_id || '');
      setNewStatus(response.data.trip.status || 'planning');
    } catch (error) {
      toast.error('Failed to fetch trip details');
      navigate('/trips');
    } finally {
      setLoading(false);
    }
  }, [tripId, navigate]);

  const fetchParcels = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/trips/${tripId}/parcels?status=${parcelFilter}`, { withCredentials: true });
      setParcels(response.data);
    } catch (error) {
      console.error('Failed to fetch parcels');
    }
  }, [tripId, parcelFilter]);

  const fetchClientsSummary = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/trips/${tripId}/clients-summary`, { withCredentials: true });
      setClientsSummary(response.data);
    } catch (error) {
      console.error('Failed to fetch clients summary');
    }
  }, [tripId]);

  const fetchExpenses = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/trips/${tripId}/expenses`, { withCredentials: true });
      setExpenses(response.data);
    } catch (error) {
      console.error('Failed to fetch expenses');
    }
  }, [tripId]);

  const fetchHistory = useCallback(async () => {
    try {
      const filter = historyFilter === 'all' ? '' : `?filter_type=${historyFilter}`;
      const response = await axios.get(`${API}/trips/${tripId}/history${filter}`, { withCredentials: true });
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch history');
    }
  }, [tripId, historyFilter]);

  const fetchDocuments = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/trips/${tripId}/documents`, { withCredentials: true });
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to fetch documents');
    }
  }, [tripId]);

  const fetchPackingList = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/trips/${tripId}/packing-list`, { withCredentials: true });
      setPackingList((r.data.items || []).map((item, idx) => ({ ...item, _id: Date.now() + idx })));
    } catch {}
  }, [tripId]);

  const fetchTeamMembers = async () => {
    try {
      const response = await axios.get(`${API}/team-members`, { withCredentials: true });
      setTeamMembers(response.data);
    } catch (error) {
      console.error('Failed to fetch team members');
    }
  };

  const fetchVehiclesAndDrivers = async () => {
    try {
      const [vehiclesRes, driversRes] = await Promise.all([
        axios.get(`${API}/vehicles`, { withCredentials: true }),
        axios.get(`${API}/drivers`, { withCredentials: true })
      ]);
      setVehicles(vehiclesRes.data);
      setDrivers(driversRes.data);
    } catch (error) {
      console.error('Failed to fetch vehicles/drivers');
    }
  };

  useEffect(() => {
    fetchTripData();
    fetchTeamMembers();
  }, [fetchTripData]);

  useEffect(() => {
    if (activeTab === 'parcels') fetchParcels();
    if (activeTab === 'clients') fetchClientsSummary();
    if (activeTab === 'expenses') fetchExpenses();
    if (activeTab === 'history') fetchHistory();
    if (activeTab === 'documents') { fetchDocuments(); fetchPackingList(); }
  }, [activeTab, fetchParcels, fetchClientsSummary, fetchExpenses, fetchHistory, fetchDocuments]);

  useEffect(() => {
    if (activeTab === 'parcels') fetchParcels();
  }, [parcelFilter, fetchParcels]);

  useEffect(() => {
    if (activeTab === 'history') fetchHistory();
  }, [historyFilter, fetchHistory]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR', maximumFractionDigits: 0 }).format(amount || 0);
  };

  // Filter parcels by search
  const filteredParcels = parcels.filter(p => {
    if (!parcelSearch) return true;
    const search = parcelSearch.toLowerCase();
    return (
      p.description?.toLowerCase().includes(search) ||
      p.id?.toLowerCase().includes(search) ||
      p.client_name?.toLowerCase().includes(search) ||
      p.pieces?.some(piece => piece.barcode?.toLowerCase().includes(search))
    );
  });

  // Calculate parcel totals
  const parcelTotals = filteredParcels.reduce((acc, p) => {
    acc.count += 1;
    acc.weight += p.total_weight || 0;
    acc.amount += p.charge_amount || 0;
    return acc;
  }, { count: 0, weight: 0, amount: 0 });

  // Handlers
  const handleCloseTrip = async () => {
    setSubmitting(true);
    try {
      await axios.post(`${API}/trips/${tripId}/close`, {}, { withCredentials: true });
      toast.success(`Trip ${tripData?.trip?.trip_number} closed successfully`);
      setConfirmCloseOpen(false);
      fetchTripData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to close trip');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateRoute = async () => {
    setSubmitting(true);
    try {
      await axios.put(`${API}/trips/${tripId}`, { route: routeStops }, { withCredentials: true });
      toast.success('Route updated');
      setEditRouteOpen(false);
      fetchTripData();
    } catch (error) {
      toast.error('Failed to update route');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateAssignment = async () => {
    setSubmitting(true);
    try {
      await axios.put(`${API}/trips/${tripId}`, {
        vehicle_id: selectedVehicle || null,
        driver_id: selectedDriver || null
      }, { withCredentials: true });
      toast.success('Assignment updated');
      setAssignmentOpen(false);
      fetchTripData();
    } catch (error) {
      toast.error('Failed to update assignment');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async () => {
    setSubmitting(true);
    try {
      await axios.put(`${API}/trips/${tripId}`, { status: newStatus }, { withCredentials: true });
      toast.success('Status updated');
      setStatusChangeOpen(false);
      fetchTripData();
    } catch (error) {
      toast.error('Failed to update status');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDuplicateTrip = async () => {
    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/trips/${tripId}/duplicate`, {}, { withCredentials: true });
      toast.success(`Trip duplicated as ${response.data.trip_number}`);
      navigate(`/trips/${response.data.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to duplicate trip');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteTrip = async () => {
    if (!window.confirm('Are you sure you want to delete this trip? This cannot be undone.')) return;
    setSubmitting(true);
    try {
      await axios.delete(`${API}/trips/${tripId}`, { withCredentials: true });
      toast.success('Trip deleted');
      navigate('/trips');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete trip');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddExpense = async (e) => {
    e.preventDefault();
    if (!expenseForm.amount || parseFloat(expenseForm.amount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API}/trips/${tripId}/expenses`, {
        ...expenseForm,
        amount: parseFloat(expenseForm.amount)
      }, { withCredentials: true });
      toast.success('Expense added');
      setExpenseForm({
        category: 'fuel',
        amount: '',
        currency: 'ZAR',
        expense_date: new Date().toISOString().split('T')[0],
        description: '',
        supplier: '',
        receipt_url: ''
      });
      setExpenseDialogOpen(false);
      fetchExpenses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add expense');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteExpense = async (expenseId) => {
    if (!window.confirm('Delete this expense?')) return;
    try {
      await axios.delete(`${API}/trips/${tripId}/expenses/${expenseId}`, { withCredentials: true });
      toast.success('Expense deleted');
      fetchExpenses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete expense');
    }
  };

  const handleRemoveParcel = async (parcelId) => {
    if (!window.confirm('Remove this parcel from the trip?')) return;
    try {
      await axios.delete(`${API}/trips/${tripId}/parcels/${parcelId}`, { withCredentials: true });
      toast.success('Parcel removed from trip');
      fetchParcels();
      fetchTripData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove parcel');
    }
  };

  const handleGenerateInvoices = async () => {
    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/trips/${tripId}/generate-invoices`, {}, { withCredentials: true });
      toast.success(response.data.message);
      fetchClientsSummary();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate invoices');
    } finally {
      setSubmitting(false);
    }
  };

  const handleMarkReviewed = async (invoiceId) => {
    try {
      await axios.post(`${API}/invoices/${invoiceId}/mark-reviewed`, {}, { withCredentials: true });
      toast.success('Invoice marked as reviewed');
      fetchClientsSummary();
    } catch (error) {
      toast.error('Failed to mark as reviewed');
    }
  };

  const handleApproveAndSend = async (invoiceId) => {
    try {
      await axios.post(`${API}/invoices/${invoiceId}/approve-and-send`, {}, { withCredentials: true });
      toast.success('Invoice approved and sent');
      fetchClientsSummary();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve');
    }
  };

  // Quick status change handler for action buttons
  const handleQuickStatusChange = async (newStatus) => {
    try {
      await axios.put(`${API}/trips/${tripId}`, { status: newStatus }, { withCredentials: true });
      toast.success(`Trip status updated to ${newStatus.replace('_', ' ')}`);
      fetchTrip();
      fetchParcels();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const handleAddComment = async (invoiceId) => {
    if (!commentText.trim()) return;
    try {
      await axios.post(`${API}/invoices/${invoiceId}/comments`, {
        content: commentText,
        mentioned_user_ids: selectedMentions.map(m => m.id)
      }, { withCredentials: true });
      toast.success('Comment added');
      setCommentText('');
      setSelectedMentions([]);
      setCommentPopoverOpen(null);
    } catch (error) {
      toast.error('Failed to add comment');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(',')[1];
      setDocForm({
        ...docForm,
        file_name: file.name,
        file_type: file.type,
        file_data: base64
      });
    };
    reader.readAsDataURL(file);
  };

  const handleUploadDocument = async () => {
    if (!docForm.file_data) {
      toast.error('Please select a file');
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API}/trips/${tripId}/documents`, docForm, { withCredentials: true });
      toast.success('Document uploaded');
      setDocForm({ file_name: '', file_type: '', file_data: '', category: 'Other' });
      setUploadDocOpen(false);
      fetchDocuments();
    } catch (error) {
      toast.error('Failed to upload document');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await axios.delete(`${API}/trips/${tripId}/documents/${docId}`, { withCredentials: true });
      toast.success('Document deleted');
      fetchDocuments();
    } catch (error) {
      toast.error('Failed to delete document');
    }
  };

  const handleDownloadDocument = async (doc) => {
    try {
      const response = await axios.get(`${API}/trips/${tripId}/documents/${doc.id}/download`, { withCredentials: true });
      const link = document.createElement('a');
      link.href = `data:${response.data.file_type};base64,${response.data.file_data}`;
      link.download = response.data.file_name;
      link.click();
    } catch (error) {
      toast.error('Failed to download document');
    }
  };

  const handleDownloadWorksheet = async () => {
    try {
      const response = await axios.get(`${API}/finance/trip-worksheet/${tripId}/pdf`, {
        withCredentials: true,
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `Worksheet-${trip?.trip_number || tripId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Worksheet downloaded');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Failed to download worksheet');
    }
  };

  const addRouteStop = () => {
    if (routeInput.trim()) {
      setRouteStops([...routeStops, routeInput.trim()]);
      setRouteInput('');
    }
  };

  const removeRouteStop = (index) => {
    setRouteStops(routeStops.filter((_, i) => i !== index));
  };

  const getReviewStatus = (invoice) => {
    if (invoice.approved_at) return 'approved';
    if (invoice.reviewed_at) return 'reviewed';
    return 'not_reviewed';
  };

  // Calculate expense totals by category
  const expenseTotals = expenses.reduce((acc, exp) => {
    acc[exp.category] = (acc[exp.category] || 0) + (exp.amount || 0);
    acc.total = (acc.total || 0) + (exp.amount || 0);
    return acc;
  }, { total: 0 });

  if (loading) {
    return (
      <>
        <div className="p-6">
          <Skeleton className="h-10 w-48 mb-6" />
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32" />)}
          </div>
          <Skeleton className="h-96" />
        </div>
      </>
    );
  }

  if (!tripData) return null;

  const { trip, stats, created_by, created_at } = tripData;
  const status = statusConfig[trip.status] || statusConfig.planning;
  const isLocked = !!trip.locked_at;
  const isOwner = user?.role === 'owner';
  const isManager = user?.role === 'manager';
  const canApprove = isOwner || isManager;

  return (
    <>
      <div className="p-6" data-testid="trip-detail-page">
        {/* Top Bar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/trips')} data-testid="back-btn">
              <ArrowLeft className="h-4 w-4 mr-2" /> Trip Manager
            </Button>
            <h1 className="text-3xl font-bold text-[#3C3F42]">Trip {trip.trip_number}</h1>
            <Badge className={`${status.bg} ${status.text} border-0 px-3 py-1`}>
              {status.label}
            </Badge>
            {isLocked && (
              <Badge variant="outline" className="border-red-500 text-red-500">
                <Lock className="h-3 w-3 mr-1" /> Locked
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Status Action Buttons - Based on current trip status */}
            {trip.status === 'planning' && (
              <Button 
                onClick={() => handleQuickStatusChange('loading')}
                className="bg-amber-500 hover:bg-amber-600"
                data-testid="mark-loading-btn"
              >
                <Package className="h-4 w-4 mr-2" />
                Mark as Loading
              </Button>
            )}
            {trip.status === 'loading' && (
              <Button 
                onClick={() => handleQuickStatusChange('in_transit')}
                className="bg-[#6B633C] hover:bg-[#5a5432]"
                data-testid="mark-in-transit-btn"
              >
                <Truck className="h-4 w-4 mr-2" />
                Mark as In Transit
              </Button>
            )}
            {trip.status === 'in_transit' && (
              <Button 
                onClick={() => handleQuickStatusChange('delivered')}
                className="bg-green-600 hover:bg-green-700"
                data-testid="mark-delivered-btn"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Mark as Delivered
              </Button>
            )}
            {trip.status === 'delivered' && !isLocked && (
              <Button 
                onClick={() => setConfirmCloseOpen(true)}
                variant="outline"
                data-testid="close-trip-btn"
              >
                <Lock className="h-4 w-4 mr-2" />
                Close Trip
              </Button>
            )}
            
            {/* Trip Actions Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" data-testid="trip-actions-btn">
                  <MoreVertical className="h-4 w-4 mr-2" /> Actions
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {!isLocked && (
                  <DropdownMenuItem onClick={() => { fetchVehiclesAndDrivers(); setAssignmentOpen(true); }}>
                    <Edit className="h-4 w-4 mr-2" /> Edit Assignment
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={handleDuplicateTrip}>
                  <Copy className="h-4 w-4 mr-2" /> Duplicate Trip
                </DropdownMenuItem>
                {!isLocked && (
                  <DropdownMenuItem onClick={() => setStatusChangeOpen(true)}>
                    <RefreshCw className="h-4 w-4 mr-2" /> Change Status
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={handleDownloadWorksheet}>
                  <Download className="h-4 w-4 mr-2" /> Download Summary
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                {!isLocked && isOwner && (
                  <DropdownMenuItem onClick={() => setConfirmCloseOpen(true)}>
                    <Lock className="h-4 w-4 mr-2" /> Close Trip
                  </DropdownMenuItem>
                )}
                {!isLocked && (
                  <DropdownMenuItem onClick={handleDeleteTrip} className="text-red-600">
                    <Trash2 className="h-4 w-4 mr-2" /> Delete Trip
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Header Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card className="bg-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-[#6B633C]/10 rounded-lg">
                  <Package className="h-6 w-6 text-[#6B633C]" />
                </div>
                <div>
                  <p className="text-3xl font-bold text-[#3C3F42]">{stats.total_parcels}</p>
                  <p className="text-sm text-gray-500">{stats.total_clients} clients</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-[#6B633C]/10 rounded-lg">
                  <Weight className="h-6 w-6 text-[#6B633C]" />
                </div>
                <div className="flex-1">
                  <p className="text-3xl font-bold text-[#3C3F42]">{stats.total_weight.toLocaleString()} kg</p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-[#6B633C]" style={{ width: `${Math.min(stats.loading_percentage, 100)}%` }} />
                    </div>
                    <span className="text-xs text-gray-500">{stats.loading_percentage}%</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-[#6B633C]/10 rounded-lg">
                  <Receipt className="h-6 w-6 text-[#6B633C]" />
                </div>
                <div>
                  <p className="text-3xl font-bold text-[#3C3F42]">{formatCurrency(stats.invoiced_value)}</p>
                  <p className="text-sm text-gray-500">Invoiced amount</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-green-100 rounded-lg">
                  <DollarSign className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-3xl font-bold text-green-600">{formatCurrency(clientsSummary.totals.total_paid || 0)}</p>
                  <p className="text-sm text-gray-500">
                    Paid / {formatCurrency(stats.invoiced_value)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="bg-white border">
            <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
            <TabsTrigger value="parcels" data-testid="tab-parcels">Parcels</TabsTrigger>
            <TabsTrigger value="clients" data-testid="tab-clients">Clients & Invoicing</TabsTrigger>
            <TabsTrigger value="expenses" data-testid="tab-expenses">Expenses</TabsTrigger>
            <TabsTrigger value="documents" data-testid="tab-documents">Documents</TabsTrigger>
            <TabsTrigger value="history" data-testid="tab-history">History</TabsTrigger>
          </TabsList>

          {/* TAB 1: Overview */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Route & Schedule */}
              <Card className="bg-white">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-[#3C3F42]">
                    <MapPin className="h-5 w-5 text-[#6B633C]" /> Route & Schedule
                  </CardTitle>
                  {!isLocked && (
                    <Button variant="outline" size="sm" onClick={() => setEditRouteOpen(true)}>
                      <Edit className="h-4 w-4 mr-1" /> Edit Route
                    </Button>
                  )}
                </CardHeader>
                <CardContent>
                  {trip.route && trip.route.length > 0 ? (
                    <div className="space-y-3">
                      {trip.route.map((stop, index) => (
                        <div key={index} className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            index === 0 ? 'bg-green-500 text-white' : 
                            index === trip.route.length - 1 ? 'bg-red-500 text-white' : 
                            'bg-[#6B633C] text-white'
                          }`}>
                            {index + 1}
                          </div>
                          <span className="font-medium text-[#3C3F42]">{stop}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500">No route defined</p>
                  )}
                  
                  {trip.departure_date && (
                    <div className="mt-4 pt-4 border-t flex items-center gap-2 text-gray-600">
                      <Calendar className="h-4 w-4" />
                      Departure: {format(new Date(trip.departure_date), 'MMMM d, yyyy')}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Vehicle & Driver */}
              <Card className="bg-white">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-[#3C3F42]">
                    <Truck className="h-5 w-5 text-[#6B633C]" /> Vehicle & Driver
                  </CardTitle>
                  {!isLocked && (
                    <Button variant="outline" size="sm" onClick={() => { fetchVehiclesAndDrivers(); setAssignmentOpen(true); }}>
                      <Edit className="h-4 w-4 mr-1" /> Change Assignment
                    </Button>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-lg">
                      <Truck className="h-5 w-5 text-gray-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Vehicle</p>
                      <p className="font-medium text-[#3C3F42]">
                        {trip.vehicle ? `${trip.vehicle.registration_number} - ${trip.vehicle.vehicle_type}` : 'Not assigned'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-lg">
                      <User className="h-5 w-5 text-gray-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Driver</p>
                      <p className="font-medium text-[#3C3F42]">
                        {trip.driver ? trip.driver.name : 'Not assigned'}
                      </p>
                      {trip.driver?.phone && (
                        <p className="text-sm text-gray-500">{trip.driver.phone}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Notes & Metadata */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {trip.notes && (
                <Card className="bg-white">
                  <CardHeader>
                    <CardTitle className="text-[#3C3F42]">Notes</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-600">{trip.notes}</p>
                  </CardContent>
                </Card>
              )}
              
              <Card className="bg-white">
                <CardHeader>
                  <CardTitle className="text-[#3C3F42]">Trip Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Created by</span>
                    <span className="font-medium">{created_by || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Created at</span>
                    <span className="font-medium">{created_at ? format(new Date(created_at), 'MMM d, yyyy h:mm a') : '-'}</span>
                  </div>
                  {trip.locked_at && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Closed at</span>
                      <span className="font-medium">{format(new Date(trip.locked_at), 'MMM d, yyyy h:mm a')}</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* TAB 2: Parcels */}
          <TabsContent value="parcels" className="space-y-4">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex flex-wrap gap-2">
                {['all', 'not_loaded', 'loaded', 'delivered'].map(filter => (
                  <Button
                    key={filter}
                    variant={parcelFilter === filter ? 'default' : 'outline'}
                    size="sm"
                    className={parcelFilter === filter ? 'bg-[#6B633C] hover:bg-[#5a5332]' : ''}
                    onClick={() => setParcelFilter(filter)}
                  >
                    {filter === 'all' ? 'All' : filter === 'not_loaded' ? 'Not Loaded' : filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </Button>
                ))}
              </div>
              <div className="flex gap-2 items-center">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search parcels..."
                    value={parcelSearch}
                    onChange={(e) => setParcelSearch(e.target.value)}
                    className="pl-9 w-[200px]"
                    data-testid="parcel-search-input"
                  />
                </div>
                <Button variant="outline" onClick={() => navigate('/warehouse')}>
                  <Plus className="h-4 w-4 mr-1" /> Assign More
                </Button>
                <Button variant="outline" onClick={handleDownloadWorksheet}>
                  <Download className="h-4 w-4 mr-1" /> Loading List
                </Button>
              </div>
            </div>

            <Card className="bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox 
                        checked={selectedParcels.size === filteredParcels.length && filteredParcels.length > 0}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedParcels(new Set(filteredParcels.map(p => p.id)));
                          } else {
                            setSelectedParcels(new Set());
                          }
                        }}
                      />
                    </TableHead>
                    <TableHead>Parcel ID</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Pieces</TableHead>
                    <TableHead>Weight</TableHead>
                    <TableHead className="text-right">Total Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-20">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredParcels.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                        No parcels found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredParcels.map(parcel => {
                      const pStatus = parcelStatusConfig[parcel.status] || parcelStatusConfig.warehouse;
                      return (
                        <TableRow key={parcel.id}>
                          <TableCell>
                            <Checkbox
                              checked={selectedParcels.has(parcel.id)}
                              onCheckedChange={(checked) => {
                                const newSelected = new Set(selectedParcels);
                                if (checked) newSelected.add(parcel.id);
                                else newSelected.delete(parcel.id);
                                setSelectedParcels(newSelected);
                              }}
                            />
                          </TableCell>
                          <TableCell className="font-mono text-sm">{parcel.id.slice(0, 8)}...</TableCell>
                          <TableCell>{parcel.client_name}</TableCell>
                          <TableCell className="max-w-[200px] truncate">{parcel.description || '-'}</TableCell>
                          <TableCell>{parcel.piece_count}</TableCell>
                          <TableCell>{parcel.total_weight || 0} kg</TableCell>
                          <TableCell className="text-right font-mono">
                            {parcel.charge_amount ? formatCurrency(parcel.charge_amount) : '-'}
                          </TableCell>
                          <TableCell>
                            <Badge className={`${pStatus.bg} ${pStatus.text} border-0`}>{pStatus.label}</Badge>
                          </TableCell>
                          <TableCell>
                            {!isLocked && (
                              <Button variant="ghost" size="icon" onClick={() => handleRemoveParcel(parcel.id)}>
                                <Trash2 className="h-4 w-4 text-red-500" />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
                {filteredParcels.length > 0 && (
                  <TableFooter>
                    <TableRow className="bg-gray-50">
                      <TableCell colSpan={4} className="font-semibold">Totals</TableCell>
                      <TableCell className="font-semibold">{parcelTotals.count}</TableCell>
                      <TableCell className="font-semibold">{parcelTotals.weight.toFixed(1)} kg</TableCell>
                      <TableCell className="text-right font-semibold font-mono">
                        {formatCurrency(parcelTotals.amount)}
                      </TableCell>
                      <TableCell colSpan={2}></TableCell>
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </Card>
          </TabsContent>

          {/* TAB 3: Clients & Invoicing */}
          <TabsContent value="clients" className="space-y-4">
            <div className="flex justify-end gap-2">
              <Button 
                className="bg-[#6B633C] hover:bg-[#5a5332]" 
                onClick={handleGenerateInvoices}
                disabled={submitting}
              >
                <FileText className="h-4 w-4 mr-1" /> Generate All Invoices
              </Button>
              <Button variant="outline">
                <Send className="h-4 w-4 mr-1" /> Send Statements
              </Button>
            </div>

            <Card className="bg-white">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Client Name</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Parcels</TableHead>
                    <TableHead>Weight</TableHead>
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Review Status</TableHead>
                    <TableHead className="w-[180px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clientsSummary.clients.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                        No clients on this trip
                      </TableCell>
                    </TableRow>
                  ) : (
                    clientsSummary.clients.map(client => (
                      <TableRow key={client.client_id}>
                        <TableCell className="pl-4 font-medium">{client.client_name}</TableCell>
                        <TableCell>{client.client_phone || '-'}</TableCell>
                        <TableCell>{client.parcel_count}</TableCell>
                        <TableCell>{client.total_weight.toFixed(1)} kg</TableCell>
                        <TableCell>
                          {client.invoices.length > 0 
                            ? client.invoices.map(inv => inv.invoice_number).join(', ')
                            : <span className="text-gray-400">-</span>
                          }
                        </TableCell>
                        <TableCell>
                          {client.invoices.length > 0
                            ? formatCurrency(client.invoices.reduce((sum, inv) => sum + inv.total, 0))
                            : '-'
                          }
                        </TableCell>
                        <TableCell>
                          {client.invoices.length > 0 ? (
                            client.invoices.map(inv => {
                              const invStatus = invoiceStatusConfig[inv.status] || invoiceStatusConfig.draft;
                              return (
                                <Badge key={inv.id} className={`${invStatus.bg} ${invStatus.text} border-0 mr-1`}>
                                  {invStatus.label}
                                </Badge>
                              );
                            })
                          ) : (
                            <Badge variant="outline">No Invoice</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {client.invoices.length > 0 ? (
                            client.invoices.map(inv => {
                              const reviewStatus = getReviewStatus(inv);
                              const reviewConfig = reviewStatusConfig[reviewStatus];
                              return (
                                <Badge key={inv.id} className={`${reviewConfig.bg} ${reviewConfig.text} border-0`}>
                                  {reviewConfig.label}
                                </Badge>
                              );
                            })
                          ) : '-'}
                        </TableCell>
                        <TableCell>
                          {client.invoices.length > 0 && (
                            <div className="flex items-center gap-1">
                              {client.invoices.map(inv => (
                                <div key={inv.id} className="flex items-center gap-1">
                                  {!inv.reviewed_at && (
                                    <Button 
                                      variant="outline" 
                                      size="sm"
                                      onClick={() => handleMarkReviewed(inv.id)}
                                    >
                                      <Check className="h-3 w-3 mr-1" /> Review
                                    </Button>
                                  )}
                                  {inv.reviewed_at && !inv.approved_at && canApprove && (
                                    <Button 
                                      size="sm"
                                      className="bg-green-600 hover:bg-green-700"
                                      onClick={() => handleApproveAndSend(inv.id)}
                                    >
                                      <Send className="h-3 w-3 mr-1" /> Approve
                                    </Button>
                                  )}
                                  <Popover open={commentPopoverOpen === inv.id} onOpenChange={(open) => setCommentPopoverOpen(open ? inv.id : null)}>
                                    <PopoverTrigger asChild>
                                      <Button variant="ghost" size="icon">
                                        <MessageSquare className="h-4 w-4" />
                                      </Button>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-80">
                                      <div className="space-y-3">
                                        <h4 className="font-medium">Add Comment</h4>
                                        <Textarea
                                          placeholder="Type @ to mention team members..."
                                          value={commentText}
                                          onChange={(e) => setCommentText(e.target.value)}
                                          rows={3}
                                        />
                                        {selectedMentions.length > 0 && (
                                          <div className="flex flex-wrap gap-1">
                                            {selectedMentions.map(m => (
                                              <Badge key={m.id} variant="secondary" className="gap-1">
                                                @{m.name}
                                                <X className="h-3 w-3 cursor-pointer" onClick={() => setSelectedMentions(prev => prev.filter(p => p.id !== m.id))} />
                                              </Badge>
                                            ))}
                                          </div>
                                        )}
                                        <div className="border rounded-md p-2 max-h-32 overflow-y-auto">
                                          <p className="text-xs text-muted-foreground mb-2">Click to mention:</p>
                                          {teamMembers.map(member => (
                                            <div 
                                              key={member.id}
                                              className="flex items-center gap-2 p-1 hover:bg-gray-100 rounded cursor-pointer"
                                              onClick={() => {
                                                if (!selectedMentions.find(m => m.id === member.id)) {
                                                  setSelectedMentions([...selectedMentions, member]);
                                                }
                                              }}
                                            >
                                              <User className="h-4 w-4" />
                                              <span className="text-sm">{member.name}</span>
                                            </div>
                                          ))}
                                        </div>
                                        <Button 
                                          className="w-full"
                                          onClick={() => handleAddComment(inv.id)}
                                          disabled={!commentText.trim()}
                                        >
                                          Post Comment
                                        </Button>
                                      </div>
                                    </PopoverContent>
                                  </Popover>
                                </div>
                              ))}
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              
              {/* Summary Row */}
              {clientsSummary.clients.length > 0 && (
                <div className="border-t p-4 bg-gray-50 flex justify-between items-center">
                  <div className="flex gap-6 text-sm">
                    <span><strong>{clientsSummary.totals.total_clients}</strong> clients</span>
                    <span><strong>{clientsSummary.totals.total_parcels}</strong> parcels</span>
                    <span><strong>{clientsSummary.totals.total_weight}</strong> kg</span>
                  </div>
                  <div className="text-lg font-bold text-[#3C3F42]">
                    Total: {formatCurrency(clientsSummary.totals.total_invoiced)}
                  </div>
                </div>
              )}
            </Card>
          </TabsContent>

          {/* TAB 4: Expenses */}
          <TabsContent value="expenses" className="space-y-4">
            <div className="flex justify-end">
              <Button 
                className="bg-[#6B633C] hover:bg-[#5a5332]"
                onClick={() => setExpenseDialogOpen(true)}
                disabled={isLocked && !isOwner}
              >
                <Plus className="h-4 w-4 mr-1" /> Add Expense
              </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Expense Table */}
              <Card className="bg-white lg:col-span-2">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Supplier/Paid To</TableHead>
                      <TableHead>Amount (ZAR)</TableHead>
                      <TableHead>Receipt</TableHead>
                      <TableHead>Added By</TableHead>
                      <TableHead className="w-20">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {expenses.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center py-8 text-gray-500">
                          No expenses recorded
                        </TableCell>
                      </TableRow>
                    ) : (
                      expenses.map(expense => {
                        const catConfig = expenseCategoryConfig[expense.category] || expenseCategoryConfig.other;
                        const CatIcon = catConfig.icon;
                        return (
                          <TableRow key={expense.id}>
                            <TableCell>{expense.expense_date ? format(new Date(expense.expense_date), 'MMM d, yyyy') : '-'}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <CatIcon className="h-4 w-4" style={{ color: catConfig.color }} />
                                {catConfig.label}
                              </div>
                            </TableCell>
                            <TableCell className="max-w-[150px] truncate">{expense.description || '-'}</TableCell>
                            <TableCell>{expense.supplier || '-'}</TableCell>
                            <TableCell className="font-medium font-mono">
                              {expense.amount?.toLocaleString()}
                            </TableCell>
                            <TableCell>
                              {expense.receipt_url ? (
                                <a href={expense.receipt_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                                  <Eye className="h-4 w-4" />
                                </a>
                              ) : '-'}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {expense.created_by_name || '-'}
                            </TableCell>
                            <TableCell>
                              {(!isLocked || isOwner) && (
                                <Button variant="ghost" size="icon" onClick={() => handleDeleteExpense(expense.id)}>
                                  <Trash2 className="h-4 w-4 text-red-500" />
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </Card>

              {/* Expense Summary */}
              <Card className="bg-white">
                <CardHeader>
                  <CardTitle className="text-[#3C3F42]">Expense Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-500">Total Expenses</p>
                    <p className="text-3xl font-bold text-[#3C3F42]">{formatCurrency(expenseTotals.total)}</p>
                  </div>
                  
                  <div className="space-y-2">
                    {Object.entries(expenseCategoryConfig).map(([key, config]) => {
                      const amount = expenseTotals[key] || 0;
                      if (amount === 0) return null;
                      const CatIcon = config.icon;
                      const percentage = expenseTotals.total > 0 ? (amount / expenseTotals.total * 100).toFixed(0) : 0;
                      return (
                        <div key={key} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <CatIcon className="h-4 w-4" style={{ color: config.color }} />
                            <span className="text-sm">{config.label}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{formatCurrency(amount)}</span>
                            <span className="text-xs text-gray-400">({percentage}%)</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* TAB 5: Documents */}
          <TabsContent value="documents" className="space-y-6">
            {/* ---- PACKING LIST ---- */}
            <Card className="bg-white">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <CardTitle className="text-base font-semibold">Packing List</CardTitle>
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="relative">
                      <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
                      <Input
                        placeholder="Search items..."
                        value={packingListSearch}
                        onChange={(e) => setPackingListSearch(e.target.value)}
                        className="pl-7 h-8 text-xs w-48"
                        data-testid="packing-list-search"
                      />
                    </div>
                    <Select value={packingListSort} onValueChange={setPackingListSort}>
                      <SelectTrigger className="h-8 text-xs w-40">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="az">A-Z</SelectItem>
                        <SelectItem value="za">Z-A</SelectItem>
                        <SelectItem value="heaviest">Heaviest First</SelectItem>
                        <SelectItem value="lightest">Lightest First</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button size="sm" variant="outline" className="h-8 text-xs" onClick={() => setPackingList(p => [...p, { _id: Date.now(), description: '', qty: 1, kg: 0 }])} data-testid="add-packing-row">
                      <Plus className="h-3.5 w-3.5 mr-1" /> Add Row
                    </Button>
                    <Button size="sm" variant="outline" className="h-8 text-xs" onClick={fetchPackingList} title="Reset to trip data" data-testid="reset-packing-list">
                      <RefreshCw className="h-3.5 w-3.5 mr-1" /> Reset
                    </Button>
                    <Button
                      size="sm"
                      className="h-8 text-xs bg-[#6B633C] hover:bg-[#5a5332]"
                      onClick={() => window.open(`${API}/trips/${tripId}/packing-list/excel`, '_blank')}
                      data-testid="download-packing-excel"
                    >
                      <Download className="h-3.5 w-3.5 mr-1" /> Download Excel
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {(() => {
                  let items = packingList.filter(i =>
                    !packingListSearch || (i.description || '').toLowerCase().includes(packingListSearch.toLowerCase())
                  );
                  if (packingListSort === 'az') items = [...items].sort((a, b) => (a.description || '').localeCompare(b.description || ''));
                  else if (packingListSort === 'za') items = [...items].sort((a, b) => (b.description || '').localeCompare(a.description || ''));
                  else if (packingListSort === 'heaviest') items = [...items].sort((a, b) => (b.kg || 0) - (a.kg || 0));
                  else if (packingListSort === 'lightest') items = [...items].sort((a, b) => (a.kg || 0) - (b.kg || 0));
                  const totalKg = items.reduce((s, i) => s + (parseFloat(i.kg) || 0), 0);
                  return (
                    <>
                      <div className="px-4 py-1 text-xs text-muted-foreground border-b bg-gray-50">
                        Showing {items.length} items — Total: {totalKg.toFixed(1)} KG
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="pl-4 w-[50%]">Description</TableHead>
                            <TableHead className="w-24 text-right">QTY</TableHead>
                            <TableHead className="w-28 text-right">KG</TableHead>
                            <TableHead className="w-12"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {items.map((item) => (
                            <TableRow key={item._id}>
                              <TableCell className="pl-4">
                                <Input
                                  value={item.description || ''}
                                  onChange={(e) => setPackingList(p => p.map(i => i._id === item._id ? { ...i, description: e.target.value } : i))}
                                  className="h-7 text-xs border-0 border-b border-transparent hover:border-gray-300 focus:border-[#6B633C] rounded-none bg-transparent px-0"
                                  placeholder="Description"
                                />
                              </TableCell>
                              <TableCell className="text-right">
                                <Input
                                  type="number"
                                  value={item.qty || 1}
                                  onChange={(e) => setPackingList(p => p.map(i => i._id === item._id ? { ...i, qty: parseInt(e.target.value) || 1 } : i))}
                                  className="h-7 text-xs w-16 text-right border-0 border-b border-transparent hover:border-gray-300 focus:border-[#6B633C] rounded-none bg-transparent ml-auto"
                                />
                              </TableCell>
                              <TableCell className="text-right">
                                <Input
                                  type="number"
                                  step="0.1"
                                  value={item.kg || 0}
                                  onChange={(e) => setPackingList(p => p.map(i => i._id === item._id ? { ...i, kg: parseFloat(e.target.value) || 0 } : i))}
                                  className="h-7 text-xs w-20 text-right border-0 border-b border-transparent hover:border-gray-300 focus:border-[#6B633C] rounded-none bg-transparent ml-auto"
                                />
                              </TableCell>
                              <TableCell>
                                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setPackingList(p => p.filter(i => i._id !== item._id))}>
                                  <Trash2 className="h-3.5 w-3.5 text-red-500" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </>
                  );
                })()}
              </CardContent>
            </Card>

            {/* ---- DIGITAL MANIFEST ---- */}
            <Card className="bg-white">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-semibold">Digital Manifest</CardTitle>
                    <p className="text-xs text-muted-foreground mt-0.5">Sorted oldest to newest by parcel entry date</p>
                  </div>
                  <Button
                    size="sm"
                    className="bg-[#6B633C] hover:bg-[#5a5332]"
                    onClick={() => window.open(`${API}/trips/${tripId}/manifest/excel`, '_blank')}
                    data-testid="download-manifest-excel"
                  >
                    <Download className="h-4 w-4 mr-2" /> Download Manifest (Excel)
                  </Button>
                </div>
              </CardHeader>
            </Card>

            {/* ---- PARCEL LABELS ---- */}
            <Card className="bg-white">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-semibold">Parcel Labels</CardTitle>
                    <p className="text-xs text-muted-foreground mt-0.5">Generate A6 labels with QR codes for all parcels in this trip</p>
                  </div>
                  <Button
                    size="sm"
                    className="bg-[#6B633C] hover:bg-[#5a5332]"
                    onClick={() => window.open(`${API}/trips/${tripId}/labels/pdf`, '_blank')}
                    data-testid="download-labels-pdf"
                  >
                    <Download className="h-4 w-4 mr-2" /> Download Labels (PDF)
                  </Button>
                </div>
              </CardHeader>
            </Card>

            {/* ---- UPLOADED DOCUMENTS ---- */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-sm font-semibold">Uploaded Documents</h3>
                <Button className="bg-[#6B633C] hover:bg-[#5a5332]" size="sm" onClick={() => setUploadDocOpen(true)}>
                  <Upload className="h-4 w-4 mr-1" /> Upload Document
                </Button>
              </div>
              <Card className="bg-white">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="pl-4">File Name</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Uploaded By</TableHead>
                      <TableHead>Uploaded At</TableHead>
                      <TableHead className="w-32">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documents.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                          <FileUp className="h-12 w-12 mx-auto mb-3 opacity-50" />
                          <p>No documents uploaded</p>
                          <Button variant="link" onClick={() => setUploadDocOpen(true)}>Upload your first document</Button>
                        </TableCell>
                      </TableRow>
                    ) : documents.map(doc => (
                      <TableRow key={doc.id}>
                        <TableCell className="pl-4 font-medium">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-[#6B633C]" />
                            {doc.file_name}
                          </div>
                        </TableCell>
                        <TableCell><Badge variant="outline">{doc.category}</Badge></TableCell>
                        <TableCell className="text-sm text-muted-foreground">{doc.file_type?.split('/')[1]?.toUpperCase() || doc.file_type}</TableCell>
                        <TableCell>{doc.uploader_name}</TableCell>
                        <TableCell>{doc.uploaded_at ? format(new Date(doc.uploaded_at), 'MMM d, yyyy h:mm a') : '-'}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="icon" onClick={() => handleDownloadDocument(doc)}><Download className="h-4 w-4" /></Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDeleteDocument(doc.id)}><Trash2 className="h-4 w-4 text-red-500" /></Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </div>
          </TabsContent>

          {/* TAB 6: History */}
          <TabsContent value="history" className="space-y-4">
            <div className="flex gap-2">
              {['all', 'parcels', 'invoices', 'expenses', 'status'].map(filter => (
                <Button
                  key={filter}
                  variant={historyFilter === filter ? 'default' : 'outline'}
                  size="sm"
                  className={historyFilter === filter ? 'bg-[#6B633C] hover:bg-[#5a5332]' : ''}
                  onClick={() => setHistoryFilter(filter)}
                >
                  {filter.charAt(0).toUpperCase() + filter.slice(1)}
                </Button>
              ))}
            </div>

            <Card className="bg-white">
              <CardContent className="p-6">
                {history.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">No history records found</p>
                ) : (
                  <div className="space-y-4">
                    {history.map((log, index) => {
                      const actionIcon = {
                        create: <CheckCircle className="h-5 w-5 text-green-500" />,
                        update: <RefreshCw className="h-5 w-5 text-blue-500" />,
                        delete: <XCircle className="h-5 w-5 text-red-500" />
                      }[log.action] || <AlertCircle className="h-5 w-5 text-gray-500" />;
                      
                      return (
                        <div key={log.id || index} className="flex gap-4 pb-4 border-b last:border-0">
                          <div className="flex-shrink-0 mt-1">{actionIcon}</div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-[#3C3F42]">{log.user_name}</span>
                              <Badge variant="outline" className="text-xs">{log.table_name}</Badge>
                              <span className="text-xs text-gray-400">
                                {log.created_at && formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600">
                              {log.action === 'create' && `Created ${log.table_name.slice(0, -1)}`}
                              {log.action === 'update' && `Updated ${log.table_name.slice(0, -1)}`}
                              {log.action === 'delete' && `Deleted ${log.table_name.slice(0, -1)}`}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Edit Route Dialog */}
        <Dialog open={editRouteOpen} onOpenChange={setEditRouteOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Route</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  value={routeInput}
                  onChange={(e) => setRouteInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addRouteStop())}
                  placeholder="Add city/stop..."
                />
                <Button type="button" onClick={addRouteStop} variant="outline">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              
              {routeStops.length > 0 && (
                <div className="space-y-2 p-3 bg-gray-50 rounded-lg">
                  {routeStops.map((stop, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-[#6B633C] text-white text-xs flex items-center justify-center">
                        {index + 1}
                      </div>
                      <span className="flex-1">{stop}</span>
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeRouteStop(index)}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditRouteOpen(false)}>Cancel</Button>
              <Button className="bg-[#6B633C] hover:bg-[#5a5332]" onClick={handleUpdateRoute} disabled={submitting}>
                {submitting ? 'Saving...' : 'Save Route'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Assignment Dialog */}
        <Dialog open={assignmentOpen} onOpenChange={setAssignmentOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Change Assignment</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Vehicle</Label>
                <Select value={selectedVehicle || 'none'} onValueChange={(v) => setSelectedVehicle(v === 'none' ? '' : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select vehicle" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No vehicle</SelectItem>
                    {vehicles.map(v => (
                      <SelectItem key={v.id} value={v.id}>
                        {v.registration_number} - {v.vehicle_type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Driver</Label>
                <Select value={selectedDriver || 'none'} onValueChange={(v) => setSelectedDriver(v === 'none' ? '' : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select driver" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No driver</SelectItem>
                    {drivers.map(d => (
                      <SelectItem key={d.id} value={d.id}>
                        {d.name} - {d.phone}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAssignmentOpen(false)}>Cancel</Button>
              <Button className="bg-[#6B633C] hover:bg-[#5a5332]" onClick={handleUpdateAssignment} disabled={submitting}>
                {submitting ? 'Saving...' : 'Update Assignment'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Status Change Dialog */}
        <Dialog open={statusChangeOpen} onOpenChange={setStatusChangeOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Change Trip Status</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Select value={newStatus} onValueChange={setNewStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(statusConfig).filter(([k]) => k !== 'closed').map(([key, config]) => (
                    <SelectItem key={key} value={key}>{config.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setStatusChangeOpen(false)}>Cancel</Button>
              <Button className="bg-[#6B633C] hover:bg-[#5a5332]" onClick={handleStatusChange} disabled={submitting}>
                {submitting ? 'Updating...' : 'Update Status'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Add Expense Dialog */}
        <Dialog open={expenseDialogOpen} onOpenChange={setExpenseDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Expense</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleAddExpense} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Category</Label>
                  <Select value={expenseForm.category} onValueChange={(v) => setExpenseForm({...expenseForm, category: v})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(expenseCategoryConfig).map(([key, config]) => (
                        <SelectItem key={key} value={key}>{config.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Currency</Label>
                  <Select value={expenseForm.currency} onValueChange={(v) => setExpenseForm({...expenseForm, currency: v})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ZAR">ZAR</SelectItem>
                      <SelectItem value="USD">USD</SelectItem>
                      <SelectItem value="KES">KES</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label>Amount</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={expenseForm.amount}
                  onChange={(e) => setExpenseForm({...expenseForm, amount: e.target.value})}
                  placeholder="0.00"
                  required
                />
              </div>
              <div>
                <Label>Date</Label>
                <Input
                  type="date"
                  value={expenseForm.expense_date}
                  onChange={(e) => setExpenseForm({...expenseForm, expense_date: e.target.value})}
                  required
                />
              </div>
              <div>
                <Label>Description</Label>
                <Textarea
                  value={expenseForm.description}
                  onChange={(e) => setExpenseForm({...expenseForm, description: e.target.value})}
                  rows={2}
                  placeholder="Brief description..."
                />
              </div>
              <div>
                <Label>Supplier / Paid To</Label>
                <Input
                  value={expenseForm.supplier}
                  onChange={(e) => setExpenseForm({...expenseForm, supplier: e.target.value})}
                  placeholder="e.g. Shell Station, Border Agency..."
                />
              </div>
              <div>
                <Label>Receipt URL (optional)</Label>
                <Input
                  value={expenseForm.receipt_url}
                  onChange={(e) => setExpenseForm({...expenseForm, receipt_url: e.target.value})}
                  placeholder="https://..."
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setExpenseDialogOpen(false)}>Cancel</Button>
                <Button type="submit" className="bg-[#6B633C] hover:bg-[#5a5332]" disabled={submitting}>
                  {submitting ? 'Adding...' : 'Add Expense'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Upload Document Dialog */}
        <Dialog open={uploadDocOpen} onOpenChange={setUploadDocOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Document</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Category</Label>
                <Select value={docForm.category} onValueChange={(v) => setDocForm({...docForm, category: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {documentCategories.map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>File</Label>
                <Input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.gif"
                  onChange={handleFileSelect}
                  ref={fileInputRef}
                />
                {docForm.file_name && (
                  <p className="text-sm text-muted-foreground mt-1">Selected: {docForm.file_name}</p>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setUploadDocOpen(false)}>Cancel</Button>
              <Button className="bg-[#6B633C] hover:bg-[#5a5332]" onClick={handleUploadDocument} disabled={submitting || !docForm.file_data}>
                {submitting ? 'Uploading...' : 'Upload'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Confirm Close Dialog */}
        <Dialog open={confirmCloseOpen} onOpenChange={setConfirmCloseOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Close Trip {trip.trip_number}?</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <p className="text-gray-600">
                Closing this trip will lock all financial data. Only owners will be able to modify expenses after closing.
              </p>
              <p className="text-sm text-gray-500 mt-2">This action cannot be undone.</p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmCloseOpen(false)}>Cancel</Button>
              <Button 
                variant="destructive" 
                onClick={handleCloseTrip} 
                disabled={submitting}
              >
                {submitting ? 'Closing...' : 'Close Trip'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}

export default TripDetail;
