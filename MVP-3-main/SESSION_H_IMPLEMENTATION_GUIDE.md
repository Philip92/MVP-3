# SESSION H: WhatsApp Template Editor Implementation Guide

## Overview
Move hardcoded WhatsApp messages from Finance.jsx to MongoDB templates with a Settings editor.

---

## 🎯 Requirements (20 credits total)

### 1. **Template Storage in MongoDB** (5 credits)
- Create `whatsapp_templates` collection
- Store message templates with placeholders
- Support multiple template types (invoice, overdue, statement, collection)

### 2. **Template Editor in Settings** (10 credits)
- Visual editor with placeholder insertion
- Live preview with sample data
- Save/reset functionality
- Template categories

### 3. **Finance Page Integration** (5 credits)
- Replace hardcoded messages with template fetch
- Populate placeholders with real data
- Maintain existing WhatsApp link generation

---

## 📁 Files to Modify

### Backend:
1. `/app/backend/routes/template_routes.py` (NEW)
   - CRUD endpoints for templates
   
2. Create default templates migration

### Frontend:
1. `/app/frontend/src/pages/Settings.jsx`
   - Add "WhatsApp Templates" section
   
2. `/app/frontend/src/components/WhatsAppTemplateEditor.jsx` (NEW)
   - Template editor component
   
3. `/app/frontend/src/pages/Finance.jsx`
   - Replace hardcoded messages with API calls

---

## 🛠 Implementation Steps

### **STEP 1: Backend - Template Model & Endpoints**

```python
# Create /app/backend/routes/template_routes.py

from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from database import db
from utils.auth import get_tenant_id, get_current_user
import uuid

router = APIRouter()

# Default templates
DEFAULT_TEMPLATES = {
    "invoice_sent": {
        "name": "Invoice Sent",
        "category": "invoices",
        "message": """Hi {{client_name}},

Your invoice {{invoice_number}} for {{amount}} is now available.

Due date: {{due_date}}

Please review and let us know if you have any questions.

Thank you!
{{company_name}}""",
        "placeholders": ["client_name", "invoice_number", "amount", "due_date", "company_name"],
        "description": "Sent when a new invoice is created"
    },
    "invoice_overdue": {
        "name": "Invoice Overdue",
        "category": "invoices",
        "message": """Hi {{client_name}},

Your invoice {{invoice_number}} for {{amount}} is now {{days_overdue}} days overdue.

Original due date: {{due_date}}
Outstanding amount: {{outstanding_amount}}

Please arrange payment at your earliest convenience.

{{company_name}}""",
        "placeholders": ["client_name", "invoice_number", "amount", "days_overdue", "due_date", "outstanding_amount", "company_name"],
        "description": "Sent when an invoice becomes overdue"
    },
    "statement_ready": {
        "name": "Statement Ready",
        "category": "statements",
        "message": """Hi {{client_name}},

Your account statement for {{period}} is ready for review.

Total outstanding: {{total_outstanding}}
Invoices: {{invoice_count}}

Please let us know if you need any clarification.

{{company_name}}""",
        "placeholders": ["client_name", "period", "total_outstanding", "invoice_count", "company_name"],
        "description": "Sent with monthly statements"
    },
    "collection_ready": {
        "name": "Collection Ready",
        "category": "collection",
        "message": """Hi {{client_name}},

Your {{parcel_count}} parcel(s) have arrived and are ready for collection at {{warehouse_name}}.

Parcels: {{parcel_list}}

Collection hours: Mon-Fri 8am-5pm

{{company_name}}""",
        "placeholders": ["client_name", "parcel_count", "warehouse_name", "parcel_list", "company_name"],
        "description": "Sent when parcels are ready for collection"
    }
}

@router.get("/templates/whatsapp")
async def get_whatsapp_templates(
    tenant_id: str = Depends(get_tenant_id)
):
    """Get all WhatsApp templates for tenant"""
    templates = await db.whatsapp_templates.find({
        "tenant_id": tenant_id
    }).to_list(100)
    
    # If no templates exist, create defaults
    if not templates:
        templates = await create_default_templates(tenant_id)
    
    return {"templates": templates}


@router.get("/templates/whatsapp/{template_id}")
async def get_whatsapp_template(
    template_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Get single template"""
    template = await db.whatsapp_templates.find_one({
        "id": template_id,
        "tenant_id": tenant_id
    })
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    return template


@router.put("/templates/whatsapp/{template_id}")
async def update_whatsapp_template(
    template_id: str,
    message: str,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update template message"""
    result = await db.whatsapp_templates.update_one(
        {"id": template_id, "tenant_id": tenant_id},
        {
            "$set": {
                "message": message,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user["id"]
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(404, "Template not found")
    
    return {"message": "Template updated"}


@router.post("/templates/whatsapp/{template_id}/reset")
async def reset_template_to_default(
    template_id: str,
    tenant_id: str = Depends(get_tenant_id)
):
    """Reset template to default message"""
    template = await db.whatsapp_templates.find_one({
        "id": template_id,
        "tenant_id": tenant_id
    })
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    default_message = DEFAULT_TEMPLATES.get(template["template_key"], {}).get("message", "")
    
    await db.whatsapp_templates.update_one(
        {"id": template_id},
        {"$set": {"message": default_message}}
    )
    
    return {"message": "Template reset to default"}


async def create_default_templates(tenant_id: str):
    """Create default templates for new tenant"""
    templates = []
    
    for key, data in DEFAULT_TEMPLATES.items():
        template = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "template_key": key,
            **data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.whatsapp_templates.insert_one(template)
        templates.append(template)
    
    return templates
```

### **STEP 2: Add Template Routes to Main App**

```python
# In /app/backend/main.py

from routes import template_routes

app.include_router(template_routes.router, prefix="/api", tags=["templates"])
```

### **STEP 3: Frontend - Template Editor Component**

```jsx
// Create /app/frontend/src/components/WhatsAppTemplateEditor.jsx

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
    warehouse_name: "Johannesburg Main",
    parcel_list: "PKG-001, PKG-002, PKG-003"
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
      <Tabs value={activeTemplate?.id} onValueChange={(id) => {
        const template = templates.find(t => t.id === id);
        setActiveTemplate(template);
        setMessage(template.message);
      }}>
        <TabsList className="grid w-full grid-cols-4">
          {Object.keys(groupedTemplates).map(category => (
            <TabsTrigger key={category} value={category}>
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </TabsTrigger>
          ))}
        </TabsList>

        {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
          <TabsContent key={category} value={category}>
            <div className="grid gap-4">
              {categoryTemplates.map(template => (
                <Card key={template.id} className={activeTemplate?.id === template.id ? "border-[#6B633C]" : ""}>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center justify-between">
                      {template.name}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setActiveTemplate(template);
                          setMessage(template.message);
                        }}
                      >
                        Edit
                      </Button>
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">{template.description}</p>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>

      {activeTemplate && (
        <div className="grid grid-cols-2 gap-4">
          {/* Editor */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Edit Template</CardTitle>
              <div className="flex flex-wrap gap-1 mt-2">
                {activeTemplate.placeholders.map(ph => (
                  <Badge
                    key={ph}
                    variant="outline"
                    className="cursor-pointer hover:bg-gray-100"
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
                rows={12}
                className="font-mono text-sm"
                placeholder="Enter message template..."
              />
              <div className="flex gap-2">
                <Button onClick={handleSave} disabled={loading} className="flex-1">
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
            </CardHeader>
            <CardContent>
              <div className="bg-green-50 p-4 rounded-lg border border-green-200 min-h-[300px] whitespace-pre-wrap">
                {renderPreview()}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
```

### **STEP 4: Add to Settings Page**

```jsx
// In /app/frontend/src/pages/Settings.jsx

import WhatsAppTemplateEditor from '../components/WhatsAppTemplateEditor';

// Add new tab in the Tabs component
<TabsTrigger value="whatsapp">WhatsApp Templates</TabsTrigger>

// Add new tab content
<TabsContent value="whatsapp" className="space-y-6">
  <div>
    <h3 className="text-lg font-semibold">WhatsApp Message Templates</h3>
    <p className="text-sm text-muted-foreground">
      Customize WhatsApp messages sent to clients
    </p>
  </div>
  <WhatsAppTemplateEditor />
</TabsContent>
```

### **STEP 5: Update Finance.jsx to Use Templates**

```jsx
// In /app/frontend/src/pages/Finance.jsx

// Add state for templates
const [whatsappTemplates, setWhatsappTemplates] = useState({});

// Fetch templates on mount
useEffect(() => {
  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${API}/templates/whatsapp`, { withCredentials: true });
      const templateMap = response.data.templates.reduce((acc, t) => {
        acc[t.template_key] = t;
        return acc;
      }, {});
      setWhatsappTemplates(templateMap);
    } catch (error) {
      console.error('Failed to load WhatsApp templates');
    }
  };
  fetchTemplates();
}, []);

// Replace hardcoded message generation with template population
const generateWhatsAppMessage = (type, data) => {
  const template = whatsappTemplates[type];
  if (!template) return "Message template not found";
  
  let message = template.message;
  Object.entries(data).forEach(([key, value]) => {
    message = message.replace(new RegExp(`{{${key}}}`, 'g'), value);
  });
  
  return message;
};

// Example usage when sending invoice reminder
const handleSendReminder = (invoice) => {
  const message = generateWhatsAppMessage('invoice_overdue', {
    client_name: invoice.client_name,
    invoice_number: invoice.invoice_number,
    amount: fmt(invoice.total),
    days_overdue: invoice.days_overdue,
    due_date: format(new Date(invoice.due_date), 'dd MMM yyyy'),
    outstanding_amount: fmt(invoice.outstanding),
    company_name: 'SERVEX Holdings'
  });
  
  const whatsappUrl = `https://wa.me/${invoice.client_phone}?text=${encodeURIComponent(message)}`;
  window.open(whatsappUrl, '_blank');
};
```

---

## 🧪 Testing Checklist

- [ ] Default templates created on first load
- [ ] Template editor loads all templates
- [ ] Placeholder insertion works
- [ ] Preview updates in real-time
- [ ] Save updates template in database
- [ ] Reset restores default message
- [ ] Finance page uses templates instead of hardcoded
- [ ] Placeholders populated correctly with real data
- [ ] WhatsApp link generation works with new templates

---

## 📊 Database Collection

```javascript
// whatsapp_templates collection
{
  id: "uuid",
  tenant_id: "tenant_id",
  template_key: "invoice_sent", // Unique key for code reference
  name: "Invoice Sent",
  category: "invoices", // invoices | statements | collection
  message: "Hi {{client_name}},\n\nYour invoice...",
  placeholders: ["client_name", "invoice_number", "amount"],
  description: "Sent when a new invoice is created",
  created_at: "2026-02-25T10:00:00Z",
  updated_at: "2026-02-25T10:00:00Z",
  updated_by: "user_id" // optional
}
```

---

**Estimated Implementation Time**: 4-5 hours
**Priority**: MEDIUM (Nice to have, improves maintainability)
