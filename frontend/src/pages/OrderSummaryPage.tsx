import React, { useState, useEffect } from 'react';
import {
  Printer,
  Receipt,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  AlertCircle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { api } from '../services/api';
import { ApiGroceryBill } from '../types';

/**
 * Screen 7 / Resident Billing: Order & Savings Summary.
 * Loads actual, verified bills from the Phase 7 Billing Service.
 */
export const OrderSummaryPage: React.FC = () => {
  const navigate = useNavigate();
  const { society, currentUser } = useApp();

  const [bills, setBills] = useState<ApiGroceryBill[]>([]);
  const [selectedBill, setSelectedBill] = useState<ApiGroceryBill | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    api.billing
      .getMyBills()
      .then((res) => {
        setBills(res);
        if (res.length > 0) {
          setSelectedBill(res[0]);
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to load grocery bills.');
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="py-16 text-center space-y-3">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-3 border-emerald-600 border-t-transparent" />
        <p className="text-xs text-[#718078]">Loading verified grocery bills...</p>
      </div>
    );
  }

  if (bills.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="My Grocery Bills"
          description={`Flat ${currentUser?.flatNumber || ''} • ${society?.name || 'Society Cart'}`}
          badge={<Badge variant="neutral" size="md">Resident Billing</Badge>}
          actions={
            <Button size="sm" variant="outline" onClick={() => navigate('/resident')}>
              Back to Dashboard
            </Button>
          }
        />
        <Card className="py-16 text-center space-y-4 max-w-lg mx-auto">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
            <Receipt className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-[#18231E]">No Finalized Bills Yet</h3>
            <p className="mt-1 text-xs text-[#718078] leading-relaxed">
              When the society volunteer completes shopping and finalizes the round, your flat's itemized bill and verified retail savings will appear here.
            </p>
          </div>
          <Button size="sm" variant="primary" onClick={() => navigate('/resident')}>
            View Active Round
          </Button>
        </Card>
      </div>
    );
  }

  const bill = selectedBill || bills[0];

  return (
    <div className="space-y-6 print:space-y-4">
      {/* Top Header */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-800 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      <PageHeader
        title="Itemized Grocery Bill"
        description={`Round #${bill.round_number} • Flat ${bill.flat_number} (${bill.resident_name})`}
        badge={
          <Badge
            variant={
              bill.status === 'published'
                ? 'success'
                : bill.status === 'corrected'
                ? 'warning'
                : 'primary'
            }
            size="md"
          >
            {bill.status === 'corrected'
              ? `Corrected (v${bill.bill_version})`
              : bill.status.toUpperCase()}
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2 print:hidden">
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/resident')}
              leftIcon={<ArrowLeft className="h-4 w-4" />}
            >
              Dashboard
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={handlePrint}
              leftIcon={<Printer className="h-4 w-4" />}
            >
              Print Bill
            </Button>
          </div>
        }
      />

      {/* Bill selector if resident has multiple rounds */}
      {bills.length > 1 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-1 print:hidden">
          <span className="text-xs font-semibold text-[#718078] shrink-0">Select Round:</span>
          {bills.map((b) => (
            <button
              key={b.id}
              onClick={() => setSelectedBill(b)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                b.id === bill.id
                  ? 'bg-[#196B48] text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-[#18231E] hover:bg-slate-50'
              }`}
            >
              Round #{b.round_number} — ₹{b.total_amount.toFixed(2)}
            </button>
          ))}
        </div>
      )}

      {/* Correction Banner if applicable */}
      {bill.status === 'corrected' && bill.correction_notes && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 text-xs text-amber-900 flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <strong>Notice of Bill Correction (v{bill.bill_version}):</strong> {bill.correction_notes}
          </div>
        </div>
      )}

      {/* Hero Bill Summary Card */}
      <Card className="border-emerald-200 bg-gradient-to-r from-emerald-50/40 via-white to-emerald-50/20 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-[#23865B]" /> Verified Community Bulk Order
            </span>
            <h2 className="text-2xl font-black text-[#18231E]">
              Total Payable: ₹{bill.total_amount.toFixed(2)}
            </h2>
            <p className="text-xs text-[#718078]">
              {society?.name || bill.society_name} • Round #{bill.round_number}
            </p>
          </div>

          <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-emerald-100 shadow-xs shrink-0">
            <div className="text-center px-3 border-r border-slate-100">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Items Subtotal</span>
              <span className="text-base font-bold text-[#18231E]">₹{bill.items_subtotal.toFixed(2)}</span>
            </div>
            {bill.shared_costs_total > 0 && (
              <div className="text-center px-3 border-r border-slate-100">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Shared Expenses</span>
                <span className="text-base font-bold text-[#18231E]">₹{bill.shared_costs_total.toFixed(2)}</span>
              </div>
            )}
            <div className="text-center px-3">
              <span className="text-[10px] uppercase font-bold text-[#23865B] block">Status</span>
              <Badge variant="success" size="sm">
                {bill.status.toUpperCase()}
              </Badge>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Grid: Itemized Bill Table (2 Cols) + Invoice Meta (1 Col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#18231E]">Itemized Bill Details</h3>
            <span className="text-xs text-[#718078]">{bill.items.length} Items</span>
          </div>

          <Card className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAF9] border-b border-[#E6ECE8] text-[#718078] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Item & Details</th>
                    <th className="py-3 px-4 text-center">Requested</th>
                    <th className="py-3 px-4 text-center">Received</th>
                    <th className="py-3 px-4 text-right">Unit Rate</th>
                    <th className="py-3 px-4 text-right">Total (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6ECE8]">
                  {bill.items.map((it, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-[#18231E]">{it.item_name}</div>
                        {(it.brand || it.variant) && (
                          <div className="text-[11px] text-[#718078]">
                            {[it.brand, it.variant].filter(Boolean).join(' • ')}
                          </div>
                        )}
                        {it.is_substituted && (
                          <span className="inline-block mt-1 text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-medium">
                            {it.substitute_notes || 'Product Substituted'}
                          </span>
                        )}
                        {it.is_unfulfilled && (
                          <span className="inline-block mt-1 text-[10px] text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded font-medium">
                            {it.unfulfilled_quantity > 0
                              ? `Partially unfulfilled (${it.unfulfilled_quantity} ${it.unit} unavailable)`
                              : 'Item unavailable at store'}
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-center font-medium text-[#718078]">
                        {it.requested_quantity} {it.unit}
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-[#18231E]">
                        {it.allocated_quantity > 0 ? (
                          `${it.allocated_quantity} ${it.unit}`
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right text-[#23865B] font-semibold">
                        {it.allocated_quantity > 0 ? `₹${it.unit_price.toFixed(2)}/${it.unit}` : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-right font-bold text-[#18231E]">
                        ₹{it.item_total.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-[#F8FAF9] border-t border-[#E6ECE8] font-bold text-xs">
                  <tr>
                    <td colSpan={4} className="py-2.5 px-4 text-right text-[#718078]">
                      Grocery Subtotal:
                    </td>
                    <td className="py-2.5 px-4 text-right text-[#18231E]">
                      ₹{bill.items_subtotal.toFixed(2)}
                    </td>
                  </tr>
                  {bill.shared_costs.map((sc, sidx) => (
                    <tr key={sidx}>
                      <td colSpan={4} className="py-2 px-4 text-right text-[#718078] font-normal">
                        {sc.name}:
                      </td>
                      <td className="py-2 px-4 text-right text-[#18231E]">
                        ₹{sc.amount.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                  <tr className="border-t-2 border-slate-200 text-sm">
                    <td colSpan={4} className="py-3 px-4 text-right text-[#18231E] font-extrabold">
                      Final Amount Payable:
                    </td>
                    <td className="py-3 px-4 text-right text-[#23865B] font-black">
                      ₹{bill.total_amount.toFixed(2)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>
        </div>

        {/* Invoice Meta */}
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Invoice Meta
            </h4>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Resident Name</span>
                <strong className="text-[#18231E]">{bill.resident_name}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Flat Number</span>
                <strong className="text-[#18231E]">Flat {bill.flat_number}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Society</span>
                <strong className="text-[#18231E]">{bill.society_name}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Bill Version</span>
                <strong className="text-[#18231E]">v{bill.bill_version}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Created Date</span>
                <strong className="text-[#18231E]">
                  {new Date(bill.created_at).toLocaleDateString()}
                </strong>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#718078]">Verification</span>
                <Badge variant="success" size="sm">
                  Verified Reconciled
                </Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
