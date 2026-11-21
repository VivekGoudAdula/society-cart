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
 * compiling bulk items, and managing apartment community resident roles.
 * Redesigned in warm Pinterest-inspired lifestyle palette.
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
  const progressPercent = Math.round((purchasedCount / (groceryItems.length || 1)) * 100);

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
    <div className="space-y-8">
      {/* Top Header */}
      <PageHeader
        title={`Operations Hub — ${currentUser.name.split(' ')[0]}`}
        description={`${society?.name || 'Society Cart'} • Society Management & Bulk Logistics`}
        badge={
          <Badge variant={isAdmin ? 'warning' : 'primary'} size="md">
            {isAdmin ? 'Admin View' : 'Volunteer View'}
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2.5">
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
              className="shadow-sm shadow-[#174D3A]/20"
            >
              Consolidated Shopping List
            </Button>
          </div>
        }
      />

      {/* Operational Key Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <StatCard
          label="Active Order Round"
          value={`Round #${activeRound.roundNumber}`}
          subtext={activeRound.status === 'open' ? 'Accepting resident lists' : 'Locked for purchasing'}
          icon={<Layers className="h-5 w-5 text-[#174D3A]" />}
        />

        <StatCard
          label="Registered Residents"
          value={members.length > 0 ? `${members.length} Members` : `${activeRound.participatingFlatsCount} Flats`}
          subtext={`Society: ${society?.name || 'Society'}`}
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
        <Card className="p-6 bg-white border-[#EBE8DF] shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-[#174D3A]" />
              <h3 className="text-sm font-bold text-[#252824]">Society Residents & Roles</h3>
              <Badge variant="neutral" size="sm">
                {members.length} Registered
              </Badge>
            </div>
            <button
              onClick={loadMembers}
              disabled={isLoadingMembers}
              className="inline-flex items-center gap-1 text-xs text-[#827F76] hover:text-[#174D3A] transition-colors"
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
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              {memberMessage.text}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF9F6] border-b border-[#EBE8DF] text-[#827F76] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Flat</th>
                  <th className="py-2.5 px-3">Name</th>
                  <th className="py-2.5 px-3">Email</th>
                  <th className="py-2.5 px-3">Role</th>
                  {isAdmin && <th className="py-2.5 px-3 text-right">Role Assignment</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EBE8DF]">
                {members.map((m) => (
                  <tr key={m.id} className="hover:bg-[#FAF9F6] transition-colors">
                    <td className="py-3 px-3 font-bold text-[#252824]">Flat {m.flat_number}</td>
                    <td className="py-3 px-3 font-semibold text-[#252824]">
                      {m.user_name || 'Resident'}
                    </td>
                    <td className="py-3 px-3 text-[#827F76]">{m.user_email || '—'}</td>
                    <td className="py-3 px-3">
                      <Badge
                        size="sm"
                        variant={m.role === 'admin' ? 'warning' : m.role === 'volunteer' ? 'primary' : 'neutral'}
                      >
                        {m.role === 'admin' ? (
                          <span className="flex items-center gap-1">
                            <Shield className="h-3 w-3 text-amber-700" /> Admin
                          </span>
                        ) : m.role === 'volunteer' ? (
                          <span className="flex items-center gap-1 font-semibold">
                            <ShieldCheck className="h-3 w-3 text-[#174D3A]" /> Volunteer
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <User className="h-3 w-3 text-[#827F76]" /> Resident
                          </span>
                        )}
                      </Badge>
                    </td>
                    {isAdmin && (
                      <td className="py-3 px-3 text-right">
                        {m.role === 'admin' ? (
                          <span className="text-[11px] text-[#827F76] font-medium">Society Creator</span>
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
      <Card className="p-6 sm:p-8 bg-white border-[#EBE8DF] shadow-soft">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#827F76]">
                Logistics Controller
              </span>
              <Badge
                variant={activeRound.status === 'open' ? 'primary' : 'neutral'}
                pulseDot={activeRound.status === 'open'}
              >
                STATUS: {activeRound.status.toUpperCase()}
              </Badge>
            </div>

            <h2 className="text-xl sm:text-2xl font-bold text-[#252824] tracking-tight">
              {activeRound.title}
            </h2>

            <p className="text-xs sm:text-sm text-[#827F76] leading-relaxed">
              When all residents have posted requirements in the group chat, close the round to lock new requests and compile the master shopping list for wholesale bulk purchase.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-[#252824]">
              <div className="flex items-center gap-1.5 font-medium">
                <Clock className="h-4 w-4 text-[#C87D25]" />
                <span>Order Deadline: <strong>{activeRound.deadlineText}</strong></span>
              </div>
              <div className="flex items-center gap-1.5 font-medium">
                <Calendar className="h-4 w-4 text-[#174D3A]" />
                <span>Visit Date: <strong>{activeRound.shopVisitDate}</strong></span>
              </div>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row lg:flex-col gap-3 shrink-0">
            {isVolunteerOrAdmin && activeRound.status !== 'open' && (
              <Button
                variant="primary"
                size="md"
                onClick={() => setShowCreateModal(true)}
                leftIcon={<PlusCircle className="h-4 w-4" />}
                className="shadow-sm shadow-[#174D3A]/20"
              >
                Start New Grocery Round
              </Button>
            )}

            <Button
              variant={activeRound.status === 'open' ? 'primary' : 'outline'}
              size="md"
              onClick={() => navigate(currentActiveRound ? `/shopping-list?roundId=${currentActiveRound.id}` : '/shopping-list')}
              leftIcon={<ShoppingCart className="h-4 w-4" />}
            >
              Compile & View Shopping List
            </Button>

            {activeRound.status === 'open' ? (
              <Button
                variant="outline"
                size="md"
                onClick={() => setShowCloseModal(true)}
                leftIcon={<Lock className="h-4 w-4 text-[#C87D25]" />}
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
          <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-800 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
            <span>{actionError}</span>
          </div>
        )}

        {/* Packing & Purchasing Progress Bar */}
        <div className="mt-6 pt-5 border-t border-[#EBE8DF]">
          <div className="flex items-center justify-between text-xs mb-2 font-semibold text-[#252824]">
            <span>Shopping Progress</span>
            <span>{purchasedCount} of {groceryItems.length} items purchased ({progressPercent}%)</span>
          </div>
          <div className="h-2.5 w-full bg-[#F3F0E8] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#174D3A] rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </Card>

      {/* Historical Rounds Archive */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-[#252824]">Completed Grocery Drives</h3>
            <Badge variant="neutral" size="sm">
              {pastRoundsList.length > 0 ? `${pastRoundsList.length} Rounds` : 'Archive'}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#827F76]">Past distribution records</span>
            <button
              onClick={loadRoundsHistory}
              disabled={isLoadingRounds}
              title="Refresh Rounds History"
              className="inline-flex items-center gap-1 text-xs text-[#827F76] hover:text-[#174D3A] transition-colors"
            >
              <RefreshCw className={`h-3 w-3 ${isLoadingRounds ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        <Card className="p-0 overflow-hidden bg-white border-[#EBE8DF] shadow-soft">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF9F6] border-b border-[#EBE8DF] text-[#827F76] font-bold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Round</th>
                  <th className="py-3 px-4">Shopping Date</th>
                  <th className="py-3 px-4">Deadline</th>
                  <th className="py-3 px-4">Orders</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EBE8DF]">
                {pastRoundsList.length > 0 ? (
                  pastRoundsList.map((r) => (
                    <tr key={r.id} className="hover:bg-[#FAF9F6] transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#252824]">
                        Round #{r.round_number} — {r.title}
                      </td>
                      <td className="py-3.5 px-4 text-[#827F76]">{r.shopping_date}</td>
                      <td className="py-3.5 px-4 text-[#827F76]">
                        {new Date(r.deadline_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })},{' '}
                        {new Date(r.deadline_at).toLocaleDateString([], { day: 'numeric', month: 'short' })}
                      </td>
                      <td className="py-3.5 px-4 font-medium text-[#252824]">
                        {r.submissions_count} submissions
                      </td>
                      <td className="py-3.5 px-4">
                        <Badge
                          variant={r.status === 'open' ? 'primary' : r.status === 'draft' ? 'warning' : 'neutral'}
                          size="sm"
                        >
                          {r.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => navigate(`/shopping-list?roundId=${r.id}`)}
                          className="font-semibold text-[#174D3A] hover:underline"
                        >
                          Shopping Manifest
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  pastRounds.map((r) => (
                    <tr key={r.id} className="hover:bg-[#FAF9F6] transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#252824]">
                        Round #{r.roundNumber} — {r.title}
                      </td>
                      <td className="py-3.5 px-4 text-[#827F76]">{r.shopVisitDate}</td>
                      <td className="py-3.5 px-4 text-[#827F76]">{r.deadlineText}</td>
                      <td className="py-3.5 px-4 font-medium text-[#252824]">
                        {r.participatingFlatsCount} flats
                      </td>
                      <td className="py-3.5 px-4">
                        <Badge variant="neutral" size="sm">
                          {r.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => navigate('/shopping-list')}
                          className="font-semibold text-[#174D3A] hover:underline"
                        >
                          View Items
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
        onClose={() => setShowCreateModal(false)}
        title="Start New Grocery Round"
        description="Schedule a collective purchasing round for your apartment community."
      >
        <form onSubmit={handleCreateAndOpenRound} className="space-y-4">
          <Input
            label="Round Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="e.g. Sunday Morning Wholesale Market"
            required
          />

          <Input
            label="Description (Optional)"
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            placeholder="e.g. Aggregating organic essentials and staples"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Submission Deadline"
              type="datetime-local"
              value={newDeadline}
              onChange={(e) => setNewDeadline(e.target.value)}
              required
            />
            <Input
              label="Procurement / Shop Visit"
              value={newShoppingDate}
              onChange={(e) => setNewShoppingDate(e.target.value)}
              placeholder="e.g. Sunday 9:00 AM"
              required
            />
          </div>

          {actionError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-800">
              {actionError}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-3">
            <Button variant="outline" size="sm" type="button" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" type="submit" isLoading={isCreating}>
              Create & Open Round
            </Button>
          </div>
        </form>
      </Modal>

      {/* Confirmation Dialog: Close Round */}
      <ConfirmationDialog
        isOpen={showCloseModal}
        onClose={() => setShowCloseModal(false)}
        onConfirm={handleConfirmClose}
        title="Close Active Grocery Round?"
        message="Closing locks the round and stops accepting new grocery messages. The volunteer can then compile the consolidated master shopping list for wholesale purchase."
        confirmLabel={isClosing ? 'Closing...' : 'Close Round & Lock'}
        cancelLabel="Keep Open"
      />
    </div>
  );
};
