import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '../components/ui/sheet';
import { toast } from 'sonner';
import { Plus, Search, MoreVertical, Edit, Trash2, Package, Eye, Barcode } from 'lucide-react';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

const statusColors = {
  warehouse: 'status-warehouse',
  staged: 'status-staged',
  loaded: 'status-loaded',
  in_transit: 'status-in-transit',
  delivered: 'status-delivered'
};

export function Shipments() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [shipments, setShipments] = useState([]);
  const [clients, setClients] = useState([]);
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingShipment, setEditingShipment] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedShipment, setSelectedShipment] = useState(null);
  const [pieces, setPieces] = useState([]);
  const [pieceDialogOpen, setPieceDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    client_id: '',
    description: '',
    destination: '',
    total_pieces: 1,
    total_weight: 0,
    total_cbm: null,
    trip_id: null
  });
  const [pieceForm, setPieceForm] = useState({
    piece_number: 1,
    weight: 0,
    length_cm: null,
    width_cm: null,
    height_cm: null
  });

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const fetchData = async () => {
    try {
      const [shipmentsRes, clientsRes, tripsRes] = await Promise.all([
        axios.get(`${API}/shipments${statusFilter !== 'all' ? `?status=${statusFilter}` : ''}`, { withCredentials: true }),
        axios.get(`${API}/clients`, { withCredentials: true }),
        axios.get(`${API}/trips`, { withCredentials: true })
      ]);
      setShipments(shipmentsRes.data);
      setClients(clientsRes.data);
      setTrips(tripsRes.data);
    } catch (error) {
      toast.error('Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const fetchShipmentDetails = async (shipmentId) => {
    try {
      const response = await axios.get(`${API}/shipments/${shipmentId}`, { withCredentials: true });
      setSelectedShipment(response.data);
      setPieces(response.data.pieces || []);
    } catch (error) {
      toast.error('Failed to fetch shipment details');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        total_cbm: formData.total_cbm || null,
        trip_id: formData.trip_id || null
      };

      if (editingShipment) {
        await axios.put(`${API}/shipments/${editingShipment.id}`, payload, { withCredentials: true });
        toast.success('Shipment updated');
      } else {
        await axios.post(`${API}/shipments`, payload, { withCredentials: true });
        toast.success('Shipment created');
      }
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save shipment');
    }
  };

  const handleDelete = async (shipmentId) => {
    if (!window.confirm('Are you sure you want to delete this shipment?')) return;
    try {
      await axios.delete(`${API}/shipments/${shipmentId}`, { withCredentials: true });
      toast.success('Shipment deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete shipment');
    }
  };

  const handleAddPiece = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/shipments/${selectedShipment.id}/pieces`, pieceForm, { withCredentials: true });
      toast.success('Piece added');
      fetchShipmentDetails(selectedShipment.id);
      setPieceForm({
        piece_number: pieces.length + 2,
        weight: 0,
        length_cm: null,
        width_cm: null,
        height_cm: null
      });
      setPieceDialogOpen(false);
    } catch (error) {
      toast.error('Failed to add piece');
    }
  };

  const handleUpdateStatus = async (shipmentId, newStatus) => {
    try {
      await axios.put(`${API}/shipments/${shipmentId}`, { status: newStatus }, { withCredentials: true });
      toast.success('Status updated');
      fetchData();
      if (selectedShipment?.id === shipmentId) {
        fetchShipmentDetails(shipmentId);
      }
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const resetForm = () => {
    setFormData({
      client_id: '',
      description: '',
      destination: '',
      total_pieces: 1,
      total_weight: 0,
      total_cbm: null,
      trip_id: null
    });
    setEditingShipment(null);
  };

  const openEdit = (shipment) => {
    setEditingShipment(shipment);
    setFormData({
      client_id: shipment.client_id,
      description: shipment.description,
      destination: shipment.destination,
      total_pieces: shipment.total_pieces,
      total_weight: shipment.total_weight,
      total_cbm: shipment.total_cbm,
      trip_id: shipment.trip_id
    });
    setDialogOpen(true);
  };

  const openDetails = (shipment) => {
    fetchShipmentDetails(shipment.id);
    setDetailsOpen(true);
  };

  const getClientName = (clientId) => {
    const client = clients.find(c => c.id === clientId);
    return client?.name || 'Unknown';
  };

  const filteredShipments = shipments.filter(shipment =>
    shipment.description.toLowerCase().includes(search.toLowerCase()) ||
    shipment.destination.toLowerCase().includes(search.toLowerCase()) ||
    getClientName(shipment.client_id).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <div className="space-y-6" data-testid="shipments-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold">Shipments</h1>
            <p className="text-muted-foreground mt-1">Track and manage all shipments</p>
          </div>
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-shipment-btn">
                <Plus className="h-4 w-4 mr-2" />
                New Shipment
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>{editingShipment ? 'Edit Shipment' : 'Create Shipment'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label>Client *</Label>
                  <Select
                    value={formData.client_id}
                    onValueChange={(value) => setFormData({ ...formData, client_id: value })}
                    required
                  >
                    <SelectTrigger data-testid="shipment-client-select">
                      <SelectValue placeholder="Select client" />
                    </SelectTrigger>
                    <SelectContent>
                      {clients.map((client) => (
                        <SelectItem key={client.id} value={client.id}>
                          {client.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Description *</Label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    required
                    data-testid="shipment-description-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Destination *</Label>
                  <Input
                    value={formData.destination}
                    onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                    required
                    data-testid="shipment-destination-input"
                  />
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Pieces</Label>
                    <Input
                      type="number"
                      value={formData.total_pieces}
                      onChange={(e) => setFormData({ ...formData, total_pieces: parseInt(e.target.value) || 1 })}
                      data-testid="shipment-pieces-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Weight (kg) *</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.total_weight}
                      onChange={(e) => setFormData({ ...formData, total_weight: parseFloat(e.target.value) || 0 })}
                      required
                      data-testid="shipment-weight-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>CBM</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={formData.total_cbm || ''}
                      onChange={(e) => setFormData({ ...formData, total_cbm: parseFloat(e.target.value) || null })}
                      data-testid="shipment-cbm-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Assign to Trip</Label>
                  <Select
                    value={formData.trip_id || 'none'}
                    onValueChange={(value) => setFormData({ ...formData, trip_id: value === 'none' ? null : value })}
                  >
                    <SelectTrigger data-testid="shipment-trip-select">
                      <SelectValue placeholder="No trip assigned" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No trip assigned</SelectItem>
                      {trips.map((trip) => (
                        <SelectItem key={trip.id} value={trip.id}>
                          {trip.trip_number} - {trip.destination}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <DialogFooter>
                  <Button type="submit" data-testid="save-shipment-btn">
                    {editingShipment ? 'Update' : 'Create'} Shipment
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search shipments..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="shipment-search-input"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-48" data-testid="status-filter-select">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="warehouse">Warehouse</SelectItem>
                  <SelectItem value="staged">Staged</SelectItem>
                  <SelectItem value="loaded">Loaded</SelectItem>
                  <SelectItem value="in_transit">In Transit</SelectItem>
                  <SelectItem value="delivered">Delivered</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Shipments Table */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : filteredShipments.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Client</TableHead>
                      <TableHead className="hidden sm:table-cell">Destination</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="hidden md:table-cell">Pieces</TableHead>
                      <TableHead className="text-right">Weight</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredShipments.map((shipment) => (
                      <TableRow key={shipment.id} data-testid={`shipment-row-${shipment.id}`}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{getClientName(shipment.client_id)}</p>
                            <p className="text-sm text-muted-foreground line-clamp-1">
                              {shipment.description}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">
                          {shipment.destination}
                        </TableCell>
                        <TableCell>
                          <Badge className={cn('text-xs capitalize', statusColors[shipment.status])}>
                            {shipment.status.replace('_', ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden md:table-cell font-mono">
                          {shipment.total_pieces}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {shipment.total_weight} kg
                        </TableCell>
                        <TableCell className="text-right">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" data-testid={`shipment-menu-${shipment.id}`}>
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => openDetails(shipment)}>
                                <Eye className="h-4 w-4 mr-2" />
                                View Details
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => openEdit(shipment)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleDelete(shipment.id)}
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
              <div className="text-center py-12 text-muted-foreground">
                <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No shipments found</p>
                <Button
                  variant="link"
                  onClick={() => setDialogOpen(true)}
                  className="mt-2"
                >
                  Create your first shipment
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Shipment Details Sheet */}
        <Sheet open={detailsOpen} onOpenChange={setDetailsOpen}>
          <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Shipment Details</SheetTitle>
            </SheetHeader>
            {selectedShipment && (
              <div className="mt-6 space-y-6">
                {/* Basic Info */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Badge className={cn('capitalize', statusColors[selectedShipment.status])}>
                      {selectedShipment.status.replace('_', ' ')}
                    </Badge>
                    <Select
                      value={selectedShipment.status}
                      onValueChange={(value) => handleUpdateStatus(selectedShipment.id, value)}
                    >
                      <SelectTrigger className="w-36" data-testid="update-status-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="warehouse">Warehouse</SelectItem>
                        <SelectItem value="staged">Staged</SelectItem>
                        <SelectItem value="loaded">Loaded</SelectItem>
                        <SelectItem value="in_transit">In Transit</SelectItem>
                        <SelectItem value="delivered">Delivered</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Client</p>
                      <p className="font-medium">{getClientName(selectedShipment.client_id)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Destination</p>
                      <p className="font-medium">{selectedShipment.destination}</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground">Description</p>
                    <p className="font-medium">{selectedShipment.description}</p>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Pieces</p>
                      <p className="font-mono font-semibold">{selectedShipment.total_pieces}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Weight</p>
                      <p className="font-mono font-semibold">{selectedShipment.total_weight} kg</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">CBM</p>
                      <p className="font-mono font-semibold">{selectedShipment.total_cbm || '-'}</p>
                    </div>
                  </div>
                </div>

                {/* Pieces */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-heading font-semibold">Pieces & Barcodes</h3>
                    <Dialog open={pieceDialogOpen} onOpenChange={setPieceDialogOpen}>
                      <DialogTrigger asChild>
                        <Button size="sm" data-testid="add-piece-btn">
                          <Plus className="h-4 w-4 mr-1" />
                          Add Piece
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Add Piece</DialogTitle>
                        </DialogHeader>
                        <form onSubmit={handleAddPiece} className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Piece Number</Label>
                              <Input
                                type="number"
                                value={pieceForm.piece_number}
                                onChange={(e) => setPieceForm({ ...pieceForm, piece_number: parseInt(e.target.value) || 1 })}
                                data-testid="piece-number-input"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Weight (kg)</Label>
                              <Input
                                type="number"
                                step="0.01"
                                value={pieceForm.weight}
                                onChange={(e) => setPieceForm({ ...pieceForm, weight: parseFloat(e.target.value) || 0 })}
                                data-testid="piece-weight-input"
                              />
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-4">
                            <div className="space-y-2">
                              <Label>Length (cm)</Label>
                              <Input
                                type="number"
                                value={pieceForm.length_cm || ''}
                                onChange={(e) => setPieceForm({ ...pieceForm, length_cm: parseFloat(e.target.value) || null })}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Width (cm)</Label>
                              <Input
                                type="number"
                                value={pieceForm.width_cm || ''}
                                onChange={(e) => setPieceForm({ ...pieceForm, width_cm: parseFloat(e.target.value) || null })}
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Height (cm)</Label>
                              <Input
                                type="number"
                                value={pieceForm.height_cm || ''}
                                onChange={(e) => setPieceForm({ ...pieceForm, height_cm: parseFloat(e.target.value) || null })}
                              />
                            </div>
                          </div>
                          <DialogFooter>
                            <Button type="submit" data-testid="save-piece-btn">Add Piece</Button>
                          </DialogFooter>
                        </form>
                      </DialogContent>
                    </Dialog>
                  </div>

                  {pieces.length > 0 ? (
                    <div className="space-y-2">
                      {pieces.map((piece) => (
                        <div
                          key={piece.id}
                          className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                          data-testid={`piece-${piece.id}`}
                        >
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded bg-primary/10 flex items-center justify-center">
                              <Barcode className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                              <p className="font-mono font-semibold text-primary">
                                {piece.barcode}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                Piece #{piece.piece_number} • {piece.weight} kg
                              </p>
                            </div>
                          </div>
                          {piece.loaded_at && (
                            <Badge className="status-delivered">Loaded</Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No pieces added yet
                    </p>
                  )}
                </div>
              </div>
            )}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
