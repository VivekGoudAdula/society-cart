import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  Users,
  ShoppingBag,
  IndianRupee,
  Clock,
  ShoppingCart,
  MessageSquare,
  Lock,
  Calendar,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { StatCard } from '../components/common/StatCard';
import { ConfirmationDialog } from '../components/common/ConfirmationDialog';

/**
 * Screen 4: Volunteer Operations Dashboard — Logistics control center for closing rounds, tallying bulk items, and tracking orders.
 */
export const VolunteerDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser, society, activeRound, pastRounds, closeActiveRound, groceryItems } = useApp();

  const [showCloseModal, setShowCloseModal] = useState(false);

  const purchasedCount = groceryItems.filter((i) => i.isPurchased).length;
  const progressPercent = Math.round((purchasedCount / groceryItems.length) * 100);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <PageHeader
        title={`Operations Dashboard — ${currentUser.name.split(' ')[0]}`}
        description={`${society.name} • Society Volunteer Coordinator`}
        badge={
          <Badge variant="primary" size="md">
            Volunteer View
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/chat')}
              leftIcon={<MessageSquare className="h-4 w-4" />}
            >
              Society Chat
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={() => navigate('/shopping-list')}
              leftIcon={<ShoppingCart className="h-4 w-4" />}
            >
              Consolidated Shopping List
            </Button>
          </div>
        }
      />

      {/* Operational Key Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Active Order Round"
          value={`Round #${activeRound.roundNumber}`}
          subtext={activeRound.status === 'open' ? 'Accepting resident lists' : 'Locked for purchasing'}
          icon={<Layers className="h-5 w-5 text-[#23865B]" />}
        />

        <StatCard
          label="Participating Flats"
          value={`${activeRound.participatingFlatsCount} Flats`}
          subtext="Out of 128 society flats"
          icon={<Users className="h-5 w-5" />}
          trend={{ value: '+4 flats vs last round', isPositive: true }}
        />

        <StatCard
          label="Consolidated Items"
          value={`${groceryItems.length} Products`}
          subtext={`${activeRound.totalItemsCount} flat request lines`}
          icon={<ShoppingBag className="h-5 w-5" />}
        />

        <StatCard
          label="Estimated Bulk Value"
          value={`₹${activeRound.estimatedTotalValue.toLocaleString('en-IN')}`}
          subtext="Wholesale benchmark"
          icon={<IndianRupee className="h-5 w-5" />}
          trend={{ value: 'Est. ~₹1,420 community savings', isPositive: true }}
        />
      </div>

      {/* Active Round Management Operational Card */}
      <Card className="p-6 border-slate-200">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Logistics Controller
              </span>
              <Badge
                variant={activeRound.status === 'open' ? 'success' : 'neutral'}
                pulseDot={activeRound.status === 'open'}
              >
                STATUS: {activeRound.status.toUpperCase()}
              </Badge>
            </div>

            <h2 className="text-lg font-bold text-[#18231E]">
              {activeRound.title}
            </h2>

            <p className="text-xs text-[#718078] leading-relaxed">
              When all residents have posted their requirements in the group chat, close the round to lock new requests and generate the final consolidated manifest for wholesale purchase.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-[#18231E]">
              <div className="flex items-center gap-1.5 font-medium">
                <Clock className="h-4 w-4 text-amber-600" />
                <span>Order Deadline: <strong>{activeRound.deadlineText}</strong></span>
              </div>
              <div className="flex items-center gap-1.5 font-medium">
                <Calendar className="h-4 w-4 text-[#23865B]" />
                <span>Visit Date: <strong>{activeRound.shopVisitDate}</strong></span>
              </div>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row lg:flex-col gap-2.5 shrink-0">
            <Button
              variant="primary"
              size="md"
              onClick={() => navigate('/shopping-list')}
              leftIcon={<ShoppingCart className="h-4 w-4" />}
            >
              Open Bulk Shopping List
            </Button>

            {activeRound.status === 'open' ? (
              <Button
                variant="outline"
                size="md"
                onClick={() => setShowCloseModal(true)}
                leftIcon={<Lock className="h-4 w-4 text-amber-600" />}
                className="hover:border-amber-500 hover:text-amber-800"
              >
                Close Order Round
              </Button>
            ) : (
              <Badge variant="neutral" size="md" className="py-2.5 justify-center">
                Round Closed for Orders
              </Badge>
            )}
          </div>
        </div>

        {/* Packing & Purchasing Progress Bar */}
        <div className="mt-6 pt-5 border-t border-[#E6ECE8]">
          <div className="flex items-center justify-between text-xs mb-1.5 font-semibold text-[#18231E]">
            <span>Shopping Progress</span>
            <span>{purchasedCount} of {groceryItems.length} items purchased ({progressPercent}%)</span>
          </div>
          <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#23865B] rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </Card>

      {/* Historical Rounds Archive */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-[#18231E]">Completed Grocery Drives</h3>
          <span className="text-xs text-[#718078]">Past distribution records</span>
        </div>

        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAF9] border-b border-[#E6ECE8] text-[#718078] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Round</th>
                  <th className="py-3 px-4">Delivery Date</th>
                  <th className="py-3 px-4">Flats</th>
                  <th className="py-3 px-4">Total Items</th>
                  <th className="py-3 px-4">Final Cost</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6ECE8]">
                {pastRounds.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-[#18231E]">
                      Round #{r.roundNumber} — {r.title}
                    </td>
                    <td className="py-3.5 px-4 text-[#718078]">{r.shopVisitDate}</td>
                    <td className="py-3.5 px-4 font-medium">{r.participatingFlatsCount} Flats</td>
                    <td className="py-3.5 px-4 text-[#718078]">{r.totalItemsCount} items</td>
                    <td className="py-3.5 px-4 font-bold text-[#18231E]">
                      ₹{r.finalPurchasedValue?.toLocaleString('en-IN')}
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge variant="success" size="sm">
                        Delivered
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => navigate('/order-summary')}
                        className="font-semibold text-[#23865B] hover:underline"
                      >
                        View Bill & Savings
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Close Round Confirmation Modal */}
      <ConfirmationDialog
        isOpen={showCloseModal}
        onClose={() => setShowCloseModal(false)}
        onConfirm={closeActiveRound}
        title="Close Round #6 for New Orders?"
        message="Closing the round will lock resident message submissions and compile the final packing manifest. You will proceed to the market for bulk purchasing."
        confirmLabel="Yes, Close Round"
        cancelLabel="Keep Open"
      />
    </div>
  );
};
