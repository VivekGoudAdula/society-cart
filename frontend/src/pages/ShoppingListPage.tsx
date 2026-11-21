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
  Receipt,
  CreditCard,
  TrendingDown,
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

/**
 * Screen 6: Volunteer Shopping Dashboard & Bulk Procurement Hub.
 * Redesigned in Pinterest-inspired warm ivory & deep forest green palette.
 */
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
      <div className="p-8 text-center bg-white rounded-3xl border border-[#EBE8DF] shadow-soft max-w-md mx-auto my-12">
        <div className="h-12 w-12 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center mx-auto mb-3">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-bold text-[#252824]">Volunteer Access Required</h2>
        <p className="text-xs text-[#827F76] mt-1.5 leading-relaxed">
          The consolidated grocery shopping list and packing manifests are reserved for authorized society volunteers and administrators.
        </p>
        <Button variant="outline" size="sm" className="mt-5" onClick={() => navigate('/resident')}>
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
          title="Consolidated Shopping List"
          description={`${activeSocietyPair?.society.name || 'Society'} • Aggregated grocery manifest & packing allocation`}
          badge={
            shoppingList ? (
              <Badge variant="primary" size="md">
                Round #{shoppingList.round_number} (v{shoppingList.version})
              </Badge>
            ) : (
              <Badge variant="neutral" size="md">
                Round Selected
              </Badge>
            )
          }
          actions={
            <div className="flex flex-wrap items-center gap-2.5">
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

                  <Button
                    size="sm"
                    variant="outline"
                    disabled={isExporting}
                    leftIcon={<FileSpreadsheet className="h-4 w-4 text-[#174D3A]" />}
                    onClick={() => handleExportCsv('consolidated')}
                  >
                    Export CSV
                  </Button>
                </>
              )}

              <Button
                size="sm"
                variant="primary"
                onClick={handleCompile}
                disabled={isCompiling || !targetRoundId}
                leftIcon={<RefreshCw className={`h-4 w-4 ${isCompiling ? 'animate-spin' : ''}`} />}
                className="shadow-sm shadow-[#174D3A]/20"
              >
                {shoppingList ? 'Recompile List' : 'Compile Shopping List'}
              </Button>
            </div>
          }
        />
      </div>

      {/* Round Selection Bar */}
      {availableRounds.length > 1 && (
        <Card className="p-3 bg-white border-[#EBE8DF] shadow-2xs print:hidden">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#252824]">
              <Clock className="h-4 w-4 text-[#174D3A]" />
              <span>Select Round:</span>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto py-1">
              {availableRounds.map((r) => (
                <button
                  key={r.id}
                  onClick={() => navigate(`/shopping-list?roundId=${r.id}`)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                    r.id === targetRoundId
                      ? 'bg-[#174D3A] text-white shadow-xs'
                      : 'bg-[#FAF9F6] text-[#827F76] border border-[#DFDAD0] hover:bg-[#F3F0E8] hover:text-[#252824]'
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
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-800 flex items-center gap-3 print:hidden">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Empty State: Not yet compiled */}
      {!isLoading && !shoppingList && (
        <Card className="p-12 text-center border-dashed border-2 border-[#DFDAD0] bg-white shadow-soft">
          <div className="h-14 w-14 rounded-2xl bg-[#EBF2EE] text-[#174D3A] flex items-center justify-center mx-auto mb-4 shadow-xs">
            <ShoppingBag className="h-7 w-7" />
          </div>
          <h3 className="text-lg font-bold text-[#252824]">Shopping List Not Compiled Yet</h3>
          <p className="text-xs sm:text-sm text-[#827F76] mt-1.5 max-w-md mx-auto leading-relaxed">
            Compile the confirmed resident grocery orders for this round into a single, consolidated bulk shopping manifest.
          </p>
          <div className="mt-6 flex justify-center">
            <Button
              variant="primary"
              size="md"
              onClick={handleCompile}
              disabled={isCompiling || !targetRoundId}
              leftIcon={<Sparkles className="h-4 w-4" />}
              className="shadow-md shadow-[#174D3A]/20"
            >
              {isCompiling ? 'Compiling Master List...' : 'Compile Shopping List'}
            </Button>
          </div>
        </Card>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="py-16 text-center text-[#827F76]">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-[#174D3A] mb-3" />
          <span className="text-xs font-medium">Loading consolidated grocery manifest...</span>
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
              icon={<Users className="h-5 w-5 text-[#174D3A]" />}
            />
            <StatCard
              label="Distinct Bulk Products"
              value={`${shoppingList.summary.total_distinct_items} Items`}
              subtext={`${shoppingList.summary.total_items_count} individual request lines`}
              icon={<ShoppingBag className="h-5 w-5 text-[#174D3A]" />}
            />
            <StatCard
              label="Procurement Progress"
              value={`${procuredCount} of ${totalDistinctItems}`}
              subtext={`${procurementPercent}% items procured`}
              icon={<CheckCircle2 className="h-5 w-5 text-[#174D3A]" />}
            />
            <StatCard
              label="Pending Confirmation"
              value={shoppingList.summary.total_unresolved_orders.toString()}
              subtext={`${shoppingList.summary.total_unresolved_flats} flats awaiting review`}
              icon={<AlertTriangle className={`h-5 w-5 ${shoppingList.summary.has_unresolved_orders ? 'text-[#C87D25]' : 'text-[#827F76]'}`} />}
            />
          </div>

          {/* Unresolved Orders Warning Banner */}
          {shoppingList.summary.has_unresolved_orders && (
            <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/70 border border-amber-200 text-amber-950 flex flex-col sm:flex-row sm:items-center justify-between gap-3 print:hidden shadow-xs">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900">
                    Pending Resident Confirmations ({shoppingList.summary.total_unresolved_orders} Orders Excluded)
                  </h4>
                  <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                    Some residents still have orders awaiting confirmation or clarification across{' '}
                    <strong>{shoppingList.summary.total_unresolved_flats} flats</strong>. They are safely excluded from this manifest.
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setActiveTab('unresolved')}
                className="shrink-0 bg-white border-amber-300 text-amber-950 hover:bg-amber-100"
              >
                Inspect {shoppingList.summary.total_unresolved_orders} Orders
              </Button>
            </div>
          )}

          {/* Navigation Tabs Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#EBE8DF] pb-3 print:hidden">
            <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
              <button
                onClick={() => setActiveTab('master')}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                  activeTab === 'master'
                    ? 'bg-[#174D3A] text-white shadow-xs'
                    : 'text-[#827F76] hover:text-[#252824] hover:bg-[#F3F0E8]'
                }`}
              >
                <ShoppingBag className="h-4 w-4" />
                <span>Master Manifest</span>
                <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                  activeTab === 'master' ? 'bg-white/20 text-white' : 'bg-[#EBF2EE] text-[#174D3A]'
                }`}>
                  {shoppingList.summary.total_distinct_items}
                </span>
              </button>

              <button
                onClick={() => setActiveTab('packing')}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                  activeTab === 'packing'
                    ? 'bg-[#174D3A] text-white shadow-xs'
                    : 'text-[#827F76] hover:text-[#252824] hover:bg-[#F3F0E8]'
                }`}
              >
                <PackageCheck className="h-4 w-4" />
                <span>Flat Packing</span>
                <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                  activeTab === 'packing' ? 'bg-white/20 text-white' : 'bg-[#EBF2EE] text-[#174D3A]'
                }`}>
                  {shoppingList.packing_breakdown.length} Flats
                </span>
              </button>

              <button
                onClick={() => setActiveTab('purchases')}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                  activeTab === 'purchases'
                    ? 'bg-[#174D3A] text-white shadow-xs'
                    : 'text-[#827F76] hover:text-[#252824] hover:bg-[#F3F0E8]'
                }`}
              >
                <Receipt className="h-4 w-4" />
                <span>Record Purchases</span>
              </button>

              <button
                onClick={() => setActiveTab('allocation')}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                  activeTab === 'allocation'
                    ? 'bg-[#174D3A] text-white shadow-xs'
                    : 'text-[#827F76] hover:text-[#252824] hover:bg-[#F3F0E8]'
                }`}
              >
                <CreditCard className="h-4 w-4" />
                <span>Cost Allocation</span>
              </button>

              <button
                onClick={() => setActiveTab('spending')}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                  activeTab === 'spending'
                    ? 'bg-[#174D3A] text-white shadow-xs'
                    : 'text-[#827F76] hover:text-[#252824] hover:bg-[#F3F0E8]'
                }`}
              >
                <TrendingDown className="h-4 w-4" />
                <span>Verified Savings</span>
              </button>

              <button
                onClick={() => setActiveTab('unresolved')}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                  activeTab === 'unresolved'
                    ? 'bg-[#C87D25] text-white shadow-xs'
                    : 'text-[#827F76] hover:text-[#252824] hover:bg-[#F3F0E8]'
                }`}
              >
                <HelpCircle className="h-4 w-4" />
                <span>Unresolved ({shoppingList.summary.total_unresolved_orders})</span>
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
                    : 'Filter records...'
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
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                      selectedCategory === cf.id
                        ? 'bg-[#174D3A] text-white shadow-xs'
                        : 'bg-[#F3F0E8] text-[#827F76] hover:bg-[#EBE8DF] hover:text-[#252824]'
                    }`}
                  >
                    {cf.label}
                  </button>
                ))}
              </div>

              {filteredCategoryGroups.length === 0 ? (
                <div className="p-8 text-center bg-white rounded-2xl border border-[#EBE8DF]">
                  <p className="text-xs text-[#827F76]">No confirmed items match your filter criteria.</p>
                </div>
              ) : (
                filteredCategoryGroups.map((cg) => (
                  <Card key={cg.category} className="p-5 sm:p-6 bg-white border-[#EBE8DF] shadow-soft print:border-black print:shadow-none mb-6">
                    <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#EBE8DF] print:border-black">
                      <div className="flex items-center gap-2.5">
                        <span className="h-2.5 w-2.5 rounded-full bg-[#174D3A] print:hidden" />
                        <h3 className="text-sm font-bold text-[#252824] uppercase tracking-wider">
                          {cg.category_name}
                        </h3>
                        <Badge variant="sage" size="sm">
                          {cg.items.length} {cg.items.length === 1 ? 'Product' : 'Products'}
                        </Badge>
                      </div>
                    </div>

                    <div className="divide-y divide-[#EBE8DF]/70 print:divide-black">
                      {cg.items.map((item) => {
                        const isPurchased = purchasedItemKeys[item.item_key];
                        const isExpanded = expandedItems[item.item_key];

                        return (
                          <div
                            key={item.item_key}
                            className={`py-3.5 transition-colors ${
                              isPurchased ? 'bg-[#EBF2EE]/40 print:bg-white' : ''
                            }`}
                          >
                            <div className="flex items-center justify-between gap-4">
                              {/* Left: Checkbox + Name + Brand/Variant Badge */}
                              <div className="flex items-center gap-3 min-w-0">
                                <input
                                  type="checkbox"
                                  checked={isPurchased || false}
                                  onChange={() => togglePurchased(item.item_key)}
                                  className="h-4 w-4 rounded border-[#DFDAD0] text-[#174D3A] focus:ring-[#174D3A] cursor-pointer"
                                />

                                <div className="min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span
                                      className={`text-sm font-bold text-[#252824] ${
                                        isPurchased ? 'line-through text-[#827F76]' : ''
                                      }`}
                                    >
                                      {item.normalized_name}
                                    </span>

                                    {item.brand && (
                                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#EBF2EE] text-[#174D3A] border border-[#174D3A]/20">
                                        Brand: {item.brand}
                                      </span>
                                    )}

                                    {item.variant && (
                                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#F3F0E8] text-[#252824] border border-[#DFDAD0]">
                                        {item.variant}
                                      </span>
                                    )}
                                  </div>

                                  {item.original_names.length > 0 && (
                                    <span className="text-[11px] text-[#827F76] italic block mt-0.5">
                                      Requested as: {item.original_names.join(', ')}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Right: Quantity + Unit + Contributing Flats Toggle */}
                              <div className="flex items-center gap-4 shrink-0">
                                <div className="text-right">
                                  <span className="text-base font-black text-[#174D3A] tracking-tight">
                                    {item.total_quantity} {item.unit}
                                  </span>
                                  <span className="text-[11px] text-[#827F76] block">
                                    across {item.contributing_flats_count} {item.contributing_flats_count === 1 ? 'flat' : 'flats'}
                                  </span>
                                </div>

                                <button
                                  type="button"
                                  onClick={() => toggleItemExpanded(item.item_key)}
                                  className="p-1 rounded-lg hover:bg-[#F3F0E8] text-[#827F76] hover:text-[#252824] print:hidden transition-colors"
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
                              <div className="mt-3 ml-7 p-3.5 bg-[#FAF9F6] rounded-2xl border border-[#DFDAD0] text-xs space-y-1.5 print:hidden">
                                <span className="font-bold text-[#252824] block text-[11px] uppercase tracking-wider">
                                  Breakdown by Flat:
                                </span>
                                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
                                  {item.contributing_flats.map((cf, idx) => (
                                    <div
                                      key={`${cf.order_id}_${idx}`}
                                      className="p-2.5 bg-white rounded-xl border border-[#EBE8DF] flex justify-between items-center shadow-2xs"
                                    >
                                      <div>
                                        <span className="font-bold text-[#252824]">{cf.flat_number}</span>
                                        <span className="text-[10px] text-[#827F76] block">{cf.user_name}</span>
                                      </div>
                                      <span className="font-black text-[#174D3A]">
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
                <span className="text-xs text-[#827F76] font-medium">
                  {filteredPackingBreakdown.length} Flats with confirmed orders
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
                <div className="p-8 text-center bg-white rounded-2xl border border-[#EBE8DF]">
                  <p className="text-xs text-[#827F76]">No flat packing records match your search.</p>
                </div>
              ) : (
                filteredPackingBreakdown.map((fb) => (
                  <Card key={fb.flat_number} className="p-5 sm:p-6 bg-white border-[#EBE8DF] shadow-soft print:border-black print:mb-4">
                    <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#EBE8DF] print:border-black">
                      <div className="flex items-center gap-2">
                        <PackageCheck className="h-4 w-4 text-[#174D3A]" />
                        <h4 className="text-sm font-bold text-[#252824]">
                          Flat {fb.flat_number}
                        </h4>
                        <span className="text-xs text-[#827F76]">({fb.user_name})</span>
                      </div>
                      <Badge variant="sage" size="sm">
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
                            className={`p-3 rounded-xl border text-xs flex items-center justify-between gap-2 transition-all ${
                              isPacked
                                ? 'bg-[#EBF2EE]/50 border-[#174D3A]/20 text-[#827F76]'
                                : 'bg-[#FAF9F6] border-[#DFDAD0] text-[#252824]'
                            }`}
                          >
                            <div className="flex items-center gap-2.5 min-w-0">
                              <input
                                type="checkbox"
                                checked={isPacked || false}
                                onChange={() => togglePacked(packedKey)}
                                className="h-4 w-4 rounded border-[#DFDAD0] text-[#174D3A] cursor-pointer"
                              />
                              <div className="min-w-0">
                                <span className={`font-bold block truncate ${isPacked ? 'line-through text-[#827F76]' : ''}`}>
                                  {it.normalized_name}
                                </span>
                                {(it.brand || it.variant) && (
                                  <span className="text-[10px] text-[#827F76] block truncate">
                                    {[it.brand, it.variant].filter(Boolean).join(' • ')}
                                  </span>
                                )}
                              </div>
                            </div>
                            <span className="font-black text-[#174D3A] shrink-0">
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
              <div className="p-3.5 bg-amber-50/70 rounded-2xl border border-amber-200 text-xs text-amber-900 flex items-center gap-2.5">
                <HelpCircle className="h-4 w-4 text-amber-700 shrink-0" />
                <span>
                  These orders cannot enter the master shopping list until residents confirm or clarify them in their dashboard.
                </span>
              </div>

              {shoppingList.unresolved_orders.length === 0 ? (
                <div className="p-8 text-center bg-white rounded-2xl border border-[#EBE8DF]">
                  <CheckCircle2 className="h-8 w-8 text-[#174D3A] mx-auto mb-2" />
                  <h4 className="text-sm font-bold text-[#252824]">All Submitted Orders Are Confirmed!</h4>
                  <p className="text-xs text-[#827F76] mt-1">
                    There are no pending, ambiguous, or failed grocery submissions for this round.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {shoppingList.unresolved_orders.map((uo) => (
                    <Card key={uo.order_id} className="p-4 sm:p-5 bg-white border-[#EBE8DF] shadow-soft">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-bold text-[#252824]">Flat {uo.flat_number}</span>
                            <span className="text-xs text-[#827F76]">• {uo.user_name}</span>
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

                          <p className="text-xs text-[#252824] bg-[#FAF9F6] p-2.5 rounded-xl border border-[#DFDAD0] font-mono">
                            "{uo.raw_text}"
                          </p>

                          {uo.clarification_prompt && (
                            <p className="text-xs text-amber-800 font-semibold pt-1">
                              Clarification Requested: {uo.clarification_prompt}
                            </p>
                          )}

                          {uo.error_message && (
                            <p className="text-xs text-rose-700 font-semibold pt-1">
                              Error: {uo.error_message}
                            </p>
                          )}
                        </div>

                        <div className="text-right shrink-0">
                          <span className="text-[10px] text-[#827F76] block">
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
