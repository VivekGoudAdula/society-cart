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
 * Redesigned with warm Pinterest-inspired lifestyle aesthetics.
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
    <div className="space-y-8">
      {/* Top Page Header */}
      <PageHeader
        title={`Welcome, ${currentUser.name.split(' ')[0]}`}
        description={`${society?.name || 'Society Cart'} • Flat ${currentUser.flatNumber}`}
        badge={
          <Badge variant="primary" size="md">
            Resident Mode
          </Badge>
        }
        actions={
          <Button
            size="md"
            variant="primary"
            onClick={() => navigate('/chat')}
            leftIcon={<MessageSquare className="h-4 w-4" />}
            className="shadow-sm shadow-[#174D3A]/20"
          >
            Open Society Chat
          </Button>
        }
      />

      {/* Hero Active Order Round Card */}
      <div
        className={`rounded-3xl p-6 sm:p-8 transition-all border ${
          activeRound.status === 'open'
            ? 'bg-gradient-to-br from-white via-white to-[#EBF2EE]/40 border-[#DFDAD0] shadow-card'
            : 'bg-white border-[#EBE8DF] shadow-soft'
        }`}
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-3.5 max-w-2xl">
            <div className="flex items-center gap-2.5">
              <Badge
                variant={activeRound.status === 'open' ? 'primary' : 'neutral'}
                pulseDot={activeRound.status === 'open'}
              >
                {activeRound.status === 'open'
                  ? `Round #${activeRound.roundNumber} OPEN`
                  : 'ORDERING CLOSED'}
              </Badge>
              <span className="text-xs text-[#827F76] font-medium">• Collective Order Drive</span>
            </div>

            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-[#252824] tracking-tight">
                {activeRound.status === 'open' ? activeRound.title : 'No Active Grocery Round'}
              </h2>
              <p className="mt-1 text-xs sm:text-sm text-[#827F76] leading-relaxed">
                {activeRound.status === 'open'
                  ? 'Drop your grocery needs in society group chat before the deadline. Our volunteer purchases wholesale in bulk.'
                  : 'Grocery ordering is currently closed. Volunteers will schedule the next collective round soon.'}
              </p>
            </div>

            {/* Timing & Volunteer Meta Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="flex items-center gap-2 text-xs text-[#252824]">
                <Clock className="h-4 w-4 text-[#C87D25] shrink-0" />
                <span>
                  Deadline:{' '}
                  <strong className={activeRound.status === 'open' ? 'text-[#C87D25]' : 'text-[#827F76]'}>
                    {activeRound.deadlineText}
                  </strong>
                </span>
              </div>

              <div className="flex items-center gap-2 text-xs text-[#252824]">
                <Calendar className="h-4 w-4 text-[#174D3A] shrink-0" />
                <span>
                  Delivery: <strong>{activeRound.shopVisitDate}</strong>
                </span>
              </div>

              <div className="flex items-center gap-2 text-xs text-[#252824]">
                <User className="h-4 w-4 text-[#827F76] shrink-0" />
                <span>
                  Volunteer: <strong>{activeRound.volunteerName}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row lg:flex-col gap-3 shrink-0">
            {activeRound.status === 'open' ? (
              <Button
                variant="primary"
                size="md"
                onClick={() => navigate('/chat')}
                leftIcon={<MessageSquare className="h-4 w-4" />}
                className="shadow-sm shadow-[#174D3A]/20"
              >
                Add Groceries in Chat
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
      </div>

      {/* Phase 5: Active AI Parsed Orders Card (if any pending confirmation or clarification) */}
      {orders.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-[#252824] flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#174D3A]" />
              <span>AI-Interpreted Orders ({orders.length})</span>
            </h3>
            <span className="text-xs text-[#827F76]">Click to review, clarify, or confirm</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {orders.map((ord) => (
              <Card
                key={ord.id}
                hoverable
                onClick={() => setSelectedOrder(ord)}
                className={`p-5 transition-all ${
                  ord.status === 'needs_clarification'
                    ? 'border-amber-300 bg-amber-50/20'
                    : ord.status === 'pending_review' || ord.status === 'awaiting_confirmation'
                    ? 'border-[#A7B8A0] bg-[#EBF2EE]/30'
                    : 'border-[#EBE8DF]'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-[#252824]">
                        Round #{ord.round_number}
                      </span>
                      <Badge
                        size="sm"
                        variant={
                          ord.status === 'confirmed'
                            ? 'primary'
                            : ord.status === 'needs_clarification'
                            ? 'warning'
                            : 'sage'
                        }
                      >
                        {ord.status.replace(/_/g, ' ')}
                      </Badge>
                    </div>
                    <p className="text-xs text-[#827F76] italic mt-1.5 truncate max-w-sm">
                      "{ord.raw_text}"
                    </p>
                    <p className="text-[11px] text-[#827F76] mt-1">
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
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-[#252824]">My Grocery Bills & Invoices</h3>
            <span className="text-xs text-[#827F76]">{myBills.length} Invoices</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {myBills.map((b) => (
              <Card
                key={b.id}
                hoverable
                onClick={() => navigate('/order-summary')}
                className="p-5 border-[#EBE8DF] bg-white space-y-3 cursor-pointer group hover:border-[#174D3A]/30"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#252824]">Round #{b.round_number}</span>
                  <Badge variant={b.status === 'published' ? 'primary' : 'neutral'} size="sm">
                    {b.status.toUpperCase()}
                  </Badge>
                </div>

                <div className="flex items-baseline justify-between pt-2 border-t border-[#EBE8DF]">
                  <span className="text-xs text-[#827F76]">{b.items.length} items</span>
                  <span className="text-lg font-black text-[#174D3A]">
                    ₹{b.total_amount.toFixed(2)}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-[#827F76] group-hover:text-[#174D3A] transition-colors">
                  <span>View Itemized Receipt</span>
                  <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Quick Statistics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
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
          icon={<TrendingDown className="h-5 w-5 text-[#174D3A]" />}
          trend={{ value: '21% below retail', isPositive: true }}
        />

        <StatCard
          label="Completed Rounds"
          value="3 Orders"
          subtext={`Delivered to Flat ${currentUser.flatNumber}`}
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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Activity Feed (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-[#252824]">Society Activity Stream</h3>
            <span className="text-xs text-[#827F76]">Live round updates</span>
          </div>

          <Card className="divide-y divide-[#EBE8DF] p-0 overflow-hidden">
            {notifications.map((item) => (
              <div key={item.id} className="flex items-start gap-3 p-4 sm:p-5 text-left hover:bg-[#FAF9F6] transition-colors">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#EBF2EE] text-[#174D3A] mt-0.5">
                  <BellRing className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-[#252824]">{item.title}</h4>
                    <span className="text-[10px] text-[#827F76]">{item.timestamp}</span>
                  </div>
                  <p className="mt-1 text-xs text-[#827F76] leading-relaxed">{item.description}</p>
                </div>
              </div>
            ))}
          </Card>
        </div>

        {/* Quick Actions & Tips (1 Col) */}
        <div className="space-y-4">
          <h3 className="text-base font-bold text-[#252824]">Quick Actions</h3>

          <div className="space-y-3">
            <Card
              hoverable
              onClick={() => navigate('/chat')}
              className="p-4 sm:p-5 flex items-center justify-between group"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EBF2EE] text-[#174D3A]">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-[#252824] group-hover:text-[#174D3A] transition-colors">
                    Society Group Chat
                  </h4>
                  <p className="text-[11px] text-[#827F76]">Type what you need in plain text</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-[#827F76] group-hover:translate-x-1 transition-transform" />
            </Card>

            <Card
              hoverable
              onClick={() => navigate('/order-summary')}
              className="p-4 sm:p-5 flex items-center justify-between group"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#F3F0E8] text-[#C87D25]">
                  <Receipt className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-[#252824] group-hover:text-[#174D3A] transition-colors">
                    Check My Bill
                  </h4>
                  <p className="text-[11px] text-[#827F76]">Itemized receipt & savings proof</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-[#827F76] group-hover:translate-x-1 transition-transform" />
            </Card>

            {/* Smart Tip Card */}
            <div className="rounded-2xl border border-[#DFDAD0] bg-[#FAF9F6] p-5 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-[#174D3A]">
                <Sparkles className="h-4 w-4" />
                <span>Multilingual AI Tip</span>
              </div>
              <p className="text-xs text-[#827F76] leading-relaxed">
                You can write grocery requests in English, Telugu, or Hindi (e.g., <em>"2 kg rice, 1 packet sugar"</em> or <em>"Naaku 2 packets atta kavali"</em>). The AI assistant extracts items and brands automatically!
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
