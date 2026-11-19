import React from 'react';
import {
  Printer,
  TrendingDown,
  AlertCircle,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';

/**
 * Screen 7: Order & Savings Summary — Shows completed order reconciliation, itemized flat bill, and formula-backed savings proof.
 */
export const OrderSummaryPage: React.FC = () => {
  const { society, residentBill, pastRounds } = useApp();

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <PageHeader
        title="Order Summary & Savings Receipt"
        description={`${residentBill.roundTitle} • Flat ${residentBill.flatNumber} (${residentBill.residentName})`}
        badge={
          <Badge variant="success" size="md">
            Order Delivered & Billed
          </Badge>
        }
        actions={
          <Button
            size="sm"
            variant="outline"
            onClick={handlePrint}
            leftIcon={<Printer className="h-4 w-4" />}
            className="print:hidden"
          >
            Download / Print Bill
          </Button>
        }
      />

      {/* Illustrative Demo Notice */}
      <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3 text-xs text-amber-900 flex items-start gap-2.5 print:hidden">
        <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
        <span>
          <strong>Illustrative Pricing Demonstration:</strong> Item prices and retail benchmark values shown below are simulated for UI evaluation. Actual savings in Phase 7 will be computed directly against verified local shop receipts.
        </span>
      </div>

      {/* Hero Savings Comparison Card */}
      <Card className="border-emerald-200 bg-gradient-to-r from-emerald-50/60 via-white to-emerald-50/40 p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
              <TrendingDown className="h-4 w-4 text-[#23865B]" /> Verified Group Savings Calculation
            </span>
            <h2 className="text-xl sm:text-2xl font-black text-[#18231E]">
              Flat {residentBill.flatNumber} Saved ₹{residentBill.totalSavings}
            </h2>
            <p className="text-xs text-[#718078] max-w-xl">
              By combining orders with 14 neighbors, you paid wholesale rates rather than standard instant-delivery retail markup.
            </p>

            {/* Formula callout */}
            <div className="inline-block mt-2 px-3 py-1.5 rounded-lg bg-white border border-emerald-200 text-[11px] text-emerald-950 font-mono">
              Savings = Retail Benchmark (₹{residentBill.benchmarkMarketTotal}) - Bulk Cost (₹{residentBill.finalPayableAmount}) = ₹{residentBill.totalSavings}
            </div>
          </div>

          {/* Quick Metrics Trio */}
          <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-emerald-100 shadow-xs shrink-0">
            <div className="text-center px-3 border-r border-slate-100">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Retail Value</span>
              <span className="text-base font-bold text-slate-400 line-through">
                ₹{residentBill.benchmarkMarketTotal}
              </span>
            </div>
            <div className="text-center px-3 border-r border-slate-100">
              <span className="text-[10px] uppercase font-bold text-emerald-800 block">You Paid</span>
              <span className="text-lg font-black text-[#18231E]">
                ₹{residentBill.finalPayableAmount}
              </span>
            </div>
            <div className="text-center px-3">
              <span className="text-[10px] uppercase font-bold text-[#23865B] block">Saved</span>
              <span className="text-lg font-black text-[#23865B]">
                ₹{residentBill.totalSavings}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Grid: Itemized Bill (2 Cols) + Summary Meta (1 Col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Itemized Flat Bill Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#18231E]">Itemized Invoice</h3>
            <span className="text-xs text-[#718078]">Order #{residentBill.id.toUpperCase()}</span>
          </div>

          <Card className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAF9] border-b border-[#E6ECE8] text-[#718078] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Grocery Item</th>
                    <th className="py-3 px-4 text-center">Quantity</th>
                    <th className="py-3 px-4 text-right">Wholesale Rate</th>
                    <th className="py-3 px-4 text-right">Retail Rate</th>
                    <th className="py-3 px-4 text-right">Total (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6ECE8]">
                  {residentBill.items.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#18231E]">
                        {item.name}
                      </td>
                      <td className="py-3.5 px-4 text-center font-medium">
                        {item.quantity} {item.unit}
                      </td>
                      <td className="py-3.5 px-4 text-right text-[#23865B] font-semibold">
                        ₹{item.unitPrice}/{item.unit}
                      </td>
                      <td className="py-3.5 px-4 text-right text-slate-400 line-through">
                        ₹{Math.round(item.benchmarkPrice / item.quantity)}/{item.unit}
                      </td>
                      <td className="py-3.5 px-4 text-right font-bold text-[#18231E]">
                        ₹{item.totalPrice}
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
                      ₹{residentBill.subtotal}
                    </td>
                  </tr>
                  <tr>
                    <td colSpan={4} className="py-2.5 px-4 text-right text-[#718078]">
                      Volunteer Delivery & Handling Fee:
                    </td>
                    <td className="py-2.5 px-4 text-right text-[#18231E]">
                      ₹{residentBill.deliveryHandlingFee}
                    </td>
                  </tr>
                  <tr className="border-t-2 border-slate-200 text-sm">
                    <td colSpan={4} className="py-3 px-4 text-right text-[#18231E] font-extrabold">
                      Final Payable Amount:
                    </td>
                    <td className="py-3 px-4 text-right text-[#23865B] font-black">
                      ₹{residentBill.finalPayableAmount}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>
        </div>

        {/* Order Meta & Past Rounds Card */}
        <div className="space-y-6">
          {/* Order Details Card */}
          <Card className="p-5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Receipt Details
            </h4>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Resident</span>
                <strong className="text-[#18231E]">{residentBill.residentName}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Flat Number</span>
                <strong className="text-[#18231E]">Flat {residentBill.flatNumber}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Society</span>
                <strong className="text-[#18231E]">{society.name}</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-[#718078]">Order Date</span>
                <strong className="text-[#18231E]">{residentBill.orderDate}</strong>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-[#718078]">Payment Status</span>
                <Badge variant="success" size="sm">
                  PAID (Verified by Volunteer)
                </Badge>
              </div>
            </div>
          </Card>

          {/* Past Rounds Mini-List */}
          <Card className="p-5 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Past Completed Rounds
            </h4>

            <div className="divide-y divide-slate-100">
              {pastRounds.map((round) => (
                <div key={round.id} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <p className="font-bold text-[#18231E]">Round #{round.roundNumber}</p>
                    <p className="text-[11px] text-[#718078]">{round.shopVisitDate} • {round.participatingFlatsCount} Flats</p>
                  </div>
                  <span className="font-extrabold text-[#23865B]">
                    ₹{round.finalPurchasedValue}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
