import React, { useState, useEffect } from 'react';
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
  ShieldCheck,
  User,
  Shield,
  RefreshCw,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { StatCard } from '../components/common/StatCard';
import { ConfirmationDialog } from '../components/common/ConfirmationDialog';
import { api } from '../services/api';
import { ApiMembership } from '../types';

/**
 * Screen 4: Volunteer Operations Dashboard — Logistics control center for closing rounds,
 * tallying bulk items, and managing apartment community resident roles.
 */
export const VolunteerDashboard: React.FC = () => {
  const navigate = useNavigate();
  const {
    currentUser,
    society,
    activeRound,
    pastRounds,
    closeActiveRound,
    groceryItems,
    activeSocietyPair,
    isAuthenticated,
  } = useApp();

  const [showCloseModal, setShowCloseModal] = useState(false);
  const [members, setMembers] = useState<ApiMembership[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [updatingMemberId, setUpdatingMemberId] = useState<string | null>(null);
  const [memberMessage, setMemberMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const purchasedCount = groceryItems.filter((i) => i.isPurchased).length;
  const progressPercent = Math.round((purchasedCount / groceryItems.length) * 100);

  const isAdmin = activeSocietyPair?.membership.role === 'admin';

  /**
   * Fetches real registered members for the active society.
   */
  const loadMembers = async () => {
    if (!activeSocietyPair?.society.id) return;
    setIsLoadingMembers(true);
    try {
      const data = await api.societies.getMembers(activeSocietyPair.society.id);
      setMembers(data);
    } catch {
      // If error (e.g. unauthenticated demo), fallback will be empty
    } finally {
      setIsLoadingMembers(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && activeSocietyPair) {
      loadMembers();
    }
  }, [isAuthenticated, activeSocietyPair]);

  /**
   * Admin promotion or demotion of a society member between volunteer and resident roles.
   */
  const handleToggleVolunteerRole = async (member: ApiMembership) => {
    if (!activeSocietyPair || !isAdmin) return;
    const newRole = member.role === 'volunteer' ? 'resident' : 'volunteer';
    setUpdatingMemberId(member.id);
    setMemberMessage(null);

    try {
      await api.societies.assignRole(activeSocietyPair.society.id, member.id, newRole);
      setMemberMessage({
        type: 'success',
        text: `Updated Flat ${member.flat_number} (${member.user_name || 'Resident'}) to ${newRole}.`,
      });
      await loadMembers();
    } catch (err: any) {
      setMemberMessage({
        type: 'error',
        text: err.message || 'Failed to update member role.',
      });
    } finally {
      setUpdatingMemberId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <PageHeader
        title={`Operations Dashboard — ${currentUser.name.split(' ')[0]}`}
        description={`${society.name} • Society Management & Operations`}
        badge={
          <Badge variant={isAdmin ? 'warning' : 'primary'} size="md">
            {isAdmin ? 'Admin View' : 'Volunteer View'}
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
          label="Registered Residents"
          value={members.length > 0 ? `${members.length} Members` : `${activeRound.participatingFlatsCount} Flats`}
          subtext={`Society: ${society.name}`}
          icon={<Users className="h-5 w-5" />}
          trend={{ value: 'Active community roster', isPositive: true }}
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

      {/* Society Members Management Card (RBAC) */}
      {isAuthenticated && members.length > 0 && (
        <Card className="p-6 border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-[#23865B]" />
              <h3 className="text-sm font-bold text-[#18231E]">Society Residents & Roles</h3>
              <Badge variant="neutral" size="sm">
                {members.length} Registered
              </Badge>
            </div>
            <button
              onClick={loadMembers}
              disabled={isLoadingMembers}
              className="inline-flex items-center gap-1 text-xs text-[#718078] hover:text-[#23865B] transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingMembers ? 'animate-spin' : ''}`} />
              <span>Refresh Roster</span>
            </button>
          </div>

          {memberMessage && (
            <div
              className={`mb-4 p-3 rounded-xl text-xs font-semibold ${
                memberMessage.type === 'success'
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-red-50 text-red-800 border border-red-200'
              }`}
            >
              {memberMessage.text}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAF9] border-b border-[#E6ECE8] text-[#718078] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Flat</th>
                  <th className="py-2.5 px-3">Name</th>
                  <th className="py-2.5 px-3">Email</th>
                  <th className="py-2.5 px-3">Role</th>
                  {isAdmin && <th className="py-2.5 px-3 text-right">Role Assignment</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6ECE8]">
                {members.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-3 font-bold text-[#18231E]">Flat {m.flat_number}</td>
                    <td className="py-3 px-3 font-semibold text-[#18231E]">
                      {m.user_name || 'Resident'}
                    </td>
                    <td className="py-3 px-3 text-[#718078]">{m.user_email || '—'}</td>
                    <td className="py-3 px-3">
                      <Badge
                        size="sm"
                        variant={m.role === 'admin' ? 'warning' : m.role === 'volunteer' ? 'primary' : 'neutral'}
                      >
                        {m.role === 'admin' ? (
                          <span className="flex items-center gap-1">
                            <Shield className="h-3 w-3 text-amber-600" /> Admin
                          </span>
                        ) : m.role === 'volunteer' ? (
                          <span className="flex items-center gap-1">
                            <ShieldCheck className="h-3 w-3 text-[#23865B]" /> Volunteer
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3 text-slate-500" /> Resident
                          </span>
                        )}
                      </Badge>
                    </td>
                    {isAdmin && (
                      <td className="py-3 px-3 text-right">
                        {m.role === 'admin' ? (
                          <span className="text-[11px] text-slate-400 font-medium">Society Creator</span>
                        ) : (
                          <Button
                            size="sm"
                            variant={m.role === 'volunteer' ? 'outline' : 'primary'}
                            isLoading={updatingMemberId === m.id}
                            onClick={() => handleToggleVolunteerRole(m)}
                            leftIcon={
                              m.role === 'volunteer' ? (
                                <User className="h-3.5 w-3.5" />
                              ) : (
                                <ShieldCheck className="h-3.5 w-3.5" />
                              )
                            }
                          >
                            {m.role === 'volunteer' ? 'Revoke Volunteer' : 'Make Volunteer'}
                          </Button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

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
