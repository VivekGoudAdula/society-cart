import React, { useState, useMemo } from 'react';
import {
  Printer,
  Check,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { SearchInput } from '../components/common/SearchInput';

type ViewMode = 'consolidated' | 'flat-wise';

/**
 * Screen 6: Consolidated Shopping List Screen — Operations tool for volunteers to buy in bulk and pack orders flat-by-flat.
 */
export const ShoppingListPage: React.FC = () => {
  const { society, activeRound, groceryItems, toggleItemPurchased } = useApp();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [viewMode, setViewMode] = useState<ViewMode>('consolidated');

  const categories = ['All', 'Grains & Staples', 'Vegetables', 'Dairy', 'Household', 'Fruits', 'Others'];

  // Filter items by category & search query
  const filteredItems = useMemo(() => {
    return groceryItems.filter((item) => {
      const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory === 'All' || item.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [groceryItems, searchQuery, selectedCategory]);

  // Aggregate flat-wise packing breakdown
  const flatPackingBreakdown = useMemo(() => {
    const flatMap: Record<string, Array<{ itemName: string; quantity: number; unit: string }>> = {};

    groceryItems.forEach((item) => {
      item.flatRequests.forEach((req) => {
        if (!flatMap[req.flatNumber]) {
          flatMap[req.flatNumber] = [];
        }
        flatMap[req.flatNumber].push({
          itemName: item.name,
          quantity: req.quantity,
          unit: item.unit,
        });
      });
    });

    return Object.entries(flatMap).sort(([flatA], [flatB]) => flatA.localeCompare(flatB));
  }, [groceryItems]);

  const purchasedCount = groceryItems.filter((i) => i.isPurchased).length;
  const progressPercent = Math.round((purchasedCount / groceryItems.length) * 100);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Consolidated Bulk Shopping List"
        description={`${activeRound.title} • ${society.name} • ${activeRound.participatingFlatsCount} Flats Combined`}
        badge={
          <Badge variant={activeRound.status === 'open' ? 'success' : 'neutral'} pulseDot={activeRound.status === 'open'}>
            Round #{activeRound.roundNumber} ({activeRound.status.toUpperCase()})
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
            Print Checklist
          </Button>
        }
      />

      {/* Progress & Summary Bar */}
      <Card className="p-4 bg-white border-slate-200">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[#18231E]">Purchasing Checklist</span>
              <span className="text-xs text-[#718078]">
                ({purchasedCount} of {groceryItems.length} items procured)
              </span>
            </div>
            <div className="mt-2 h-2.5 w-64 max-w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#23865B] rounded-full transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-100 border border-slate-200 self-start sm:self-center">
            <button
              onClick={() => setViewMode('consolidated')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                viewMode === 'consolidated'
                  ? 'bg-white text-[#18231E] shadow-xs'
                  : 'text-[#718078] hover:text-[#18231E]'
              }`}
            >
              Master Items List
            </button>
            <button
              onClick={() => setViewMode('flat-wise')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                viewMode === 'flat-wise'
                  ? 'bg-white text-[#18231E] shadow-xs'
                  : 'text-[#718078] hover:text-[#18231E]'
              }`}
            >
              Flat Packing View ({flatPackingBreakdown.length} Flats)
            </button>
          </div>
        </div>
      </Card>

      {/* View 1: Consolidated Bulk Manifest */}
      {viewMode === 'consolidated' && (
        <div className="space-y-4">
          {/* Filter & Search Bar */}
          <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
            <SearchInput
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search grocery item name..."
              className="w-full sm:w-72"
            />

            {/* Category Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`shrink-0 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                    selectedCategory === cat
                      ? 'bg-[#23865B] text-white shadow-xs'
                      : 'bg-white border border-[#E6ECE8] text-[#718078] hover:border-slate-300 hover:text-[#18231E]'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Consolidated Items Table Card */}
          <Card className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F8FAF9] border-b border-[#E6ECE8] text-[#718078] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="py-3 px-4 w-12 text-center">Done</th>
                    <th className="py-3 px-4">Product Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-center">Flats</th>
                    <th className="py-3 px-4 text-right">Total Bulk Qty</th>
                    <th className="py-3 px-4 text-right">Est. Unit Price</th>
                    <th className="py-3 px-4 text-right">Est. Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E6ECE8]">
                  {filteredItems.map((item) => (
                    <tr
                      key={item.id}
                      className={`transition-colors ${
                        item.isPurchased ? 'bg-emerald-50/40 hover:bg-emerald-50/60' : 'hover:bg-slate-50/70'
                      }`}
                    >
                      {/* Procured Checkbox */}
                      <td className="py-3.5 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => toggleItemPurchased(item.id)}
                          className={`flex h-5 w-5 mx-auto items-center justify-center rounded-md border transition-all ${
                            item.isPurchased
                              ? 'bg-[#23865B] border-[#23865B] text-white'
                              : 'border-slate-300 bg-white hover:border-[#23865B]'
                          }`}
                          aria-label={`Mark ${item.name} as purchased`}
                        >
                          {item.isPurchased && <Check className="h-3.5 w-3.5" />}
                        </button>
                      </td>

                      {/* Item Name */}
                      <td className="py-3.5 px-4">
                        <div className="flex flex-col">
                          <span
                            className={`font-bold text-sm ${
                              item.isPurchased ? 'line-through text-slate-500' : 'text-[#18231E]'
                            }`}
                          >
                            {item.name}
                          </span>
                          <span className="text-[11px] text-[#718078]">
                            Requested by {item.flatRequests.map((f) => f.flatNumber).join(', ')}
                          </span>
                        </div>
                      </td>

                      {/* Category Badge */}
                      <td className="py-3.5 px-4">
                        <Badge variant="neutral" size="sm">
                          {item.category}
                        </Badge>
                      </td>

                      {/* Flats Count */}
                      <td className="py-3.5 px-4 text-center font-bold text-[#18231E]">
                        {item.flatsCount} Flats
                      </td>

                      {/* Total Bulk Quantity */}
                      <td className="py-3.5 px-4 text-right">
                        <span className="text-sm font-extrabold text-[#23865B]">
                          {item.totalQuantity} {item.unit}
                        </span>
                      </td>

                      {/* Estimated Unit Price */}
                      <td className="py-3.5 px-4 text-right text-[#718078]">
                        ₹{item.estimatedUnitPrice}/{item.unit}
                      </td>

                      {/* Estimated Subtotal */}
                      <td className="py-3.5 px-4 text-right font-bold text-[#18231E]">
                        ₹{(item.totalQuantity * item.estimatedUnitPrice).toLocaleString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* View 2: Flat-Wise Packing Breakdown */}
      {viewMode === 'flat-wise' && (
        <div className="space-y-4">
          <p className="text-xs text-[#718078]">
            Packing manifest: Separate the wholesale sacks and boxes into individual flat bundles after return from the market.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {flatPackingBreakdown.map(([flatNo, items]) => (
              <Card key={flatNo} className="p-4 border-slate-200">
                <div className="flex items-center justify-between pb-2.5 border-b border-[#E6ECE8]">
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#EAF5EE] text-[#196B48] font-bold text-xs">
                      {flatNo.split('-')[0]}
                    </span>
                    <h3 className="text-sm font-bold text-[#18231E]">Flat {flatNo}</h3>
                  </div>
                  <Badge variant="primary" size="sm">
                    {items.length} Items
                  </Badge>
                </div>

                <ul className="mt-3 divide-y divide-slate-100 text-xs">
                  {items.map((i, idx) => (
                    <li key={idx} className="py-1.5 flex items-center justify-between text-[#18231E]">
                      <span className="truncate pr-2">{i.itemName}</span>
                      <strong className="text-[#23865B] shrink-0">
                        {i.quantity} {i.unit}
                      </strong>
                    </li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
