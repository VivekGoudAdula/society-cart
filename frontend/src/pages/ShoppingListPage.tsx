import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Printer,
  Download,
  RefreshCw,
  ShoppingBag,
  PackageCheck,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Users,
  CheckCircle2,
  FileSpreadsheet,
  Clock,
  Sparkles,
  ArrowLeft,
  HelpCircle,
  AlertCircle,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { SearchInput } from '../components/common/SearchInput';
import { StatCard } from '../components/common/StatCard';
import { api } from '../services/api';
import {
  ApiCompiledShoppingList,
  ApiOrderRound,
} from '../types';
import { PurchaseRecordingSection } from '../components/billing/PurchaseRecordingSection';
import { CostAllocationSection } from '../components/billing/CostAllocationSection';
import { SpendingAndSavingsSection } from '../components/billing/SpendingAndSavingsSection';

type DashboardTab = 'master' | 'packing' | 'purchases' | 'allocation' | 'spending' | 'unresolved';

export const ShoppingListPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { activeSocietyPair, currentActiveRound } = useApp();

  const societyId = activeSocietyPair?.society.id;
  const isVolunteerOrAdmin =
    activeSocietyPair?.membership.role === 'volunteer' ||
    activeSocietyPair?.membership.role === 'admin';

  // Target Round ID from URL or active round
  const targetRoundId = searchParams.get('roundId') || currentActiveRound?.id;

  const [shoppingList, setShoppingList] = useState<ApiCompiledShoppingList | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isCompiling, setIsCompiling] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState<DashboardTab>('master');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Accordion state for master items (item_key -> boolean)
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  // Checklist states (local session state)
  const [purchasedItemKeys, setPurchasedItemKeys] = useState<Record<string, boolean>>({});
  const [packedFlatItemKeys, setPackedFlatItemKeys] = useState<Record<string, boolean>>({});

  // Available rounds for selection
  const [availableRounds, setAvailableRounds] = useState<ApiOrderRound[]>([]);

  useEffect(() => {
    if (societyId) {
      api.rounds.list(societyId).then((res) => {
        setAvailableRounds(res.items);
      }).catch(() => {});
    }
  }, [societyId]);

  // Load existing shopping list
  const loadShoppingList = async (roundId: string) => {
    if (!societyId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.shoppingList.get(societyId, roundId);
      setShoppingList(data);
    } catch (err: any) {
      if (err.status === 404) {
        setShoppingList(null);
      } else {
        setError(err.message || 'Failed to load shopping list.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (societyId && targetRoundId) {
      loadShoppingList(targetRoundId);
    } else {
      setIsLoading(false);
    }
  }, [societyId, targetRoundId]);

  // Compile / Recompile Handler
  const handleCompile = async () => {
    if (!societyId || !targetRoundId) return;
    setIsCompiling(true);
    setError(null);
    try {
      const compiled = await api.shoppingList.compile(societyId, targetRoundId);
      setShoppingList(compiled);
    } catch (err: any) {
      setError(err.message || 'Failed to compile shopping list.');
    } finally {
      setIsCompiling(false);
    }
  };

  // CSV Export Handler
  const handleExportCsv = async (type: 'consolidated' | 'packing') => {
    if (!societyId || !targetRoundId) return;
    setIsExporting(true);
    try {
      await api.shoppingList.downloadCsv(societyId, targetRoundId, type);
    } catch (err: any) {
      setError(err.message || 'Failed to export CSV.');
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const toggleItemExpanded = (itemKey: string) => {
    setExpandedItems((prev) => ({ ...prev, [itemKey]: !prev[itemKey] }));
  };

  const togglePurchased = (itemKey: string) => {
    setPurchasedItemKeys((prev) => ({ ...prev, [itemKey]: !prev[itemKey] }));
  };

  const togglePacked = (flatItemKey: string) => {
    setPackedFlatItemKeys((prev) => ({ ...prev, [flatItemKey]: !prev[flatItemKey] }));
  };

  // Categories present in compiled list
  const categoryFilters = useMemo(() => {
    if (!shoppingList) return [];
    return [
      { id: 'all', label: 'All Categories' },
      ...shoppingList.categories
        .filter((c) => c.item_count > 0)
        .map((c) => ({ id: c.category, label: c.category_name })),
    ];
  }, [shoppingList]);

  // Filtered master items
  const filteredCategoryGroups = useMemo(() => {
    if (!shoppingList) return [];
    return shoppingList.categories
      .map((cg) => {
        if (selectedCategory !== 'all' && cg.category !== selectedCategory) {
          return { ...cg, items: [] };
        }
        const filteredItems = cg.items.filter((item) => {
          const q = searchQuery.toLowerCase().trim();
          if (!q) return true;
          return (
            item.normalized_name.toLowerCase().includes(q) ||
            (item.brand && item.brand.toLowerCase().includes(q)) ||
            (item.variant && item.variant.toLowerCase().includes(q)) ||
            item.original_names.some((orig) => orig.toLowerCase().includes(q)) ||
            item.contributing_flats.some((cf) => cf.flat_number.toLowerCase().includes(q))
          );
        });
        return { ...cg, items: filteredItems };
      })
      .filter((cg) => cg.items.length > 0);
  }, [shoppingList, selectedCategory, searchQuery]);

  // Filtered flat packing breakdown
  const filteredPackingBreakdown = useMemo(() => {
    if (!shoppingList) return [];
    const q = searchQuery.toLowerCase().trim();
    if (!q) return shoppingList.packing_breakdown;
    return shoppingList.packing_breakdown.filter((fb) => {
      return (
        fb.flat_number.toLowerCase().includes(q) ||
        fb.user_name.toLowerCase().includes(q) ||
        fb.items.some((it) => it.normalized_name.toLowerCase().includes(q))
      );
    });
  }, [shoppingList, searchQuery]);

  // Calculate procurement progress
  const totalDistinctItems = shoppingList?.summary.total_distinct_items || 0;
  const procuredCount = useMemo(() => {
    if (!shoppingList) return 0;
    let count = 0;
    shoppingList.categories.forEach((cg) => {
      cg.items.forEach((it) => {
        if (purchasedItemKeys[it.item_key]) count++;
      });
    });
    return count;
  }, [shoppingList, purchasedItemKeys]);

  const procurementPercent = totalDistinctItems > 0 ? Math.round((procuredCount / totalDistinctItems) * 100) : 0;

  if (!isVolunteerOrAdmin) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-slate-200">
        <AlertTriangle className="h-10 w-10 text-amber-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-800">Volunteer Access Required</h2>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          The consolidated grocery shopping list and packing manifests are reserved for authorized society volunteers and administrators.
        </p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/resident')}>
          Go to Resident Dashboard
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Printable Header - Visible ONLY during print */}
      <div className="hidden print:block mb-6 p-4 border-b border-black">
        <h1 className="text-2xl font-bold text-black uppercase tracking-tight">
          {activeSocietyPair?.society.name} — Community Shopping Manifest
        </h1>
        <div className="flex justify-between items-center text-xs text-black mt-2">
          <span>Round #{shoppingList?.round_number || 1}: {shoppingList?.round_title}</span>
          <span>Shopping Date: {shoppingList?.shopping_date || 'Not specified'}</span>
          <span>Compiled: {shoppingList ? new Date(shoppingList.compiled_at).toLocaleString() : ''}</span>
          <span>Flats: {shoppingList?.summary.total_confirmed_flats}</span>
        </div>
      </div>

      {/* Main Page Header */}
      <div className="print:hidden">
        <PageHeader
          title="Volunteer Shopping Dashboard"
          description={`${activeSocietyPair?.society.name || 'Society'} • Consolidated bulk orders & packing manifests`}
          badge={
            shoppingList ? (
              <Badge variant="success" size="md">
                Round #{shoppingList.round_number} (v{shoppingList.version})
              </Badge>
            ) : (
              <Badge variant="neutral" size="md">
                Round Selected
              </Badge>
            )
          }
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => navigate('/volunteer')}
                leftIcon={<ArrowLeft className="h-4 w-4" />}
              >
                Volunteer Ops
              </Button>

              {shoppingList && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handlePrint}
                    leftIcon={<Printer className="h-4 w-4" />}
                  >
                    Print Checklist
                  </Button>

                  <div className="relative inline-flex group">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={isExporting}
                      leftIcon={<FileSpreadsheet className="h-4 w-4 text-emerald-600" />}
                      onClick={() => handleExportCsv('consolidated')}
                    >
                      Export CSV
                    </Button>
                  </div>
                </>
              )}

              <Button
                size="sm"
                variant="primary"
                onClick={handleCompile}
                disabled={isCompiling || !targetRoundId}
                leftIcon={<RefreshCw className={`h-4 w-4 ${isCompiling ? 'animate-spin' : ''}`} />}
              >
                {shoppingList ? 'Recompile List' : 'Compile Shopping List'}
              </Button>
            </div>
          }
        />
      </div>

      {/* Round Selection & Error Banner */}
      {availableRounds.length > 1 && (
        <Card className="p-3 bg-slate-50 border-slate-200 print:hidden">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
              <Clock className="h-4 w-4 text-[#23865B]" />
              <span>Select Round:</span>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto py-1">
              {availableRounds.map((r) => (
                <button
                  key={r.id}
                  onClick={() => navigate(`/shopping-list?roundId=${r.id}`)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    r.id === targetRoundId
                      ? 'bg-[#23865B] text-white shadow-sm font-semibold'
                      : 'bg-white text-slate-700 border border-slate-200 hover:border-slate-300'
                  }`}
                >
                  Round #{r.round_number} ({r.status.toUpperCase()})
                </button>
              ))}
            </div>
          </div>
        </Card>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs font-semibold text-red-800 flex items-center gap-3 print:hidden">
          <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Empty State: Not yet compiled */}
      {!isLoading && !shoppingList && (
        <Card className="p-12 text-center border-dashed border-2 border-slate-200 bg-white">
          <ShoppingBag className="h-12 w-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">Shopping List Not Compiled Yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
            Compile the verified resident grocery orders for this round into a consolidated bulk shopping manifest.
          </p>
          <div className="mt-6 flex justify-center">
            <Button
              variant="primary"
              size="md"
              onClick={handleCompile}
              disabled={isCompiling || !targetRoundId}
              leftIcon={<Sparkles className="h-4 w-4" />}
            >
              {isCompiling ? 'Compiling Master List...' : 'Compile Shopping List'}
            </Button>
          </div>
        </Card>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="py-12 text-center text-slate-400">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-[#23865B] mb-2" />
          <span className="text-xs font-medium">Loading society grocery manifest...</span>
        </div>
      )}

      {/* Compiled Dashboard Content */}
      {shoppingList && (
        <>
          {/* Compilation Summary Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 print:hidden">
            <StatCard
              label="Confirmed Flats"
              value={`${shoppingList.summary.total_confirmed_flats} Flats`}
              subtext={`${shoppingList.summary.total_confirmed_orders} confirmed orders`}
              icon={<Users className="h-5 w-5 text-[#23865B]" />}
            />
            <StatCard
              label="Distinct Bulk Products"
              value={`${shoppingList.summary.total_distinct_items} Items`}
              subtext={`${shoppingList.summary.total_items_count} individual request lines`}
              icon={<ShoppingBag className="h-5 w-5 text-emerald-600" />}
            />
            <StatCard
              label="Procurement Progress"
              value={`${procuredCount} of ${totalDistinctItems}`}
              subtext={`${procurementPercent}% items procured`}
              icon={<CheckCircle2 className="h-5 w-5 text-teal-600" />}
            />
            <StatCard
              label="Pending Confirmation"
              value={shoppingList.summary.total_unresolved_orders.toString()}
              subtext={`${shoppingList.summary.total_unresolved_flats} flats awaiting review`}
              icon={<AlertTriangle className={`h-5 w-5 ${shoppingList.summary.has_unresolved_orders ? 'text-amber-500' : 'text-slate-400'}`} />}
            />
          </div>

          {/* Unresolved Orders Warning Banner */}
          {shoppingList.summary.has_unresolved_orders && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 print:hidden">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-800">
                    Pending Resident Confirmations ({shoppingList.summary.total_unresolved_orders} Orders Excluded)
                  </h4>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Some residents still have orders awaiting confirmation or clarification across{' '}
                    <strong>{shoppingList.summary.total_unresolved_flats} flats</strong>. They have been excluded from this shopping list.
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setActiveTab('unresolved')}
                className="shrink-0 bg-white border-amber-300 text-amber-900 hover:bg-amber-100"
              >
                Inspect {shoppingList.summary.total_unresolved_orders} Unresolved Orders
              </Button>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-2 print:hidden">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('master')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeTab === 'master'
                    ? 'bg-[#23865B] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <ShoppingBag className="h-4 w-4" />
                <span>Master Shopping List</span>
                <Badge variant={activeTab === 'master' ? 'neutral' : 'neutral'} size="sm">
                  {shoppingList.summary.total_distinct_items}
                </Badge>
              </button>

              <button
                onClick={() => setActiveTab('packing')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeTab === 'packing'
                    ? 'bg-[#23865B] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <PackageCheck className="h-4 w-4" />
                <span>Flat-wise Packing Breakdown</span>
                <Badge variant="neutral" size="sm">
                  {shoppingList.packing_breakdown.length} Flats
                </Badge>
              </button>

              <button
                onClick={() => setActiveTab('purchases')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeTab === 'purchases'
                    ? 'bg-[#196B48] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <span>Record Purchases</span>
              </button>

              <button
                onClick={() => setActiveTab('allocation')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeTab === 'allocation'
                    ? 'bg-[#196B48] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <span>Cost Allocation & Bills</span>
              </button>

              <button
                onClick={() => setActiveTab('spending')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeTab === 'spending'
                    ? 'bg-[#196B48] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <span>Spending & Savings</span>
              </button>

              <button
                onClick={() => setActiveTab('unresolved')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeTab === 'unresolved'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <HelpCircle className="h-4 w-4" />
                <span>Pending Confirmations</span>
                {shoppingList.summary.total_unresolved_orders > 0 && (
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    activeTab === 'unresolved' ? 'bg-amber-800 text-white' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {shoppingList.summary.total_unresolved_orders}
                  </span>
                )}
              </button>
            </div>

            {/* Quick search input */}
            <div className="w-full sm:w-64">
              <SearchInput
                value={searchQuery}
                onChange={setSearchQuery}
                placeholder={
                  activeTab === 'master'
                    ? 'Filter items, brands, flats...'
                    : activeTab === 'packing'
                    ? 'Search flat or resident...'
                    : 'Filter pending orders...'
                }
              />
            </div>
          </div>

          {/* TAB 1: MASTER SHOPPING LIST (Category Grouped) */}
          {(activeTab === 'master' || window.matchMedia?.('print').matches) && (
            <div className="space-y-6">
              {/* Category Pills (Hidden on print) */}
              <div className="flex items-center gap-2 overflow-x-auto pb-1 print:hidden">
                {categoryFilters.map((cf) => (
                  <button
                    key={cf.id}
                    onClick={() => setSelectedCategory(cf.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                      selectedCategory === cf.id
                        ? 'bg-[#18231E] text-white shadow-sm'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {cf.label}
                  </button>
                ))}
              </div>

              {filteredCategoryGroups.length === 0 ? (
                <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
                  <p className="text-xs text-slate-500">No confirmed items match your filter criteria.</p>
                </div>
              ) : (
                filteredCategoryGroups.map((cg) => (
                  <Card key={cg.category} className="p-5 border-slate-200 print:border-black print:shadow-none mb-6">
                    <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100 print:border-black">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full bg-[#23865B] print:hidden" />
                        <h3 className="text-sm font-bold text-[#18231E] uppercase tracking-wider">
                          {cg.category_name}
                        </h3>
                        <Badge variant="neutral" size="sm">
                          {cg.items.length} {cg.items.length === 1 ? 'Product' : 'Products'}
                        </Badge>
                      </div>
                    </div>

                    <div className="divide-y divide-slate-100 print:divide-black">
                      {cg.items.map((item) => {
                        const isPurchased = purchasedItemKeys[item.item_key];
                        const isExpanded = expandedItems[item.item_key];

                        return (
                          <div
                            key={item.item_key}
                            className={`py-3.5 transition-colors ${
                              isPurchased ? 'bg-emerald-50/50 print:bg-white' : ''
                            }`}
                          >
                            <div className="flex items-center justify-between gap-4">
                              {/* Left: Checkbox + Name + Brand/Variant Badge */}
                              <div className="flex items-center gap-3 min-w-0">
                                <input
                                  type="checkbox"
                                  checked={isPurchased || false}
                                  onChange={() => togglePurchased(item.item_key)}
                                  className="h-4 w-4 rounded border-slate-300 text-[#23865B] focus:ring-[#23865B] cursor-pointer"
                                />

                                <div className="min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span
                                      className={`text-sm font-bold text-slate-900 ${
                                        isPurchased ? 'line-through text-slate-400' : ''
                                      }`}
                                    >
                                      {item.normalized_name}
                                    </span>

                                    {item.brand && (
                                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                                        Brand: {item.brand}
                                      </span>
                                    )}

                                    {item.variant && (
                                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
                                        {item.variant}
                                      </span>
                                    )}
                                  </div>

                                  {item.original_names.length > 0 && (
                                    <span className="text-[11px] text-slate-400 italic block mt-0.5">
                                      Requested as: {item.original_names.join(', ')}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Right: Quantity + Unit + Contributing Flats Toggle */}
                              <div className="flex items-center gap-4 shrink-0">
                                <div className="text-right">
                                  <span className="text-base font-black text-[#23865B] tracking-tight">
                                    {item.total_quantity} {item.unit}
                                  </span>
                                  <span className="text-[11px] text-slate-500 block">
                                    across {item.contributing_flats_count} {item.contributing_flats_count === 1 ? 'flat' : 'flats'}
                                  </span>
                                </div>

                                <button
                                  type="button"
                                  onClick={() => toggleItemExpanded(item.item_key)}
                                  className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-700 print:hidden"
                                  title="View contributing flats"
                                >
                                  {isExpanded ? (
                                    <ChevronDown className="h-4 w-4" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4" />
                                  )}
                                </button>
                              </div>
                            </div>

                            {/* Accordion: Contributing flats list */}
                            {isExpanded && (
                              <div className="mt-3 ml-7 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5 print:hidden">
                                <span className="font-semibold text-slate-700 block text-[11px] uppercase tracking-wider">
                                  Breakdown by Flat:
                                </span>
                                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
                                  {item.contributing_flats.map((cf, idx) => (
                                    <div
                                      key={`${cf.order_id}_${idx}`}
                                      className="p-2 bg-white rounded-lg border border-slate-200 flex justify-between items-center"
                                    >
                                      <div>
                                        <span className="font-bold text-slate-800">{cf.flat_number}</span>
                                        <span className="text-[10px] text-slate-500 block">{cf.user_name}</span>
                                      </div>
                                      <span className="font-black text-[#23865B]">
                                        {cf.quantity} {cf.unit || item.unit}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* TAB 2: PACKING BREAKDOWN (Flat-wise Distribution) */}
          {activeTab === 'packing' && (
            <div className="space-y-4 print:block">
              <div className="flex items-center justify-between pb-2 print:hidden">
                <span className="text-xs text-slate-500 font-medium">
                  {filteredPackingBreakdown.length} Flats with confirmed deliveries
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExportCsv('packing')}
                  leftIcon={<Download className="h-3.5 w-3.5" />}
                >
                  Export Flat Packing CSV
                </Button>
              </div>

              {filteredPackingBreakdown.length === 0 ? (
                <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
                  <p className="text-xs text-slate-500">No flat packing records match your search.</p>
                </div>
              ) : (
                filteredPackingBreakdown.map((fb) => (
                  <Card key={fb.flat_number} className="p-5 border-slate-200 print:border-black print:mb-4">
                    <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100 print:border-black">
                      <div className="flex items-center gap-2">
                        <PackageCheck className="h-4 w-4 text-[#23865B]" />
                        <h4 className="text-sm font-bold text-[#18231E]">
                          Flat {fb.flat_number}
                        </h4>
                        <span className="text-xs text-slate-500">({fb.user_name})</span>
                      </div>
                      <Badge variant="neutral" size="sm">
                        {fb.items.length} {fb.items.length === 1 ? 'Item' : 'Items'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                      {fb.items.map((it, idx) => {
                        const packedKey = `${fb.flat_number}_${it.item_id}_${idx}`;
                        const isPacked = packedFlatItemKeys[packedKey];

                        return (
                          <div
                            key={packedKey}
                            className={`p-2.5 rounded-lg border text-xs flex items-center justify-between gap-2 transition-all ${
                              isPacked
                                ? 'bg-emerald-50/60 border-emerald-200 text-slate-400'
                                : 'bg-slate-50/60 border-slate-200 text-slate-800'
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <input
                                type="checkbox"
                                checked={isPacked || false}
                                onChange={() => togglePacked(packedKey)}
                                className="h-3.5 w-3.5 rounded border-slate-300 text-[#23865B] cursor-pointer"
                              />
                              <div className="min-w-0">
                                <span className={`font-semibold block truncate ${isPacked ? 'line-through' : ''}`}>
                                  {it.normalized_name}
                                </span>
                                {(it.brand || it.variant) && (
                                  <span className="text-[10px] text-slate-400 block truncate">
                                    {[it.brand, it.variant].filter(Boolean).join(' • ')}
                                  </span>
                                )}
                              </div>
                            </div>
                            <span className="font-bold text-[#23865B] shrink-0">
                              {it.quantity} {it.unit}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* TAB 3: PENDING RESIDENT CONFIRMATIONS */}
          {activeTab === 'unresolved' && (
            <div className="space-y-4 print:hidden">
              <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-xs text-amber-800 flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-amber-600 shrink-0" />
                <span>
                  These orders cannot enter the master shopping list until residents confirm or clarify them in their dashboard.
                </span>
              </div>

              {shoppingList.unresolved_orders.length === 0 ? (
                <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
                  <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                  <h4 className="text-sm font-bold text-slate-800">All Submitted Orders Are Confirmed!</h4>
                  <p className="text-xs text-slate-500 mt-1">
                    There are no pending, ambiguous, or failed grocery submissions for this round.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {shoppingList.unresolved_orders.map((uo) => (
                    <Card key={uo.order_id} className="p-4 border-slate-200">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-slate-900">Flat {uo.flat_number}</span>
                            <span className="text-xs text-slate-500">• {uo.user_name}</span>
                            <Badge
                              variant={
                                uo.status === 'needs_clarification'
                                  ? 'warning'
                                  : uo.status === 'failed'
                                  ? 'danger'
                                  : 'neutral'
                              }
                              size="sm"
                            >
                              {uo.status.replace('_', ' ').toUpperCase()}
                            </Badge>
                          </div>

                          <p className="text-xs text-slate-600 bg-slate-50 p-2 rounded-lg font-mono">
                            "{uo.raw_text}"
                          </p>

                          {uo.clarification_prompt && (
                            <p className="text-xs text-amber-700 font-semibold pt-1">
                              Clarification Requested: {uo.clarification_prompt}
                            </p>
                          )}

                          {uo.error_message && (
                            <p className="text-xs text-red-600 pt-1">
                              Error: {uo.error_message}
                            </p>
                          )}
                        </div>

                        <div className="text-right shrink-0">
                          <span className="text-[10px] text-slate-400 block">
                            Last Updated: {new Date(uo.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Phase 7: Purchases Tab */}
          {activeTab === 'purchases' && targetRoundId && societyId && (
            <PurchaseRecordingSection
              societyId={societyId}
              roundId={targetRoundId}
              onPurchasesChanged={() => {}}
            />
          )}

          {/* Phase 7: Cost Allocation & Bills Tab */}
          {activeTab === 'allocation' && targetRoundId && societyId && (
            <CostAllocationSection
              societyId={societyId}
              roundId={targetRoundId}
            />
          )}

          {/* Phase 7: Spending & Verified Savings Tab */}
          {activeTab === 'spending' && targetRoundId && societyId && (
            <SpendingAndSavingsSection
              societyId={societyId}
              roundId={targetRoundId}
            />
          )}
        </>
      )}
    </div>
  );
};
