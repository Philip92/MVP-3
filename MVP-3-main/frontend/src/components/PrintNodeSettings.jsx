import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Printer, Check, Trash2, Loader2, RefreshCw, Wifi, WifiOff, Eye, EyeOff } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function PrintNodeSettings() {
  const [config, setConfig] = useState(null);
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [printers, setPrinters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchingPrinters, setFetchingPrinters] = useState(false);
  const [printJobs, setPrintJobs] = useState([]);

  useEffect(() => {
    fetchConfig();
    fetchJobs();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await axios.get(`${API}/printnode/config`, { withCredentials: true });
      setConfig(response.data);
      if (response.data.configured && response.data.api_key_set) {
        fetchPrinters();
      }
    } catch (error) {
      // Config doesn't exist yet, that's ok
    }
  };

  const fetchPrinters = async () => {
    setFetchingPrinters(true);
    try {
      const response = await axios.get(`${API}/printnode/printers`, { withCredentials: true });
      setPrinters(response.data.printers || []);
    } catch (error) {
      if (error.response?.status !== 400) {
        toast.error('Failed to fetch printers');
      }
    } finally {
      setFetchingPrinters(false);
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API}/printnode/jobs`, { withCredentials: true });
      setPrintJobs(response.data.jobs || []);
    } catch (error) {
      // Ignore
    }
  };

  const handleSaveKey = async () => {
    if (!apiKey.trim()) {
      toast.error('Please enter your PrintNode API key');
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.post(`${API}/printnode/config`, {
        api_key: apiKey
      }, { withCredentials: true });
      
      toast.success(`Connected as ${response.data.account_name || response.data.account_email}`);
      setApiKey('');
      fetchConfig();
      fetchPrinters();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save API key');
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (printer) => {
    try {
      await axios.post(`${API}/printnode/default-printer`, {
        printer_id: printer.id,
        printer_name: printer.name
      }, { withCredentials: true });
      toast.success(`Default printer set to ${printer.name}`);
      fetchConfig();
    } catch (error) {
      toast.error('Failed to set default printer');
    }
  };

  const handleRemoveConfig = async () => {
    if (!window.confirm('Remove PrintNode configuration? This will disable printing.')) return;
    try {
      await axios.delete(`${API}/printnode/config`, { withCredentials: true });
      toast.success('PrintNode configuration removed');
      setConfig(null);
      setPrinters([]);
      setApiKey('');
    } catch (error) {
      toast.error('Failed to remove configuration');
    }
  };

  const handleTestPrint = async () => {
    if (!config?.default_printer_id) {
      toast.error('Please set a default printer first');
      return;
    }
    
    setLoading(true);
    try {
      // Create a simple test PDF in base64
      const testContent = btoa('Test print from Servex Holdings - ' + new Date().toISOString());
      
      await axios.post(`${API}/printnode/print`, {
        title: 'Servex Test Print',
        content_type: 'raw_uri',
        content: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',
        source: 'test',
        copies: 1
      }, { withCredentials: true });
      
      toast.success('Test print job submitted');
      fetchJobs();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Test print failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* API Key Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Printer className="h-5 w-5" />
            PrintNode Configuration
          </CardTitle>
          <CardDescription>
            Connect your PrintNode account to enable direct label and invoice printing from Servex.
            Get your API key from{' '}
            <a href="https://app.printnode.com/account/apikeys" target="_blank" rel="noopener noreferrer" className="text-[#6B633C] underline">
              printnode.com/account/apikeys
            </a>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {config?.configured ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Badge className="bg-green-100 text-green-700 border-0">
                  <Wifi className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
                <span className="text-sm text-muted-foreground">
                  API Key: {config.api_key_preview}
                </span>
                {config.default_printer_name && (
                  <Badge variant="outline" className="text-xs">
                    <Printer className="h-3 w-3 mr-1" />
                    Default: {config.default_printer_name}
                  </Badge>
                )}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleTestPrint} disabled={loading || !config.default_printer_id}>
                  {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Printer className="h-4 w-4 mr-1" />}
                  Test Print
                </Button>
                <Button variant="outline" size="sm" onClick={() => { fetchPrinters(); toast.info('Refreshing printer list...'); }}>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh Printers
                </Button>
                <Button variant="destructive" size="sm" onClick={handleRemoveConfig}>
                  <Trash2 className="h-4 w-4 mr-1" />
                  Disconnect
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-muted-foreground">
                  <WifiOff className="h-3 w-3 mr-1" />
                  Not Connected
                </Badge>
              </div>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Input
                    type={showKey ? "text" : "password"}
                    placeholder="Enter your PrintNode API key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveKey()}
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <Button onClick={handleSaveKey} disabled={loading} className="bg-[#6B633C] hover:bg-[#5a5332]">
                  {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Check className="h-4 w-4 mr-1" />}
                  Connect
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Sign up at <a href="https://www.printnode.com" target="_blank" rel="noopener noreferrer" className="underline">printnode.com</a>, 
                install the PrintNode client on the computer connected to your printer, then paste your API key above.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Printers */}
      {config?.configured && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Available Printers</CardTitle>
            <CardDescription>
              Select a default printer for label and invoice printing. Printers show from computers with PrintNode client installed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {fetchingPrinters ? (
              <div className="flex items-center justify-center py-6 text-muted-foreground">
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Loading printers...
              </div>
            ) : printers.length === 0 ? (
              <div className="text-center py-6 text-muted-foreground">
                <Printer className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="font-medium">No printers found</p>
                <p className="text-sm mt-1">Make sure PrintNode client is installed and running on the computer connected to your printer.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {printers.map(printer => (
                  <div 
                    key={printer.id} 
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      config.default_printer_id === printer.id 
                        ? 'border-[#6B633C] bg-[#EDEAE5]/30' 
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Printer className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium text-sm">{printer.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {printer.computer_name} • {printer.state || 'unknown'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={printer.state === 'online' ? 'default' : 'secondary'} className="text-xs">
                        {printer.state || 'offline'}
                      </Badge>
                      {config.default_printer_id === printer.id ? (
                        <Badge className="bg-[#6B633C] text-white border-0">Default</Badge>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => handleSetDefault(printer)}>
                          Set Default
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Recent Print Jobs */}
      {config?.configured && printJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Print Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {printJobs.slice(0, 10).map(job => (
                <div key={job.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium">{job.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(job.created_at).toLocaleString()} • {job.source}
                    </p>
                  </div>
                  <Badge variant="outline" className="text-xs capitalize">
                    {job.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
