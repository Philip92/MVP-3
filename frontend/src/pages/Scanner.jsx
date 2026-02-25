import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { ScanLine, X, Package, Check, Loader2, Keyboard, Camera, MapPin, User } from 'lucide-react';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

export function Scanner() {
  const [mode, setMode] = useState('camera'); // 'camera' or 'manual'
  const [barcode, setBarcode] = useState('');
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (mode === 'manual' && inputRef.current) {
      inputRef.current.focus();
    }
  }, [mode]);

  const handleScan = async (code) => {
    if (!code.trim()) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`${API}/pieces/scan/${encodeURIComponent(code.trim())}`, {
        withCredentials: true
      });
      setResult(response.data);
      setScanning(false);
      toast.success('Barcode found!');
    } catch (error) {
      if (error.response?.status === 404) {
        toast.error('Barcode not found');
      } else {
        toast.error('Failed to scan barcode');
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkLoaded = async () => {
    if (!result?.piece?.id) return;
    
    try {
      await axios.put(`${API}/pieces/${result.piece.id}/load`, {}, {
        withCredentials: true
      });
      toast.success('Piece marked as loaded');
      // Update local state
      setResult(prev => ({
        ...prev,
        piece: { ...prev.piece, loaded_at: new Date().toISOString() }
      }));
    } catch (error) {
      toast.error('Failed to mark as loaded');
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    handleScan(barcode);
    setBarcode('');
  };

  const clearResult = () => {
    setResult(null);
    setBarcode('');
    if (mode === 'manual' && inputRef.current) {
      inputRef.current.focus();
    }
  };

  const statusColors = {
    warehouse: 'status-warehouse',
    staged: 'status-staged',
    loaded: 'status-loaded',
    in_transit: 'status-in-transit',
    delivered: 'status-delivered'
  };

  return (
    <>
      <div className="max-w-lg mx-auto space-y-6" data-testid="scanner-page">
        {/* Header */}
        <div className="text-center">
          <h1 className="font-heading text-2xl sm:text-3xl font-bold">Barcode Scanner</h1>
          <p className="text-muted-foreground mt-1">Scan or enter barcodes to look up shipment pieces</p>
        </div>

        {/* Mode Toggle */}
        <div className="flex gap-2 justify-center">
          <Button
            variant={mode === 'camera' ? 'default' : 'outline'}
            onClick={() => setMode('camera')}
            data-testid="camera-mode-btn"
          >
            <Camera className="h-4 w-4 mr-2" />
            Camera
          </Button>
          <Button
            variant={mode === 'manual' ? 'default' : 'outline'}
            onClick={() => setMode('manual')}
            data-testid="manual-mode-btn"
          >
            <Keyboard className="h-4 w-4 mr-2" />
            Manual Entry
          </Button>
        </div>

        {/* Scanner Area */}
        {!result && (
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              {mode === 'camera' ? (
                /* Camera Scanner (Simulated) */
                <div className="relative aspect-square bg-black">
                  {/* Viewfinder */}
                  <div className="absolute inset-8 border-2 border-white/50 rounded-lg">
                    {/* Corner markers */}
                    <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-primary rounded-tl-lg" />
                    <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-primary rounded-tr-lg" />
                    <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-primary rounded-bl-lg" />
                    <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-primary rounded-br-lg" />
                    
                    {/* Scan Line Animation */}
                    {scanning && (
                      <div className="absolute left-2 right-2 h-1 bg-primary/80 rounded scan-line" />
                    )}
                  </div>

                  {/* Controls Overlay */}
                  <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 to-transparent">
                    {scanning ? (
                      <Button
                        variant="secondary"
                        className="w-full"
                        onClick={() => setScanning(false)}
                        data-testid="stop-scan-btn"
                      >
                        <X className="h-4 w-4 mr-2" />
                        Stop Scanning
                      </Button>
                    ) : (
                      <Button
                        className="w-full"
                        onClick={() => setScanning(true)}
                        data-testid="start-scan-btn"
                      >
                        <ScanLine className="h-4 w-4 mr-2" />
                        Start Scanning
                      </Button>
                    )}
                  </div>

                  {/* Instructions */}
                  <div className="absolute top-4 left-0 right-0 text-center">
                    <p className="text-white/80 text-sm px-4">
                      {scanning
                        ? 'Position barcode within the frame'
                        : 'Tap to start scanning'}
                    </p>
                  </div>
                </div>
              ) : (
                /* Manual Entry */
                <div className="p-6">
                  <form onSubmit={handleManualSubmit} className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Enter Barcode</label>
                      <Input
                        ref={inputRef}
                        value={barcode}
                        onChange={(e) => setBarcode(e.target.value.toUpperCase())}
                        placeholder="e.g., S27-001-01 or TEMP-123456"
                        className="text-center font-mono text-lg h-12"
                        data-testid="barcode-input"
                      />
                    </div>
                    <Button
                      type="submit"
                      className="w-full"
                      disabled={!barcode.trim() || loading}
                      data-testid="lookup-btn"
                    >
                      {loading ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <ScanLine className="h-4 w-4 mr-2" />
                      )}
                      Look Up Barcode
                    </Button>
                  </form>

                  <div className="mt-6 pt-6 border-t">
                    <p className="text-sm text-muted-foreground text-center">
                      Barcode format: <code className="bg-muted px-1 rounded">TRIP-SEQ-PIECE</code>
                    </p>
                    <p className="text-xs text-muted-foreground text-center mt-1">
                      Example: S27-001-01, TEMP-123456
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Result Card */}
        {result && (
          <Card className="overflow-hidden" data-testid="scan-result">
            <div className="bg-primary p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-lg bg-white/20 flex items-center justify-center">
                    <Package className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="font-mono font-bold text-white text-lg">
                      {result.piece.barcode}
                    </p>
                    <p className="text-white/80 text-sm">
                      Piece #{result.piece.piece_number}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearResult}
                  className="text-white hover:bg-white/20"
                  data-testid="close-result-btn"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            </div>

            <CardContent className="p-4 space-y-4">
              {/* Piece Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Weight</p>
                  <p className="font-mono font-semibold">{result.piece.weight} kg</p>
                </div>
                {result.piece.length_cm && (
                  <div>
                    <p className="text-sm text-muted-foreground">Dimensions</p>
                    <p className="font-mono text-sm">
                      {result.piece.length_cm} × {result.piece.width_cm} × {result.piece.height_cm} cm
                    </p>
                  </div>
                )}
              </div>

              {/* Shipment Info */}
              <div className="border-t pt-4">
                <h4 className="font-heading font-semibold mb-3">Shipment Details</h4>
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <MapPin className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium">{result.shipment.destination}</p>
                      <p className="text-sm text-muted-foreground">{result.shipment.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <User className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{result.client?.name || 'Unknown Client'}</p>
                      {result.client?.phone && (
                        <p className="text-sm text-muted-foreground">{result.client.phone}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Status */}
              <div className="flex items-center justify-between pt-4 border-t">
                <div>
                  <p className="text-sm text-muted-foreground">Shipment Status</p>
                  <Badge className={cn('mt-1 capitalize', statusColors[result.shipment.status])}>
                    {result.shipment.status.replace('_', ' ')}
                  </Badge>
                </div>
                {result.piece.loaded_at ? (
                  <Badge className="status-delivered">
                    <Check className="h-3 w-3 mr-1" />
                    Loaded
                  </Badge>
                ) : (
                  <Button onClick={handleMarkLoaded} data-testid="mark-loaded-btn">
                    <Check className="h-4 w-4 mr-2" />
                    Mark as Loaded
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quick Tips */}
        {!result && (
          <Card>
            <CardContent className="p-4">
              <h4 className="font-heading font-semibold mb-2">Quick Tips</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Use camera mode for quick barcode scanning</li>
                <li>• Manual entry accepts partial codes</li>
                <li>• Mark pieces as loaded after physical verification</li>
                <li>• Temporary barcodes start with "TEMP-"</li>
              </ul>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
