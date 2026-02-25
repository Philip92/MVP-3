import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { AuditHistory } from '../components/AuditHistory';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Checkbox } from '../components/ui/checkbox';
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '../components/ui/command';
import { toast } from 'sonner';
import { 
  Package, Search, MoreVertical, Edit, Trash2, Eye, Printer, 
  X, Filter, ChevronLeft, ChevronRight, ArrowUpDown,
  Truck, Check, ChevronsUpDown, Image as ImageIcon, Upload, Loader2, ZoomIn,
  Copy, AlertTriangle, Warehouse as WarehouseIcon, RefreshCw, ScanLine, FileSpreadsheet, Download
} from 'lucide-react';
import { cn } from '../lib/utils';
import { format } from 'date-fns';
import CollectionWarningDialog from '../components/CollectionWarningDialog';

const API = `${window.location.origin}/api`;

const statusColors = {
  warehouse: 'bg-[#938878]/20 text-[#3C3F42] border border-[#938878]',
  staged: 'bg-[#E8DC88] text-[#3C3F42] border border-[#E8DC88]',
  loaded: 'bg-[#6B633C] text-white border border-[#6B633C]',
  in_transit: 'bg-[#3C3F42] text-white border border-[#3C3F42]',
  arrived: 'bg-[#4A90D9] text-white border border-[#4A90D9]',
  delivered: 'bg-[#5A8F3B] text-white border border-[#5A8F3B]',
  collected: 'bg-[#7B68EE] text-white border border-[#7B68EE]',
};

const statusLabels = {
  warehouse: 'In Warehouse',
  staged: 'Ready to Load',
  loaded: 'Loaded',
  in_transit: 'In Transit',
  arrived: 'Awaiting Collection',
  delivered: 'Delivered',
  collected: 'Collected',
};

const sortOptions = [
  { value: 'created_at-desc', label: 'Date Added (Newest)' },
  { value: 'created_at-asc', label: 'Date Added (Oldest)' },
  { value: 'total_weight-desc', label: 'Weight (High to Low)' },
  { value: 'total_weight-asc', label: 'Weight (Low to High)' },
  { value: 'destination-asc', label: 'Destination A-Z' },
];

const getInitials = (name) => {
  if (!name) return '?';
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
};

export function Warehouse() {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Data state
  const [parcels, setParcels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  
  // Warehouse state
  const [warehouses, setWarehouses] = useState([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState('all');
  
  // Duplicate detection state
  const [duplicates, setDuplicates] = useState(new Set());
  const [showDuplicatesOnly, setShowDuplicatesOnly] = useState(false);
  
  // Uninvoiced filter state
  const [uninvoicedOnly, setUninvoicedOnly] = useState(false);
  
  // Select all state
  const [selectAllMatching, setSelectAllMatching] = useState(false);
  const [showSelectAllBanner, setShowSelectAllBanner] = useState(false);
  
  // Filter options
  const [filterOptions, setFilterOptions] = useState({
    destinations: [],
    clients: [],
    trips: [],
    statuses: []
  });
  
  // Current filters
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('created_at-desc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [tripFilter, setTripFilter] = useState('all');
  
  // Active filters
  const [activeFilters, setActiveFilters] = useState({
    status: [],
    destination: null,
    client_id: null,
    trip_id: null,
    date_from: null,
    date_to: null,
    weight_min: null,
    weight_max: null,
  });
  
  // Filter panel state
  const [filterPanelOpen, setFilterPanelOpen] = useState(false);
  const [clientSearchOpen, setClientSearchOpen] = useState(false);
  
  // Selection state
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [selectAll, setSelectAll] = useState(false);
  
  // Detail modal state
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('details');
  
  // Bulk action dialogs
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [tripDialogOpen, setTripDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [bulkStatus, setBulkStatus] = useState('');
  const [bulkTripId, setBulkTripId] = useState('');
  const [bulkLoading, setBulkLoading] = useState(false);
  
  // Available trips for assignment
  const [availableTrips, setAvailableTrips] = useState([]);
  
  // Photo upload state
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [photoViewerOpen, setPhotoViewerOpen] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const fileInputRef = useRef(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightParcelId, setHighlightParcelId] = useState(null);
  
  // Refresh state
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  
  // Collection scanner state
  const [collectionBarcode, setCollectionBarcode] = useState('');
  const [collectionScanning, setCollectionScanning] = useState(false);
  const collectionBarcodeRef = useRef(null);
  
  // Session G: Collection mode state
  const [collectionMode, setCollectionMode] = useState(false);
  const [collectionCheckData, setCollectionCheckData] = useState(null);
  const [collectionDialogOpen, setCollectionDialogOpen] = useState(false);
  const [collectingParcelId, setCollectingParcelId] = useState(null);
  const [collectingLoading, setCollectingLoading] = useState(false);

  // Initialize with user's default warehouse
  useEffect(() => {
    if (user?.default_warehouse) {
      setSelectedWarehouse(user.default_warehouse);
    }
  }, [user]);

  // Handle URL highlight param - auto-open parcel details
  useEffect(() => {
    const highlightId = searchParams.get('highlight');
    if (highlightId && parcels.length > 0) {
      setHighlightParcelId(highlightId);
      
      // Find the parcel and open its detail modal
      const parcelToHighlight = parcels.find(p => p.id === highlightId);
      if (parcelToHighlight) {
        // Scroll to the parcel row
        setTimeout(() => {
          const row = document.querySelector(`[data-parcel-id="${highlightId}"]`);
          if (row) {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
          // Open the detail modal
          openDetailModal(parcelToHighlight);
          
          // Clear the URL param after 2 seconds
          setTimeout(() => {
            setHighlightParcelId(null);
            setSearchParams(new URLSearchParams());
          }, 2000);
        }, 300);
      }
    }
  }, [searchParams, parcels]);

  useEffect(() => {
    fetchFilterOptions();
    fetchTrips();
    fetchWarehouses();
  }, []);

  useEffect(() => {
    fetchParcels();
  }, [search, sortBy, page, pageSize, activeFilters, tripFilter, selectedWarehouse]);

  // Auto-refresh every 60 seconds when page is visible
  useEffect(() => {
    let intervalId;
    
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !refreshing && !loading) {
        // Refresh when tab becomes visible if it's been more than 30 seconds
        const timeSinceRefresh = Date.now() - lastRefresh.getTime();
        if (timeSinceRefresh > 30000) {
          fetchParcels(true);
        }
      }
    };
    
    // Set up auto-refresh interval (60 seconds)
    intervalId = setInterval(() => {
      if (document.visibilityState === 'visible' && !refreshing && !loading) {
        fetchParcels(true);
      }
    }, 60000);
    
    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [lastRefresh, refreshing, loading]);

  const fetchFilterOptions = async () => {
    try {
      const response = await axios.get(`${API}/warehouse/filters`, { withCredentials: true });
      setFilterOptions(response.data);
    } catch (error) {
      console.error('Failed to fetch filter options');
    }
  };

  const fetchTrips = async () => {
    try {
      const response = await axios.get(`${API}/trips`, { withCredentials: true });
      // Filter to only open trips and ensure each has a valid id
      const validTrips = response.data.filter(t => 
        !['closed', 'delivered'].includes(t.status) && t.id
      );
      console.log('Available trips for assignment:', validTrips);
      setAvailableTrips(validTrips);
    } catch (error) {
      console.error('Failed to fetch trips');
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

  // Find duplicates based on description, weight, and client_id
  const findDuplicates = useCallback(() => {
    const seen = new Map();
    const duplicateIds = new Set();
    
    parcels.forEach(parcel => {
      const key = `${parcel.description?.toLowerCase().trim()}-${parcel.total_weight}-${parcel.client_id}`;
      if (seen.has(key)) {
        duplicateIds.add(parcel.id);
        duplicateIds.add(seen.get(key));
      } else {
        seen.set(key, parcel.id);
      }
    });
    
    setDuplicates(duplicateIds);
    
    if (duplicateIds.size > 0) {
      toast.warning(`Found ${duplicateIds.size} potential duplicate parcels`, {
        description: 'Highlighted in yellow. Same description, weight, and client.'
      });
    } else {
      toast.success('No duplicates found');
    }
  }, [parcels]);

  const fetchParcels = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      const [sortField, sortOrder] = sortBy.split('-');
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortField,
        sort_order: sortOrder,
        _t: Date.now().toString() // Cache buster
      });
      
      if (search) params.append('search', search);
      if (activeFilters.status.length > 0) params.append('status', activeFilters.status.join(','));
      if (activeFilters.destination) params.append('destination', activeFilters.destination);
      if (activeFilters.client_id) params.append('client_id', activeFilters.client_id);
      // Use tripFilter if set, otherwise use activeFilters.trip_id
      if (tripFilter && tripFilter !== 'all') {
        params.append('trip_id', tripFilter);
      } else if (activeFilters.trip_id) {
        params.append('trip_id', activeFilters.trip_id);
      }
      if (activeFilters.date_from) params.append('date_from', activeFilters.date_from);
      if (activeFilters.date_to) params.append('date_to', activeFilters.date_to);
      if (activeFilters.weight_min !== null) params.append('weight_min', activeFilters.weight_min.toString());
      if (activeFilters.weight_max !== null) params.append('weight_max', activeFilters.weight_max.toString());
      
      // Add warehouse filter
      if (selectedWarehouse && selectedWarehouse !== 'all') {
        params.append('warehouse_id', selectedWarehouse);
      }
      
      // Add uninvoiced filter
      if (uninvoicedOnly) {
        params.append('not_invoiced', 'true');
      }
      
      const response = await axios.get(`${API}/warehouse/parcels?${params}`, { withCredentials: true });
      setParcels(response.data.items);
      setTotalCount(response.data.total);
      setTotalPages(response.data.total_pages);
      setLastRefresh(new Date());
    } catch (error) {
      toast.error('Failed to fetch parcels');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchParcelDetail = async (parcelId) => {
    setDetailLoading(true);
    try {
      const response = await axios.get(`${API}/warehouse/parcels/${parcelId}`, { withCredentials: true });
      setSelectedParcel(response.data);
    } catch (error) {
      toast.error('Failed to fetch parcel details');
    } finally {
      setDetailLoading(false);
    }
  };

  const openDetailModal = (parcel) => {
    setSelectedParcel(parcel);
    setDetailModalOpen(true);
    setActiveTab('details');
    fetchParcelDetail(parcel.id);
  };

  const handleSelectAll = (checked) => {
    setSelectAll(checked);
    if (checked) {
      setSelectedIds(new Set(parcels.map(p => p.id)));
      // Show banner to select all matching parcels
      if (totalCount > parcels.length) {
        setShowSelectAllBanner(true);
      }
    } else {
      setSelectedIds(new Set());
      setShowSelectAllBanner(false);
      setSelectAllMatching(false);
    }
  };

  const handleSelectOne = (parcelId, checked) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(parcelId);
    } else {
      newSelected.delete(parcelId);
    }
    setSelectedIds(newSelected);
    setSelectAll(newSelected.size === parcels.length && parcels.length > 0);
  };

  const selectAllMatchingParcels = async () => {
    try {
      const [sortField, sortOrder] = sortBy.split('-');
      const params = new URLSearchParams({
        page_size: '9999',
        sort_by: sortField,
        sort_order: sortOrder,
      });
      
      if (search) params.append('search', search);
      if (activeFilters.status.length > 0) params.append('status', activeFilters.status.join(','));
      if (activeFilters.destination) params.append('destination', activeFilters.destination);
      if (activeFilters.client_id) params.append('client_id', activeFilters.client_id);
      if (tripFilter && tripFilter !== 'all') {
        params.append('trip_id', tripFilter);
      } else if (activeFilters.trip_id) {
        params.append('trip_id', activeFilters.trip_id);
      }
      if (activeFilters.date_from) params.append('date_from', activeFilters.date_from);
      if (activeFilters.date_to) params.append('date_to', activeFilters.date_to);
      if (activeFilters.weight_min !== null) params.append('weight_min', activeFilters.weight_min.toString());
      if (activeFilters.weight_max !== null) params.append('weight_max', activeFilters.weight_max.toString());
      if (selectedWarehouse && selectedWarehouse !== 'all') {
        params.append('warehouse_id', selectedWarehouse);
      }
      if (uninvoicedOnly) {
        params.append('not_invoiced', 'true');
      }
      
      const response = await axios.get(`${API}/warehouse/parcels?${params}`, { withCredentials: true });
      const allIds = response.data.items.map(p => p.id);
      setSelectedIds(new Set(allIds));
      setSelectAllMatching(true);
      setShowSelectAllBanner(false);
      toast.success(`Selected all ${allIds.length} matching parcels`);
    } catch (error) {
      toast.error('Failed to fetch all matching parcels');
    }
  };


  const clearSelection = () => {
    setSelectedIds(new Set());
    setSelectAll(false);
  };

  // Filter management
  const addFilter = (key, value) => {
    if (key === 'status') {
      const newStatus = [...activeFilters.status];
      if (!newStatus.includes(value)) {
        newStatus.push(value);
        setActiveFilters({ ...activeFilters, status: newStatus });
      }
    } else {
      setActiveFilters({ ...activeFilters, [key]: value });
    }
    setPage(1);
  };

  const removeFilter = (key, value = null) => {
    if (key === 'status' && value) {
      setActiveFilters({
        ...activeFilters,
        status: activeFilters.status.filter(s => s !== value)
      });
    } else {
      setActiveFilters({ ...activeFilters, [key]: key === 'status' ? [] : null });
    }
    setPage(1);
  };

  const clearAllFilters = () => {
    setActiveFilters({
      status: [],
      destination: null,
      client_id: null,
      trip_id: null,
      date_from: null,
      date_to: null,
      weight_min: null,
      weight_max: null,
    });
    setPage(1);
  };

  const activeFilterCount = useMemo(() => {
    let count = activeFilters.status.length;
    if (activeFilters.destination) count++;
    if (activeFilters.client_id) count++;
    if (activeFilters.trip_id) count++;
    if (activeFilters.date_from) count++;
    if (activeFilters.date_to) count++;
    if (activeFilters.weight_min !== null) count++;
    if (activeFilters.weight_max !== null) count++;
    return count;
  }, [activeFilters]);

  // Bulk actions
  const handleBulkStatusChange = async () => {
    if (!bulkStatus) return;
    setBulkLoading(true);
    try {
      await axios.put(`${API}/warehouse/parcels/bulk-status`, {
        parcel_ids: Array.from(selectedIds),
        status: bulkStatus
      }, { withCredentials: true });
      toast.success(`${selectedIds.size} parcels status updated`);
      setStatusDialogOpen(false);
      clearSelection();
      fetchParcels();
    } catch (error) {
      toast.error('Failed to update status');
    } finally {
      setBulkLoading(false);
    }
  };

  const handleBulkAssignTrip = async () => {
    setBulkLoading(true);
    try {
      // If "unassign" is selected, send null to remove trip assignment
      const tripIdToAssign = bulkTripId === 'unassign' ? null : bulkTripId;
      const selectedTrip = availableTrips.find(t => t.id === tripIdToAssign);
      const count = selectedIds.size;
      
      await axios.put(`${API}/warehouse/parcels/bulk-assign-trip`, {
        parcel_ids: Array.from(selectedIds),
        trip_id: tripIdToAssign
      }, { withCredentials: true });
      
      // Success - close modal and show toast
      setTripDialogOpen(false);
      setBulkTripId('');
      clearSelection();
      
      if (tripIdToAssign && selectedTrip) {
        toast.success(`✓ ${count} parcel(s) assigned to ${selectedTrip.trip_number}`);
      } else {
        toast.success(`✓ ${count} parcel(s) unassigned from trip`);
      }
      
      // Refresh table (separate try-catch so it doesn't trigger error toast)
      try {
        await fetchParcels();
      } catch (e) {
        console.error('Failed to refresh parcels after assignment');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign to trip');
    } finally {
      setBulkLoading(false);
    }
  };

  const handleBulkDelete = async () => {
    setBulkLoading(true);
    try {
      await axios.delete(`${API}/warehouse/parcels/bulk-delete`, {
        data: { parcel_ids: Array.from(selectedIds) },
        withCredentials: true
      });
      toast.success(`${selectedIds.size} parcels deleted`);
      setDeleteDialogOpen(false);
      clearSelection();
      fetchParcels();
    } catch (error) {
      toast.error('Failed to delete parcels');
    } finally {
      setBulkLoading(false);
    }
  };

  const handleBulkPrint = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      toast.error('No parcels selected');
      return;
    }
    try {
      const response = await axios.post(`${API}/warehouse/labels/pdf`, {
        shipment_ids: ids
      }, { withCredentials: true, responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `warehouse_labels_${ids.length}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
      toast.success(`${ids.length} label${ids.length > 1 ? 's' : ''} downloaded`);
    } catch {
      toast.error('Failed to generate labels PDF');
    }
  };

  const handleExportExcel = () => {
    const params = new URLSearchParams();
    if (selectedWarehouse !== 'all') params.append('warehouse_id', selectedWarehouse);
    if (activeFilters.length > 0) params.append('status', activeFilters.join(','));
    if (searchQuery) params.append('search', searchQuery);
    window.open(`${API}/warehouse/export/excel?${params.toString()}`, '_blank');
  };

  const handleSingleDelete = async (parcelId) => {
    if (!window.confirm('Are you sure you want to delete this parcel?')) return;
    try {
      await axios.delete(`${API}/shipments/${parcelId}`, { withCredentials: true });
      toast.success('Parcel deleted');
      fetchParcels();
      if (selectedParcel?.id === parcelId) {
        setDetailModalOpen(false);
      }
    } catch (error) {
      toast.error('Failed to delete parcel');
    }
  };

  const handlePrintSingle = (parcelId) => {
    console.log('Print label for:', parcelId);
    toast.success('1 label ready to print');
  };

  // Handle parcel verification
  const handleVerifyParcel = async (parcelId, verified) => {
    try {
      await axios.put(`${API}/shipments/${parcelId}/verify`, { verified }, { withCredentials: true });
      toast.success(verified ? 'Parcel verified' : 'Verification removed');
      fetchParcels();
    } catch (error) {
      toast.error('Failed to update verification');
    }
  };

  // Handle marking parcels as collected
  const handleMarkCollected = async () => {
    if (selectedIds.size === 0) return;
    setBulkLoading(true);
    try {
      await axios.put(`${API}/warehouse/parcels/bulk-collect`, {
        parcel_ids: Array.from(selectedIds)
      }, { withCredentials: true });
      toast.success(`${selectedIds.size} parcel(s) marked as collected`);
      clearSelection();
      fetchParcels();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark as collected');
    } finally {
      setBulkLoading(false);
    }
  };

  // Handle collection barcode scan
  const handleCollectionScan = async () => {
    if (!collectionBarcode.trim()) return;
    
    setCollectionScanning(true);
    try {
      const response = await axios.post(`${API}/warehouse/scan-collect`, {
        barcode: collectionBarcode.trim()
      }, { withCredentials: true });
      
      toast.success(
        <div>
          <div className="font-medium">Parcel Collected</div>
          <div className="text-sm text-muted-foreground">
            {response.data.parcel_id?.slice(0, 8).toUpperCase()} - {response.data.client_name}
          </div>
        </div>
      );
      fetchParcels();
    } catch (error) {
      console.error('Collection scan error:', error);
      toast.error(error.response?.data?.detail || 'Failed to collect parcel');
    } finally {
      setCollectionScanning(false);
      setCollectionBarcode('');
      collectionBarcodeRef.current?.focus();
    }
  };

  const handleCollectionKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleCollectionScan();
    }
  };

  // SESSION G: Collection check before collecting
  const handleCollectionCheck = async (parcelId) => {
    setCollectingParcelId(parcelId);
    try {
      const response = await axios.get(`${API}/warehouse/parcels/${parcelId}/collection-check`, { withCredentials: true });
      setCollectionCheckData(response.data);
      
      // If paid and no warning, collect immediately
      if (!response.data.requires_confirmation && response.data.can_collect) {
        await handleCollectionConfirm('', parcelId);
        return;
      }
      
      setCollectionDialogOpen(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to check collection eligibility');
    }
  };

  // SESSION G: Confirm collection (with optional note)
  const handleCollectionConfirm = async (note, overrideParcelId) => {
    const pid = overrideParcelId || collectingParcelId;
    if (!pid) return;
    
    setCollectingLoading(true);
    try {
      const response = await axios.post(`${API}/warehouse/parcels/${pid}/collect`, {
        confirmation_note: note
      }, { withCredentials: true });
      
      if (response.data.admin_notified) {
        toast.warning('Parcel collected. Admin has been notified about outstanding payment.');
      } else {
        toast.success('Parcel collected successfully');
      }
      
      setCollectionDialogOpen(false);
      setCollectionCheckData(null);
      setCollectingParcelId(null);
      fetchParcels();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to collect parcel');
    } finally {
      setCollectingLoading(false);
    }
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !selectedParcel) return;
    
    setUploadingPhoto(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await axios.post(
        `${API}/warehouse/parcels/${selectedParcel.id}/photos`,
        formData,
        { 
          withCredentials: true,
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      
      toast.success('Photo uploaded successfully');
      // Refresh parcel details to show new photo
      fetchParcelDetail(selectedParcel.id);
    } catch (error) {
      toast.error('Failed to upload photo');
    } finally {
      setUploadingPhoto(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeletePhoto = async (pieceId) => {
    if (!selectedParcel) return;
    
    try {
      await axios.delete(
        `${API}/warehouse/parcels/${selectedParcel.id}/photos/${pieceId}`,
        { withCredentials: true }
      );
      
      toast.success('Photo deleted');
      fetchParcelDetail(selectedParcel.id);
    } catch (error) {
      toast.error('Failed to delete photo');
    }
  };

  const openPhotoViewer = (photo, piece) => {
    setSelectedPhoto({ url: photo, piece });
    setPhotoViewerOpen(true);
  };

  const formatDate = (dateStr) => {
    try {
      return format(new Date(dateStr), 'MMM d, yyyy');
    } catch {
      return dateStr;
    }
  };

  const getClientName = (clientId) => {
    const client = filterOptions.clients.find(c => c.id === clientId);
    return client?.name || 'Unknown';
  };

  const getWarehouseName = () => {
    if (selectedWarehouse === 'all') return 'All Warehouses';
    const warehouse = warehouses.find(w => w.id === selectedWarehouse);
    return warehouse?.name || 'Unknown Warehouse';
  };

  // Get displayed parcels - filter duplicates if showDuplicatesOnly is true
  const displayedParcels = useMemo(() => {
    if (showDuplicatesOnly && duplicates.size > 0) {
      return parcels.filter(p => duplicates.has(p.id));
    }
    return parcels;
  }, [parcels, duplicates, showDuplicatesOnly]);

  return (
    <>
      <div className="space-y-4" data-testid="warehouse-page">
        {/* Header with Warehouse Name */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <WarehouseIcon className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="font-heading text-2xl sm:text-3xl font-bold" data-testid="warehouse-title">
                  {getWarehouseName()}
                </h1>
                <p className="text-muted-foreground text-sm">
                  {totalCount} parcel{totalCount !== 1 ? 's' : ''} 
                  {duplicates.size > 0 && (
                    <span className="ml-2 text-amber-600">
                      ({duplicates.size} potential duplicate{duplicates.size !== 1 ? 's' : ''})
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              onClick={() => fetchParcels(true)} 
              disabled={refreshing}
              data-testid="refresh-btn"
            >
              {refreshing ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Refresh
            </Button>
            <Button 
              variant="outline" 
              onClick={findDuplicates}
              data-testid="find-duplicates-btn"
            >
              <Copy className="h-4 w-4 mr-2" />
              Find Duplicates
            </Button>
            <Button 
              variant="outline" 
              onClick={handleExportExcel}
              data-testid="export-excel-btn"
            >
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              Export Excel
            </Button>
            <Button onClick={() => navigate('/parcels/intake')} data-testid="add-parcel-btn">
              <Package className="h-4 w-4 mr-2" />
              Add Parcel
            </Button>
          </div>
        </div>

        {/* Duplicates banner */}
        {duplicates.size > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-800">
              <AlertTriangle className="h-5 w-5" />
              <span className="font-medium">{duplicates.size} potential duplicates found</span>
              <span className="text-sm text-amber-600">Same description, weight, and client</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant={showDuplicatesOnly ? "default" : "outline"}
                size="sm"
                onClick={() => setShowDuplicatesOnly(!showDuplicatesOnly)}
                data-testid="toggle-duplicates-btn"
              >
                {showDuplicatesOnly ? 'Show All' : 'Show Only Duplicates'}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setDuplicates(new Set()); setShowDuplicatesOnly(false); }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Select All Matching Banner */}
        {showSelectAllBanner && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-blue-800">
              <span className="font-medium">
                Select all {totalCount} matching parcels in inventory?
              </span>
              <Button
                variant="link"
                className="text-blue-700 underline p-0 h-auto font-medium"
                onClick={selectAllMatchingParcels}
              >
                Yes, select all
              </Button>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setShowSelectAllBanner(false); handleSelectAll(false); }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Collection Scanner */}
        <Card className="bg-[#3C3F42] border-[#6B633C]">
          <CardContent className="py-4 px-4">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
              <div className="flex-1 min-w-[280px]">
                <Label className="text-sm font-medium mb-2 block text-white">
                  Scan Parcel for Collection
                </Label>
                <div className="flex gap-2">
                  <Input
                    ref={collectionBarcodeRef}
                    value={collectionBarcode}
                    onChange={(e) => setCollectionBarcode(e.target.value)}
                    onKeyPress={handleCollectionKeyPress}
                    placeholder="Scan barcode or enter parcel ID..."
                    disabled={collectionScanning}
                    className="flex-1 bg-white"
                    data-testid="collection-barcode-input"
                  />
                  <Button 
                    onClick={handleCollectionScan} 
                    disabled={!collectionBarcode.trim() || collectionScanning}
                    className="bg-[#6B633C] hover:bg-[#5A5432] text-white"
                    data-testid="collection-scan-btn"
                  >
                    {collectionScanning ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ScanLine className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-white/70 mt-1">
                  Only parcels with "Arrived" status can be collected. Collected parcels are removed from warehouse inventory.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Filter Bar */}
        <Card>
          <CardContent className="py-3 px-4">
            <div className="flex flex-wrap gap-2 items-center">
              {/* Search */}
              <div className="relative flex-1 min-w-[180px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search parcels or client name..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  className="pl-9 h-9"
                  data-testid="warehouse-search-input"
                />
              </div>

              {/* Warehouse dropdown */}
              <Select value={selectedWarehouse} onValueChange={setSelectedWarehouse}>
                <SelectTrigger className="w-[150px] h-9" data-testid="warehouse-select">
                  <WarehouseIcon className="h-4 w-4 mr-1" />
                  <SelectValue placeholder="Warehouse" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Warehouses</SelectItem>
                  {warehouses.map(w => (
                    <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Client filter dropdown */}
              <Select 
                value={activeFilters.client_id || 'all'} 
                onValueChange={(v) => {
                  if (v === 'all') {
                    removeFilter('client_id');
                  } else {
                    addFilter('client_id', v);
                  }
                }}
              >
                <SelectTrigger className="w-[150px] h-9" data-testid="client-filter-select">
                  <SelectValue placeholder="Client" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Clients</SelectItem>
                  {filterOptions.clients.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Trip filter dropdown */}
              <Select value={tripFilter} onValueChange={(v) => { setTripFilter(v); setPage(1); }}>
                <SelectTrigger className="w-[150px] h-9" data-testid="trip-filter-select">
                  <Truck className="h-4 w-4 mr-1" />
                  <SelectValue placeholder="Trip" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Trips</SelectItem>
                  <SelectItem value="unassigned">Unassigned</SelectItem>
                  {availableTrips.map(trip => (
                    <SelectItem key={trip.id} value={trip.id}>
                      {trip.trip_number} ({trip.status})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Uninvoiced Only Toggle */}
              <Button
                variant={uninvoicedOnly ? "default" : "outline"}
                onClick={() => { setUninvoicedOnly(!uninvoicedOnly); setPage(1); }}
                className="h-9 text-sm"
                data-testid="uninvoiced-toggle-btn"
              >
                Uninvoiced
              </Button>

              {/* Sort */}
              <Select value={sortBy} onValueChange={(v) => { setSortBy(v); setPage(1); }}>
                <SelectTrigger className="w-[170px] h-9" data-testid="sort-select">
                  <ArrowUpDown className="h-4 w-4 mr-1" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {sortOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Add Filter button */}
              <Button
                variant="outline"
                onClick={() => setFilterPanelOpen(true)}
                className="gap-1 h-9 shrink-0"
                data-testid="add-filter-btn"
              >
                <Filter className="h-4 w-4" />
                Filters
                {activeFilterCount > 0 && (
                  <Badge className="ml-1 h-5 w-5 p-0 flex items-center justify-center rounded-full">
                    {activeFilterCount}
                  </Badge>
                )}
              </Button>

              {/* Session G: Collection Mode Toggle */}
              <Button
                variant={collectionMode ? "default" : "outline"}
                onClick={() => {
                  setCollectionMode(!collectionMode);
                  if (!collectionMode) {
                    // When entering collection mode, filter to 'arrived' status
                    addFilter('status', 'arrived');
                    toast.info('Collection mode ON - showing arrived parcels');
                  } else {
                    removeFilter('status', 'arrived');
                    toast.info('Collection mode OFF');
                  }
                }}
                className={cn("gap-1 h-9 shrink-0", collectionMode && "bg-purple-600 hover:bg-purple-700")}
                data-testid="collection-mode-btn"
              >
                <ScanLine className="h-4 w-4" />
                {collectionMode ? 'Exit Collection' : 'Collection Mode'}
              </Button>
            </div>

            {/* Active filter badges */}
            {activeFilterCount > 0 && (
              <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t">
                {activeFilters.status.map(s => (
                  <Badge key={s} variant="secondary" className="gap-1 pr-1">
                    Status: {statusLabels[s] || s}
                    <button onClick={() => removeFilter('status', s)} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
                {activeFilters.destination && (
                  <Badge variant="secondary" className="gap-1 pr-1">
                    Destination: {activeFilters.destination}
                    <button onClick={() => removeFilter('destination')} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {activeFilters.client_id && (
                  <Badge variant="secondary" className="gap-1 pr-1">
                    Client: {getClientName(activeFilters.client_id)}
                    <button onClick={() => removeFilter('client_id')} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {activeFilters.trip_id && (
                  <Badge variant="secondary" className="gap-1 pr-1">
                    Trip: {activeFilters.trip_id === 'unassigned' ? 'Unassigned' : filterOptions.trips.find(t => t.id === activeFilters.trip_id)?.trip_number || activeFilters.trip_id}
                    <button onClick={() => removeFilter('trip_id')} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {activeFilters.date_from && (
                  <Badge variant="secondary" className="gap-1 pr-1">
                    From: {activeFilters.date_from}
                    <button onClick={() => removeFilter('date_from')} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {activeFilters.date_to && (
                  <Badge variant="secondary" className="gap-1 pr-1">
                    To: {activeFilters.date_to}
                    <button onClick={() => removeFilter('date_to')} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {activeFilters.weight_min !== null && (
                  <Badge variant="secondary" className="gap-1 pr-1">
                    Min Weight: {activeFilters.weight_min}kg
                    <button onClick={() => removeFilter('weight_min')} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                {activeFilters.weight_max !== null && (
                  <Badge variant="secondary" className="gap-1 pr-1">
                    Max Weight: {activeFilters.weight_max}kg
                    <button onClick={() => removeFilter('weight_max')} className="ml-1 hover:bg-muted rounded-full p-0.5">
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                )}
                <button 
                  onClick={clearAllFilters}
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  Clear all
                </button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Main Table */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3, 4, 5].map(i => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : displayedParcels.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="w-[40px]">
                        <Checkbox
                          checked={selectAll}
                          onCheckedChange={handleSelectAll}
                          data-testid="select-all-checkbox"
                        />
                      </TableHead>
                      <TableHead>Parcel #</TableHead>
                      <TableHead className="hidden sm:table-cell">Date In</TableHead>
                      <TableHead>Client</TableHead>
                      <TableHead className="hidden md:table-cell max-w-[200px]">Description</TableHead>
                      <TableHead className="hidden lg:table-cell">Pieces</TableHead>
                      <TableHead className="text-right">Weight</TableHead>
                      <TableHead className="hidden md:table-cell">Destination</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="hidden lg:table-cell">Trip</TableHead>
                      <TableHead className="hidden lg:table-cell">Invoice</TableHead>
                      <TableHead className="hidden lg:table-cell">Inv Status</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayedParcels.map((parcel) => (
                      <TableRow 
                        key={parcel.id} 
                        className={cn(
                          selectedIds.has(parcel.id) && "bg-primary/5",
                          duplicates.has(parcel.id) && "bg-amber-50 border-l-4 border-l-amber-400",
                          highlightParcelId === parcel.id && "animate-highlight-flash bg-amber-100"
                        )}
                        data-testid={`parcel-row-${parcel.id}`}
                        data-parcel-id={parcel.id}
                      >
                        <TableCell>
                          <Checkbox
                            checked={selectedIds.has(parcel.id)}
                            onCheckedChange={(checked) => handleSelectOne(parcel.id, checked)}
                            data-testid={`select-checkbox-${parcel.id}`}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <div className="flex items-center gap-1">
                              {duplicates.has(parcel.id) && (
                                <Copy className="h-3 w-3 text-amber-600" title="Potential duplicate" />
                              )}
                              <button
                                onClick={() => openDetailModal(parcel)}
                                className="font-mono text-sm text-primary hover:underline font-medium"
                                data-testid={`parcel-id-${parcel.id}`}
                              >
                                {parcel.id.slice(0, 8).toUpperCase()}
                              </button>
                            </div>
                            {parcel.parcel_sequence && parcel.total_in_sequence && (
                              <span className="text-xs text-muted-foreground">
                                {parcel.parcel_sequence} of {parcel.total_in_sequence}
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                          {formatDate(parcel.created_at)}
                        </TableCell>
                        <TableCell className="font-medium">{parcel.client_name}</TableCell>
                        <TableCell className="hidden md:table-cell max-w-[200px]">
                          <span className="line-clamp-1 text-sm text-muted-foreground" title={parcel.description}>
                            {parcel.description}
                          </span>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          <span className="text-sm">
                            {parcel.total_pieces} piece{parcel.total_pieces !== 1 ? 's' : ''}
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {parcel.total_weight.toFixed(1)} kg
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-sm">{parcel.destination}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Badge className={cn('text-xs capitalize', statusColors[parcel.status])}>
                              {statusLabels[parcel.status] || parcel.status}
                            </Badge>
                            {collectionMode && parcel.status === 'arrived' && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-6 px-2 text-xs bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100"
                                onClick={(e) => { e.stopPropagation(); handleCollectionCheck(parcel.id); }}
                              >
                                <Check className="h-3 w-3 mr-1" />
                                Collect
                              </Button>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          {parcel.trip_number ? (
                            <span className="font-mono text-sm text-primary">{parcel.trip_number}</span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          {parcel.invoice_number ? (
                            <span className="font-mono text-sm text-primary">{parcel.invoice_number}</span>
                          ) : (
                            <Badge variant="outline" className="text-xs text-amber-600 border-amber-300 bg-amber-50">
                              Not Invoiced
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          {parcel.invoice_status ? (
                            <Badge className={cn('text-xs capitalize', 
                              parcel.invoice_status === 'paid' && 'bg-green-100 text-green-700 border-green-300',
                              parcel.invoice_status === 'sent' && 'bg-blue-100 text-blue-700 border-blue-300',
                              parcel.invoice_status === 'draft' && 'bg-gray-100 text-gray-700 border-gray-300',
                              parcel.invoice_status === 'overdue' && 'bg-red-100 text-red-700 border-red-300'
                            )}>
                              {parcel.invoice_status}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8" data-testid={`parcel-menu-${parcel.id}`}>
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openDetailModal(parcel)}>
                                <Eye className="h-4 w-4 mr-2" />
                                View
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openDetailModal(parcel)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handlePrintSingle(parcel.id)}>
                                <Printer className="h-4 w-4 mr-2" />
                                Print Label
                              </DropdownMenuItem>
                              {parcel.status === 'arrived' && (
                                <DropdownMenuItem onClick={() => handleCollectionCheck(parcel.id)}>
                                  <Check className="h-4 w-4 mr-2" />
                                  Collect Parcel
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              <DropdownMenuItem 
                                onClick={() => handleSingleDelete(parcel.id)}
                                className="text-destructive"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="text-center py-16 text-muted-foreground">
                <Package className="h-16 w-16 mx-auto mb-4 opacity-30" />
                <p className="text-lg font-medium">No parcels in warehouse</p>
                <p className="text-sm mt-1">Add your first parcel to get started</p>
                <Button
                  onClick={() => navigate('/parcels/intake')}
                  className="mt-4"
                  data-testid="empty-add-parcel-btn"
                >
                  Add Parcel
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, totalCount)} of {totalCount}
            </div>
            <div className="flex items-center gap-2">
              <Select value={pageSize.toString()} onValueChange={(v) => { setPageSize(parseInt(v)); setPage(1); }}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10 / page</SelectItem>
                  <SelectItem value="25">25 / page</SelectItem>
                  <SelectItem value="50">50 / page</SelectItem>
                  <SelectItem value="100">100 / page</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm px-2">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Floating Action Bar */}
        {selectedIds.size > 0 && (
          <div 
            className="fixed bottom-0 left-0 right-0 h-[72px] bg-gray-900 dark:bg-gray-800 border-t shadow-lg z-50 flex items-center justify-between px-6"
            data-testid="floating-action-bar"
          >
            <div className="flex items-center gap-4">
              <span className="text-white font-medium">
                {selectedIds.size} parcel{selectedIds.size > 1 ? 's' : ''} selected
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={() => setTripDialogOpen(true)}
                data-testid="bulk-assign-trip-btn"
              >
                <Truck className="h-4 w-4 mr-2" />
                Assign to Trip
              </Button>
              <Button
                variant="secondary"
                onClick={handleBulkPrint}
                data-testid="bulk-print-btn"
              >
                <Printer className="h-4 w-4 mr-2" />
                Bulk Print Labels
              </Button>
              <Button
                variant="secondary"
                onClick={() => setStatusDialogOpen(true)}
                data-testid="bulk-status-btn"
              >
                <Edit className="h-4 w-4 mr-2" />
                Change Status
              </Button>
              <Button
                variant="secondary"
                onClick={handleMarkCollected}
                disabled={bulkLoading}
                data-testid="bulk-collect-btn"
              >
                <Check className="h-4 w-4 mr-2" />
                Mark Collected
              </Button>
              <Button
                variant="destructive"
                onClick={() => setDeleteDialogOpen(true)}
                data-testid="bulk-delete-btn"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Selected
              </Button>
              <Button
                variant="outline"
                onClick={clearSelection}
                className="text-white border-white/30 hover:bg-white/10"
                data-testid="cancel-selection-btn"
              >
                Cancel Selection
              </Button>
            </div>
          </div>
        )}

        {/* Filter Panel Dialog */}
        <Dialog open={filterPanelOpen} onOpenChange={setFilterPanelOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Filter Parcels</DialogTitle>
            </DialogHeader>
            <div className="space-y-6 py-4">
              {/* Status checkboxes */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Status</Label>
                <div className="grid grid-cols-2 gap-2">
                  {['warehouse', 'staged', 'loaded', 'in_transit', 'arrived', 'delivered', 'collected'].map(status => (
                    <div key={status} className="flex items-center gap-2">
                      <Checkbox
                        id={`filter-status-${status}`}
                        checked={activeFilters.status.includes(status)}
                        onCheckedChange={(checked) => {
                          if (checked) addFilter('status', status);
                          else removeFilter('status', status);
                        }}
                      />
                      <label htmlFor={`filter-status-${status}`} className="text-sm capitalize cursor-pointer">
                        {statusLabels[status]}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Destination dropdown */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Destination</Label>
                <Select
                  value={activeFilters.destination || '__any__'}
                  onValueChange={(v) => addFilter('destination', v === '__any__' ? null : v)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Any destination" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__any__">Any destination</SelectItem>
                    {filterOptions.destinations.map(d => (
                      <SelectItem key={d} value={d}>{d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Client autocomplete */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Client</Label>
                <Popover open={clientSearchOpen} onOpenChange={setClientSearchOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      className="w-full justify-between font-normal"
                    >
                      {activeFilters.client_id
                        ? getClientName(activeFilters.client_id)
                        : "Any client"}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-full p-0">
                    <Command>
                      <CommandInput placeholder="Search clients..." />
                      <CommandList>
                        <CommandEmpty>No client found.</CommandEmpty>
                        <CommandGroup>
                          <CommandItem onSelect={() => { addFilter('client_id', null); setClientSearchOpen(false); }}>
                            <Check className={cn("mr-2 h-4 w-4", !activeFilters.client_id ? "opacity-100" : "opacity-0")} />
                            Any client
                          </CommandItem>
                          {filterOptions.clients.map(client => (
                            <CommandItem
                              key={client.id}
                              value={client.name}
                              onSelect={() => { addFilter('client_id', client.id); setClientSearchOpen(false); }}
                            >
                              <Check className={cn("mr-2 h-4 w-4", activeFilters.client_id === client.id ? "opacity-100" : "opacity-0")} />
                              {client.name}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>

              {/* Date range */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Date Range</Label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Input
                      type="date"
                      value={activeFilters.date_from || ''}
                      onChange={(e) => addFilter('date_from', e.target.value || null)}
                      placeholder="From"
                    />
                  </div>
                  <div>
                    <Input
                      type="date"
                      value={activeFilters.date_to || ''}
                      onChange={(e) => addFilter('date_to', e.target.value || null)}
                      placeholder="To"
                    />
                  </div>
                </div>
              </div>

              {/* Weight range */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Weight Range (kg)</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    value={activeFilters.weight_min ?? ''}
                    onChange={(e) => addFilter('weight_min', e.target.value ? parseFloat(e.target.value) : null)}
                    placeholder="Min"
                  />
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    value={activeFilters.weight_max ?? ''}
                    onChange={(e) => addFilter('weight_max', e.target.value ? parseFloat(e.target.value) : null)}
                    placeholder="Max"
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={clearAllFilters}>
                Clear All
              </Button>
              <Button onClick={() => setFilterPanelOpen(false)}>
                Apply Filters
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Detail Modal */}
        <Dialog open={detailModalOpen} onOpenChange={setDetailModalOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Parcel {selectedParcel?.id?.slice(0, 8).toUpperCase()}
              </DialogTitle>
            </DialogHeader>
            
            {detailLoading ? (
              <div className="space-y-4 py-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : selectedParcel ? (
              <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="history">History</TabsTrigger>
                  <TabsTrigger value="photos">Photos</TabsTrigger>
                </TabsList>
                
                <div className="flex-1 overflow-y-auto mt-4">
                  <TabsContent value="details" className="m-0 space-y-4">
                    {/* Status badge and edit */}
                    <div className="flex items-center justify-between">
                      <Badge className={cn('text-sm', statusColors[selectedParcel.status])}>
                        {statusLabels[selectedParcel.status]}
                      </Badge>
                      <Select
                        value={selectedParcel.status}
                        onValueChange={async (newStatus) => {
                          try {
                            await axios.put(`${API}/shipments/${selectedParcel.id}`, { status: newStatus }, { withCredentials: true });
                            toast.success('Status updated');
                            setSelectedParcel({ ...selectedParcel, status: newStatus });
                            fetchParcels();
                          } catch (error) {
                            toast.error('Failed to update status');
                          }
                        }}
                      >
                        <SelectTrigger className="w-[150px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(statusLabels).map(([key, label]) => (
                            <SelectItem key={key} value={key}>{label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Basic info grid */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">Client</p>
                        <p className="font-medium">{selectedParcel.client?.name || selectedParcel.client_name}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Destination</p>
                        <p className="font-medium">{selectedParcel.destination}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Date Added</p>
                        <p className="font-medium">{formatDate(selectedParcel.created_at)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Added By</p>
                        <p className="font-medium">{selectedParcel.staff?.name || selectedParcel.staff_name}</p>
                      </div>
                    </div>

                    <div>
                      <p className="text-sm text-muted-foreground">Description</p>
                      <p className="font-medium">{selectedParcel.description}</p>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">Pieces</p>
                        <p className="font-mono font-semibold">{selectedParcel.total_pieces}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Weight</p>
                        <p className="font-mono font-semibold">{selectedParcel.total_weight} kg</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">CBM</p>
                        <p className="font-mono font-semibold">{selectedParcel.total_cbm || '-'}</p>
                      </div>
                    </div>

                    {/* Trip info */}
                    {selectedParcel.trip && (
                      <div className="p-3 bg-muted/50 rounded-lg">
                        <p className="text-sm text-muted-foreground mb-1">Assigned to Trip</p>
                        <p className="font-mono font-medium text-primary">{selectedParcel.trip.trip_number}</p>
                      </div>
                    )}

                    {/* Pieces table */}
                    {selectedParcel.pieces && selectedParcel.pieces.length > 0 && (
                      <div className="border rounded-lg">
                        <div className="p-3 border-b bg-muted/50">
                          <p className="font-medium">Pieces ({selectedParcel.pieces.length})</p>
                        </div>
                        <div className="divide-y">
                          {selectedParcel.pieces.map((piece, idx) => (
                            <div key={piece.id || idx} className="p-3 flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="h-8 w-8 rounded bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                                  #{piece.piece_number}
                                </div>
                                <div>
                                  <p className="font-mono text-sm">{piece.barcode}</p>
                                  <p className="text-xs text-muted-foreground">{piece.weight} kg</p>
                                </div>
                              </div>
                              {piece.loaded_at && <Badge className="bg-green-100 text-green-700">Loaded</Badge>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="history" className="m-0">
                    <AuditHistory tableName="shipments" recordId={selectedParcel.id} />
                  </TabsContent>
                  
                  <TabsContent value="photos" className="m-0 space-y-4">
                    {/* Hidden file input */}
                    <input
                      type="file"
                      ref={fileInputRef}
                      className="hidden"
                      accept="image/*"
                      onChange={handlePhotoUpload}
                    />
                    
                    {/* Photo gallery */}
                    {selectedParcel.pieces?.some(p => p.photo_url) ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-3 gap-3">
                          {selectedParcel.pieces.filter(p => p.photo_url).map((piece, idx) => (
                            <div 
                              key={piece.id || idx} 
                              className="relative group aspect-square rounded-lg overflow-hidden bg-muted"
                            >
                              <img
                                src={piece.photo_url}
                                alt={`Piece ${piece.piece_number}`}
                                className="w-full h-full object-cover cursor-pointer"
                                onClick={() => openPhotoViewer(piece.photo_url, piece)}
                              />
                              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                <Button
                                  size="icon"
                                  variant="secondary"
                                  className="h-8 w-8"
                                  onClick={() => openPhotoViewer(piece.photo_url, piece)}
                                >
                                  <ZoomIn className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="icon"
                                  variant="destructive"
                                  className="h-8 w-8"
                                  onClick={() => handleDeletePhoto(piece.id)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                              <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1">
                                <p className="text-white text-xs font-mono">#{piece.piece_number}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                        
                        {/* Upload more button */}
                        <div className="flex justify-center">
                          <Button
                            variant="outline"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploadingPhoto}
                          >
                            {uploadingPhoto ? (
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                              <Upload className="h-4 w-4 mr-2" />
                            )}
                            {uploadingPhoto ? 'Uploading...' : 'Upload More Photos'}
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-12 text-muted-foreground">
                        <ImageIcon className="h-12 w-12 mx-auto mb-3 opacity-30" />
                        <p>No photos available</p>
                        <Button
                          variant="outline"
                          className="mt-4"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploadingPhoto}
                        >
                          {uploadingPhoto ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Upload className="h-4 w-4 mr-2" />
                          )}
                          {uploadingPhoto ? 'Uploading...' : 'Upload Photos'}
                        </Button>
                      </div>
                    )}
                  </TabsContent>
                </div>
              </Tabs>
            ) : null}
            
            <DialogFooter className="mt-4">
              <Button variant="outline" onClick={() => handlePrintSingle(selectedParcel?.id)}>
                <Printer className="h-4 w-4 mr-2" />
                Print Label
              </Button>
              <Button variant="outline" onClick={() => setDetailModalOpen(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Bulk Status Change Dialog */}
        <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Change Status for {selectedIds.size} parcels</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <Label className="mb-2 block">New Status</Label>
              <Select value={bulkStatus} onValueChange={setBulkStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(statusLabels).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setStatusDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleBulkStatusChange} disabled={!bulkStatus || bulkLoading}>
                {bulkLoading ? 'Updating...' : 'Update Status'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Bulk Assign Trip Dialog */}
        <Dialog open={tripDialogOpen} onOpenChange={setTripDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Assign {selectedIds.size} parcels to Trip</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <Label className="mb-2 block">Select Trip</Label>
              <Select value={bulkTripId} onValueChange={setBulkTripId}>
                <SelectTrigger data-testid="trip-select-dropdown">
                  <SelectValue placeholder="Select trip" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unassign">Unassign from trip</SelectItem>
                  {availableTrips.map(trip => (
                    <SelectItem key={trip.id} value={trip.id}>
                      {trip.trip_number} ({trip.status})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setTripDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleBulkAssignTrip} disabled={bulkLoading}>
                {bulkLoading ? 'Assigning...' : 'Assign to Trip'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Bulk Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete {selectedIds.size} parcels?</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <p className="text-muted-foreground">
                This action cannot be undone. All selected parcels and their pieces will be permanently deleted.
              </p>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
              <Button variant="destructive" onClick={handleBulkDelete} disabled={bulkLoading}>
                {bulkLoading ? 'Deleting...' : 'Delete Parcels'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Photo Viewer Dialog */}
        <Dialog open={photoViewerOpen} onOpenChange={setPhotoViewerOpen}>
          <DialogContent className="max-w-3xl p-2">
            {selectedPhoto && (
              <div className="space-y-2">
                <img
                  src={selectedPhoto.url}
                  alt={`Piece ${selectedPhoto.piece?.piece_number}`}
                  className="w-full h-auto rounded-lg"
                />
                <div className="flex items-center justify-between px-2 py-1">
                  <span className="text-sm text-muted-foreground">
                    Piece #{selectedPhoto.piece?.piece_number} - {selectedPhoto.piece?.weight} kg
                  </span>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => {
                      handleDeletePhoto(selectedPhoto.piece?.id);
                      setPhotoViewerOpen(false);
                    }}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Photo
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Session G: Collection Warning Dialog */}
        <CollectionWarningDialog
          open={collectionDialogOpen}
          onOpenChange={setCollectionDialogOpen}
          checkData={collectionCheckData}
          onConfirm={handleCollectionConfirm}
          loading={collectingLoading}
        />
      </div>
    </>
  );
}
