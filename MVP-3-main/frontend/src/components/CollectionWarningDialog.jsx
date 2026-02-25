import { useState } from 'react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { AlertTriangle, CheckCircle, XCircle, DollarSign } from 'lucide-react';

/**
 * CollectionWarningDialog - Session G P-16
 * Shows payment status warning when collecting a parcel.
 * Requires confirmation note for unpaid parcels.
 */
export default function CollectionWarningDialog({
  open,
  onOpenChange,
  checkData,
  onConfirm,
  loading,
}) {
  const [confirmationNote, setConfirmationNote] = useState('');

  if (!checkData) return null;

  const { can_collect, warning, payment_status, message, total_amount, paid_amount, outstanding, requires_confirmation, requires_admin_notification } = checkData;

  const getStatusBadge = () => {
    if (payment_status === 'paid') {
      return <Badge className="bg-green-100 text-green-700 border-0"><CheckCircle className="h-3 w-3 mr-1" /> Paid</Badge>;
    }
    if (payment_status === 'partial') {
      return <Badge className="bg-amber-100 text-amber-700 border-0"><DollarSign className="h-3 w-3 mr-1" /> Partial</Badge>;
    }
    if (warning === 'not_invoiced') {
      return <Badge className="bg-blue-100 text-blue-700 border-0">Not Invoiced</Badge>;
    }
    return <Badge className="bg-red-100 text-red-700 border-0"><XCircle className="h-3 w-3 mr-1" /> Unpaid</Badge>;
  };

  const handleConfirm = () => {
    onConfirm(confirmationNote);
    setConfirmationNote('');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {requires_confirmation ? (
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            ) : (
              <CheckCircle className="h-5 w-5 text-green-500" />
            )}
            Collection Confirmation
          </DialogTitle>
          <DialogDescription>
            Review payment status before collecting this parcel.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Payment Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Payment Status</span>
            {getStatusBadge()}
          </div>

          {/* Message */}
          <div className={`p-3 rounded-lg text-sm ${
            requires_admin_notification ? 'bg-red-50 text-red-700 border border-red-200' :
            requires_confirmation ? 'bg-amber-50 text-amber-700 border border-amber-200' :
            'bg-green-50 text-green-700 border border-green-200'
          }`}>
            {message}
          </div>

          {/* Financial Details */}
          {(total_amount !== undefined) && (
            <div className="space-y-1 text-sm">
              {total_amount > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Amount</span>
                  <span className="font-medium">R {total_amount?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
              )}
              {paid_amount > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Amount Paid</span>
                  <span className="font-medium text-green-600">R {paid_amount?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
              )}
              {outstanding > 0 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Outstanding</span>
                  <span className="font-bold text-red-600">R {outstanding?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
              )}
            </div>
          )}

          {/* Admin notification warning */}
          {requires_admin_notification && (
            <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 p-2 rounded">
              <AlertTriangle className="h-3 w-3" />
              Admin/manager will be notified of this collection
            </div>
          )}

          {/* Confirmation note for unpaid parcels */}
          {requires_confirmation && (
            <div className="space-y-2">
              <Label htmlFor="collection-note">Confirmation Note {requires_admin_notification ? '*' : '(optional)'}</Label>
              <Input
                id="collection-note"
                placeholder="e.g., Client promised payment by Friday..."
                value={confirmationNote}
                onChange={(e) => setConfirmationNote(e.target.value)}
              />
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          {can_collect && (
            <Button
              onClick={handleConfirm}
              disabled={loading || (requires_admin_notification && !confirmationNote.trim())}
              className={requires_admin_notification ? 'bg-amber-600 hover:bg-amber-700' : 'bg-green-600 hover:bg-green-700'}
            >
              {loading ? 'Processing...' : 'Confirm Collection'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
