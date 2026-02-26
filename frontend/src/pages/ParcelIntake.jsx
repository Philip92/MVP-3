import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '../components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
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
import { toast } from 'sonner';
import { 
  Package, Camera, Plus, Trash2, Printer, Check, ChevronsUpDown,
  MoreVertical, Eye, Tag, FileText, Upload, Image as ImageIcon, X, Save,
  AlertTriangle, XCircle, UserPlus, Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';
import { format } from 'date-fns';

const API = `${window.location.origin}/api`;

// Empty row template
const createEmptyRow = (rowNum) => ({
  id: `row-${Date.now()}-${rowNum}`,
  sender: '', // Sub-client or secondary sender
  description: '',
  qty: 1,
  weight: '',
  length: '',
  width: '',
  height: '',
  volume: 0,
  volumetricWeight: 0,
  photos: [],
  documents: [],
  saved: false,
  shipmentId: null,
  barcode: null,
  // New recipient fields
  recipient_phone: '',
  recipient_vat: '',
  shipping_address: ''
});

// Calculate volumetric weight: (L x W x H) / 5000
const calculateVolumetricWeight = (l, w, h) => {
  const length = parseFloat(l) || 0;
  const width = parseFloat(w) || 0;
  const height = parseFloat(h) || 0;
  if (length === 0 || width === 0 || height === 0) return 0;
  return (length * width * height) / 5000;
};

// Calculate chargeable weight: MAX(actual weight, volumetric weight)
const calculateChargeableWeight = (actualWeight, volumetricWeight) => {
  const actual = parseFloat(actualWeight) || 0;
  const volumetric = parseFloat(volumetricWeight) || 0;
  return Math.max(actual, volumetric);
};

export function ParcelIntake() {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Sticky fields (persist after save)
  const [selectedClient, setSelectedClient] = useState(null);
  const [recipient, setRecipient] = useState('');
  const [selectedTrip, setSelectedTrip] = useState(null);
  
  // Data
  const [clients, setClients] = useState([]);
  const [trips, setTrips] = useState([]);
  const [rows, setRows] = useState([createEmptyRow(1), createEmptyRow(2), createEmptyRow(3)]);
  
  // UI State
  const [clientOpen, setClientOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [photoDialogOpen, setPhotoDialogOpen] = useState(false);
  const [documentDialogOpen, setDocumentDialogOpen] = useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [uploadsDialogOpen, setUploadsDialogOpen] = useState(false);
  const [activeRowId, setActiveRowId] = useState(null);
  const [previewType, setPreviewType] = useState('barcode'); // 'barcode' or 'label'
  
  // Add Client Modal State
  const [addClientModalOpen, setAddClientModalOpen] = useState(false);
  const [newClientData, setNewClientData] = useState({
    name: '',
    phone: '',
    whatsapp: '',
    email: '',
    default_currency: 'ZAR',
    rate_type: 'per_kg',
    rate_value: ''
  });
  const [addingClient, setAddingClient] = useState(false);
  
  // Add Recipient Modal State
  const [addRecipientModalOpen, setAddRecipientModalOpen] = useState(false);
  const [newRecipientData, setNewRecipientData] = useState({
    name: '',
    phone: '',
    whatsapp: '',
    email: '',
    vat_number: '',
    shipping_address: ''
  });
  const [addingRecipient, setAddingRecipient] = useState(false);
  const [recipients, setRecipients] = useState([]);
  
  // Invoice Assignment State
  const [addToInvoice, setAddToInvoice] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [invoiceSearchOpen, setInvoiceSearchOpen] = useState(false);
  const [invoiceSearchQuery, setInvoiceSearchQuery] = useState('');
  const [creatingInvoice, setCreatingInvoice] = useState(false);
  
  // Unsaved data warning
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState(null);
  const [showClearDialog, setShowClearDialog] = useState(false);
  
  // Refs for keyboard navigation
  const inputRefs = useRef({});
  const fileInputRef = useRef(null);
  const docInputRef = useRef(null);

  // Fetch clients and trips
  useEffect(() => {
    fetchClients();
    fetchTrips();
    fetchRecipients();
  }, []);

  // Fetch invoices when client changes
  useEffect(() => {
    if (selectedClient && addToInvoice) {
      fetchInvoices();
    }
  }, [selectedClient, addToInvoice]);

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/clients`, { withCredentials: true });
      setClients(response.data);
    } catch (error) {
      console.error('Failed to fetch clients');
    }
  };

  const fetchTrips = async () => {
    try {
      const response = await axios.get(`${API}/trips`, { withCredentials: true });
      // Filter to only open trips
      setTrips(response.data.filter(t => !['closed', 'delivered'].includes(t.status)));
    } catch (error) {
      console.error('Failed to fetch trips');
    }
  };

  const fetchRecipients = async () => {
    try {
      const response = await axios.get(`${API}/recipients`, { withCredentials: true });
      setRecipients(response.data);
    } catch (error) {
      console.error('Failed to fetch recipients');
    }
  };

  const fetchInvoices = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedClient) params.append('client_id', selectedClient.id);
      if (invoiceSearchQuery) params.append('q', invoiceSearchQuery);
      params.append('status', 'draft'); // Only show draft invoices for assignment
      
      const response = await axios.get(`${API}/invoices/search?${params}`, { withCredentials: true });
      setInvoices(response.data);
    } catch (error) {
      console.error('Failed to fetch invoices');
    }
  };

  const handleCreateNewInvoice = async () => {
    if (!selectedClient) {
      toast.error('Select a client first');
      return;
    }
    
    setCreatingInvoice(true);
    try {
      const response = await axios.post(`${API}/invoices-enhanced`, {
        client_id: selectedClient.id,
        trip_id: selectedTrip?.id || null,
        currency: selectedClient.default_currency || 'ZAR',
        line_items: [],
        adjustments: [],
        status: 'draft'
      }, { withCredentials: true });
      
      const newInvoice = response.data;
      setSelectedInvoice({
        id: newInvoice.id,
        invoice_number: newInvoice.invoice_number,
        client_name: selectedClient.name,
        status: 'draft'
      });
      setInvoiceSearchOpen(false);
      toast.success(`Created invoice ${newInvoice.invoice_number}`);
      fetchInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create invoice');
    } finally {
      setCreatingInvoice(false);
    }
  };

  const handleAddRecipient = async () => {
    if (!newRecipientData.name.trim()) {
      toast.error('Recipient name is required');
      return;
    }
    setAddingRecipient(true);
    try {
      const response = await axios.post(`${API}/recipients`, newRecipientData, { withCredentials: true });
      const newRecipient = response.data;
      setRecipients([...recipients, newRecipient]);
      // Auto-fill recipient field
      setRecipient(newRecipient.name);
      setAddRecipientModalOpen(false);
      setNewRecipientData({ name: '', phone: '', whatsapp: '', email: '', vat_number: '', shipping_address: '' });
      toast.success(`Recipient "${newRecipient.name}" added`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add recipient');
    } finally {
      setAddingRecipient(false);
    }
  };

  // Check if there's unsaved data
  const hasUnsavedData = useCallback(() => {
    return rows.some(r => r.description.trim() !== '');
  }, [rows]);

  // Get count of unsaved parcels
  const unsavedCount = rows.filter(r => r.description.trim() !== '').length;

  // Clear all rows
  const handleClearAll = () => {
    if (hasUnsavedData()) {
      setShowClearDialog(true);
    }
  };

  const confirmClearAll = () => {
    setRows([createEmptyRow(1), createEmptyRow(2), createEmptyRow(3)]);
    setShowClearDialog(false);
    toast.success('All rows cleared');
    // Focus first description field
    setTimeout(() => {
      const newRows = [createEmptyRow(1), createEmptyRow(2), createEmptyRow(3)];
      if (inputRefs.current[`${newRows[0]?.id}-description`]) {
        inputRefs.current[`${newRows[0].id}-description`].focus();
      }
    }, 100);
  };

  // Handle navigation with unsaved data warning
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasUnsavedData()) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedData]);

  // Block navigation within app when there's unsaved data
  useEffect(() => {
    const handleNavigation = (e) => {
      // Check if clicking a navigation link
      const target = e.target.closest('a[href]');
      if (target && hasUnsavedData()) {
        const href = target.getAttribute('href');
        if (href && href !== location.pathname && !href.startsWith('http')) {
          e.preventDefault();
          setPendingNavigation(href);
          setShowUnsavedDialog(true);
        }
      }
    };

    document.addEventListener('click', handleNavigation, true);
    return () => document.removeEventListener('click', handleNavigation, true);
  }, [hasUnsavedData, location.pathname]);

  const handleSaveAndNavigate = async () => {
    await handleSaveAll();
    setShowUnsavedDialog(false);
    if (pendingNavigation) {
      navigate(pendingNavigation);
      setPendingNavigation(null);
    }
  };

  const handleDiscardAndNavigate = () => {
    setShowUnsavedDialog(false);
    if (pendingNavigation) {
      navigate(pendingNavigation);
      setPendingNavigation(null);
    }
  };

  const handleCancelNavigation = () => {
    setShowUnsavedDialog(false);
    setPendingNavigation(null);
  };

  // Calculate volume and Volumetric Weight
  const calculateVolume = (l, w, h) => {
    const length = parseFloat(l) || 0;
    const width = parseFloat(w) || 0;
    const height = parseFloat(h) || 0;
    return length * width * height;
  };

  // Update row field
  const updateRow = (rowId, field, value) => {
    setRows(prev => prev.map(row => {
      if (row.id !== rowId) return row;
      
      const updated = { ...row, [field]: value };
      
      // Auto-calculate volume and volumetric weight when dimensions change
      if (['length', 'width', 'height'].includes(field)) {
        const l = field === 'length' ? value : row.length;
        const w = field === 'width' ? value : row.width;
        const h = field === 'height' ? value : row.height;
        updated.volume = calculateVolume(l, w, h);
        updated.volumetricWeight = calculateVolumetricWeight(l, w, h);
      }
      
      return updated;
    }));
  };

  // Handle adding a new client
  const handleAddClient = async () => {
    if (!newClientData.name.trim()) {
      toast.error('Client name is required');
      return;
    }
    
    setAddingClient(true);
    try {
      const payload = {
        name: newClientData.name.trim(),
        phone: newClientData.phone.trim() || null,
        whatsapp: newClientData.whatsapp.trim() || null,
        email: newClientData.email.trim() || null,
        default_currency: newClientData.default_currency,
        default_rate_type: newClientData.rate_type,
        default_rate_value: parseFloat(newClientData.rate_value) || 0,
        status: 'active'
      };
      
      const response = await axios.post(`${API}/clients`, payload, { withCredentials: true });
      const newClient = response.data;
      
      // Add to clients list and select it
      setClients(prev => [...prev, newClient]);
      setSelectedClient(newClient);
      
      // Reset form and close modal
      setNewClientData({
        name: '',
        phone: '',
        whatsapp: '',
        email: '',
        default_currency: 'ZAR',
        rate_type: 'per_kg',
        rate_value: ''
      });
      setAddClientModalOpen(false);
      
      toast.success(`Client "${newClient.name}" created and selected`);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to create client';
      toast.error(errorMessage);
    } finally {
      setAddingClient(false);
    }
  };

  // Add new row
  const addRow = useCallback(() => {
    if (rows.length >= 50) {
      toast.error('Maximum 50 rows allowed');
      return;
    }
    const newRow = createEmptyRow(rows.length + 1);
    setRows(prev => [...prev, newRow]);
    
    // Focus on description of new row after render
    setTimeout(() => {
      const key = `${newRow.id}-description`;
      if (inputRefs.current[key]) {
        inputRefs.current[key].focus();
      }
    }, 50);
  }, [rows.length]);

  // Delete row
  const deleteRow = (rowId) => {
    if (rows.length <= 1) {
      // Reset the row instead of deleting
      setRows([createEmptyRow(1)]);
      return;
    }
    setRows(prev => prev.filter(row => row.id !== rowId));
  };

  // Handle keyboard navigation
  const handleKeyDown = (e, rowId, field) => {
    const fieldOrder = ['sender', 'description', 'qty', 'weight', 'length', 'width', 'height'];
    const currentFieldIndex = fieldOrder.indexOf(field);
    const currentRowIndex = rows.findIndex(r => r.id === rowId);
    
    if (e.key === 'Tab' && !e.shiftKey) {
      // Tab forward
      if (field === 'height') {
        // Skip to camera button or next row
        e.preventDefault();
        if (currentRowIndex === rows.length - 1) {
          // Last row - add new row
          addRow();
        } else {
          // Go to next row's sender field
          const nextRow = rows[currentRowIndex + 1];
          const key = `${nextRow.id}-sender`;
          if (inputRefs.current[key]) {
            inputRefs.current[key].focus();
          }
        }
      }
    } else if (e.key === 'Tab' && e.shiftKey) {
      // Tab backward
      if (field === 'sender' && currentRowIndex > 0) {
        e.preventDefault();
        const prevRow = rows[currentRowIndex - 1];
        const key = `${prevRow.id}-height`;
        if (inputRefs.current[key]) {
          inputRefs.current[key].focus();
        }
      }
    } else if (e.key === 'Enter') {
      // Move to next field
      e.preventDefault();
      const nextFieldIndex = currentFieldIndex + 1;
      if (nextFieldIndex < fieldOrder.length) {
        const key = `${rowId}-${fieldOrder[nextFieldIndex]}`;
        if (inputRefs.current[key]) {
          inputRefs.current[key].focus();
        }
      } else if (currentRowIndex < rows.length - 1) {
        const nextRow = rows[currentRowIndex + 1];
        const key = `${nextRow.id}-description`;
        if (inputRefs.current[key]) {
          inputRefs.current[key].focus();
        }
      } else {
        addRow();
      }
    }
  };

  // Ctrl+S to save
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSaveAll();
      }
      if (e.key === 'Escape') {
        setPhotoDialogOpen(false);
        setDocumentDialogOpen(false);
        setPreviewDialogOpen(false);
        setUploadsDialogOpen(false);
      }
    };
    
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [rows, selectedClient, selectedTrip, recipient]);

  // Handle photo upload
  const handlePhotoUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!activeRowId) return;
    
    const row = rows.find(r => r.id === activeRowId);
    if (!row) return;
    
    if (row.photos.length + files.length > 10) {
      toast.error('Maximum 10 photos per parcel');
      return;
    }
    
    // Convert files to base64 for preview
    const newPhotos = await Promise.all(files.map(async (file) => {
      return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve({
          id: `photo-${Date.now()}-${Math.random()}`,
          name: file.name,
          data: e.target.result,
          file: file
        });
        reader.readAsDataURL(file);
      });
    }));
    
    updateRow(activeRowId, 'photos', [...row.photos, ...newPhotos]);
    toast.success(`Added ${files.length} photo(s)`);
    setPhotoDialogOpen(false);
  };

  // Handle document upload
  const handleDocumentUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!activeRowId) return;
    
    const row = rows.find(r => r.id === activeRowId);
    if (!row) return;
    
    if (row.documents.length + files.length > 5) {
      toast.error('Maximum 5 documents per parcel');
      return;
    }
    
    const newDocs = files.map(file => ({
      id: `doc-${Date.now()}-${Math.random()}`,
      name: file.name,
      file: file
    }));
    
    updateRow(activeRowId, 'documents', [...row.documents, ...newDocs]);
    toast.success(`Added ${files.length} document(s)`);
    setDocumentDialogOpen(false);
  };

  // Remove photo
  const removePhoto = (rowId, photoId) => {
    const row = rows.find(r => r.id === rowId);
    if (row) {
      updateRow(rowId, 'photos', row.photos.filter(p => p.id !== photoId));
    }
  };

  // Remove document
  const removeDocument = (rowId, docId) => {
    const row = rows.find(r => r.id === rowId);
    if (row) {
      updateRow(rowId, 'documents', row.documents.filter(d => d.id !== docId));
    }
  };

  // Save all parcels
  const handleSaveAll = async () => {
    // Validation - Client is required
    if (!selectedClient) {
      toast.error('Please select a client before saving.', {
        description: 'Use the "Select Client" dropdown or click "+ Add Client" to create a new one.',
        duration: 5000
      });
      return;
    }
    
    const validRows = rows.filter(r => r.description.trim() !== '' && !r.saved);
    if (validRows.length === 0) {
      toast.error('Please add at least one parcel with a description');
      return;
    }
    
    for (const row of validRows) {
      if (!row.qty || row.qty < 1) {
        toast.error('Each parcel must have quantity of at least 1');
        return;
      }
      if (!row.weight || parseFloat(row.weight) <= 0) {
        toast.error('Each parcel must have a weight greater than 0 kg');
        return;
      }
    }
    
    setSaving(true);
    
    try {
      const createdParcels = [];
      const totalParcels = validRows.reduce((sum, r) => sum + (parseInt(r.qty) || 1), 0);
      let parcelSeq = 0;
      
      for (const row of validRows) {
        const rowWeight = parseFloat(row.weight) || 0;
        const qty = parseInt(row.qty) || 1;
        
        try {
          // For batches (qty > 1), create multiple shipments with sequencing
          for (let i = 0; i < qty; i++) {
            parcelSeq++;
            
            // Get recipient info from recipients list if recipient selected
            const recipientData = recipients.find(r => r.name === recipient);
            
            // Create shipment with dimensions and invoice link
            const shipmentPayload = {
              client_id: selectedClient.id,
              recipient: recipient || null,
              recipient_phone: recipientData?.phone || row.recipient_phone || null,
              recipient_vat: recipientData?.vat_number || row.recipient_vat || null,
              shipping_address: recipientData?.shipping_address || row.shipping_address || null,
              sender: row.sender || selectedClient.name,
              description: row.description,
              quantity: 1, // Each piece is its own shipment
              total_weight: rowWeight / qty, // Divide weight among pieces
              destination: selectedTrip?.route?.[selectedTrip.route.length - 1] || 'TBD',
              trip_id: selectedTrip?.id || null,
              invoice_id: addToInvoice && selectedInvoice ? selectedInvoice.id : null,
              status: selectedTrip ? 'staged' : 'warehouse',
              // Dimensions
              length_cm: parseFloat(row.length) || null,
              width_cm: parseFloat(row.width) || null,
              height_cm: parseFloat(row.height) || null
            };
            
            // Add sequencing for batches
            if (qty > 1) {
              shipmentPayload.parcel_sequence = i + 1;
              shipmentPayload.total_in_sequence = qty;
            }
            
            const shipmentResponse = await axios.post(`${API}/shipments`, shipmentPayload, { withCredentials: true });
            const shipment = shipmentResponse.data;
            
            // Create piece with dimensions
            const piecePayload = {
              shipment_id: shipment.id,
              piece_number: 1,
              weight: rowWeight / qty,
              length_cm: parseFloat(row.length) || 0,
              width_cm: parseFloat(row.width) || 0,
              height_cm: parseFloat(row.height) || 0
            };
            
            await axios.post(`${API}/shipments/${shipment.id}/pieces`, piecePayload, { withCredentials: true });
            
            // Only upload photos to the first piece of a batch
            if (i === 0 && row.photos.length > 0) {
              for (const photo of row.photos) {
                if (photo.file) {
                  const formData = new FormData();
                  formData.append('file', photo.file);
                  try {
                    await axios.post(`${API}/warehouse/parcels/${shipment.id}/photos`, formData, {
                      withCredentials: true,
                      headers: { 'Content-Type': 'multipart/form-data' }
                    });
                  } catch (e) {
                    console.error('Photo upload failed:', e);
                  }
                }
              }
            }
            
            createdParcels.push(shipment);
          }
          
          // Mark this row as saved to prevent duplicates on retry
          updateRow(row.id, 'saved', true);
          updateRow(row.id, 'shipmentId', createdParcels[createdParcels.length - 1]?.id);
          updateRow(row.id, 'barcode', createdParcels[createdParcels.length - 1]?.barcode);
          
        } catch (rowError) {
          console.error(`Failed to save row ${row.description}:`, rowError);
          throw rowError;
        }
      }
      
      // Success message
      let message = `✓ ${createdParcels.length} parcel(s) created`;
      if (selectedTrip) message += ` and assigned to Trip ${selectedTrip.trip_number}`;
      if (addToInvoice && selectedInvoice) message += ` and added to ${selectedInvoice.invoice_number}`;
      toast.success(message);
      
      // Reset table but keep sticky fields
      setRows([createEmptyRow(1), createEmptyRow(2), createEmptyRow(3)]);
      
      // Focus first description field
      setTimeout(() => {
        const firstRow = rows[0];
        if (firstRow && inputRefs.current[`${firstRow.id}-description`]) {
          inputRefs.current[`${firstRow.id}-description`].focus();
        }
      }, 100);
      
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      let errorMessage = 'Failed to save parcels';
      
      if (typeof errorDetail === 'string') {
        errorMessage = errorDetail;
      } else if (Array.isArray(errorDetail)) {
        // Pydantic validation error
        errorMessage = errorDetail.map(e => `${e.loc?.join('.')}: ${e.msg}`).join(', ');
      } else if (errorDetail?.msg) {
        errorMessage = errorDetail.msg;
      }
      
      toast.error(errorMessage);
      console.error('Save error:', error);
    } finally {
      setSaving(false);
    }
  };

  // Open action dialogs
  const openPhotoDialog = (rowId) => {
    setActiveRowId(rowId);
    setPhotoDialogOpen(true);
  };

  // Save All & Print Labels - saves parcels then downloads labels PDF
  const handleSaveAllAndPrint = async () => {
    await handleSaveAll();
    // After save, get the saved shipment IDs and download labels
    const savedRows = rows.filter(r => r.saved && r.shipmentId);
    if (savedRows.length > 0) {
      try {
        const shipmentIds = savedRows.map(r => r.shipmentId);
        const response = await axios.post(
          `${API}/warehouse/labels/pdf`,
          { shipment_ids: shipmentIds },
          { withCredentials: true, responseType: 'blob' }
        );
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        // Open in new tab for printing
        window.open(url, '_blank');
        toast.success('Labels PDF opened for printing');
      } catch (error) {
        toast.error('Parcels saved but label generation failed');
      }
    }
  };

  const openDocumentDialog = (rowId) => {
    setActiveRowId(rowId);
    setDocumentDialogOpen(true);
  };

  const openUploadsDialog = (rowId) => {
    setActiveRowId(rowId);
    setUploadsDialogOpen(true);
  };

  const openPreview = (rowId, type) => {
    setActiveRowId(rowId);
    setPreviewType(type);
    setPreviewDialogOpen(true);
  };

  const activeRow = rows.find(r => r.id === activeRowId);
  const today = format(new Date(), 'yyyy-MM-dd');

  return (
    <>
      <div className="flex flex-col h-[calc(100vh-64px)]" data-testid="parcel-intake-page">
        {/* TOP SECTION - Compact */}
        <div className="px-4 py-3 bg-white border-b">
          {/* Header */}
          <div className="mb-2">
            <h1 className="text-xl font-bold text-[#3C3F42] flex items-center gap-2">
              <Package className="h-5 w-5 text-[#6B633C]" />
              Parcel Intake (Table View)
            </h1>
            <p className="text-gray-500 text-xs mt-0.5">
              Quick bulk parcel registration with keyboard shortcuts • <span className="text-[#6B633C]">Ctrl+S to save</span>
            </p>
          </div>

          {/* Three dropdowns */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Client/Sender */}
            <div>
              <Label className="text-sm font-medium">Select Client/Sender *</Label>
              <div className="flex gap-2 mt-1">
                <Popover open={clientOpen} onOpenChange={setClientOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={clientOpen}
                      className="flex-1 justify-between"
                      data-testid="client-selector"
                    >
                      {selectedClient ? (
                        <span>{selectedClient.name} • {selectedClient.phone}</span>
                      ) : (
                        <span className="text-gray-400">Search clients...</span>
                      )}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[400px] p-0" align="start">
                    <Command>
                      <CommandInput placeholder="Search by name or phone..." />
                      <CommandList>
                        <CommandEmpty>No client found.</CommandEmpty>
                        <CommandGroup>
                          {clients.map((client) => (
                            <CommandItem
                              key={client.id}
                              value={`${client.name} ${client.phone}`}
                              onSelect={() => {
                                setSelectedClient(client);
                                setClientOpen(false);
                              }}
                            >
                              <Check
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  selectedClient?.id === client.id ? "opacity-100" : "opacity-0"
                                )}
                              />
                              <div className="flex flex-col">
                                <span className="font-medium">{client.name}</span>
                                <span className="text-xs text-gray-500">{client.phone}</span>
                              </div>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
                <Button
                  variant="outline"
                  size="icon"
                  className="shrink-0 border-[#6B633C] text-[#6B633C] hover:bg-[#6B633C]/10"
                  onClick={() => setAddClientModalOpen(true)}
                  title="Add New Client"
                  data-testid="add-client-btn"
                >
                  <UserPlus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Recipient */}
            <div>
              <Label className="text-sm font-medium">Recipient (if different)</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="Recipient name"
                  className="flex-1"
                  data-testid="recipient-input"
                />
                <Button
                  variant="outline"
                  size="icon"
                  className="shrink-0 border-[#6B633C] text-[#6B633C] hover:bg-[#6B633C]/10"
                  onClick={() => setAddRecipientModalOpen(true)}
                  title="Add New Recipient"
                  data-testid="add-recipient-btn"
                >
                  <UserPlus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Trip */}
            <div>
              <Label className="text-sm font-medium">Assign to Trip (optional)</Label>
              <Select
                value={selectedTrip?.id || 'none'}
                onValueChange={(v) => {
                  if (v === 'none') {
                    setSelectedTrip(null);
                  } else {
                    setSelectedTrip(trips.find(t => t.id === v) || null);
                  }
                }}
              >
                <SelectTrigger className="mt-1" data-testid="trip-selector">
                  <SelectValue placeholder="Select trip (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No trip selected</SelectItem>
                  {trips.map(trip => (
                    <SelectItem key={trip.id} value={trip.id}>
                      {trip.trip_number} - {trip.route?.join(' → ') || 'No route'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Invoice Assignment Row */}
          <div className="mt-2 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="addToInvoice"
                checked={addToInvoice}
                onChange={(e) => {
                  setAddToInvoice(e.target.checked);
                  if (!e.target.checked) {
                    setSelectedInvoice(null);
                  }
                }}
                className="h-4 w-4 rounded border-gray-300 text-[#6B633C] focus:ring-[#6B633C]"
                data-testid="add-to-invoice-toggle"
              />
              <Label htmlFor="addToInvoice" className="text-sm font-medium cursor-pointer">
                Add to Invoice
              </Label>
            </div>

            {addToInvoice && (
              <div className="flex items-center gap-2 flex-1">
                <Popover open={invoiceSearchOpen} onOpenChange={setInvoiceSearchOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      disabled={!selectedClient}
                      className="w-[300px] justify-between"
                      data-testid="invoice-selector"
                    >
                      {selectedInvoice ? (
                        <span className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-[#6B633C]" />
                          {selectedInvoice.invoice_number}
                          <Badge variant="outline" className="ml-2 text-xs">
                            {selectedInvoice.client_name}
                          </Badge>
                        </span>
                      ) : (
                        <span className="text-gray-400">
                          {selectedClient ? 'Select or create invoice...' : 'Select client first'}
                        </span>
                      )}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[350px] p-0" align="start">
                    <Command>
                      <CommandInput 
                        placeholder="Search by invoice # or client..." 
                        value={invoiceSearchQuery}
                        onValueChange={(v) => {
                          setInvoiceSearchQuery(v);
                          fetchInvoices();
                        }}
                      />
                      <CommandList>
                        <CommandEmpty>
                          <div className="p-2 text-center">
                            <p className="text-sm text-gray-500 mb-2">No invoices found</p>
                            <Button
                              size="sm"
                              onClick={handleCreateNewInvoice}
                              disabled={creatingInvoice}
                              className="bg-[#6B633C] hover:bg-[#5a5332]"
                            >
                              {creatingInvoice ? (
                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                              ) : (
                                <Plus className="h-4 w-4 mr-2" />
                              )}
                              Create New Invoice
                            </Button>
                          </div>
                        </CommandEmpty>
                        <CommandGroup heading="Draft Invoices">
                          {invoices.map((inv) => (
                            <CommandItem
                              key={inv.id}
                              value={`${inv.invoice_number} ${inv.client_name}`}
                              onSelect={() => {
                                setSelectedInvoice(inv);
                                setInvoiceSearchOpen(false);
                              }}
                            >
                              <Check
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  selectedInvoice?.id === inv.id ? "opacity-100" : "opacity-0"
                                )}
                              />
                              <div className="flex flex-col">
                                <span className="font-medium">{inv.invoice_number}</span>
                                <span className="text-xs text-gray-500">
                                  {inv.client_name} • R {(inv.total || 0).toFixed(2)}
                                </span>
                              </div>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                        <CommandGroup>
                          <CommandItem
                            onSelect={handleCreateNewInvoice}
                            className="border-t"
                          >
                            <Plus className="mr-2 h-4 w-4 text-[#6B633C]" />
                            <span className="text-[#6B633C] font-medium">Create New Invoice</span>
                          </CommandItem>
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>

                {selectedInvoice && (
                  <Badge className="bg-[#6B633C]/10 text-[#6B633C] border-[#6B633C]/20">
                    Will add parcels to {selectedInvoice.invoice_number}
                  </Badge>
                )}
              </div>
            )}
          </div>
        </div>

        {/* BOTTOM SECTION - Table */}
        <div className="flex-1 overflow-auto bg-[#f5f5f5] p-3">
          <Card className="bg-white h-full flex flex-col">
            <CardContent className="p-0 flex-1 overflow-auto">
              <div className="overflow-x-auto">
                <table className="w-full border-collapse" data-testid="parcel-table">
                  {/* Fixed header */}
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-[#6B633C] text-white text-xs">
                      <th className="px-2 py-2 text-left font-medium w-[80px]">Date</th>
                      <th className="px-2 py-2 text-center font-medium w-[40px]">No</th>
                      <th className="px-2 py-2 text-left font-medium w-[120px]">Sub-Client / Sender</th>
                      <th className="px-2 py-2 text-left font-medium min-w-[180px]">Description *</th>
                      <th className="px-2 py-2 text-right font-medium w-[70px]">Qty</th>
                      <th className="px-2 py-2 text-right font-medium w-[90px]">Weight (kg) *</th>
                      <th className="px-2 py-2 text-right font-medium w-[80px]">L (cm)</th>
                      <th className="px-2 py-2 text-right font-medium w-[80px]">W (cm)</th>
                      <th className="px-2 py-2 text-right font-medium w-[80px]">H (cm)</th>
                      <th className="px-2 py-2 text-right font-medium w-[80px]">Vol Wt</th>
                      <th className="px-2 py-2 text-right font-medium w-[90px]">Chargeable</th>
                      <th className="px-2 py-2 text-center font-medium w-[40px]">📷</th>
                      <th className="px-2 py-2 text-center font-medium w-[40px]">⋮</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, index) => (
                      <tr 
                        key={row.id}
                        className={cn(
                          "border-b border-gray-100 hover:bg-[#E8E4D0]/30 transition-colors",
                          index % 2 === 1 && "bg-gray-50/50"
                        )}
                        style={{ height: '40px' }}
                      >
                        {/* Date - Auto (darker) */}
                        <td className="px-2 py-1 text-xs text-gray-700 align-middle">{today}</td>
                        
                        {/* No - Auto (darker) */}
                        <td className="px-2 py-1 text-center text-xs text-gray-700 align-middle">{index + 1}</td>
                        
                        {/* Sender - INPUT (editable for sub-clients) */}
                        <td className="px-1.5 py-1 align-middle">
                          <Input
                            ref={(el) => inputRefs.current[`${row.id}-sender`] = el}
                            value={row.sender}
                            onChange={(e) => updateRow(row.id, 'sender', e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, row.id, 'sender')}
                            placeholder={selectedClient?.name || 'Sender name'}
                            className="h-8 text-xs border-gray-200 focus:border-[#6B633C] focus:ring-[#6B633C] placeholder:text-gray-400/40"
                            data-testid={`sender-${index}`}
                          />
                        </td>
                        
                        {/* Description - INPUT (lighter placeholder) */}
                        <td className="px-1.5 py-1 align-middle">
                          <Input
                            ref={(el) => inputRefs.current[`${row.id}-description`] = el}
                            value={row.description}
                            onChange={(e) => updateRow(row.id, 'description', e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, row.id, 'description')}
                            placeholder="e.g., Electronics, Wine, Clothing"
                            className="h-8 text-xs border-gray-200 focus:border-[#6B633C] focus:ring-[#6B633C] placeholder:text-gray-400/40"
                            data-testid={`description-${index}`}
                          />
                        </td>
                        
                        {/* Qty - INPUT */}
                        <td className="px-1.5 py-1 align-middle">
                          <Input
                            ref={(el) => inputRefs.current[`${row.id}-qty`] = el}
                            type="number"
                            min="1"
                            value={row.qty}
                            onChange={(e) => updateRow(row.id, 'qty', e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, row.id, 'qty')}
                            className="h-8 text-xs text-right border-gray-200 focus:border-[#6B633C] focus:ring-[#6B633C] w-full min-w-[70px]"
                            data-testid={`qty-${index}`}
                          />
                        </td>
                        
                        {/* Weight (Kg) - INPUT */}
                        <td className="px-1.5 py-1 align-middle">
                          <Input
                            ref={(el) => inputRefs.current[`${row.id}-weight`] = el}
                            type="number"
                            step="0.1"
                            min="0"
                            value={row.weight}
                            onChange={(e) => updateRow(row.id, 'weight', e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, row.id, 'weight')}
                            placeholder="0.0"
                            className="h-8 text-xs text-right border-gray-200 focus:border-[#6B633C] focus:ring-[#6B633C] placeholder:text-gray-400/40 w-full min-w-[80px]"
                            data-testid={`weight-${index}`}
                          />
                        </td>
                        
                        {/* Length - INPUT */}
                        <td className="px-1.5 py-1 align-middle">
                          <Input
                            ref={(el) => inputRefs.current[`${row.id}-length`] = el}
                            type="number"
                            value={row.length}
                            onChange={(e) => updateRow(row.id, 'length', e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, row.id, 'length')}
                            placeholder="0"
                            className="h-8 text-xs text-right border-gray-200 focus:border-[#6B633C] focus:ring-[#6B633C] w-full min-w-[80px]"
                            data-testid={`length-${index}`}
                          />
                        </td>
                        
                        {/* Width - INPUT */}
                        <td className="px-1.5 py-1 align-middle">
                          <Input
                            ref={(el) => inputRefs.current[`${row.id}-width`] = el}
                            type="number"
                            value={row.width}
                            onChange={(e) => updateRow(row.id, 'width', e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, row.id, 'width')}
                            placeholder="0"
                            className="h-8 text-xs text-right border-gray-200 focus:border-[#6B633C] focus:ring-[#6B633C] w-full min-w-[80px]"
                            data-testid={`width-${index}`}
                          />
                        </td>
                        
                        {/* Height - INPUT */}
                        <td className="px-1.5 py-1 align-middle">
                          <Input
                            ref={(el) => inputRefs.current[`${row.id}-height`] = el}
                            type="number"
                            value={row.height}
                            onChange={(e) => updateRow(row.id, 'height', e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, row.id, 'height')}
                            placeholder="0"
                            className="h-8 text-xs text-right border-gray-200 focus:border-[#6B633C] focus:ring-[#6B633C] w-full min-w-[80px]"
                            data-testid={`height-${index}`}
                          />
                        </td>
                        
                        {/* Volumetric Weight - CALC */}
                        <td className="px-2 py-1 text-right text-xs text-gray-400 italic align-middle">
                          {row.volumetricWeight > 0 ? row.volumetricWeight.toFixed(2) : '-'}
                        </td>
                        
                        {/* Chargeable Weight - CALC (max of actual vs volumetric) */}
                        <td className="px-2 py-1 text-right text-xs font-medium">
                          {(() => {
                            const chargeableWt = calculateChargeableWeight(row.weight, row.volumetricWeight);
                            if (chargeableWt === 0) return <span className="text-gray-400 italic">-</span>;
                            const isVolumetric = row.volumetricWeight > (parseFloat(row.weight) || 0);
                            return (
                              <span className={isVolumetric ? 'text-amber-600' : 'text-gray-700'}>
                                {chargeableWt.toFixed(2)} kg
                                {isVolumetric && <span className="text-xs ml-1">(V)</span>}
                              </span>
                            );
                          })()}
                        </td>
                        
                        {/* Camera button */}
                        <td className="px-1 py-0.5 text-center">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 relative"
                            onClick={() => openPhotoDialog(row.id)}
                            data-testid={`camera-${index}`}
                          >
                            <Camera className="h-4 w-4 text-gray-500" />
                            {row.photos.length > 0 && (
                              <Badge className="absolute -top-1 -right-1 h-4 w-4 p-0 text-[10px] bg-[#6B633C]">
                                {row.photos.length}
                              </Badge>
                            )}
                          </Button>
                        </td>
                        
                        {/* Action menu */}
                        <td className="px-1 py-0.5 text-center">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8" data-testid={`menu-${index}`}>
                                <MoreVertical className="h-4 w-4 text-gray-500" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openPreview(row.id, 'barcode')}>
                                <Eye className="h-4 w-4 mr-2" /> Preview Barcode
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openPreview(row.id, 'label')}>
                                <Tag className="h-4 w-4 mr-2" /> Preview Label
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={() => openPhotoDialog(row.id)}>
                                <Camera className="h-4 w-4 mr-2" /> Upload Photos
                                {row.photos.length > 0 && <Badge className="ml-auto">{row.photos.length}</Badge>}
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openDocumentDialog(row.id)}>
                                <FileText className="h-4 w-4 mr-2" /> Upload Documents
                                {row.documents.length > 0 && <Badge className="ml-auto">{row.documents.length}</Badge>}
                              </DropdownMenuItem>
                              {(row.photos.length > 0 || row.documents.length > 0) && (
                                <DropdownMenuItem onClick={() => openUploadsDialog(row.id)}>
                                  <ImageIcon className="h-4 w-4 mr-2" /> View Uploads
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              <DropdownMenuItem 
                                onClick={() => deleteRow(row.id)}
                                className="text-red-600 focus:text-red-600"
                              >
                                <Trash2 className="h-4 w-4 mr-2" /> Delete Row
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Add Row button */}
              <div className="p-3 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={addRow}
                  className="text-[#6B633C] border-[#6B633C] hover:bg-[#6B633C]/10"
                  data-testid="add-row-btn"
                >
                  <Plus className="h-4 w-4 mr-1" /> Add Row
                </Button>
                <span className="text-xs text-gray-400 ml-3">
                  Tab from last field to auto-add row • {rows.length}/50 rows
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Bottom action bar */}
        <div className="p-4 bg-white border-t flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              className="bg-[#6B633C] hover:bg-[#5a5332] text-white"
              onClick={handleSaveAllAndPrint}
              disabled={saving}
              data-testid="save-all-print-btn"
            >
              <Printer className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : `Save All & Print Labels (${rows.filter(r => r.description.trim()).length})`}
            </Button>
            
            <Button
              variant="outline"
              onClick={handleSaveAll}
              disabled={saving}
              data-testid="save-all-btn"
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : 'Save All Only'}
            </Button>
            
            <Button 
              variant="outline" 
              onClick={handleClearAll}
              disabled={!hasUnsavedData()}
              className="text-gray-600 border-gray-300 hover:bg-gray-50"
              data-testid="clear-all-btn"
            >
              <XCircle className="h-4 w-4 mr-2" />
              Clear All
            </Button>
          </div>
          
          <Button variant="outline" disabled>
            <Printer className="h-4 w-4 mr-2" /> Print All Labels
          </Button>
        </div>

        {/* Photo Upload Dialog */}
        <Dialog open={photoDialogOpen} onOpenChange={setPhotoDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Photos</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <div 
                className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-[#6B633C] transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Camera className="h-12 w-12 mx-auto text-gray-400 mb-3" />
                <p className="text-gray-600">Click to upload photos</p>
                <p className="text-xs text-gray-400 mt-1">JPG, PNG, HEIC • Max 10 photos</p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={handlePhotoUpload}
              />
              
              {activeRow?.photos.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium mb-2">Attached ({activeRow.photos.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {activeRow.photos.map(photo => (
                      <div key={photo.id} className="relative group">
                        <img 
                          src={photo.data} 
                          alt={photo.name}
                          className="w-16 h-16 object-cover rounded"
                        />
                        <button
                          className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => removePhoto(activeRowId, photo.id)}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setPhotoDialogOpen(false)}>Done</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Document Upload Dialog */}
        <Dialog open={documentDialogOpen} onOpenChange={setDocumentDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Documents</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <div 
                className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-[#6B633C] transition-colors"
                onClick={() => docInputRef.current?.click()}
              >
                <FileText className="h-12 w-12 mx-auto text-gray-400 mb-3" />
                <p className="text-gray-600">Click to upload documents</p>
                <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG • Max 5 files</p>
              </div>
              <input
                ref={docInputRef}
                type="file"
                accept=".pdf,image/*"
                multiple
                className="hidden"
                onChange={handleDocumentUpload}
              />
              
              {activeRow?.documents.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium mb-2">Attached ({activeRow.documents.length})</p>
                  <div className="space-y-1">
                    {activeRow.documents.map(doc => (
                      <div key={doc.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <span className="text-sm truncate">{doc.name}</span>
                        <button
                          className="text-red-500 hover:text-red-700"
                          onClick={() => removeDocument(activeRowId, doc.id)}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDocumentDialogOpen(false)}>Done</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Preview Dialog */}
        <Dialog open={previewDialogOpen} onOpenChange={setPreviewDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{previewType === 'barcode' ? 'Barcode Preview' : 'Label Preview'}</DialogTitle>
            </DialogHeader>
            <div className="py-4 text-center">
              <div className="border rounded-lg p-6 bg-gray-50">
                {activeRow?.barcode ? (
                  <div>
                    <div className="font-mono text-2xl mb-2">{activeRow.barcode}</div>
                    <div className="h-16 bg-[repeating-linear-gradient(90deg,#000,#000_2px,#fff_2px,#fff_4px)] mx-auto w-48" />
                  </div>
                ) : (
                  <div>
                    <div className="font-mono text-lg text-gray-500 mb-2">TEMP-{Math.random().toString(36).substr(2, 8).toUpperCase()}</div>
                    <div className="h-12 bg-[repeating-linear-gradient(90deg,#999,#999_2px,#fff_2px,#fff_4px)] mx-auto w-40" />
                    <p className="text-xs text-gray-400 mt-3">Temporary barcode - final barcode assigned on save</p>
                  </div>
                )}
                
                {previewType === 'label' && (
                  <div className="mt-4 pt-4 border-t text-left text-sm">
                    <p><strong>From:</strong> {selectedClient?.name || 'Not selected'}</p>
                    <p><strong>To:</strong> {recipient || selectedClient?.name || '-'}</p>
                    <p><strong>Description:</strong> {activeRow?.description || '-'}</p>
                    <p><strong>Dimensions:</strong> {activeRow?.length || 0} × {activeRow?.width || 0} × {activeRow?.height || 0} cm</p>
                  </div>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setPreviewDialogOpen(false)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* View Uploads Dialog */}
        <Dialog open={uploadsDialogOpen} onOpenChange={setUploadsDialogOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Uploaded Files</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              {activeRow?.photos.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm font-medium mb-2">Photos ({activeRow.photos.length})</p>
                  <div className="grid grid-cols-4 gap-2">
                    {activeRow.photos.map(photo => (
                      <div key={photo.id} className="relative group">
                        <img 
                          src={photo.data} 
                          alt={photo.name}
                          className="w-full h-24 object-cover rounded cursor-pointer hover:opacity-90"
                          onClick={() => window.open(photo.data, '_blank')}
                        />
                        <button
                          className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={() => removePhoto(activeRowId, photo.id)}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {activeRow?.documents.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Documents ({activeRow.documents.length})</p>
                  <div className="space-y-1">
                    {activeRow.documents.map(doc => (
                      <div key={doc.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4 text-gray-500" />
                          <span className="text-sm">{doc.name}</span>
                        </div>
                        <button
                          className="text-red-500 hover:text-red-700"
                          onClick={() => removeDocument(activeRowId, doc.id)}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {!activeRow?.photos.length && !activeRow?.documents.length && (
                <p className="text-center text-gray-500 py-8">No files uploaded for this row</p>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setUploadsDialogOpen(false)}>Close</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Unsaved Data Warning Dialog */}
        <AlertDialog open={showUnsavedDialog} onOpenChange={setShowUnsavedDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                You have {unsavedCount} unsaved parcel{unsavedCount !== 1 ? 's' : ''}
              </AlertDialogTitle>
              <AlertDialogDescription>
                Save before leaving? Your data will be lost if you discard.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={handleCancelNavigation}>Cancel</AlertDialogCancel>
              <Button variant="outline" onClick={handleDiscardAndNavigate}>
                Discard
              </Button>
              <AlertDialogAction 
                onClick={handleSaveAndNavigate}
                className="bg-[#6B633C] hover:bg-[#5a5332]"
              >
                Save All
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Clear All Confirmation Dialog */}
        <AlertDialog open={showClearDialog} onOpenChange={setShowClearDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear all unsaved parcels?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove all {unsavedCount} unsaved parcel{unsavedCount !== 1 ? 's' : ''} from the table. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction 
                onClick={confirmClearAll}
                className="bg-red-600 hover:bg-red-700"
              >
                Clear All
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Add Client Modal */}
        <Dialog open={addClientModalOpen} onOpenChange={setAddClientModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <UserPlus className="h-5 w-5 text-[#6B633C]" />
                Add New Client
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label className="text-sm font-medium">Client Name *</Label>
                <Input
                  value={newClientData.name}
                  onChange={(e) => setNewClientData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Client or company name"
                  className="mt-1"
                  data-testid="new-client-name"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Phone</Label>
                  <Input
                    value={newClientData.phone}
                    onChange={(e) => setNewClientData(prev => ({ ...prev, phone: e.target.value }))}
                    placeholder="+27 xxx xxx xxxx"
                    className="mt-1"
                    data-testid="new-client-phone"
                  />
                </div>
                <div>
                  <Label className="text-sm font-medium">WhatsApp</Label>
                  <Input
                    value={newClientData.whatsapp}
                    onChange={(e) => setNewClientData(prev => ({ ...prev, whatsapp: e.target.value }))}
                    placeholder="+27 xxx xxx xxxx"
                    className="mt-1"
                    data-testid="new-client-whatsapp"
                  />
                </div>
              </div>
              
              <div>
                <Label className="text-sm font-medium">Email</Label>
                <Input
                  type="email"
                  value={newClientData.email}
                  onChange={(e) => setNewClientData(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="client@example.com"
                  className="mt-1"
                  data-testid="new-client-email"
                />
              </div>
              
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-sm font-medium">Currency</Label>
                  <Select
                    value={newClientData.default_currency}
                    onValueChange={(v) => setNewClientData(prev => ({ ...prev, default_currency: v }))}
                  >
                    <SelectTrigger className="mt-1" data-testid="new-client-currency">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ZAR">ZAR</SelectItem>
                      <SelectItem value="USD">USD</SelectItem>
                      <SelectItem value="EUR">EUR</SelectItem>
                      <SelectItem value="GBP">GBP</SelectItem>
                      <SelectItem value="NGN">NGN</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-sm font-medium">Rate Type</Label>
                  <Select
                    value={newClientData.rate_type}
                    onValueChange={(v) => setNewClientData(prev => ({ ...prev, rate_type: v }))}
                  >
                    <SelectTrigger className="mt-1" data-testid="new-client-rate-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="per_kg">Per Kg</SelectItem>
                      <SelectItem value="per_cbm">Per CBM</SelectItem>
                      <SelectItem value="flat_rate">Flat Rate</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-sm font-medium">Rate Value</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={newClientData.rate_value}
                    onChange={(e) => setNewClientData(prev => ({ ...prev, rate_value: e.target.value }))}
                    placeholder="0.00"
                    className="mt-1"
                    data-testid="new-client-rate-value"
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAddClientModalOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleAddClient}
                disabled={addingClient}
                className="bg-[#6B633C] hover:bg-[#5a5332]"
                data-testid="save-new-client-btn"
              >
                {addingClient ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Client
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Add Recipient Modal */}
        <Dialog open={addRecipientModalOpen} onOpenChange={setAddRecipientModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <UserPlus className="h-5 w-5 text-[#6B633C]" />
                Add New Recipient
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label className="text-sm font-medium">Recipient Name *</Label>
                <Input
                  value={newRecipientData.name}
                  onChange={(e) => setNewRecipientData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Recipient name"
                  className="mt-1"
                  data-testid="new-recipient-name"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Phone</Label>
                  <Input
                    value={newRecipientData.phone}
                    onChange={(e) => setNewRecipientData(prev => ({ ...prev, phone: e.target.value }))}
                    placeholder="+27 xxx xxx xxxx"
                    className="mt-1"
                    data-testid="new-recipient-phone"
                  />
                </div>
                <div>
                  <Label className="text-sm font-medium">WhatsApp</Label>
                  <Input
                    value={newRecipientData.whatsapp}
                    onChange={(e) => setNewRecipientData(prev => ({ ...prev, whatsapp: e.target.value }))}
                    placeholder="+27 xxx xxx xxxx"
                    className="mt-1"
                    data-testid="new-recipient-whatsapp"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">Email</Label>
                  <Input
                    type="email"
                    value={newRecipientData.email}
                    onChange={(e) => setNewRecipientData(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="recipient@example.com"
                    className="mt-1"
                    data-testid="new-recipient-email"
                  />
                </div>
                <div>
                  <Label className="text-sm font-medium">VAT Number</Label>
                  <Input
                    value={newRecipientData.vat_number}
                    onChange={(e) => setNewRecipientData(prev => ({ ...prev, vat_number: e.target.value }))}
                    placeholder="VAT123456"
                    className="mt-1"
                    data-testid="new-recipient-vat"
                  />
                </div>
              </div>
              
              <div>
                <Label className="text-sm font-medium">Shipping Address</Label>
                <textarea
                  value={newRecipientData.shipping_address}
                  onChange={(e) => setNewRecipientData(prev => ({ ...prev, shipping_address: e.target.value }))}
                  placeholder="Full shipping address..."
                  className="mt-1 w-full min-h-[80px] px-3 py-2 border rounded-md text-sm resize-none"
                  data-testid="new-recipient-address"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setAddRecipientModalOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleAddRecipient}
                disabled={addingRecipient}
                className="bg-[#6B633C] hover:bg-[#5a5332]"
                data-testid="save-new-recipient-btn"
              >
                {addingRecipient ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Recipient
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}

export default ParcelIntake;
