import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { Landing } from './pages/Landing';
import { Dashboard } from './pages/Dashboard';
import { Clients } from './pages/Clients';
import { Shipments } from './pages/Shipments';
import { LoadingStaging } from './pages/LoadingStaging';
import { Trips } from './pages/Trips';
import { TripDetail } from './pages/TripDetail';
import { Scanner } from './pages/Scanner';
import { Finance } from './pages/Finance';
import { Fleet } from './pages/Fleet';
import { ParcelIntake } from './pages/ParcelIntake';
import { Warehouse } from './pages/Warehouse';
import { Team } from './pages/Team';
import { Settings } from './pages/Settings';
import { Toaster } from './components/ui/sonner';
import './App.css';

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      {/* Single nested layout route - Layout mounts once, only page content re-renders */}
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/clients/new" element={<Clients />} />
        <Route path="/loading" element={<LoadingStaging />} />
        <Route path="/shipments" element={<Shipments />} />
        <Route path="/shipments/new" element={<Shipments />} />
        <Route path="/parcels/intake" element={<ParcelIntake />} />
        <Route path="/warehouse" element={<Warehouse />} />
        <Route path="/trips" element={<Trips />} />
        <Route path="/trips/new" element={<Trips />} />
        <Route path="/trips/:tripId" element={<TripDetail />} />
        <Route path="/scanner" element={<Scanner />} />
        <Route path="/finance" element={<Finance />} />
        <Route path="/fleet" element={<Fleet />} />
        <Route path="/team" element={<Team />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
