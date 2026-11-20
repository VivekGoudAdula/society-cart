import React, { useState, useEffect } from 'react';
import {
  PlusCircle,
  Trash2,
  Receipt,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { api } from '../../services/api';
import { ApiPurchaseRecord, ApiRecordPurchaseRequest } from '../../types';

interface PurchaseRecordingSectionProps {
  societyId: string;
  roundId: string;
  onPurchasesChanged?: () => void;
}

export const PurchaseRecordingSection: React.FC<PurchaseRecordingSectionProps> = ({
  societyId,
  roundId,
  onPurchasesChanged,
}) => {
  const [purchases, setPurchases] = useState<ApiPurchaseRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form State
  const [itemName, setItemName] = useState('');
  const [category, setCategory] = useState('grains_rice');
  const [brand, setBrand] = useState('');
  const [variant, setVariant] = useState('');
  const [actualQuantity, setActualQuantity] = useState('');
  const [unit, setUnit] = useState('kg');
  const [totalPrice, setTotalPrice] = useState('');
  const [shopName, setShopName] = useState('');
  const [invoiceRef, setInvoiceRef] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubstitution, setIsSubstitution] = useState(false);
  const [substituteForItemName, setSubstituteForItemName] = useState('');

  const loadPurchases = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.billing.listPurchases(societyId, roundId);
      setPurchases(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load purchase records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPurchases();
  }, [societyId, roundId]);

  const handleRecordPurchase = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const qty = parseFloat(actualQuantity);
    const price = parseFloat(totalPrice);

    if (!itemName.trim() || isNaN(qty) || qty <= 0 || isNaN(price) || price < 0 || !shopName.trim()) {
      setError('Please fill all required fields with positive quantity and non-negative price.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: ApiRecordPurchaseRequest = {
        item_name: itemName.trim(),
        category,
        brand: brand.trim() || null,
        variant: variant.trim() || null,
        actual_quantity: qty,
        unit: unit.trim(),
        total_price: price,
        shop_name: shopName.trim(),
        invoice_ref: invoiceRef.trim() || null,
        notes: notes.trim() || null,
        is_substitution: isSubstitution,
        substitute_for_item_name: isSubstitution ? substituteForItemName.trim() : null,
      };

      await api.billing.recordPurchase(societyId, roundId, payload);
      setSuccessMsg(`Successfully recorded purchase for "${itemName}".`);

      // Reset form
      setItemName('');
      setBrand('');
      setVariant('');
      setActualQuantity('');
      setTotalPrice('');
      setInvoiceRef('');
      setNotes('');
      setIsSubstitution(false);
      setSubstituteForItemName('');

      await loadPurchases();
      if (onPurchasesChanged) onPurchasesChanged();
    } catch (err: any) {
      setError(err.message || 'Failed to record purchase.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (purchaseId: string) => {
    if (!window.confirm('Are you sure you want to delete this purchase entry?')) return;
    try {
      await api.billing.deletePurchase(societyId, roundId, purchaseId);
      await loadPurchases();
      if (onPurchasesChanged) onPurchasesChanged();
    } catch (err: any) {
      setError(err.message || 'Failed to delete purchase record.');
    }
  };

  const totalSpent = purchases.reduce((acc, p) => acc + p.total_price, 0);

  return (
    <div className="space-y-6">
      {/* Overview Stat */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white border border-[#E6ECE8] shadow-xs">
        <div>
          <h3 className="text-base font-bold text-[#18231E]">Actual Purchases Recorded</h3>
          <p className="text-xs text-[#718078] mt-0.5">
            Record physical receipts and invoices from local stores or wholesale markets.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Total Expenditure</span>
            <span className="text-xl font-black text-[#18231E]">₹{totalSpent.toFixed(2)}</span>
          </div>
          <Badge variant="primary" size="md">{purchases.length} Items</Badge>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-800 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 flex items-center gap-3">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Record Purchase Form Card */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-bold text-[#18231E] flex items-center gap-2">
            <PlusCircle className="h-4 w-4 text-[#196B48]" /> Record New Purchase
          </h4>
          <span className="text-xs text-[#718078]">Requires receipt details</span>
        </div>

        <form onSubmit={handleRecordPurchase} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Item Name *</label>
              <input
                type="text"
                value={itemName}
                onChange={(e) => setItemName(e.target.value)}
                placeholder="e.g. Sona Masoori Rice"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Category *</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
              >
                <option value="grains_rice">Grains & Rice</option>
                <option value="staples_atta_dal">Atta, Flour & Dals</option>
                <option value="dairy_oil">Dairy, Ghee & Oils</option>
                <option value="produce_vegetables">Vegetables & Onions/Potatoes</option>
                <option value="staples_sugar">Sugar, Salt & Spices</option>
                <option value="personal_cleaning">Cleaning & Detergents</option>
                <option value="other">Other Essentials</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Brand (Optional)</label>
              <input
                type="text"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                placeholder="e.g. India Gate, Fortune"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Variant (Optional)</label>
              <input
                type="text"
                value={variant}
                onChange={(e) => setVariant(e.target.value)}
                placeholder="e.g. Aged, Refined"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Actual Quantity *</label>
              <input
                type="number"
                step="any"
                value={actualQuantity}
                onChange={(e) => setActualQuantity(e.target.value)}
                placeholder="e.g. 25"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Unit *</label>
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
              >
                <option value="kg">kg (Kilograms)</option>
                <option value="L">L (Litres)</option>
                <option value="packet">packet</option>
                <option value="piece">piece</option>
                <option value="box">box</option>
                <option value="bottle">bottle</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Total Cost (₹) *</label>
              <input
                type="number"
                step="0.01"
                value={totalPrice}
                onChange={(e) => setTotalPrice(e.target.value)}
                placeholder="e.g. 1250.00"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Shop / Store Name *</label>
              <input
                type="text"
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
                placeholder="e.g. D-Mart Wholesale"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Invoice / Receipt Ref</label>
              <input
                type="text"
                value={invoiceRef}
                onChange={(e) => setInvoiceRef(e.target.value)}
                placeholder="e.g. INV-8921"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#18231E] mb-1">Notes</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Bought 25kg bulk sack"
                className="w-full text-xs rounded-lg border border-slate-200 p-2.5 focus:border-emerald-600 focus:outline-none"
              />
            </div>
          </div>

          {/* Substitution Mapping */}
          <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isSubstitution}
                onChange={(e) => setIsSubstitution(e.target.checked)}
                className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
              />
              <span className="text-xs font-bold text-[#18231E]">
                This is an explicit product substitution
              </span>
            </label>
            {isSubstitution && (
              <div>
                <label className="block text-[11px] font-semibold text-[#718078] mb-1">
                  Original Requested Item Name being Substituted:
                </label>
                <input
                  type="text"
                  value={substituteForItemName}
                  onChange={(e) => setSubstituteForItemName(e.target.value)}
                  placeholder="e.g. Basmati Rice (substituting for Regular Rice)"
                  className="w-full text-xs rounded-lg border border-slate-200 p-2 bg-white focus:border-emerald-600 focus:outline-none"
                  required={isSubstitution}
                />
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={isSubmitting}
              leftIcon={<PlusCircle className="h-4 w-4" />}
            >
              {isSubmitting ? 'Recording Purchase...' : 'Add Purchase Entry'}
            </Button>
          </div>
        </form>
      </Card>

      {/* Recorded Purchases Table */}
      <Card className="p-0 overflow-hidden">
        <div className="p-4 border-b border-[#E6ECE8] flex items-center justify-between">
          <h4 className="text-sm font-bold text-[#18231E]">Recorded Purchases Log</h4>
          <span className="text-xs text-[#718078]">{purchases.length} Entries</span>
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            Loading recorded purchases...
          </div>
        ) : purchases.length === 0 ? (
          <div className="py-12 text-center text-slate-400">
            <Receipt className="h-10 w-10 mx-auto text-slate-300 mb-2" />
            <p className="text-xs">No purchase entries recorded yet. Use the form above to add receipts.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAF9] border-b border-[#E6ECE8] text-[#718078] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Item & Brand</th>
                  <th className="py-3 px-4">Store</th>
                  <th className="py-3 px-4 text-center">Purchased Qty</th>
                  <th className="py-3 px-4 text-right">Unit Rate</th>
                  <th className="py-3 px-4 text-right">Total Cost</th>
                  <th className="py-3 px-4 text-center">Invoice Ref</th>
                  <th className="py-3 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6ECE8]">
                {purchases.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-[#18231E]">{p.item_name}</div>
                      {(p.brand || p.variant) && (
                        <div className="text-[11px] text-[#718078]">
                          {[p.brand, p.variant].filter(Boolean).join(' • ')}
                        </div>
                      )}
                      {p.is_substitution && (
                        <span className="inline-block mt-1 text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-medium">
                          Substituted for {p.substitute_for_item_name}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-[#718078]">{p.shop_name}</td>
                    <td className="py-3 px-4 text-center font-bold text-[#18231E]">
                      {p.actual_quantity} {p.unit}
                    </td>
                    <td className="py-3 px-4 text-right text-[#23865B] font-semibold">
                      ₹{p.unit_price.toFixed(2)}/{p.unit}
                    </td>
                    <td className="py-3 px-4 text-right font-black text-[#18231E]">
                      ₹{p.total_price.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-center text-[#718078]">
                      {p.invoice_ref || '—'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => handleDelete(p.id)}
                        className="text-slate-400 hover:text-rose-600 transition-colors p-1"
                        title="Delete entry"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
