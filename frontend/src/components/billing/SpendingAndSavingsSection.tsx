import React, { useState, useEffect } from 'react';
import {
  TrendingDown,
  Receipt,
  PlusCircle,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Building2,
} from 'lucide-react';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { StatCard } from '../common/StatCard';
import { api } from '../../services/api';
import {
  ApiRecordBenchmarkRequest,
  ApiRetailBenchmark,
  ApiSocietySavingsSummary,
  ApiSocietySpendingSummary,
} from '../../types';

interface SpendingAndSavingsSectionProps {
  societyId: string;
  roundId: string;
}

export const SpendingAndSavingsSection: React.FC<SpendingAndSavingsSectionProps> = ({
  societyId,
  roundId,
}) => {
  const [spending, setSpending] = useState<ApiSocietySpendingSummary | null>(null);
  const [savings, setSavings] = useState<ApiSocietySavingsSummary | null>(null);
  const [benchmarks, setBenchmarks] = useState<ApiRetailBenchmark[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New Benchmark Form Modal
  const [showModal, setShowModal] = useState<boolean>(false);
  const [productName, setProductName] = useState('');
  const [brand, setBrand] = useState('');
  const [variant, setVariant] = useState('');
  const [pkgSize, setPkgSize] = useState('1');
  const [pkgUnit, setPkgUnit] = useState('kg');
  const [benchPrice, setBenchPrice] = useState('');
  const [storeName, setStoreName] = useState('');
  const [sourceType, setSourceType] = useState('receipt');
  const [evidenceRef, setEvidenceRef] = useState('');
  const [location, setLocation] = useState('Local Market');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [spendingData, savingsData, benchmarksData] = await Promise.all([
        api.billing.getSpendingSummary(societyId, roundId),
        api.billing.getSavingsSummary(societyId, roundId),
        api.billing.listBenchmarks(societyId, roundId),
      ]);
      setSpending(spendingData);
      setSavings(savingsData);
      setBenchmarks(benchmarksData);
    } catch (err: any) {
      setError(err.message || 'Failed to load spending and savings data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [societyId, roundId]);

  const handleCreateBenchmark = async (e: React.FormEvent) => {
    e.preventDefault();
    const size = parseFloat(pkgSize);
    const price = parseFloat(benchPrice);
    if (!productName.trim() || isNaN(size) || size <= 0 || isNaN(price) || price <= 0 || !storeName.trim()) {
      setError('Please provide valid product name, package size > 0, price > 0, and store name.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const payload: ApiRecordBenchmarkRequest = {
        product_name: productName.trim(),
        brand: brand.trim() || null,
        variant: variant.trim() || null,
        package_size: size,
        package_unit: pkgUnit.trim(),
        benchmark_price: price,
        store_name: storeName.trim(),
        source_type: sourceType,
        evidence_ref: evidenceRef.trim() || null,
        evidence_url: null,
        evidence_date: new Date().toISOString(),
        location: location.trim(),
      };
      await api.billing.recordBenchmark(societyId, roundId, payload);
      setSuccessMsg(`Recorded retail benchmark evidence for "${productName}".`);
      setShowModal(false);

      // Reset
      setProductName('');
      setBrand('');
      setVariant('');
      setBenchPrice('');
      setStoreName('');
      setEvidenceRef('');

      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to record benchmark.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-12 text-center text-slate-400">
        <RefreshCw className="h-8 w-8 animate-spin mx-auto text-[#23865B] mb-2" />
        <span className="text-xs font-medium">Loading society spending audit and savings analysis...</span>
      </div>
    );
  }

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

      {/* 1. Society Spending Summary */}
      {spending && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-serif font-bold text-[#252824]">Society Procurement & Spending Summary</h3>
            <span className="text-xs text-[#827F76]">Audit Reconciliation</span>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Total Bulk Spend"
              value={`₹${spending.total_actual_purchase_cost.toFixed(2)}`}
              subtext={`${spending.total_purchased_items_count} items bought`}
              icon={<Receipt className="h-5 w-5 text-[#174D3A]" />}
            />
            <StatCard
              label="Allocated to Flats"
              value={`₹${spending.total_allocated_bill_costs.toFixed(2)}`}
              subtext={`${spending.total_flats_billed} flats billed`}
              icon={<Building2 className="h-5 w-5 text-[#174D3A]" />}
            />
            <StatCard
              label="Shared Expenses"
              value={`₹${spending.total_shared_costs.toFixed(2)}`}
              subtext="Delivery & handling"
              icon={<TrendingDown className="h-5 w-5 text-[#827F76]" />}
            />
            <StatCard
              label="Unallocated Inventory"
              value={`₹${spending.total_unallocated_cost.toFixed(2)}`}
              subtext="Surplus quantity value"
              icon={<ShieldCheck className="h-5 w-5 text-[#174D3A]" />}
            />
          </div>

          <Card className="p-4 bg-[#F3F0E8]/40 border border-[#EBE8DF] text-xs">
            <div className="font-bold text-[#252824] mb-1">Reconciliation Equation:</div>
            <code className="text-[#174D3A] font-mono text-[11px] block">{spending.reconciliation_equation}</code>
          </Card>
        </div>
      )}

      {/* 2. Verified Retail Benchmark Savings */}
      {savings && (
        <div className="space-y-4 pt-4 border-t border-[#EBE8DF]">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-serif font-bold text-[#252824]">Verified Retail Savings Analysis</h3>
              <p className="text-xs text-[#827F76]">
                Formula: Savings = Individual Retail Benchmark Cost - Bulk Purchase Cost
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowModal(true)}
              leftIcon={<PlusCircle className="h-4 w-4" />}
            >
              Add Price Evidence
            </Button>
          </div>

          {/* Hero Savings Card */}
          <Card className="p-6 border-[#EBE8DF] bg-gradient-to-r from-[#F3F0E8]/70 via-white to-[#F3F0E8]/40 shadow-card">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#174D3A] flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-[#174D3A]" /> {savings.label}
                </span>
                <h2 className="text-2xl sm:text-3xl font-serif font-bold text-[#252824]">
                  ₹{savings.verified_savings_amount.toFixed(2)} ({savings.verified_savings_percentage}%)
                </h2>
                <p className="text-xs text-[#827F76]">
                  Computed for {savings.items_with_verified_benchmarks} products with verified retail evidence.
                  {savings.is_partial_coverage && (
                    <span className="text-amber-800 font-medium ml-1">
                      ({savings.items_excluded_count} items excluded due to missing evidence; not extrapolated).
                    </span>
                  )}
                </p>
              </div>

              <div className="flex items-center gap-4 bg-white p-4 rounded-2xl border border-[#EBE8DF] shadow-xs shrink-0">
                <div className="text-center px-3 border-r border-[#EBE8DF]">
                  <span className="text-[10px] uppercase font-bold text-[#827F76] block">Retail Benchmark</span>
                  <span className="text-base font-bold text-[#827F76] line-through">
                    ₹{savings.total_individual_benchmark_cost.toFixed(2)}
                  </span>
                </div>
                <div className="text-center px-3">
                  <span className="text-[10px] uppercase font-bold text-[#174D3A] block">Bulk Cost</span>
                  <span className="text-lg font-bold text-[#252824]">
                    ₹{savings.total_bulk_cost_comparable_items.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Itemized Comparison Table */}
          <Card className="p-0 overflow-hidden border-[#EBE8DF]">
            <div className="p-4 border-b border-[#EBE8DF] flex items-center justify-between">
              <h4 className="text-sm font-serif font-bold text-[#252824]">Item-by-Item Price Comparison</h4>
              <span className="text-xs text-[#827F76]">{savings.items.length} Evaluated Items</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F3F0E8] border-b border-[#EBE8DF] text-[#827F76] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Product Name</th>
                    <th className="py-3 px-4 text-center">Procured Qty</th>
                    <th className="py-3 px-4 text-right">Bulk Rate</th>
                    <th className="py-3 px-4 text-right">Retail Benchmark</th>
                    <th className="py-3 px-4 text-right">Verified Savings</th>
                    <th className="py-3 px-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EBE8DF]">
                  {savings.items.map((it, idx) => (
                    <tr key={idx} className="hover:bg-[#FAF9F6] transition-colors">
                      <td className="py-3 px-4">
                        <span className="font-bold text-[#252824]">{it.item_name}</span>
                        {(it.brand || it.variant) && (
                          <span className="text-[11px] text-[#827F76] block">
                            {[it.brand, it.variant].filter(Boolean).join(' • ')}
                          </span>
                        )}
                        {it.benchmark_store && (
                          <span className="text-[10px] text-[#827F76] block">
                            Store: {it.benchmark_store}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center font-medium text-[#827F76]">
                        {it.quantity} {it.unit}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-[#252824]">
                        ₹{it.bulk_unit_price.toFixed(2)}/{it.unit}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {it.has_benchmark && it.benchmark_unit_price ? (
                          <span className="text-[#827F76] font-semibold">
                            ₹{it.benchmark_unit_price.toFixed(2)}/{it.unit}
                          </span>
                        ) : (
                          <span className="text-slate-400 italic">No evidence</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {it.has_benchmark && it.savings_amount !== null && it.savings_amount !== undefined ? (
                          <span className="font-bold text-[#174D3A]">
                            ₹{it.savings_amount.toFixed(2)} ({it.savings_percentage}%)
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge variant={it.has_benchmark ? 'success' : 'neutral'} size="sm">
                          {it.status_label}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* 3. Recorded Retail Benchmarks Log */}
      <Card className="p-0 overflow-hidden border-[#EBE8DF]">
        <div className="p-4 border-b border-[#EBE8DF] flex items-center justify-between">
          <h4 className="text-sm font-serif font-bold text-[#252824]">Verified Benchmark Evidence Library</h4>
          <span className="text-xs text-[#827F76]">{benchmarks.length} Evidence Records</span>
        </div>

        {benchmarks.length === 0 ? (
          <div className="py-12 text-center text-[#827F76]">
            <Receipt className="h-10 w-10 mx-auto text-[#DFDAD0] mb-2" />
            <p className="text-xs">No benchmark evidence recorded yet. Add receipts to verify savings.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F3F0E8] border-b border-[#EBE8DF] text-[#827F76] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Product & Brand</th>
                  <th className="py-3 px-4">Retailer</th>
                  <th className="py-3 px-4 text-center">Package Size</th>
                  <th className="py-3 px-4 text-right">Retail Price</th>
                  <th className="py-3 px-4 text-right">Unit Rate</th>
                  <th className="py-3 px-4 text-center">Evidence Date</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EBE8DF]">
                {benchmarks.map((b) => (
                  <tr key={b.id} className="hover:bg-[#FAF9F6] transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-[#252824]">{b.product_name}</div>
                      {(b.brand || b.variant) && (
                        <div className="text-[11px] text-[#827F76]">
                          {[b.brand, b.variant].filter(Boolean).join(' • ')}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-[#827F76]">
                      {b.store_name} ({b.location})
                    </td>
                    <td className="py-3 px-4 text-center text-[#827F76]">
                      {b.package_size} {b.package_unit}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-[#252824]">
                      ₹{b.benchmark_price.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right text-[#174D3A] font-semibold">
                      ₹{b.benchmark_unit_price.toFixed(2)}/{b.package_unit}
                    </td>
                    <td className="py-3 px-4 text-center text-[#827F76]">
                      {new Date(b.evidence_date).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant="success" size="sm">{b.verification_status.toUpperCase()}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Add Benchmark Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#252824]/50 backdrop-blur-xs p-4">
          <div className="bg-[#FAF9F6] rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-lifted border border-[#EBE8DF]">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-serif font-bold text-[#252824]">Record Retail Benchmark Evidence</h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-[#827F76] hover:text-[#252824] text-sm font-bold p-1 rounded-lg"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-[#827F76]">
              Attach verifiable retail purchase price proof from receipts, store quotations, or dated listings.
            </p>

            <form onSubmit={handleCreateBenchmark} className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-[#252824] mb-1">Product Name *</label>
                <input
                  type="text"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder="e.g. Sona Masoori Rice"
                  className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Brand (Optional)</label>
                  <input
                    type="text"
                    value={brand}
                    onChange={(e) => setBrand(e.target.value)}
                    placeholder="e.g. India Gate"
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Variant (Optional)</label>
                  <input
                    type="text"
                    value={variant}
                    onChange={(e) => setVariant(e.target.value)}
                    placeholder="e.g. Premium"
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Pack Size *</label>
                  <input
                    type="number"
                    step="any"
                    value={pkgSize}
                    onChange={(e) => setPkgSize(e.target.value)}
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Unit *</label>
                  <select
                    value={pkgUnit}
                    onChange={(e) => setPkgUnit(e.target.value)}
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                  >
                    <option value="kg">kg</option>
                    <option value="L">L</option>
                    <option value="packet">packet</option>
                    <option value="piece">piece</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Price (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={benchPrice}
                    onChange={(e) => setBenchPrice(e.target.value)}
                    placeholder="65.00"
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Retailer Store *</label>
                  <input
                    type="text"
                    value={storeName}
                    onChange={(e) => setStoreName(e.target.value)}
                    placeholder="e.g. Reliance Fresh"
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Receipt / Proof Ref</label>
                  <input
                    type="text"
                    value={evidenceRef}
                    onChange={(e) => setEvidenceRef(e.target.value)}
                    placeholder="e.g. REC-10294"
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Evidence Type</label>
                  <select
                    value={sourceType}
                    onChange={(e) => setSourceType(e.target.value)}
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                  >
                    <option value="receipt">Store Receipt</option>
                    <option value="quotation">Vendor Quotation</option>
                    <option value="price_listing">Dated Catalog Listing</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#252824] mb-1">Locality / Market</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Kondapur, Hyderabad"
                    className="w-full text-xs rounded-xl border border-[#DFDAD0] bg-white p-2.5 focus:border-[#174D3A] focus:ring-2 focus:ring-[#174D3A]/10 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmitting}
                  leftIcon={<CheckCircle2 className="h-4 w-4" />}
                >
                  {isSubmitting ? 'Saving Evidence...' : 'Save Benchmark Evidence'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
