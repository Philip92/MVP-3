import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
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
import { 
  Plus, Search, MoreVertical, Edit, Trash2, Truck, Eye, User,
  AlertTriangle, CheckCircle, Clock, Shield, Car, CalendarClock,
  Bell, FileWarning, FileText, Upload
} from 'lucide-react';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

const vehicleStatusColors = {
  available: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  in_transit: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  repair: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
};

const driverStatusColors = {
  available: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  on_trip: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  on_leave: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  inactive: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
};

const vehicleComplianceLabels = {
  license_disk: 'License Disk',
  insurance: 'Insurance',
  roadworthy: 'Roadworthy',
  service: 'Service',
  custom: 'Custom'
};

const driverComplianceLabels = {
  license: 'License',
  work_permit: 'Work Permit',
  medical: 'Medical',
  prdp: 'PRDP',
  custom: 'Custom'
};

export function Fleet() {
  const [activeTab, setActiveTab] = useState('vehicles');
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [reminders, setReminders] = useState(null);
  const [allCompliance, setAllCompliance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  
  // Vehicle state
  const [vehicleDialogOpen, setVehicleDialogOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [vehicleDetailsOpen, setVehicleDetailsOpen] = useState(false);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [vehicleComplianceDialogOpen, setVehicleComplianceDialogOpen] = useState(false);
  
  // Driver state
  const [driverDialogOpen, setDriverDialogOpen] = useState(false);
  const [editingDriver, setEditingDriver] = useState(null);
  const [driverDetailsOpen, setDriverDetailsOpen] = useState(false);
  const [selectedDriver, setSelectedDriver] = useState(null);
  const [driverComplianceDialogOpen, setDriverComplianceDialogOpen] = useState(false);
  
  // Forms
  const [vehicleForm, setVehicleForm] = useState({
    name: '', registration_number: '', vin: '', make: '', model: '',
    year: '', max_weight_kg: '', max_volume_cbm: ''
  });
  
  const [driverForm, setDriverForm] = useState({
    name: '', phone: '', email: '', id_passport_number: '', nationality: ''
  });
  
  const [vehicleComplianceForm, setVehicleComplianceForm] = useState({
    item_type: 'license_disk', item_label: '', expiry_date: '',
    reminder_days_before: 30, provider: '', policy_number: '',
    file_name: '', file_type: '', file_data: ''
  });
  
  const [driverComplianceForm, setDriverComplianceForm] = useState({
    item_type: 'license', item_label: '', expiry_date: '',
    reminder_days_before: 30, license_number: '', issuing_country: '',
    file_name: '', file_type: '', file_data: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [vehiclesRes, driversRes, remindersRes, complianceRes] = await Promise.all([
        axios.get(`${API}/vehicles`, { withCredentials: true }),
        axios.get(`${API}/drivers`, { withCredentials: true }),
        axios.get(`${API}/reminders`, { withCredentials: true }),
        axios.get(`${API}/compliance/all`, { withCredentials: true })
      ]);
      setVehicles(vehiclesRes.data);
      setDrivers(driversRes.data);
      setReminders(remindersRes.data);
      setAllCompliance(complianceRes.data);
    } catch (error) {
      toast.error('Failed to fetch fleet data');
    } finally {
      setLoading(false);
    }
  };

  const fetchVehicleDetails = async (vehicleId) => {
    try {
      const response = await axios.get(`${API}/vehicles/${vehicleId}`, { withCredentials: true });
      setSelectedVehicle(response.data);
    } catch (error) {
      toast.error('Failed to fetch vehicle details');
    }
  };

  const fetchDriverDetails = async (driverId) => {
    try {
      const response = await axios.get(`${API}/drivers/${driverId}`, { withCredentials: true });
      setSelectedDriver(response.data);
    } catch (error) {
      toast.error('Failed to fetch driver details');
    }
  };

  // Vehicle handlers
  const handleVehicleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...vehicleForm,
        year: vehicleForm.year ? parseInt(vehicleForm.year) : null,
        max_weight_kg: vehicleForm.max_weight_kg ? parseFloat(vehicleForm.max_weight_kg) : null,
        max_volume_cbm: vehicleForm.max_volume_cbm ? parseFloat(vehicleForm.max_volume_cbm) : null
      };
      
      if (editingVehicle) {
        await axios.put(`${API}/vehicles/${editingVehicle.id}`, payload, { withCredentials: true });
        toast.success('Vehicle updated');
      } else {
        await axios.post(`${API}/vehicles`, payload, { withCredentials: true });
        toast.success('Vehicle added');
      }
      setVehicleDialogOpen(false);
      resetVehicleForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save vehicle');
    }
  };

  const handleDeleteVehicle = async (vehicleId) => {
    if (!window.confirm('Delete this vehicle and all compliance records?')) return;
    try {
      await axios.delete(`${API}/vehicles/${vehicleId}`, { withCredentials: true });
      toast.success('Vehicle deleted');
      setVehicleDetailsOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to delete vehicle');
    }
  };

  const handleVehicleComplianceSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/vehicles/${selectedVehicle.id}/compliance`, vehicleComplianceForm, { withCredentials: true });
      toast.success('Compliance item added');
      setVehicleComplianceDialogOpen(false);
      resetVehicleComplianceForm();
      fetchVehicleDetails(selectedVehicle.id);
      fetchData();
    } catch (error) {
      toast.error('Failed to add compliance item');
    }
  };

  const handleDeleteVehicleCompliance = async (complianceId) => {
    try {
      await axios.delete(`${API}/vehicles/${selectedVehicle.id}/compliance/${complianceId}`, { withCredentials: true });
      toast.success('Compliance item deleted');
      fetchVehicleDetails(selectedVehicle.id);
      fetchData();
    } catch (error) {
      toast.error('Failed to delete compliance item');
    }
  };

  // Driver handlers
  const handleDriverSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingDriver) {
        await axios.put(`${API}/drivers/${editingDriver.id}`, driverForm, { withCredentials: true });
        toast.success('Driver updated');
      } else {
        await axios.post(`${API}/drivers`, driverForm, { withCredentials: true });
        toast.success('Driver added');
      }
      setDriverDialogOpen(false);
      resetDriverForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save driver');
    }
  };

  const handleDeleteDriver = async (driverId) => {
    if (!window.confirm('Delete this driver and all compliance records?')) return;
    try {
      await axios.delete(`${API}/drivers/${driverId}`, { withCredentials: true });
      toast.success('Driver deleted');
      setDriverDetailsOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to delete driver');
    }
  };

  const handleDriverComplianceSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/drivers/${selectedDriver.id}/compliance`, driverComplianceForm, { withCredentials: true });
      toast.success('Compliance item added');
      setDriverComplianceDialogOpen(false);
      resetDriverComplianceForm();
      fetchDriverDetails(selectedDriver.id);
      fetchData();
    } catch (error) {
      toast.error('Failed to add compliance item');
    }
  };

  const handleDeleteDriverCompliance = async (complianceId) => {
    try {
      await axios.delete(`${API}/drivers/${selectedDriver.id}/compliance/${complianceId}`, { withCredentials: true });
      toast.success('Compliance item deleted');
      fetchDriverDetails(selectedDriver.id);
      fetchData();
    } catch (error) {
      toast.error('Failed to delete compliance item');
    }
  };

  // Reset forms
  const resetVehicleForm = () => {
    setVehicleForm({
      name: '', registration_number: '', vin: '', make: '', model: '',
      year: '', max_weight_kg: '', max_volume_cbm: ''
    });
    setEditingVehicle(null);
  };

  const resetDriverForm = () => {
    setDriverForm({
      name: '', phone: '', email: '', id_passport_number: '', nationality: ''
    });
    setEditingDriver(null);
  };

  const resetVehicleComplianceForm = () => {
    setVehicleComplianceForm({
      item_type: 'license_disk', item_label: '', expiry_date: '',
      reminder_days_before: 30, provider: '', policy_number: '',
      file_name: '', file_type: '', file_data: ''
    });
  };

  const resetDriverComplianceForm = () => {
    setDriverComplianceForm({
      item_type: 'license', item_label: '', expiry_date: '',
      reminder_days_before: 30, license_number: '', issuing_country: '',
      file_name: '', file_type: '', file_data: ''
    });
  };

  const handleVehicleComplianceFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(',')[1];
      setVehicleComplianceForm({
        ...vehicleComplianceForm,
        file_name: file.name,
        file_type: file.type,
        file_data: base64
      });
    };
    reader.readAsDataURL(file);
  };

  const handleDriverComplianceFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(',')[1];
      setDriverComplianceForm({
        ...driverComplianceForm,
        file_name: file.name,
        file_type: file.type,
        file_data: base64
      });
    };
    reader.readAsDataURL(file);
  };

  const getComplianceStatusColorByStatus = (statusColor) => {
    if (statusColor === 'red') return 'text-red-600 bg-red-100 dark:bg-red-900/30 border-red-200';
    if (statusColor === 'yellow') return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 border-yellow-200';
    return 'text-green-600 bg-green-100 dark:bg-green-900/30 border-green-200';
  };

  const openEditVehicle = (vehicle) => {
    setEditingVehicle(vehicle);
    setVehicleForm({
      name: vehicle.name, registration_number: vehicle.registration_number,
      vin: vehicle.vin || '', make: vehicle.make || '', model: vehicle.model || '',
      year: vehicle.year || '', max_weight_kg: vehicle.max_weight_kg || '',
      max_volume_cbm: vehicle.max_volume_cbm || ''
    });
    setVehicleDialogOpen(true);
  };

  const openEditDriver = (driver) => {
    setEditingDriver(driver);
    setDriverForm({
      name: driver.name, phone: driver.phone,
      email: driver.email || '', id_passport_number: driver.id_passport_number || '',
      nationality: driver.nationality || ''
    });
    setDriverDialogOpen(true);
  };

  const getComplianceStatusColor = (expiryDate) => {
    const today = new Date().toISOString().split('T')[0];
    const weekLater = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    
    if (expiryDate < today) return 'text-red-600 bg-red-100 dark:bg-red-900/30';
    if (expiryDate <= weekLater) return 'text-orange-600 bg-orange-100 dark:bg-orange-900/30';
    return 'text-green-600 bg-green-100 dark:bg-green-900/30';
  };

  const filteredVehicles = vehicles.filter(v =>
    v.name.toLowerCase().includes(search.toLowerCase()) ||
    v.registration_number.toLowerCase().includes(search.toLowerCase())
  );

  const filteredDrivers = drivers.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.phone.includes(search)
  );

  return (
    <>
      <div className="space-y-6" data-testid="fleet-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold">Fleet Management</h1>
            <p className="text-muted-foreground mt-1">Manage vehicles, drivers, and compliance</p>
          </div>
        </div>

        {/* Compliance Alerts */}
        {reminders && (reminders.summary.overdue > 0 || reminders.summary.due_this_week > 0) && (
          <Card className="border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-orange-600" />
                <div className="flex-1">
                  <p className="font-medium">Compliance Attention Required</p>
                  <p className="text-sm text-muted-foreground">
                    {reminders.summary.overdue > 0 && (
                      <span className="text-red-600 font-semibold">{reminders.summary.overdue} overdue</span>
                    )}
                    {reminders.summary.overdue > 0 && reminders.summary.due_this_week > 0 && ' • '}
                    {reminders.summary.due_this_week > 0 && (
                      <span className="text-orange-600">{reminders.summary.due_this_week} due this week</span>
                    )}
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={() => setActiveTab('reminders')}>
                  View All
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full max-w-lg grid-cols-3">
            <TabsTrigger value="vehicles" className="flex items-center gap-2">
              <Truck className="h-4 w-4" />
              Vehicles ({vehicles.length})
            </TabsTrigger>
            <TabsTrigger value="drivers" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Drivers ({drivers.length})
            </TabsTrigger>
            <TabsTrigger value="reminders" className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              Reminders
              {reminders?.summary.overdue > 0 && (
                <Badge variant="destructive" className="ml-1 h-5 w-5 p-0 flex items-center justify-center text-xs">
                  {reminders.summary.overdue}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Vehicles Tab */}
          <TabsContent value="vehicles" className="mt-6 space-y-4">
            <div className="flex flex-col sm:flex-row gap-4 justify-between">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search vehicles..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="vehicle-search"
                />
              </div>
              <Dialog open={vehicleDialogOpen} onOpenChange={(open) => { setVehicleDialogOpen(open); if (!open) resetVehicleForm(); }}>
                <DialogTrigger asChild>
                  <Button data-testid="add-vehicle-btn">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Vehicle
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle>{editingVehicle ? 'Edit Vehicle' : 'Add Vehicle'}</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleVehicleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2 col-span-2">
                        <Label>Name *</Label>
                        <Input
                          value={vehicleForm.name}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, name: e.target.value })}
                          placeholder="e.g., MAN TGM Box Truck"
                          required
                          data-testid="vehicle-name-input"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Registration *</Label>
                        <Input
                          value={vehicleForm.registration_number}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, registration_number: e.target.value })}
                          placeholder="e.g., CA 123-456"
                          required
                          data-testid="vehicle-reg-input"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>VIN</Label>
                        <Input
                          value={vehicleForm.vin}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, vin: e.target.value })}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Make</Label>
                        <Input
                          value={vehicleForm.make}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, make: e.target.value })}
                          placeholder="e.g., MAN"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Model</Label>
                        <Input
                          value={vehicleForm.model}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, model: e.target.value })}
                          placeholder="e.g., TGM"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Year</Label>
                        <Input
                          type="number"
                          value={vehicleForm.year}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, year: e.target.value })}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Max Weight (kg)</Label>
                        <Input
                          type="number"
                          value={vehicleForm.max_weight_kg}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, max_weight_kg: e.target.value })}
                        />
                      </div>
                      <div className="space-y-2 col-span-2">
                        <Label>Max Volume (CBM)</Label>
                        <Input
                          type="number"
                          step="0.1"
                          value={vehicleForm.max_volume_cbm}
                          onChange={(e) => setVehicleForm({ ...vehicleForm, max_volume_cbm: e.target.value })}
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button type="submit" data-testid="save-vehicle-btn">
                        {editingVehicle ? 'Update' : 'Add'} Vehicle
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </div>

            <Card>
              <CardContent className="p-0">
                {loading ? (
                  <div className="p-6 space-y-3">
                    {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
                  </div>
                ) : filteredVehicles.length > 0 ? (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Vehicle</TableHead>
                          <TableHead className="hidden sm:table-cell">Registration</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="hidden md:table-cell">Capacity</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredVehicles.map((vehicle) => (
                          <TableRow key={vehicle.id} data-testid={`vehicle-row-${vehicle.id}`}>
                            <TableCell>
                              <div className="flex items-center gap-3">
                                <div className="h-9 w-9 rounded bg-primary/10 flex items-center justify-center">
                                  <Truck className="h-5 w-5 text-primary" />
                                </div>
                                <div>
                                  <p className="font-medium">{vehicle.name}</p>
                                  <p className="text-sm text-muted-foreground sm:hidden">
                                    {vehicle.registration_number}
                                  </p>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="hidden sm:table-cell font-mono">
                              {vehicle.registration_number}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Badge className={cn('capitalize', vehicleStatusColors[vehicle.status])}>
                                  {vehicle.status.replace('_', ' ')}
                                </Badge>
                                {vehicle.compliance_issues > 0 && (
                                  <Badge variant="destructive" className="h-5 w-5 p-0 flex items-center justify-center">
                                    {vehicle.compliance_issues}
                                  </Badge>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                              {vehicle.max_weight_kg ? `${vehicle.max_weight_kg} kg` : '-'}
                              {vehicle.max_volume_cbm && ` / ${vehicle.max_volume_cbm} CBM`}
                            </TableCell>
                            <TableCell className="text-right">
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem onClick={() => { fetchVehicleDetails(vehicle.id); setVehicleDetailsOpen(true); }}>
                                    <Eye className="h-4 w-4 mr-2" />
                                    View Details
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => openEditVehicle(vehicle)}>
                                    <Edit className="h-4 w-4 mr-2" />
                                    Edit
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => handleDeleteVehicle(vehicle.id)} className="text-destructive">
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
                    <Truck className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No vehicles found</p>
                    <Button variant="link" onClick={() => setVehicleDialogOpen(true)} className="mt-2">
                      Add your first vehicle
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Drivers Tab */}
          <TabsContent value="drivers" className="mt-6 space-y-4">
            <div className="flex flex-col sm:flex-row gap-4 justify-between">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search drivers..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="driver-search"
                />
              </div>
              <Dialog open={driverDialogOpen} onOpenChange={(open) => { setDriverDialogOpen(open); if (!open) resetDriverForm(); }}>
                <DialogTrigger asChild>
                  <Button data-testid="add-driver-btn">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Driver
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>{editingDriver ? 'Edit Driver' : 'Add Driver'}</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleDriverSubmit} className="space-y-4">
                    <div className="space-y-2">
                      <Label>Name *</Label>
                      <Input
                        value={driverForm.name}
                        onChange={(e) => setDriverForm({ ...driverForm, name: e.target.value })}
                        required
                        data-testid="driver-name-input"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Phone *</Label>
                        <Input
                          value={driverForm.phone}
                          onChange={(e) => setDriverForm({ ...driverForm, phone: e.target.value })}
                          required
                          data-testid="driver-phone-input"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Email</Label>
                        <Input
                          type="email"
                          value={driverForm.email}
                          onChange={(e) => setDriverForm({ ...driverForm, email: e.target.value })}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>ID/Passport</Label>
                        <Input
                          value={driverForm.id_passport_number}
                          onChange={(e) => setDriverForm({ ...driverForm, id_passport_number: e.target.value })}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Nationality</Label>
                        <Input
                          value={driverForm.nationality}
                          onChange={(e) => setDriverForm({ ...driverForm, nationality: e.target.value })}
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button type="submit" data-testid="save-driver-btn">
                        {editingDriver ? 'Update' : 'Add'} Driver
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </div>

            <Card>
              <CardContent className="p-0">
                {loading ? (
                  <div className="p-6 space-y-3">
                    {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
                  </div>
                ) : filteredDrivers.length > 0 ? (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Driver</TableHead>
                          <TableHead className="hidden sm:table-cell">Phone</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredDrivers.map((driver) => (
                          <TableRow key={driver.id} data-testid={`driver-row-${driver.id}`}>
                            <TableCell>
                              <div className="flex items-center gap-3">
                                <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
                                  <User className="h-5 w-5 text-primary" />
                                </div>
                                <div>
                                  <p className="font-medium">{driver.name}</p>
                                  <p className="text-sm text-muted-foreground sm:hidden">
                                    {driver.phone}
                                  </p>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="hidden sm:table-cell">
                              {driver.phone}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Badge className={cn('capitalize', driverStatusColors[driver.status])}>
                                  {driver.status.replace('_', ' ')}
                                </Badge>
                                {driver.compliance_issues > 0 && (
                                  <Badge variant="destructive" className="h-5 w-5 p-0 flex items-center justify-center">
                                    {driver.compliance_issues}
                                  </Badge>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="text-right">
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem onClick={() => { fetchDriverDetails(driver.id); setDriverDetailsOpen(true); }}>
                                    <Eye className="h-4 w-4 mr-2" />
                                    View Details
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => openEditDriver(driver)}>
                                    <Edit className="h-4 w-4 mr-2" />
                                    Edit
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={() => handleDeleteDriver(driver.id)} className="text-destructive">
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
                    <User className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No drivers found</p>
                    <Button variant="link" onClick={() => setDriverDialogOpen(true)} className="mt-2">
                      Add your first driver
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reminders Tab - All Compliance Items Sorted by Expiry */}
          <TabsContent value="reminders" className="mt-6 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  All Compliance Items
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Sorted by expiry date. Red = expired or within 30 days, Yellow = within 60 days, Green = more than 60 days
                </p>
              </CardHeader>
              <CardContent>
                {allCompliance.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No compliance items found</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {allCompliance.map((item, i) => (
                      <div 
                        key={`${item.type}-${item.compliance_id}`} 
                        className={cn(
                          "flex items-center justify-between p-3 rounded-lg border",
                          getComplianceStatusColorByStatus(item.status_color)
                        )}
                      >
                        <div className="flex items-center gap-3">
                          {item.type === 'vehicle' ? (
                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                              <Truck className="h-5 w-5 text-primary" />
                            </div>
                          ) : (
                            <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                              <User className="h-5 w-5 text-blue-600" />
                            </div>
                          )}
                          <div>
                            <p className="font-medium">{item.entity_name}</p>
                            <p className="text-sm">
                              {item.item_label}
                              {item.registration && <span className="text-muted-foreground"> • {item.registration}</span>}
                              {item.phone && <span className="text-muted-foreground"> • {item.phone}</span>}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {item.provider && `Provider: ${item.provider}`}
                              {item.policy_number && ` • Policy: ${item.policy_number}`}
                              {item.license_number && `License: ${item.license_number}`}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          {item.file_name && (
                            <FileText className="h-4 w-4 text-muted-foreground" title={item.file_name} />
                          )}
                          <div className="text-right">
                            <p className="font-medium">{item.expiry_date}</p>
                            <Badge 
                              className={cn(
                                'capitalize text-xs',
                                item.status_color === 'red' && 'bg-red-500 text-white',
                                item.status_color === 'yellow' && 'bg-yellow-500 text-white',
                                item.status_color === 'green' && 'bg-green-500 text-white'
                              )}
                            >
                              {item.status_color === 'red' ? 'Urgent' : item.status_color === 'yellow' ? 'Soon' : 'OK'}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Vehicle Details Sheet */}
        <Sheet open={vehicleDetailsOpen} onOpenChange={setVehicleDetailsOpen}>
          <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Vehicle Details</SheetTitle>
            </SheetHeader>
            {selectedVehicle && (
              <div className="mt-6 space-y-6">
                <div className="flex items-center gap-4">
                  <div className="h-14 w-14 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Truck className="h-7 w-7 text-primary" />
                  </div>
                  <div>
                    <p className="font-bold text-lg">{selectedVehicle.name}</p>
                    <p className="font-mono text-muted-foreground">{selectedVehicle.registration_number}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div><p className="text-sm text-muted-foreground">Make</p><p className="font-medium">{selectedVehicle.make || '-'}</p></div>
                  <div><p className="text-sm text-muted-foreground">Model</p><p className="font-medium">{selectedVehicle.model || '-'}</p></div>
                  <div><p className="text-sm text-muted-foreground">Year</p><p className="font-medium">{selectedVehicle.year || '-'}</p></div>
                  <div><p className="text-sm text-muted-foreground">Status</p><Badge className={cn('capitalize mt-1', vehicleStatusColors[selectedVehicle.status])}>{selectedVehicle.status}</Badge></div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-heading font-semibold">Compliance</h3>
                    <Dialog open={vehicleComplianceDialogOpen} onOpenChange={(open) => { setVehicleComplianceDialogOpen(open); if (!open) resetVehicleComplianceForm(); }}>
                      <DialogTrigger asChild>
                        <Button size="sm" variant="outline">
                          <Plus className="h-4 w-4 mr-1" />
                          Add
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Add Compliance Item</DialogTitle>
                        </DialogHeader>
                        <form onSubmit={handleVehicleComplianceSubmit} className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Type</Label>
                              <Select value={vehicleComplianceForm.item_type} onValueChange={(v) => setVehicleComplianceForm({ ...vehicleComplianceForm, item_type: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                  {Object.entries(vehicleComplianceLabels).map(([k, v]) => (
                                    <SelectItem key={k} value={k}>{v}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2">
                              <Label>Expiry Date *</Label>
                              <Input type="date" value={vehicleComplianceForm.expiry_date} onChange={(e) => setVehicleComplianceForm({ ...vehicleComplianceForm, expiry_date: e.target.value })} required />
                            </div>
                          </div>
                          {vehicleComplianceForm.item_type === 'custom' && (
                            <div className="space-y-2">
                              <Label>Label</Label>
                              <Input value={vehicleComplianceForm.item_label} onChange={(e) => setVehicleComplianceForm({ ...vehicleComplianceForm, item_label: e.target.value })} placeholder="e.g., Cross-border permit" />
                            </div>
                          )}
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Provider</Label>
                              <Input value={vehicleComplianceForm.provider} onChange={(e) => setVehicleComplianceForm({ ...vehicleComplianceForm, provider: e.target.value })} />
                            </div>
                            <div className="space-y-2">
                              <Label>Policy/Ref #</Label>
                              <Input value={vehicleComplianceForm.policy_number} onChange={(e) => setVehicleComplianceForm({ ...vehicleComplianceForm, policy_number: e.target.value })} />
                            </div>
                          </div>
                          <div className="space-y-2">
                            <Label>Upload Document (PDF or Image)</Label>
                            <Input 
                              type="file" 
                              accept=".pdf,.png,.jpg,.jpeg" 
                              onChange={handleVehicleComplianceFileSelect}
                            />
                            {vehicleComplianceForm.file_name && (
                              <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <FileText className="h-3 w-3" /> {vehicleComplianceForm.file_name}
                              </p>
                            )}
                          </div>
                          <DialogFooter>
                            <Button type="submit">Add Item</Button>
                          </DialogFooter>
                        </form>
                      </DialogContent>
                    </Dialog>
                  </div>

                  {selectedVehicle.compliance?.length > 0 ? (
                    <div className="space-y-2">
                      {selectedVehicle.compliance.map((item) => (
                        <div key={item.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            {item.file_name ? (
                              <div className="h-10 w-10 rounded bg-muted flex items-center justify-center">
                                <FileText className="h-5 w-5 text-muted-foreground" />
                              </div>
                            ) : (
                              <div className="h-10 w-10 rounded bg-muted/50 flex items-center justify-center">
                                <Shield className="h-5 w-5 text-muted-foreground" />
                              </div>
                            )}
                            <div>
                              <p className="font-medium">{item.item_label || vehicleComplianceLabels[item.item_type]}</p>
                              <p className="text-sm text-muted-foreground">
                                Expires: <span className={cn('font-mono', getComplianceStatusColor(item.expiry_date).split(' ')[0])}>{item.expiry_date}</span>
                                {item.provider && ` • ${item.provider}`}
                              </p>
                            </div>
                          </div>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteVehicleCompliance(item.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">No compliance items</p>
                  )}
                </div>
              </div>
            )}
          </SheetContent>
        </Sheet>

        {/* Driver Details Sheet */}
        <Sheet open={driverDetailsOpen} onOpenChange={setDriverDetailsOpen}>
          <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Driver Details</SheetTitle>
            </SheetHeader>
            {selectedDriver && (
              <div className="mt-6 space-y-6">
                <div className="flex items-center gap-4">
                  <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-7 w-7 text-primary" />
                  </div>
                  <div>
                    <p className="font-bold text-lg">{selectedDriver.name}</p>
                    <p className="text-muted-foreground">{selectedDriver.phone}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div><p className="text-sm text-muted-foreground">Email</p><p className="font-medium">{selectedDriver.email || '-'}</p></div>
                  <div><p className="text-sm text-muted-foreground">ID/Passport</p><p className="font-medium">{selectedDriver.id_passport_number || '-'}</p></div>
                  <div><p className="text-sm text-muted-foreground">Nationality</p><p className="font-medium">{selectedDriver.nationality || '-'}</p></div>
                  <div><p className="text-sm text-muted-foreground">Status</p><Badge className={cn('capitalize mt-1', driverStatusColors[selectedDriver.status])}>{selectedDriver.status}</Badge></div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-heading font-semibold">Compliance</h3>
                    <Dialog open={driverComplianceDialogOpen} onOpenChange={(open) => { setDriverComplianceDialogOpen(open); if (!open) resetDriverComplianceForm(); }}>
                      <DialogTrigger asChild>
                        <Button size="sm" variant="outline">
                          <Plus className="h-4 w-4 mr-1" />
                          Add
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Add Compliance Item</DialogTitle>
                        </DialogHeader>
                        <form onSubmit={handleDriverComplianceSubmit} className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Type</Label>
                              <Select value={driverComplianceForm.item_type} onValueChange={(v) => setDriverComplianceForm({ ...driverComplianceForm, item_type: v })}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                  {Object.entries(driverComplianceLabels).map(([k, v]) => (
                                    <SelectItem key={k} value={k}>{v}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2">
                              <Label>Expiry Date *</Label>
                              <Input type="date" value={driverComplianceForm.expiry_date} onChange={(e) => setDriverComplianceForm({ ...driverComplianceForm, expiry_date: e.target.value })} required />
                            </div>
                          </div>
                          {driverComplianceForm.item_type === 'custom' && (
                            <div className="space-y-2">
                              <Label>Label</Label>
                              <Input value={driverComplianceForm.item_label} onChange={(e) => setDriverComplianceForm({ ...driverComplianceForm, item_label: e.target.value })} />
                            </div>
                          )}
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>License #</Label>
                              <Input value={driverComplianceForm.license_number} onChange={(e) => setDriverComplianceForm({ ...driverComplianceForm, license_number: e.target.value })} />
                            </div>
                            <div className="space-y-2">
                              <Label>Issuing Country</Label>
                              <Input value={driverComplianceForm.issuing_country} onChange={(e) => setDriverComplianceForm({ ...driverComplianceForm, issuing_country: e.target.value })} />
                            </div>
                          </div>
                          <div className="space-y-2">
                            <Label>Upload Document (PDF or Image)</Label>
                            <Input 
                              type="file" 
                              accept=".pdf,.png,.jpg,.jpeg" 
                              onChange={handleDriverComplianceFileSelect}
                            />
                            {driverComplianceForm.file_name && (
                              <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <FileText className="h-3 w-3" /> {driverComplianceForm.file_name}
                              </p>
                            )}
                          </div>
                          <DialogFooter>
                            <Button type="submit">Add Item</Button>
                          </DialogFooter>
                        </form>
                      </DialogContent>
                    </Dialog>
                  </div>

                  {selectedDriver.compliance?.length > 0 ? (
                    <div className="space-y-2">
                      {selectedDriver.compliance.map((item) => (
                        <div key={item.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            {item.file_name ? (
                              <div className="h-10 w-10 rounded bg-muted flex items-center justify-center">
                                <FileText className="h-5 w-5 text-muted-foreground" />
                              </div>
                            ) : (
                              <div className="h-10 w-10 rounded bg-muted/50 flex items-center justify-center">
                                <Shield className="h-5 w-5 text-muted-foreground" />
                              </div>
                            )}
                            <div>
                              <p className="font-medium">{item.item_label || driverComplianceLabels[item.item_type]}</p>
                              <p className="text-sm text-muted-foreground">
                                Expires: <span className={cn('font-mono', getComplianceStatusColor(item.expiry_date).split(' ')[0])}>{item.expiry_date}</span>
                                {item.license_number && ` • ${item.license_number}`}
                              </p>
                            </div>
                          </div>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteDriverCompliance(item.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">No compliance items</p>
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
