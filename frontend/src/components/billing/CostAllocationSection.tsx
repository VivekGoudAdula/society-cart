import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  Send,
  Lock,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { api } from '../../services/api';
import {
  ApiAllocationPreviewResponse,
  ApiGroceryBill,
} from '../../types';

interface CostAllocationSectionProps {
  societyId: string;
  roundId: string;
}

export const CostAllocationSection: React.FC<CostAllocationSectionProps> = ({
  societyId,
  roundId,
}) => {
  const [preview, setPreview] = useState<ApiAllocationPreviewResponse | null>(null);
  const [finalizedBills, setFinalizedBills] = useState<ApiGroceryBill[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isFinalizing, setIsFinalizing] = useState<boolean>(false);
  const [isPublishing, setIsPublishing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [expandedFlats, setExpandedFlats] = useState<Record<string, boolean>>({});

  // Shared expenses state
  const [deliveryCost, setDeliveryCost] = useState('0');

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Check if bills already finalized
      const bills = await api.billing.getRoundBills(societyId, roundId);
      setFinalizedBills(bills);

      // 2. Fetch allocation preview
      const prev = await api.billing.getAllocationPreview(societyId, roundId);
      setPreview(prev);
    } catch (err: any) {
      setError(err.message || 'Failed to load cost allocation preview.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [societyId, roundId]);

  const handleFinalizeBills = async () => {
    if (!preview?.can_finalize) return;
    if (!window.confirm('Finalize bills for all flats? This creates persistent immutable billing records.')) return;

    setIsFinalizing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const deliveryAmt = parseFloat(deliveryCost) || 0;
      const sharedCosts = deliveryAmt > 0 ? [{ name: 'Logistics / Delivery Share', amount: deliveryAmt }] : [];

      const result = await api.billing.finalizeBills(societyId, roundId, {
        shared_costs: sharedCosts,
      });
      setFinalizedBills(result);
      setSuccessMsg(`Successfully finalized ${result.length} flat bills!`);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to finalize bills.');
    } finally {
      setIsFinalizing(false);
    }
  };

  const handlePublishAnnouncement = async () => {
    setIsPublishing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await api.billing.publishAnnouncement(societyId, roundId);
      setSuccessMsg('Generic privacy-safe bill availability announcement sent to Nexconn Group Chat!');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to dispatch chat announcement.');
    } finally {
      setIsPublishing(false);
    }
  };

  const toggleFlat = (flatNum: string) => {
    setExpandedFlats((prev) => ({ ...prev, [flatNum]: !prev[flatNum] }));
  };

  if (isLoading) {
    return (
      <div className="py-12 text-center text-slate-400">
        <RefreshCw className="h-8 w-8 animate-spin mx-auto text-[#23865B] mb-2" />
        <span className="text-xs font-medium">Calculating per-flat cost allocations...</span>
      </div>
    );
  }

  const isFinalized = finalizedBills.length > 0;
  const isPublished = finalizedBills.some((b) => b.status === 'published');

  return (
    <div className="space-y-6">
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

      {/* Top Reconciliation Status Card */}
      {preview && (
        <Card className={`p-6 border-2 ${preview.is_reconciled ? 'border-[#A7B8A0] bg-[#F3F0E8]/60' : 'border-amber-200 bg-amber-50/40'}`}>
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <Badge variant={preview.is_reconciled ? 'success' : 'warning'} size="md">
                  {preview.is_reconciled ? 'Reconciliation Verified' : 'Reconciliation Pending'}
                </Badge>
                {isFinalized && (
                  <Badge variant={isPublished ? 'success' : 'primary'} size="md">
                    {isPublished ? 'PUBLISHED IN CHAT' : 'BILLS FINALIZED'}
                  </Badge>
                )}
              </div>
              <h3 className="text-base font-serif font-bold text-[#252824]">
                {preview.reconciliation_message}
              </h3>
              <p className="text-xs text-[#827F76]">
                Formula: Actual Purchases (₹{preview.total_actual_purchase_cost.toFixed(2)}) =
                Allocated (₹{preview.total_allocated_flats_cost.toFixed(2)}) +
                Unallocated (₹{preview.unallocated_cost.toFixed(2)})
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 shrink-0">
              {!isFinalized ? (
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleFinalizeBills}
                  disabled={!preview.can_finalize || isFinalizing}
                  leftIcon={<Lock className="h-4 w-4" />}
                >
                  {isFinalizing ? 'Finalizing Bills...' : 'Finalize & Lock Bills'}
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="md"
                  onClick={handlePublishAnnouncement}
                  disabled={isPublishing}
                  leftIcon={<Send className="h-4 w-4" />}
                >
                  {isPublishing ? 'Publishing...' : 'Announce in Nexconn Chat'}
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Optional Shared Logistics Input (Only before finalization) */}
      {!isFinalized && (
        <Card className="p-4 bg-[#F3F0E8]/40 border border-[#EBE8DF]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h4 className="text-xs font-bold text-[#252824]">Additional Shared Round Expenses (Optional)</h4>
              <p className="text-[11px] text-[#827F76]">
                e.g. Porter / Auto / Delivery fee split evenly across all participating flats.
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs font-bold text-[#252824]">₹</span>
              <input
                type="number"
                step="1"
                value={deliveryCost}
                onChange={(e) => setDeliveryCost(e.target.value)}
                placeholder="0"
                className="w-24 text-xs rounded-xl border border-[#DFDAD0] p-2 bg-white text-right focus:outline-none focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 font-bold"
              />
            </div>
          </div>
        </Card>
      )}

      {/* Purchase-to-Order Fulfillment Summary */}
      {preview && preview.matching_summaries.length > 0 && (
        <Card className="p-0 overflow-hidden border-[#EBE8DF]">
          <div className="p-4 border-b border-[#EBE8DF] flex items-center justify-between">
            <h4 className="text-sm font-serif font-bold text-[#252824]">Purchase Fulfillment Matching</h4>
            <span className="text-xs text-[#827F76]">{preview.matching_summaries.length} Products</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F3F0E8] border-b border-[#EBE8DF] text-[#827F76] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Item Name</th>
                  <th className="py-3 px-4 text-center">Requested Qty</th>
                  <th className="py-3 px-4 text-center">Purchased Qty</th>
                  <th className="py-3 px-4 text-center">Fulfilled</th>
                  <th className="py-3 px-4 text-center">Unfulfilled</th>
                  <th className="py-3 px-4 text-right">Effective Rate</th>
                  <th className="py-3 px-4 text-right">Total Allocated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EBE8DF]">
                {preview.matching_summaries.map((m) => (
                  <tr key={m.item_key} className="hover:bg-[#FAF9F6] transition-colors">
                    <td className="py-3 px-4">
                      <span className="font-bold text-[#252824]">{m.item_name}</span>
                      {(m.brand || m.variant) && (
                        <span className="text-[11px] text-[#827F76] block">
                          {[m.brand, m.variant].filter(Boolean).join(' • ')}
                        </span>
                      )}
                      {m.is_substituted && (
                        <span className="inline-block mt-0.5 text-[10px] text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
                          Substituted with {m.substitute_item_name}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center text-[#827F76]">{m.requested_quantity} {m.unit}</td>
                    <td className="py-3 px-4 text-center font-bold text-[#252824]">{m.purchased_quantity} {m.unit}</td>
                    <td className="py-3 px-4 text-center text-[#174D3A] font-semibold">{m.fulfilled_quantity} {m.unit}</td>
                    <td className="py-3 px-4 text-center">
                      {m.unfulfilled_quantity > 0 ? (
                        <span className="text-rose-700 font-bold">{m.unfulfilled_quantity} {m.unit}</span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right text-[#174D3A] font-semibold">
                      ₹{m.effective_unit_cost.toFixed(2)}/{m.unit}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-[#252824]">
                      ₹{m.total_cost.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Flat-wise Cost Allocations */}
      {preview && (
        <Card className="p-0 overflow-hidden border-[#EBE8DF]">
          <div className="p-4 border-b border-[#EBE8DF] flex items-center justify-between">
            <h4 className="text-sm font-serif font-bold text-[#252824]">Per-Flat Bill Allocations</h4>
            <span className="text-xs text-[#827F76]">{preview.flat_allocations.length} Flats</span>
          </div>

          <div className="divide-y divide-[#EBE8DF]">
            {preview.flat_allocations.map((flat) => {
              const isExpanded = !!expandedFlats[flat.flat_number];
              return (
                <div key={flat.flat_number} className="p-4 hover:bg-[#FAF9F6] transition-colors">
                  <div
                    onClick={() => toggleFlat(flat.flat_number)}
                    className="flex items-center justify-between cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-[#827F76]" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-[#827F76]" />
                      )}
                      <div>
                        <div className="font-bold text-xs text-[#252824]">
                          Flat {flat.flat_number} — {flat.resident_name}
                        </div>
                        <div className="text-[11px] text-[#827F76]">
                          {flat.items.length} items requested
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-xs font-bold text-[#174D3A]">
                        ₹{flat.final_amount_payable.toFixed(2)}
                      </span>
                      {flat.shared_costs_allocated > 0 && (
                        <span className="text-[10px] text-[#827F76] block">
                          incl. ₹{flat.shared_costs_allocated.toFixed(2)} shared
                        </span>
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-[#EBE8DF] pl-7">
                      <table className="w-full text-left text-[11px]">
                        <thead>
                          <tr className="text-[#827F76] border-b border-[#EBE8DF]">
                            <th className="py-1">Item</th>
                            <th className="py-1 text-center">Req / Alloc</th>
                            <th className="py-1 text-right">Unit Rate</th>
                            <th className="py-1 text-right">Total</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[#EBE8DF]/50">
                          {flat.items.map((it, idx) => (
                            <tr key={idx}>
                              <td className="py-1.5 font-medium text-[#252824]">
                                {it.item_name}
                                {it.is_substituted && (
                                  <span className="text-[9px] text-amber-800 ml-1.5 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded-full">Substituted</span>
                                )}
                                {it.is_unfulfilled && (
                                  <span className="text-[9px] text-rose-800 ml-1.5 bg-rose-50 border border-rose-200 px-1.5 py-0.5 rounded-full">Unavailable</span>
                                )}
                              </td>
                              <td className="py-1.5 text-center text-[#827F76]">
                                {it.requested_quantity} / <strong className="text-[#252824]">{it.allocated_quantity} {it.unit}</strong>
                              </td>
                              <td className="py-1.5 text-right text-[#827F76]">
                                ₹{it.unit_price.toFixed(2)}
                              </td>
                              <td className="py-1.5 text-right font-bold text-[#252824]">
                                ₹{it.item_total.toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
};
