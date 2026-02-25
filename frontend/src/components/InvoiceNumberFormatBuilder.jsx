import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { toast } from 'sonner';
import { Plus, Trash2, Save, Loader2, GripVertical, Eye } from 'lucide-react';

const API = `${window.location.origin}/api`;

const SEGMENT_TYPES = [
  { value: 'STATIC', label: 'Static Text', description: 'Fixed text like "INV", "S"' },
  { value: 'YEAR', label: 'Year', description: 'Current year (2 or 4 digits)' },
  { value: 'MONTH', label: 'Month', description: 'Current month (1 or 2 digits)' },
  { value: 'TRIP_SEQ', label: 'Trip Sequence', description: 'Counter per trip' },
  { value: 'GLOBAL_SEQ', label: 'Global Sequence', description: 'Global counter across all invoices' },
];

const SEPARATORS = [
  { value: '-', label: 'Dash (-)' },
  { value: '/', label: 'Slash (/)' },
  { value: '.', label: 'Dot (.)' },
  { value: '_', label: 'Underscore (_)' },
  { value: '', label: 'None' },
];

export default function InvoiceNumberFormatBuilder() {
  const [segments, setSegments] = useState([]);
  const [separator, setSeparator] = useState('-');
  const [preview, setPreview] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFormat();
  }, []);

  const fetchFormat = async () => {
    try {
      const res = await axios.get(`${API}/settings/invoice-number-format`, { withCredentials: true });
      setSegments(res.data.segments || []);
      setSeparator(res.data.separator || '-');
      setPreview(res.data.preview || '');
    } catch {
      setSegments([
        { type: 'STATIC', value: 'INV' },
        { type: 'YEAR', digits: 4 },
        { type: 'GLOBAL_SEQ', digits: 3 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchPreview = useCallback(async (segs, sep) => {
    try {
      const res = await axios.post(`${API}/settings/invoice-number-format/preview`, {
        segments: segs,
        separator: sep
      }, { withCredentials: true });
      setPreview(res.data.preview);
    } catch {
      // Build local preview
      const parts = segs.map(seg => {
        if (seg.type === 'STATIC') return seg.value || 'TEXT';
        if (seg.type === 'YEAR') return seg.digits === 2 ? '26' : '2026';
        if (seg.type === 'MONTH') return '02';
        if (seg.type === 'TRIP_SEQ') return 'X'.repeat(seg.digits || 3);
        if (seg.type === 'GLOBAL_SEQ') return 'X'.repeat(seg.digits || 3);
        return '?';
      });
      setPreview(parts.join(sep));
    }
  }, []);

  const updateSegmentAndPreview = (newSegments, newSeparator) => {
    setSegments(newSegments);
    if (newSeparator !== undefined) setSeparator(newSeparator);
    fetchPreview(newSegments, newSeparator !== undefined ? newSeparator : separator);
  };

  const addSegment = (type) => {
    const newSeg = { type };
    if (type === 'STATIC') newSeg.value = 'INV';
    if (type === 'YEAR') newSeg.digits = 4;
    if (type === 'MONTH') newSeg.digits = 2;
    if (type === 'TRIP_SEQ') newSeg.digits = 3;
    if (type === 'GLOBAL_SEQ') newSeg.digits = 3;
    updateSegmentAndPreview([...segments, newSeg]);
  };

  const removeSegment = (idx) => {
    const newSegs = segments.filter((_, i) => i !== idx);
    updateSegmentAndPreview(newSegs);
  };

  const updateSegment = (idx, field, value) => {
    const newSegs = segments.map((seg, i) => {
      if (i === idx) {
        return { ...seg, [field]: field === 'digits' ? parseInt(value) || 1 : value };
      }
      return seg;
    });
    updateSegmentAndPreview(newSegs);
  };

  const moveSegment = (idx, direction) => {
    const newSegs = [...segments];
    const targetIdx = idx + direction;
    if (targetIdx < 0 || targetIdx >= newSegs.length) return;
    [newSegs[idx], newSegs[targetIdx]] = [newSegs[targetIdx], newSegs[idx]];
    updateSegmentAndPreview(newSegs);
  };

  const handleSave = async () => {
    if (segments.length === 0) {
      toast.error('Add at least one segment');
      return;
    }
    setSaving(true);
    try {
      const res = await axios.put(`${API}/settings/invoice-number-format`, {
        segments,
        separator
      }, { withCredentials: true });
      setPreview(res.data.preview);
      toast.success('Invoice number format saved');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save format');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-gray-400" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="invoice-number-format-builder">
      <Card>
        <CardHeader>
          <CardTitle>Invoice Number Format Builder</CardTitle>
          <CardDescription>
            Configure how invoice numbers are generated. Drag segments to reorder, set separators and digit counts.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Live Preview */}
          <div className="bg-gray-50 border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Eye className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-600">Live Preview</span>
            </div>
            <p className="text-2xl font-mono font-bold text-[#3C3F42]" data-testid="invoice-number-preview">
              {preview || 'Add segments below'}
            </p>
          </div>

          {/* Separator Selection */}
          <div className="flex items-center gap-4">
            <Label className="min-w-[80px]">Separator:</Label>
            <Select value={separator} onValueChange={(val) => updateSegmentAndPreview(segments, val)}>
              <SelectTrigger className="w-40" data-testid="separator-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SEPARATORS.map(s => (
                  <SelectItem key={s.value} value={s.value || 'none'}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Segments */}
          <div className="space-y-3">
            <Label>Segments</Label>
            {segments.map((seg, idx) => (
              <div key={idx} className="flex items-center gap-2 bg-white border rounded-lg p-3" data-testid={`segment-${idx}`}>
                <div className="flex flex-col gap-1">
                  <Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => moveSegment(idx, -1)} disabled={idx === 0}>
                    <span className="text-xs">▲</span>
                  </Button>
                  <Button variant="ghost" size="icon" className="h-5 w-5" onClick={() => moveSegment(idx, 1)} disabled={idx === segments.length - 1}>
                    <span className="text-xs">▼</span>
                  </Button>
                </div>
                <GripVertical className="h-4 w-4 text-gray-400" />
                
                <Badge variant="outline" className="min-w-[100px] justify-center">
                  {SEGMENT_TYPES.find(t => t.value === seg.type)?.label || seg.type}
                </Badge>

                {seg.type === 'STATIC' && (
                  <Input
                    value={seg.value || ''}
                    onChange={(e) => updateSegment(idx, 'value', e.target.value)}
                    className="w-24"
                    placeholder="Text"
                    data-testid={`segment-value-${idx}`}
                  />
                )}

                {(seg.type === 'YEAR') && (
                  <Select value={String(seg.digits || 4)} onValueChange={(val) => updateSegment(idx, 'digits', val)}>
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="2">2 digit</SelectItem>
                      <SelectItem value="4">4 digit</SelectItem>
                    </SelectContent>
                  </Select>
                )}

                {(seg.type === 'MONTH') && (
                  <Select value={String(seg.digits || 2)} onValueChange={(val) => updateSegment(idx, 'digits', val)}>
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 digit</SelectItem>
                      <SelectItem value="2">2 digit</SelectItem>
                    </SelectContent>
                  </Select>
                )}

                {(seg.type === 'TRIP_SEQ' || seg.type === 'GLOBAL_SEQ') && (
                  <div className="flex items-center gap-1">
                    <Label className="text-xs text-gray-500">Digits:</Label>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={seg.digits || 3}
                      onChange={(e) => updateSegment(idx, 'digits', e.target.value)}
                      className="w-16"
                      data-testid={`segment-digits-${idx}`}
                    />
                  </div>
                )}

                <Button variant="ghost" size="icon" className="ml-auto text-red-500 hover:text-red-700" onClick={() => removeSegment(idx)} data-testid={`remove-segment-${idx}`}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          {/* Add Segment Buttons */}
          <div className="flex flex-wrap gap-2">
            {SEGMENT_TYPES.map(type => (
              <Button
                key={type.value}
                variant="outline"
                size="sm"
                onClick={() => addSegment(type.value)}
                data-testid={`add-segment-${type.value}`}
              >
                <Plus className="h-3 w-3 mr-1" /> {type.label}
              </Button>
            ))}
          </div>

          {/* Segment Type Descriptions */}
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-700">
            <p className="font-semibold mb-1">Segment Types:</p>
            <ul className="space-y-0.5">
              {SEGMENT_TYPES.map(t => (
                <li key={t.value}><strong>{t.label}:</strong> {t.description}</li>
              ))}
            </ul>
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4 border-t">
            <Button onClick={handleSave} disabled={saving || segments.length === 0} className="bg-[#6B633C] hover:bg-[#5a5332]" data-testid="save-invoice-format-btn">
              {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
              Save Format
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
