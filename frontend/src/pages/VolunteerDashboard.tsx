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
  PlusCircle,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { PageHeader } from '../components/common/PageHeader';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { StatCard } from '../components/common/StatCard';
import { Modal } from '../components/common/Modal';
import { Input } from '../components/common/Input';
import { ConfirmationDialog } from '../components/common/ConfirmationDialog';
import { api } from '../services/api';
import { ApiMembership, ApiOrderRound } from '../types';

/**
 * Screen 4: Volunteer Operations Dashboard — Logistics control center for closing rounds,
 * tallying bulk items, and managing apartment community resident roles.
 */
export const VolunteerDashboard: React.FC = () => {
  const navigate = useNavigate();
  const {
    currentUser,
    society,
    currentActiveRound,
    activeRound,
    pastRounds,
    refreshActiveRound,
    createRound,
    openRound,
    closeRound,
    closeActiveRound,
    groceryItems,
    activeSocietyPair,
    isAuthenticated,
  } = useApp();

  const [showCloseModal, setShowCloseModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // New Round Form State
  const [newTitle, setNewTitle] = useState('Weekend Community Bulk Order');
  const [newDescription, setNewDescription] = useState('Aggregating essentials for Sunday wholesale procurement');
  const [newDeadline, setNewDeadline] = useState(
    new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16)
  );
  const [newShoppingDate, setNewShoppingDate] = useState('Saturday 10:00 AM');

  const [members, setMembers] = useState<ApiMembership[]>([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [updatingMemberId, setUpdatingMemberId] = useState<string | null>(null);
  const [memberMessage, setMemberMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [pastRoundsList, setPastRoundsList] = useState<ApiOrderRound[]>([]);
  const [isLoadingRounds, setIsLoadingRounds] = useState(false);

  const purchasedCount = groceryItems.filter((i) => i.isPurchased).length;
  const progressPercent = Math.round((purchasedCount / groceryItems.length) * 100);

  const isAdmin = activeSocietyPair?.membership.role === 'admin';
  const isVolunteerOrAdmin =
    activeSocietyPair?.membership.role === 'admin' ||
    activeSocietyPair?.membership.role === 'volunteer';

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

  /**
   * Fetches round history for the active society.
   */
  const loadRoundsHistory = async () => {
    if (!activeSocietyPair?.society.id) return;
    setIsLoadingRounds(true);
    try {
      const res = await api.rounds.list(activeSocietyPair.society.id);
      setPastRoundsList(res.items);
    } catch {
      // Fallback
    } finally {
      setIsLoadingRounds(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated && activeSocietyPair) {
      loadMembers();
      loadRoundsHistory();
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

  /**
   * Creates a new grocery ordering round and immediately opens it.
   */
  const handleCreateAndOpenRound = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDeadline || isCreating) return;

    setIsCreating(true);
    setActionError(null);

    const deadlineUtc = new Date(newDeadline).toISOString();

    const createRes = await createRound({
      title: newTitle.trim(),
      description: newDescription.trim() || undefined,
      deadline_at: deadlineUtc,
      shopping_date: newShoppingDate.trim(),
    });

    if (!createRes.success || !createRes.round) {
      setActionError(createRes.error || 'Failed to create grocery round.');
      setIsCreating(false);
      return;
    }

    // Now open the round immediately
    const openRes = await openRound(createRes.round.id);
    setIsCreating(false);

    if (!openRes.success) {
      setActionError(openRes.error || 'Round created as draft, but opening announcement failed.');
    } else {
      setShowCreateModal(false);
      await refreshActiveRound();
      await loadRoundsHistory();
    }
  };

  /**
   * Closes the active round.
   */
  const handleConfirmClose = async () => {
    if (!currentActiveRound) {
      closeActiveRound();
      setShowCloseModal(false);
      return;
    }

    setIsClosing(true);
    setActionError(null);
    const res = await closeRound(currentActiveRound.id);
    setIsClosing(false);
    setShowCloseModal(false);

    if (!res.success) {
      setActionError(res.error || 'Failed to close grocery round.');
    } else {
      await loadRoundsHistory();
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
            {isVolunteerOrAdmin && activeRound.status !== 'open' && (
              <Button
                variant="primary"
                size="md"
                onClick={() => setShowCreateModal(true)}
                leftIcon={<PlusCircle className="h-4 w-4" />}
              >
                Start New Grocery Round
              </Button>
            )}

            <Button
              variant={activeRound.status === 'open' ? 'primary' : 'outline'}
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

        {/* Action Error feedback if any */}
        {actionError && (
          <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs font-semibold text-red-800 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
            <span>{actionError}</span>
          </div>
        )}

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
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-[#18231E]">Completed Grocery Drives</h3>
            <Badge variant="neutral" size="sm">
              {pastRoundsList.length > 0 ? `${pastRoundsList.length} Rounds` : 'Archive'}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#718078]">Past distribution records</span>
            <button
              onClick={loadRoundsHistory}
              disabled={isLoadingRounds}
              title="Refresh Rounds History"
              className="inline-flex items-center gap-1 text-xs text-[#718078] hover:text-[#23865B] transition-colors"
            >
              <RefreshCw className={`h-3 w-3 ${isLoadingRounds ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8FAF9] border-b border-[#E6ECE8] text-[#718078] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Round</th>
                  <th className="py-3 px-4">Shopping Date</th>
                  <th className="py-3 px-4">Deadline</th>
                  <th className="py-3 px-4">Orders</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6ECE8]">
                {pastRoundsList.length > 0 ? (
                  pastRoundsList.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#18231E]">
                        Round #{r.round_number} — {r.title}
                      </td>
                      <td className="py-3.5 px-4 text-[#718078]">{r.shopping_date}</td>
                      <td className="py-3.5 px-4 text-[#718078]">
                        {new Date(r.deadline_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })},{' '}
                        {new Date(r.deadline_at).toLocaleDateString([], { day: 'numeric', month: 'short' })}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[#18231E]">
                        {r.submissions_count} submissions
                      </td>
                      <td className="py-3.5 px-4">
                        <Badge
                          variant={r.status === 'open' ? 'success' : r.status === 'draft' ? 'warning' : 'neutral'}
                          size="sm"
                        >
                          {r.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => navigate('/shopping-list')}
                          className="font-semibold text-[#23865B] hover:underline"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  pastRounds.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#18231E]">
                        Round #{r.roundNumber} — {r.title}
                      </td>
                      <td className="py-3.5 px-4 text-[#718078]">{r.shopVisitDate}</td>
                      <td className="py-3.5 px-4 text-[#718078]">{r.deadlineText}</td>
                      <td className="py-3.5 px-4 font-medium">{r.participatingFlatsCount} Flats</td>
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
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Start New Round Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => !isCreating && setShowCreateModal(false)}
        title="Start New Grocery Ordering Round"
        description="Creates an ordering round and broadcasts the opening announcement to all residents on the Nexconn group chat."
      >
        <form onSubmit={handleCreateAndOpenRound} className="space-y-4 pt-2">
          {actionError && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs font-semibold text-red-800 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <span>{actionError}</span>
            </div>
          )}

          <Input
            label="Round Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="e.g. Weekend Essentials Drive"
            required
          />

          <Input
            label="Description / Volunteer Note"
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            placeholder="e.g. Procuring from wholesale mandi on Saturday morning"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Order Submission Deadline"
              type="datetime-local"
              value={newDeadline}
              onChange={(e) => setNewDeadline(e.target.value)}
              required
            />

            <Input
              label="Expected Shopping Date"
              value={newShoppingDate}
              onChange={(e) => setNewShoppingDate(e.target.value)}
              placeholder="e.g. Saturday 10:00 AM"
              required
            />
          </div>

          <div className="p-3 rounded-xl bg-emerald-50/80 border border-emerald-200 text-xs text-emerald-900 space-y-1">
            <div className="font-bold flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <span>Real-Time Group Chat Broadcast</span>
            </div>
            <p className="text-[11px] text-emerald-800 leading-relaxed">
              Upon starting, Society Cart Assistant will publish an official announcement with the deadline to the apartment Nexconn group channel.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <Button
              type="button"
              variant="outline"
              size="md"
              disabled={isCreating}
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isCreating}
              leftIcon={<PlusCircle className="h-4 w-4" />}
            >
              Start & Announce Round
            </Button>
          </div>
        </form>
      </Modal>

      {/* Close Round Confirmation Modal */}
      <ConfirmationDialog
        isOpen={showCloseModal}
        onClose={() => !isClosing && setShowCloseModal(false)}
        onConfirm={handleConfirmClose}
        title={`Close Round #${activeRound.roundNumber} for Submissions?`}
        message="Closing the round will immediately lock resident grocery order submissions and broadcast a closing notice in the Nexconn group chat. You can then view the consolidated shopping list."
        confirmLabel={isClosing ? 'Closing...' : 'Yes, Close Round'}
        cancelLabel="Keep Open"
      />
    </div>
  );
};
