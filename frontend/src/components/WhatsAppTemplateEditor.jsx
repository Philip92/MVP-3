import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'sonner';
import { Save, RotateCcw, Copy } from 'lucide-react';

const API = `${window.location.origin}/api`;

export default function WhatsAppTemplateEditor() {
  const [templates, setTemplates] = useState([]);
  const [activeTemplate, setActiveTemplate] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState({
    client_name: "John Doe",
    invoice_number: "INV-2026-001",
    amount: "R 5,500.00",
    due_date: "2026-03-15",
    company_name: "SERVEX Holdings",
    days_overdue: "5",
    outstanding_amount: "R 5,500.00",
    period: "January 2026",
    total_outstanding: "R 15,000.00",
    invoice_count: "3",
    parcel_count: "5",
    warehouse_name: "Johannesburg Main"
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${API}/templates/whatsapp`, { withCredentials: true });
      setTemplates(response.data.templates);
      if (response.data.templates.length > 0 && !activeTemplate) {
        setActiveTemplate(response.data.templates[0]);
        setMessage(response.data.templates[0].message);
      }
    } catch (error) {
      toast.error('Failed to load templates');
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await axios.put(
        `${API}/templates/whatsapp/${activeTemplate.id}`,
        { message },
        { withCredentials: true }
      );
      toast.success('Template saved successfully');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to save template');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset this template to default? This cannot be undone.')) return;
    
    setLoading(true);
    try {
      await axios.post(
        `${API}/templates/whatsapp/${activeTemplate.id}/reset`,
        {},
        { withCredentials: true }
      );
      toast.success('Template reset to default');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to reset template');
    } finally {
      setLoading(false);
    }
  };

  const insertPlaceholder = (placeholder) => {
    const newMessage = message + `{{${placeholder}}}`;
    setMessage(newMessage);
  };

  const renderPreview = () => {
    let preview = message;
    Object.entries(previewData).forEach(([key, value]) => {
      preview = preview.replace(new RegExp(`{{${key}}}`, 'g'), value);
    });
    return preview;
  };

  const groupedTemplates = templates.reduce((acc, template) => {
    if (!acc[template.category]) acc[template.category] = [];
    acc[template.category].push(template);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {/* Template List */}
      <div className="grid gap-3">
        {templates.map(template => (
          <Card 
            key={template.id} 
            className={activeTemplate?.id === template.id ? "border-[#6B633C] bg-[#EDEAE5]/30" : "hover:border-[#6B633C]/50 cursor-pointer"}
            onClick={() => {
              setActiveTemplate(template);
              setMessage(template.message);
            }}
          >
            <CardHeader className="py-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">{template.name}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">{template.description}</p>
                </div>
                <Badge variant="outline" className="text-xs">
                  {template.category}
                </Badge>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>

      {activeTemplate && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          {/* Editor */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Edit Template: {activeTemplate.name}</CardTitle>
              <div className="flex flex-wrap gap-1 mt-2">
                <p className="text-xs text-muted-foreground w-full mb-1">Click to insert placeholder:</p>
                {activeTemplate.placeholders.map(ph => (
                  <Badge
                    key={ph}
                    variant="outline"
                    className="cursor-pointer hover:bg-[#6B633C] hover:text-white transition-colors text-xs"
                    onClick={() => insertPlaceholder(ph)}
                  >
                    <Copy className="h-3 w-3 mr-1" />
                    {ph}
                  </Badge>
                ))}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={14}
                className="font-mono text-sm"
                placeholder="Enter message template..."
              />
              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={loading} className="flex-1 bg-[#6B633C] hover:bg-[#5a5332]">
                  <Save className="h-4 w-4 mr-2" />
                  Save Template
                </Button>
                <Button variant="outline" onClick={handleReset} disabled={loading}>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Preview */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Preview</CardTitle>
              <p className="text-xs text-muted-foreground">How the message will look with sample data</p>
            </CardHeader>
            <CardContent>
              <div className="bg-green-50 p-4 rounded-lg border border-green-200 min-h-[400px] whitespace-pre-wrap font-sans text-sm">
                {renderPreview()}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
