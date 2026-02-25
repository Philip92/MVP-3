import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Skeleton } from './ui/skeleton';
import { 
  Plus, Edit, Trash2, ArrowRight, Clock,
  User
} from 'lucide-react';
import { cn } from '../lib/utils';

const API = `${window.location.origin}/api`;

const actionIcons = {
  create: Plus,
  update: Edit,
  delete: Trash2,
  status_change: ArrowRight,
};

const actionColors = {
  create: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  status_change: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
};

const formatDate = (dateString) => {
  try {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
};

const getChangedFields = (oldValue, newValue) => {
  if (!oldValue || !newValue) return [];
  
  const changes = [];
  const keys = new Set([...Object.keys(oldValue), ...Object.keys(newValue)]);
  
  keys.forEach(key => {
    // Skip internal fields
    if (['_id', 'tenant_id', 'created_at', 'created_by'].includes(key)) return;
    
    const oldVal = oldValue[key];
    const newVal = newValue[key];
    
    if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
      changes.push({
        field: key.replace(/_/g, ' '),
        old: oldVal,
        new: newVal,
      });
    }
  });
  
  return changes;
};

export function AuditHistory({ tableName, recordId }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get(
          `${API}/audit-logs/${tableName}/${recordId}`,
          { withCredentials: true }
        );
        setHistory(response.data);
      } catch (error) {
        console.error('Failed to fetch audit history');
      } finally {
        setLoading(false);
      }
    };

    if (recordId) {
      fetchHistory();
    }
  }, [tableName, recordId]);

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Clock className="h-10 w-10 mx-auto mb-2 opacity-50" />
        <p>No history available</p>
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="audit-history">
      {history.map((entry, index) => {
        const Icon = actionIcons[entry.action] || Edit;
        const changes = getChangedFields(entry.old_value, entry.new_value);
        
        return (
          <Card key={entry.id || index} className="relative">
            {/* Timeline connector */}
            {index < history.length - 1 && (
              <div className="absolute left-6 top-14 bottom-0 w-0.5 bg-border" />
            )}
            
            <CardContent className="p-4">
              <div className="flex gap-3">
                {/* Icon */}
                <div className={cn(
                  'h-8 w-8 rounded-full flex items-center justify-center shrink-0 z-10',
                  actionColors[entry.action]
                )}>
                  <Icon className="h-4 w-4" />
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="capitalize">
                        {entry.action.replace('_', ' ')}
                      </Badge>
                      <span className="text-sm text-muted-foreground flex items-center gap-1">
                        <User className="h-3 w-3" />
                        {entry.user_name || 'System'}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(entry.created_at)}
                    </span>
                  </div>
                  
                  {/* Changes */}
                  {entry.action === 'create' && entry.new_value && (
                    <div className="mt-2 text-sm text-muted-foreground">
                      Record created
                    </div>
                  )}
                  
                  {entry.action === 'delete' && (
                    <div className="mt-2 text-sm text-muted-foreground">
                      Record deleted
                    </div>
                  )}
                  
                  {(entry.action === 'update' || entry.action === 'status_change') && changes.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {changes.slice(0, 5).map((change, i) => (
                        <div key={i} className="text-sm flex items-center gap-2">
                          <span className="text-muted-foreground capitalize">
                            {change.field}:
                          </span>
                          <span className="line-through text-red-500/70">
                            {String(change.old ?? '-')}
                          </span>
                          <ArrowRight className="h-3 w-3 text-muted-foreground" />
                          <span className="text-green-600 dark:text-green-400">
                            {String(change.new ?? '-')}
                          </span>
                        </div>
                      ))}
                      {changes.length > 5 && (
                        <span className="text-xs text-muted-foreground">
                          +{changes.length - 5} more changes
                        </span>
                      )}
                    </div>
                  )}
                  
                  {entry.ip_address && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      IP: {entry.ip_address}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
