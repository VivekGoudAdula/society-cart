import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  Clock,
  Calendar,
  User,
  ShoppingBag,
  TrendingDown,
  Receipt,
  ArrowRight,
  CheckCircle2,
  BellRing,
  Sparkles,
  Layers,
  Eye,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { StatCard } from '../components/common/StatCard';
import { OrderReviewModal } from '../components/orders/OrderReviewModal';
import { ApiGroceryOrder, ApiGroceryBill } from '../types';
import { api } from '../services/api';

/**
 * Screen 3: Resident Dashboard — Primary home for apartment residents to track orders, deadlines, and savings.
 */
export const ResidentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser, society, activeRound, notifications, residentBill } = useApp();

  const [orders, setOrders] = useState<ApiGroceryOrder[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<ApiGroceryOrder | null>(null);
  const [myBills, setMyBills] = useState<ApiGroceryBill[]>([]);

  useEffect(() => {
    if (!society?.id || !activeRound?.id) return;
    api.orders
      .listByRound(society.id, activeRound.id)
      .then((res) => setOrders(res))
      .catch(() => {});

    api.billing
      .getMyBills()
      .then((res) => setMyBills(res))
      .catch(() => {});
  }, [society?.id, activeRound?.id]);

  return (
    <div className="space-y-6">
      {/* Top Page Header */}
      <PageHeader
        title={`Welcome back, ${currentUser.name.split(' ')[0]}`}
        description={`${society.name} • Flat ${currentUser.flatNumber}`}
        badge={
          <Badge variant="primary" size="md">
            Resident Mode
          </Badge>
        }
        actions={
          <Button
            size="sm"
            variant="primary"
            onClick={() => navigate('/chat')}
            leftIcon={<MessageSquare className="h-4 w-4" />}
          >
            Open Society Chat
          </Button>
        }
      />

      {/* Hero Active Order Round Card */}
      <Card
        className={`p-6 shadow-sm ${
          activeRound.status === 'open'
            ? 'border-emerald-200/80 bg-gradient-to-br from-white via-white to-emerald-50/30'
            : 'border-slate-200 bg-white'
        }`}
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge
                variant={activeRound.status === 'open' ? 'success' : 'neutral'}
                pulseDot={activeRound.status === 'open'}
              >
                {activeRound.status === 'open'
                  ? `Round #${activeRound.roundNumber} OPEN`
                  : 'ORDERING CLOSED'}
              </Badge>
              <span className="text-xs text-[#718078] font-medium">• Collective Order Drive</span>
            </div>

            <div>
              <h2 className="text-lg sm:text-xl font-bold text-[#18231E]">
                {activeRound.status === 'open' ? activeRound.title : 'No Active Grocery Round'}
              </h2>
              <p className="mt-1 text-xs sm:text-sm text-[#718078]">
                {activeRound.status === 'open'
                  ? 'Post your grocery requirements in the group chat before the deadline. Our volunteer will purchase in bulk.'
                  : 'Grocery ordering is currently closed for this society. Society volunteers will announce the next procurement round.'}
              </p>
            </div>

            {/* Timing & Volunteer Meta Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="flex items-center gap-2 text-xs text-[#18231E]">
                <Clock className="h-4 w-4 text-amber-600 shrink-0" />
                <span>
                  Status:{' '}
                  <strong className={activeRound.status === 'open' ? 'text-amber-800' : 'text-slate-600'}>
                    {activeRound.deadlineText}
                  </strong>
                </span>
              </div>

              <div className="flex items-center gap-2 text-xs text-[#18231E]">
                <Calendar className="h-4 w-4 text-[#23865B] shrink-0" />
                <span>
                  Delivery: <strong>{activeRound.shopVisitDate}</strong>
                </span>
              </div>

              <div className="flex items-center gap-2 text-xs text-[#18231E]">
                <User className="h-4 w-4 text-slate-500 shrink-0" />
                <span>
                  Volunteer: <strong>{activeRound.volunteerName}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row lg:flex-col gap-2.5 shrink-0">
            {activeRound.status === 'open' ? (
              <Button
                variant="primary"
                size="md"
                onClick={() => navigate('/chat')}
                leftIcon={<MessageSquare className="h-4 w-4" />}
              >
                Add Grocery Items in Chat
              </Button>
            ) : (
              <Button
                variant="outline"
                size="md"
                onClick={() => navigate('/chat')}
                leftIcon={<MessageSquare className="h-4 w-4" />}
              >
                Open Society Chat
              </Button>
            )}
            <Button
              variant="outline"
              size="md"
              onClick={() => navigate('/order-summary')}
              leftIcon={<Receipt className="h-4 w-4" />}
            >
              View My Order & Bills
            </Button>
          </div>
        </div>
      </Card>

      {/* Phase 5: Active AI Parsed Orders Card (if any pending confirmation or clarification) */}
      {orders.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#18231E] flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-600" />
              <span>AI-Interpreted Orders ({orders.length})</span>
            </h3>
            <span className="text-xs text-[#718078]">Click to review, clarify, or confirm</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {orders.map((ord) => (
              <Card
                key={ord.id}
                hoverable
                onClick={() => setSelectedOrder(ord)}
                className={`p-4 transition-all ${
                  ord.status === 'needs_clarification'
                    ? 'border-amber-300 bg-amber-50/30'
                    : ord.status === 'pending_review' || ord.status === 'awaiting_confirmation'
                    ? 'border-emerald-300 bg-emerald-50/20'
                    : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-gray-900 truncate">
                        Round #{ord.round_number}
                      </span>
                      <Badge
                        size="sm"
                        variant={
                          ord.status === 'confirmed'
                            ? 'success'
                            : ord.status === 'needs_clarification'
                            ? 'warning'
                            : 'primary'
                        }
                      >
                        {ord.status.replace(/_/g, ' ')}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-600 italic mt-1 truncate max-w-sm">
                      "{ord.raw_text}"
                    </p>
                    <p className="text-[11px] text-gray-400 mt-1">
                      {ord.items.length} items extracted • {ord.detected_language.toUpperCase()}
                    </p>
                  </div>

                  <Button size="sm" variant="outline" leftIcon={<Eye className="w-3.5 h-3.5" />}>
                    Review
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Phase 7: My Grocery Bills */}
      {myBills.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#18231E]">My Grocery Bills & Invoices</h3>
            <span className="text-xs text-[#718078]">{myBills.length} Invoices</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {myBills.map((b) => (
              <Card
                key={b.id}
                hoverable
                onClick={() => navigate('/order-summary')}
                className="p-4 border-emerald-100 bg-white space-y-3 cursor-pointer group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#18231E]">Round #{b.round_number}</span>
                  <Badge variant={b.status === 'published' ? 'success' : 'primary'} size="sm">
                    {b.status.toUpperCase()}
                  </Badge>
                </div>

                <div className="flex items-baseline justify-between pt-1 border-t border-slate-100">
                  <span className="text-xs text-[#718078]">{b.items.length} items</span>
                  <span className="text-base font-black text-[#196B48]">
                    ₹{b.total_amount.toFixed(2)}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400 group-hover:text-[#23865B] transition-colors">
                  <span>View Itemized Receipt</span>
                  <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Quick Statistics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="My Current Order"
          value="₹925"
          subtext="5 items extracted"
          icon={<ShoppingBag className="h-5 w-5" />}
        />

        <StatCard
          label="Cumulative Savings"
          value={`₹${residentBill.totalSavings + 280}`}
          subtext="Compared to retail apps"
          icon={<TrendingDown className="h-5 w-5 text-emerald-600" />}
          trend={{ value: '21% below retail', isPositive: true }}
        />

        <StatCard
          label="Completed Rounds"
          value="3 Orders"
          subtext="All delivered to C-402"
          icon={<CheckCircle2 className="h-5 w-5" />}
        />

        <StatCard
          label="Society Participation"
          value={`${activeRound.participatingFlatsCount} Flats`}
          subtext="Ordering together today"
          icon={<Layers className="h-5 w-5" />}
        />
      </div>

      {/* Grid: Recent Activity & Quick Action Shortcuts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity Feed (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#18231E]">Society Activity Stream</h3>
            <span className="text-xs text-[#718078]">Live round updates</span>
          </div>

          <Card className="divide-y divide-[#E6ECE8] p-0">
            {notifications.map((item) => (
              <div key={item.id} className="flex items-start gap-3 p-4 text-left hover:bg-slate-50/50 transition-colors">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[#EAF5EE] text-[#196B48] mt-0.5">
                  <BellRing className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-[#18231E]">{item.title}</h4>
                    <span className="text-[10px] text-slate-400">{item.timestamp}</span>
                  </div>
                  <p className="mt-0.5 text-xs text-[#718078] leading-relaxed">{item.description}</p>
                </div>
              </div>
            ))}
          </Card>
        </div>

        {/* Quick Actions & Tips (1 Col) */}
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-[#18231E]">Quick Actions</h3>

          <div className="space-y-3">
            <Card
              hoverable
              onClick={() => navigate('/chat')}
              className="p-4 flex items-center justify-between group"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#EAF5EE] text-[#196B48]">
                  <MessageSquare className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[#18231E] group-hover:text-[#23865B] transition-colors">
                    Society Group Chat
                  </h4>
                  <p className="text-[11px] text-[#718078]">Type what you need in plain text</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-400 group-hover:translate-x-1 transition-transform" />
            </Card>

            <Card
              hoverable
              onClick={() => navigate('/order-summary')}
              className="p-4 flex items-center justify-between group"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-50 text-amber-700">
                  <Receipt className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[#18231E] group-hover:text-[#23865B] transition-colors">
                    Check My Bill
                  </h4>
                  <p className="text-[11px] text-[#718078]">Itemized receipt & savings proof</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-400 group-hover:translate-x-1 transition-transform" />
            </Card>

            {/* Smart Tip Card */}
            <div className="rounded-2xl border border-emerald-100 bg-[#EAF5EE]/60 p-4">
              <div className="flex items-center gap-2 text-xs font-bold text-[#196B48] mb-1">
                <Sparkles className="h-4 w-4" />
                <span>Multilingual AI Tip</span>
              </div>
              <p className="text-[11px] text-emerald-900 leading-relaxed">
                You can write your grocery requests in English, Telugu, or Hindi (e.g., <em>"2 kg rice, 1 packet sugar"</em> or <em>"Naaku 2 packets atta kavali"</em>). The assistant extracts items automatically!
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Phase 5: Order Review Modal */}
      <OrderReviewModal
        order={selectedOrder}
        isOpen={!!selectedOrder}
        onClose={() => setSelectedOrder(null)}
        onOrderUpdated={(updated) => {
          setOrders((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
          setSelectedOrder(updated);
        }}
      />
    </div>
  );
};
