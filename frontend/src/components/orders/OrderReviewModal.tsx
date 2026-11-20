import React, { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Sparkles,
  Edit2,
  Trash2,
  Plus,
  Send,
  Loader2,
  X,
  HelpCircle,
} from 'lucide-react';
import { ApiGroceryOrder, ApiGroceryOrderItem } from '../../types';
import { api } from '../../services/api';

interface OrderReviewModalProps {
  order: ApiGroceryOrder | null;
  isOpen: boolean;
  onClose: () => void;
  onOrderUpdated: (updated: ApiGroceryOrder) => void;
}

export const OrderReviewModal: React.FC<OrderReviewModalProps> = ({
  order,
  isOpen,
  onClose,
  onOrderUpdated,
}) => {
  if (!isOpen || !order) return null;

  const [isEditing, setIsEditing] = useState(false);
  const [items, setItems] = useState<ApiGroceryOrderItem[]>(order.items);
  const [clarificationText, setClarificationText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New item form state for adding an item
  const [showAddItem, setShowAddItem] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [newItemQty, setNewItemQty] = useState('');
  const [newItemUnit, setNewItemUnit] = useState('kg');
  const [newItemCategory] = useState('other');

  const languageLabels: Record<string, string> = {
    en: 'English',
    te: 'Telugu (తెలుగు)',
    hi: 'Hindi (हिन्दी)',
    mixed: 'Mixed (Code-switching)',
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await api.orders.confirm(order.id);
      onOrderUpdated(updated);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to confirm order.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!window.confirm('Are you sure you want to cancel and reject this grocery order?')) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await api.orders.reject(order.id);
      onOrderUpdated(updated);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to reject order.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetry = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await api.orders.retry(order.id);
      setItems(updated.items);
      onOrderUpdated(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to retry order extraction.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendClarification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clarificationText.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await api.orders.clarify(order.id, clarificationText.trim());
      setItems(updated.items);
      setClarificationText('');
      onOrderUpdated(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to send clarification.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveItemEdits = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await api.orders.updateItems(order.id, items);
      setItems(updated.items);
      setIsEditing(false);
      onOrderUpdated(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to save item changes.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteItem = (itemId: string) => {
    setItems((prev) => prev.filter((it) => it.id !== itemId));
  };

  const handleItemFieldChange = (
    itemId: string,
    field: keyof ApiGroceryOrderItem,
    value: any
  ) => {
    setItems((prev) =>
      prev.map((it) => (it.id === itemId ? { ...it, [field]: value } : it))
    );
  };

  const handleAddNewItem = () => {
    if (!newItemName.trim()) return;
    const newItem: ApiGroceryOrderItem = {
      id: `item_${Date.now()}`,
      original_name: newItemName.trim(),
      normalized_name: newItemName.trim(),
      quantity: parseFloat(newItemQty) || 1,
      unit: newItemUnit,
      category: newItemCategory,
      confidence: 1.0,
      needs_clarification: false,
    };
    setItems((prev) => [...prev, newItem]);
    setNewItemName('');
    setNewItemQty('');
    setShowAddItem(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden border border-gray-100">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-emerald-50/50 via-teal-50/30 to-white">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-600">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 text-lg flex items-center gap-2">
                Grocery Order Review
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                  Round #{order.round_number}
                </span>
              </h3>
              <p className="text-xs text-gray-500">
                Language: {languageLabels[order.detected_language] || order.detected_language} • Flat {order.flat_number}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {error && (
            <div className="p-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Original Raw Text */}
          <div className="bg-gray-50 rounded-xl p-3.5 border border-gray-200/80">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1 flex items-center justify-between">
              <span>Original Message</span>
              <span className="text-[10px] text-gray-400 font-normal">Immutable</span>
            </div>
            <p className="text-sm font-medium text-gray-800 italic">"{order.raw_text}"</p>
          </div>

          {/* Status & Clarification Alerts */}
          {order.status === 'needs_clarification' && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
              <div className="flex items-start gap-2.5">
                <HelpCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-amber-900">Clarification Needed</h4>
                  <p className="text-xs text-amber-700 mt-0.5">
                    {order.clarification_prompt || 'Some items require your clarification on quantity or type.'}
                  </p>
                </div>
              </div>

              {/* Clarification Input */}
              <form onSubmit={handleSendClarification} className="flex gap-2 pt-1">
                <input
                  type="text"
                  value={clarificationText}
                  onChange={(e) => setClarificationText(e.target.value)}
                  placeholder="e.g., 2 litres sunflower oil, or 1 kg basmati rice"
                  className="flex-1 text-sm rounded-lg border border-amber-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                  disabled={isSubmitting}
                />
                <button
                  type="submit"
                  disabled={isSubmitting || !clarificationText.trim()}
                  className="px-3.5 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  <span>Clarify</span>
                </button>
              </form>
            </div>
          )}

          {order.status === 'confirmed' && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center gap-2.5 text-emerald-800 text-sm">
              <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
              <span>This order has been confirmed by you and is locked for the bulk round shopping list.</span>
            </div>
          )}

          {order.status === 'failed' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center justify-between gap-2.5 text-red-800 text-sm">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
                <span>AI extraction encountered an error or timed out.</span>
              </div>
              <button
                onClick={handleRetry}
                disabled={isSubmitting}
                className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold"
              >
                {isSubmitting ? 'Retrying...' : 'Retry Extraction'}
              </button>
            </div>
          )}

          {/* Extracted Grocery Items Header */}
          <div className="flex items-center justify-between pt-1">
            <h4 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
              Interpreted Items ({items.length})
            </h4>
            {order.status !== 'confirmed' && order.status !== 'rejected' && (
              <div className="flex items-center gap-2">
                {!isEditing ? (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="text-xs text-emerald-600 hover:text-emerald-700 font-medium flex items-center gap-1 px-2.5 py-1 rounded-lg hover:bg-emerald-50 transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    <span>Edit Items</span>
                  </button>
                ) : (
                  <button
                    onClick={handleSaveItemEdits}
                    disabled={isSubmitting}
                    className="text-xs bg-emerald-600 text-white font-medium flex items-center gap-1 px-3 py-1 rounded-lg hover:bg-emerald-700 transition-colors"
                  >
                    <span>Save Edits</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Items List */}
          <div className="space-y-2.5">
            {items.map((it) => (
              <div
                key={it.id}
                className={`p-3 rounded-xl border transition-all ${
                  it.needs_clarification
                    ? 'bg-amber-50/40 border-amber-300'
                    : 'bg-white border-gray-200 hover:border-gray-300'
                }`}
              >
                {!isEditing ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900 text-sm">{it.normalized_name}</span>
                        {it.original_name !== it.normalized_name && (
                          <span className="text-xs text-gray-400">({it.original_name})</span>
                        )}
                        {it.category && (
                          <span className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">
                            {it.category.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                        {it.brand && <span className="text-gray-700 font-medium">Brand: {it.brand}</span>}
                        {it.variant && <span>Variant: {it.variant}</span>}
                        {it.needs_clarification && (
                          <span className="text-amber-700 font-medium bg-amber-100 px-2 py-0.5 rounded">
                            {it.clarification_reason || 'Needs clarification'}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-right">
                      {it.quantity ? (
                        <span className="text-base font-bold text-emerald-700">
                          {it.quantity} {it.unit || ''}
                        </span>
                      ) : (
                        <span className="text-xs font-semibold text-amber-600 bg-amber-100 px-2 py-1 rounded-lg">
                          Unspecified Qty
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  /* Editable Row */
                  <div className="space-y-2">
                    <div className="grid grid-cols-12 gap-2">
                      <input
                        type="text"
                        value={it.normalized_name}
                        onChange={(e) => handleItemFieldChange(it.id, 'normalized_name', e.target.value)}
                        placeholder="Item name"
                        className="col-span-6 text-sm border rounded-lg px-2.5 py-1.5 focus:ring-1 focus:ring-emerald-500"
                      />
                      <input
                        type="number"
                        step="any"
                        value={it.quantity ?? ''}
                        onChange={(e) =>
                          handleItemFieldChange(
                            it.id,
                            'quantity',
                            e.target.value ? parseFloat(e.target.value) : null
                          )
                        }
                        placeholder="Qty"
                        className="col-span-3 text-sm border rounded-lg px-2.5 py-1.5 focus:ring-1 focus:ring-emerald-500"
                      />
                      <input
                        type="text"
                        value={it.unit ?? ''}
                        onChange={(e) => handleItemFieldChange(it.id, 'unit', e.target.value)}
                        placeholder="Unit"
                        className="col-span-2 text-sm border rounded-lg px-2.5 py-1.5 focus:ring-1 focus:ring-emerald-500"
                      />
                      <button
                        onClick={() => handleDeleteItem(it.id)}
                        className="col-span-1 text-gray-400 hover:text-red-600 flex items-center justify-center p-1 rounded hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {items.length === 0 && (
              <div className="p-6 text-center text-gray-400 text-sm border-2 border-dashed border-gray-200 rounded-xl">
                No items in this order.
              </div>
            )}

            {/* Add Item Trigger */}
            {isEditing && !showAddItem && (
              <button
                onClick={() => setShowAddItem(true)}
                className="w-full py-2 border-2 border-dashed border-gray-200 hover:border-emerald-500 text-gray-500 hover:text-emerald-700 text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Item</span>
              </button>
            )}

            {/* Add Item Form */}
            {isEditing && showAddItem && (
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-200 space-y-2">
                <div className="grid grid-cols-12 gap-2">
                  <input
                    type="text"
                    value={newItemName}
                    onChange={(e) => setNewItemName(e.target.value)}
                    placeholder="New item name"
                    className="col-span-6 text-sm border rounded-lg px-2.5 py-1.5"
                  />
                  <input
                    type="number"
                    step="any"
                    value={newItemQty}
                    onChange={(e) => setNewItemQty(e.target.value)}
                    placeholder="Qty"
                    className="col-span-3 text-sm border rounded-lg px-2.5 py-1.5"
                  />
                  <input
                    type="text"
                    value={newItemUnit}
                    onChange={(e) => setNewItemUnit(e.target.value)}
                    placeholder="kg"
                    className="col-span-3 text-sm border rounded-lg px-2.5 py-1.5"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={() => setShowAddItem(false)}
                    className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddNewItem}
                    disabled={!newItemName.trim()}
                    className="text-xs bg-emerald-600 text-white font-medium px-3 py-1 rounded-lg hover:bg-emerald-700 disabled:opacity-50"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex items-center justify-between">
          <button
            onClick={handleReject}
            disabled={isSubmitting || order.status === 'confirmed' || order.status === 'rejected'}
            className="text-xs text-red-600 hover:text-red-700 font-semibold px-3 py-2 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-40 flex items-center gap-1"
          >
            <XCircle className="w-4 h-4" />
            <span>Reject Order</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-200 text-gray-700 hover:bg-gray-100 rounded-xl text-sm font-medium transition-colors"
            >
              Close
            </button>
            {order.status !== 'confirmed' && order.status !== 'rejected' && (
              <button
                onClick={handleConfirm}
                disabled={isSubmitting || items.length === 0}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold flex items-center gap-1.5 shadow-sm hover:shadow transition-all disabled:opacity-50"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                <span>Confirm Grocery Order</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
