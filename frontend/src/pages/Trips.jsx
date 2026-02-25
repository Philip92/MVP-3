import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
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
  DialogFooter,
} from '../components/ui/dialog';
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
import { toast } from 'sonner';
import { 
  Plus, MoreVertical, Edit, Trash2, Truck, Eye, Package, 
  Users, DollarSign, Weight, Copy, Lock, X, GripVertical, Calendar, Search, ArrowUpDown, Box
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';

const API = `${window.location.origin}/api`;

// Servex brand colors for status badges
const statusConfig = {
  planning: { bg: 'bg-[#D4CFC0]', text: 'text-[#3C3F42]', label: 'Planning' },
  loading: { bg: 'bg-[#E8DC88]', text: 'text-[#3C3F42]', label: 'Loading' },
  in_transit: { bg: 'bg-[#6B633C]', text: 'text-white', label: 'In Transit' },
  delivered: { bg: 'bg-[#5A8F3B]', text: 'text-white', label: 'Delivered' },
  closed: { bg: 'bg-[#3C3F42]', text: 'text-white', label: 'Closed' }
};

const filterTabs = [
  { value: 'all', label: 'All Trips' },
  { value: 'planning', label: 'Planning' },
  { value: 'loading', label: 'Loading' },
  { value: 'in_transit', label: 'In Transit' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'closed', label: 'Closed' }
];

export function Trips() {
  const navigate = useNavigate();
  const [trips, setTrips] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('trip_number');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTrip, setEditingTrip] = useState(null);
  const [nextTripNumber, setNextTripNumber] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    trip_number: '',
    route: [],
    departure_date: '',
    vehicle_id: '',
    driver_id: '',
    destination_warehouse_id: '',
    notes: ''
  });
  const [routeInput, setRouteInput] = useState('');
  const [draggedIndex, setDraggedIndex] = useState(null);

  const fetchTrips = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/trips-with-stats${statusFilter !== 'all' ? `?status=${statusFilter}` : ''}`, { withCredentials: true });
      setTrips(response.data);
    } catch (error) {
      toast.error('Failed to fetch trips');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const fetchVehiclesAndDrivers = async () => {
    try {
      const [vehiclesRes, driversRes, warehousesRes] = await Promise.all([
        axios.get(`${API}/vehicles`, { withCredentials: true }),
        axios.get(`${API}/drivers`, { withCredentials: true }),
        axios.get(`${API}/warehouses`, { withCredentials: true })
      ]);
      setVehicles(vehiclesRes.data.filter(v => v.status === 'available'));
      setDrivers(driversRes.data.filter(d => d.status === 'available'));
      setWarehouses(warehousesRes.data.filter(w => w.status === 'active'));
    } catch (error) {
      console.error('Failed to fetch vehicles/drivers/warehouses');
    }
  };

  const fetchNextTripNumber = async () => {
    try {
      const response = await axios.get(`${API}/trips/next-number`, { withCredentials: true });
      setNextTripNumber(response.data.next_trip_number);
      return response.data.next_trip_number;
    } catch (error) {
      console.error('Failed to fetch next trip number');
      return 'S1';
    }
  };

  useEffect(() => {
    fetchTrips();
  }, [fetchTrips]);

  const openCreateDialog = async () => {
    setEditingTrip(null);
    const nextNum = await fetchNextTripNumber();
    await fetchVehiclesAndDrivers();
    
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    setFormData({
      trip_number: nextNum,
      route: [],
      departure_date: tomorrow.toISOString().split('T')[0],
      vehicle_id: '',
      driver_id: '',
      destination_warehouse_id: '',
      notes: ''
    });
    setRouteInput('');
    setDialogOpen(true);
  };

  const openEditDialog = async (trip) => {
    setEditingTrip(trip);
    await fetchVehiclesAndDrivers();
    setFormData({
      trip_number: trip.trip_number,
      route: trip.route || [],
      departure_date: trip.departure_date || '',
      vehicle_id: trip.vehicle_id || '',
      driver_id: trip.driver_id || '',
      destination_warehouse_id: trip.destination_warehouse_id || '',
      notes: trip.notes || ''
    });
    setRouteInput('');
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.route.length === 0) {
      toast.error('Please add at least one stop to the route');
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = {
        ...formData,
        vehicle_id: formData.vehicle_id || null,
        driver_id: formData.driver_id || null,
        destination_warehouse_id: formData.destination_warehouse_id || null
      };

      if (editingTrip) {
        await axios.put(`${API}/trips/${editingTrip.id}`, payload, { withCredentials: true });
        toast.success(`✓ Trip ${formData.trip_number} updated`);
      } else {
        const response = await axios.post(`${API}/trips`, payload, { withCredentials: true });
        toast.success(`✓ Trip ${formData.trip_number} created`);
        setDialogOpen(false);
        navigate(`/trips/${response.data.id}`);
        return;
      }
      setDialogOpen(false);
      fetchTrips();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save trip');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDuplicate = async (trip) => {
    const nextNum = await fetchNextTripNumber();
    try {
      await axios.post(`${API}/trips`, {
        trip_number: nextNum,
        route: trip.route || [],
        departure_date: trip.departure_date,
        vehicle_id: null,
        driver_id: null,
        notes: `Duplicated from ${trip.trip_number}`
      }, { withCredentials: true });
      toast.success(`✓ Trip ${nextNum} created (duplicated from ${trip.trip_number})`);
      fetchTrips();
    } catch (error) {
      toast.error('Failed to duplicate trip');
    }
  };

  const handleClose = async (trip) => {
    try {
      await axios.put(`${API}/trips/${trip.id}`, { status: 'closed' }, { withCredentials: true });
      toast.success(`✓ Trip ${trip.trip_number} closed`);
      fetchTrips();
    } catch (error) {
      toast.error('Failed to close trip');
    }
  };

  const handleDelete = async (trip) => {
    if (!window.confirm(`Delete trip ${trip.trip_number}? This cannot be undone.`)) return;
    try {
      await axios.delete(`${API}/trips/${trip.id}`, { withCredentials: true });
      toast.success(`✓ Trip ${trip.trip_number} deleted`);
      fetchTrips();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete trip');
    }
  };

  // Route management
  const addRouteStop = () => {
    if (routeInput.trim()) {
      setFormData(prev => ({
        ...prev,
        route: [...prev.route, routeInput.trim()]
      }));
      setRouteInput('');
    }
  };

  const removeRouteStop = (index) => {
    setFormData(prev => ({
      ...prev,
      route: prev.route.filter((_, i) => i !== index)
    }));
  };

  const handleDragStart = (index) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;
    
    const newRoute = [...formData.route];
    const draggedItem = newRoute[draggedIndex];
    newRoute.splice(draggedIndex, 1);
    newRoute.splice(index, 0, draggedItem);
    
    setFormData(prev => ({ ...prev, route: newRoute }));
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR', maximumFractionDigits: 0 }).format(amount);
  };

  const TripCard = ({ trip }) => {
    const status = statusConfig[trip.status] || statusConfig.planning;
    const stats = trip.stats || {};
    
    return (
      <Card className="bg-white hover:shadow-lg transition-shadow duration-200" data-testid={`trip-card-${trip.trip_number}`}>
        <CardContent className="p-5">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <span className="text-[32px] font-bold text-[#3C3F42]">{trip.trip_number}</span>
              <Badge className={`${status.bg} ${status.text} border-0 px-3 py-1`}>
                {status.label}
              </Badge>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" data-testid={`trip-menu-${trip.trip_number}`}>
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => openEditDialog(trip)}>
                  <Edit className="h-4 w-4 mr-2" /> Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleDuplicate(trip)}>
                  <Copy className="h-4 w-4 mr-2" /> Duplicate
                </DropdownMenuItem>
                {trip.status !== 'closed' && (
                  <DropdownMenuItem onClick={() => handleClose(trip)}>
                    <Lock className="h-4 w-4 mr-2" /> Close
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => handleDelete(trip)} className="text-red-600">
                  <Trash2 className="h-4 w-4 mr-2" /> Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Route */}
          {trip.route && trip.route.length > 0 && (
            <div className="text-sm text-[#3C3F42] mb-2 font-medium">
              {trip.route.join(' → ')}
            </div>
          )}

          {/* Departure & Vehicle/Driver */}
          <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
            {trip.departure_date && (
              <div className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                {format(new Date(trip.departure_date), 'MMM d, yyyy')}
              </div>
            )}
            {trip.vehicle && (
              <div className="flex items-center gap-1">
                <Truck className="h-3.5 w-3.5" />
                {trip.vehicle.registration_number}
              </div>
            )}
          </div>

          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Loading Progress</span>
              <span>{stats.loading_percentage || 0}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-[#6B633C] transition-all duration-300"
                style={{ width: `${stats.loading_percentage || 0}%` }}
              />
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="flex items-center gap-2 text-sm">
              <Package className="h-4 w-4 text-[#6B633C]" />
              <span className="text-gray-600">Parcels:</span>
              <span className="font-semibold text-[#3C3F42]">{stats.total_parcels || 0}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Weight className="h-4 w-4 text-[#6B633C]" />
              <span className="text-gray-600">Weight:</span>
              <span className="font-semibold text-[#3C3F42]">{(stats.total_weight || 0).toLocaleString()} kg</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4 text-[#6B633C]" />
              <span className="text-gray-600">Clients:</span>
              <span className="font-semibold text-[#3C3F42]">{stats.total_clients || 0}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <DollarSign className="h-4 w-4 text-[#6B633C]" />
              <span className="text-gray-600">Value:</span>
              <span className="font-semibold text-[#3C3F42]">{formatCurrency(stats.invoiced_value || 0)}</span>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <Button 
              className="bg-[#6B633C] hover:bg-[#5a5332] text-white"
              onClick={() => navigate(`/trips/${trip.id}`)}
              data-testid={`view-trip-${trip.trip_number}`}
            >
              <Eye className="h-4 w-4 mr-2" /> View Details
            </Button>
            {trip.created_at && (
              <span className="text-xs text-gray-400">
                Updated {formatDistanceToNow(new Date(trip.created_at), { addSuffix: true })}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  const EmptyState = () => (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-20 h-20 rounded-full bg-gray-200 flex items-center justify-center mb-6">
        <Truck className="h-10 w-10 text-gray-400" />
      </div>
      <h3 className="text-xl font-semibold text-[#3C3F42] mb-2">No trips created yet</h3>
      <p className="text-gray-500 mb-6">Create your first trip to start managing shipments</p>
      <Button 
        className="bg-[#6B633C] hover:bg-[#5a5332] text-white"
        onClick={openCreateDialog}
        data-testid="empty-create-trip-btn"
      >
        <Plus className="h-4 w-4 mr-2" /> Create Trip
      </Button>
    </div>
  );

  const LoadingSkeleton = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {[1, 2, 3, 4, 5, 6].map(i => (
        <Card key={i} className="bg-white">
          <CardContent className="p-5">
            <div className="flex justify-between mb-4">
              <Skeleton className="h-10 w-20" />
              <Skeleton className="h-6 w-24" />
            </div>
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-32 mb-4" />
            <Skeleton className="h-2 w-full mb-4" />
            <div className="grid grid-cols-2 gap-3 mb-4">
              {[1, 2, 3, 4].map(j => (
                <Skeleton key={j} className="h-5 w-full" />
              ))}
            </div>
            <Skeleton className="h-10 w-28" />
          </CardContent>
        </Card>
      ))}
    </div>
  );

  return (
    <>
      <div className="p-4 sm:p-6" data-testid="trips-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl sm:text-2xl font-bold text-[#3C3F42]">Trip Manager</h1>
          <Button 
            className="bg-[#6B633C] hover:bg-[#5a5332] text-white h-8 text-xs"
            onClick={openCreateDialog}
            data-testid="create-trip-btn"
          >
            <Plus className="h-3 w-3 mr-1" /> Create Trip
          </Button>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap gap-2 mb-4">
          {filterTabs.map(tab => (
            <Button
              key={tab.value}
              variant={statusFilter === tab.value ? 'default' : 'outline'}
              className={statusFilter === tab.value 
                ? 'bg-[#6B633C] hover:bg-[#5a5332] text-white h-7 text-xs' 
                : 'border-gray-300 text-gray-600 hover:bg-gray-100'
              }
              onClick={() => setStatusFilter(tab.value)}
              data-testid={`filter-${tab.value}`}
            >
              {tab.label}
            </Button>
          ))}
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search trips by number, route, or vehicle..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <LoadingSkeleton />
        ) : trips.length === 0 ? (
          <EmptyState />
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50">
                    <TableHead className="w-[140px] font-semibold">Trip #</TableHead>
                    <TableHead className="font-semibold">Route</TableHead>
                    <TableHead className="w-[130px] font-semibold">Date</TableHead>
                    <TableHead className="w-[120px] text-center font-semibold">Parcels</TableHead>
                    <TableHead className="w-[100px] text-right font-semibold">Weight</TableHead>
                    <TableHead className="w-[130px] font-semibold">Status</TableHead>
                    <TableHead className="w-[100px] text-center font-semibold">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trips
                    .filter(trip => {
                      // Filter by search
                      if (searchQuery) {
                        const query = searchQuery.toLowerCase();
                        return (
                          trip.trip_number.toLowerCase().includes(query) ||
                          trip.route?.some(r => r.toLowerCase().includes(query)) ||
                          trip.vehicle?.registration_number?.toLowerCase().includes(query)
                        );
                      }
                      return true;
                    })
                    .map(trip => {
                      const status = statusConfig[trip.status] || statusConfig.planning;
                      const stats = trip.stats || {};
                      
                      return (
                        <TableRow 
                          key={trip.id} 
                          className="hover:bg-gray-50 cursor-pointer"
                          onClick={() => navigate(`/trips/${trip.id}`)}
                        >
                          <TableCell className="font-bold text-base">{trip.trip_number}</TableCell>
                          <TableCell className="text-sm">
                            {trip.route && trip.route.length > 0 ? trip.route.join(' → ') : '—'}
                          </TableCell>
                          <TableCell className="text-sm text-gray-600">
                            {trip.departure_date ? format(new Date(trip.departure_date), 'MMM d, yyyy') : '—'}
                          </TableCell>
                          <TableCell className="text-center">
                            <span className="font-semibold">{stats.loaded_parcels || 0}</span>
                            <span className="text-gray-500"> of </span>
                            <span className="font-semibold">{stats.total_parcels || 0}</span>
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm">
                            {(stats.total_weight || 0).toLocaleString()} kg
                          </TableCell>
                          <TableCell>
                            <Badge className={`${status.bg} ${status.text} border-0`}>
                              {status.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-center">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigate(`/trips/${trip.id}`); }}>
                                  <Eye className="h-4 w-4 mr-2" /> View
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openEditDialog(trip); }}>
                                  <Edit className="h-4 w-4 mr-2" /> Edit
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDuplicate(trip); }}>
                                  <Copy className="h-4 w-4 mr-2" /> Duplicate
                                </DropdownMenuItem>
                                {trip.status !== 'closed' && (
                                  <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleClose(trip); }}>
                                    <Lock className="h-4 w-4 mr-2" /> Close
                                  </DropdownMenuItem>
                                )}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDelete(trip); }} className="text-red-600">
                                  <Trash2 className="h-4 w-4 mr-2" /> Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="text-[#3C3F42]">
                {editingTrip ? `Edit Trip ${editingTrip.trip_number}` : 'Create New Trip'}
              </DialogTitle>
            </DialogHeader>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Trip Number */}
              <div>
                <Label htmlFor="trip_number">Trip Number</Label>
                {!editingTrip && nextTripNumber && (
                  <p className="text-xs text-gray-500 mb-1">Next trip: {nextTripNumber}</p>
                )}
                <Input
                  id="trip_number"
                  value={formData.trip_number}
                  onChange={(e) => setFormData(prev => ({ ...prev, trip_number: e.target.value }))}
                  placeholder="e.g., S28"
                  required
                  disabled={!!editingTrip}
                  data-testid="trip-number-input"
                />
              </div>

              {/* Route */}
              <div>
                <Label>Route (Add stops in order)</Label>
                <div className="flex gap-2 mb-2">
                  <Input
                    value={routeInput}
                    onChange={(e) => setRouteInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addRouteStop())}
                    placeholder="Add city/stop..."
                    data-testid="route-input"
                  />
                  <Button type="button" onClick={addRouteStop} variant="outline" data-testid="add-stop-btn">
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                
                {/* Route chips */}
                {formData.route.length > 0 && (
                  <div className="flex flex-wrap gap-2 p-3 bg-gray-50 rounded-lg min-h-[60px]">
                    {formData.route.map((stop, index) => (
                      <div
                        key={index}
                        draggable
                        onDragStart={() => handleDragStart(index)}
                        onDragOver={(e) => handleDragOver(e, index)}
                        onDragEnd={handleDragEnd}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#6B633C] text-white text-sm cursor-move ${
                          draggedIndex === index ? 'opacity-50' : ''
                        }`}
                      >
                        <GripVertical className="h-3 w-3 opacity-70" />
                        {index > 0 && <span className="opacity-70 mr-1">→</span>}
                        {stop}
                        <button
                          type="button"
                          onClick={() => removeRouteStop(index)}
                          className="ml-1 hover:bg-white/20 rounded-full p-0.5"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {formData.route.length === 0 && (
                  <p className="text-xs text-gray-400 mt-1">Add at least one stop to define the route</p>
                )}
              </div>

              {/* Departure Date */}
              <div>
                <Label htmlFor="departure_date">Departure Date</Label>
                <Input
                  id="departure_date"
                  type="date"
                  value={formData.departure_date}
                  onChange={(e) => setFormData(prev => ({ ...prev, departure_date: e.target.value }))}
                  required
                  data-testid="departure-date-input"
                />
              </div>

              {/* Vehicle */}
              <div>
                <Label>Vehicle (optional)</Label>
                <Select 
                  value={formData.vehicle_id || 'none'} 
                  onValueChange={(v) => setFormData(prev => ({ ...prev, vehicle_id: v === 'none' ? '' : v }))}
                >
                  <SelectTrigger data-testid="vehicle-select">
                    <SelectValue placeholder="Select vehicle" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No vehicle assigned</SelectItem>
                    {vehicles.map(v => (
                      <SelectItem key={v.id} value={v.id}>
                        {v.registration_number} - {v.vehicle_type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Driver */}
              <div>
                <Label>Driver (optional)</Label>
                <Select 
                  value={formData.driver_id || 'none'} 
                  onValueChange={(v) => setFormData(prev => ({ ...prev, driver_id: v === 'none' ? '' : v }))}
                >
                  <SelectTrigger data-testid="driver-select">
                    <SelectValue placeholder="Select driver" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No driver assigned</SelectItem>
                    {drivers.map(d => (
                      <SelectItem key={d.id} value={d.id}>
                        {d.name} - {d.phone}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Destination Warehouse */}
              <div>
                <Label>Destination Warehouse</Label>
                <p className="text-xs text-gray-500 mb-1">Parcels will be placed in this warehouse upon arrival</p>
                <Select 
                  value={formData.destination_warehouse_id || 'none'} 
                  onValueChange={(v) => setFormData(prev => ({ ...prev, destination_warehouse_id: v === 'none' ? '' : v }))}
                >
                  <SelectTrigger data-testid="destination-warehouse-select">
                    <SelectValue placeholder="Select destination warehouse" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No destination (All Warehouses)</SelectItem>
                    {warehouses.map(w => (
                      <SelectItem key={w.id} value={w.id}>
                        {w.name} {w.location ? `(${w.location})` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Notes */}
              <div>
                <Label htmlFor="notes">Notes (optional)</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  rows={3}
                  placeholder="Any additional notes..."
                  data-testid="notes-input"
                />
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="bg-[#6B633C] hover:bg-[#5a5332] text-white"
                  disabled={submitting}
                  data-testid="submit-trip-btn"
                >
                  {submitting ? 'Saving...' : editingTrip ? 'Update Trip' : 'Create Trip'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}

export default Trips;
