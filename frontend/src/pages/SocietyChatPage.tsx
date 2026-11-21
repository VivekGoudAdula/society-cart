import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Sparkles,
  Clock,
  CheckCircle2,
  Building2,
  Wifi,
  WifiOff,
  Loader2,
  AlertCircle,
  ShoppingCart,
  Lock,
  Eye,
  HelpCircle,
  RotateCcw,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useChat } from '../context/ChatContext';
import { Avatar } from '../components/common/Avatar';
import { Badge } from '../components/common/Badge';
import { OrderReviewModal } from '../components/orders/OrderReviewModal';
import { ApiGroceryOrder } from '../types';
import { api } from '../services/api';

/**
 * Screen 5: Society Chat Screen — Conversational interface backed by real-time Nexconn Group Chat.
 * Redesigned in Pinterest-inspired warm ivory & deep forest green palette.
 */
export const SocietyChatPage: React.FC = () => {
  const { currentUser, society, activeRound, isAuthenticated } = useApp();
  const { connectionState, messages, isLoadingHistory, sendMessage, reconnect, error: chatError } = useChat();

  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [asGroceryOrder, setAsGroceryOrder] = useState(true);
  const [sendError, setSendError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Phase 5: Structured AI Orders state
  const [residentOrders, setResidentOrders] = useState<ApiGroceryOrder[]>([]);
  const [selectedOrderForReview, setSelectedOrderForReview] = useState<ApiGroceryOrder | null>(null);

  const fetchOrders = useCallback(async () => {
    if (!society?.id || !activeRound?.id || !isAuthenticated) return;
    try {
      const orders = await api.orders.listByRound(society.id, activeRound.id);
      setResidentOrders(orders);
    } catch {
      // Background poll failure is silent
    }
  }, [society?.id, activeRound?.id, isAuthenticated]);

  useEffect(() => {
    fetchOrders();
    const interval = setInterval(fetchOrders, 8000);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const isRoundOpen = activeRound.status === 'open';

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isSending) return;

    setSendError(null);
    setIsSending(true);
    const sentText = inputMessage;
    setInputMessage('');

    const res = await sendMessage(sentText, asGroceryOrder && isRoundOpen);
    setIsSending(false);

    if (!res.success) {
      setInputMessage(sentText);
      setSendError(res.error || 'Failed to deliver message to Nexconn channel. Please try again.');
    } else {
      setTimeout(fetchOrders, 2500);
    }
  };

  const handleOrderUpdated = (updated: ApiGroceryOrder) => {
    setResidentOrders((prev) =>
      prev.map((o) => (o.id === updated.id ? updated : o))
    );
    setSelectedOrderForReview(updated);
  };

  // Find most relevant order awaiting resident attention
  const activeReviewOrder = residentOrders.find(
    (o) => o.status === 'needs_clarification' || o.status === 'pending_review' || o.status === 'awaiting_confirmation'
  );

  const quickTemplates = [
    '5 kg sona masoori rice and 2 litre sunflower oil',
    `3 kg onions and 2 kg potatoes for Flat ${currentUser.flatNumber}`,
    'Naaku 2 packets Aashirvaad atta kavali',
    `${currentUser.flatNumber}: 1 packet tata tea gold and 1 kg sugar`,
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-5xl mx-auto rounded-3xl border border-[#EBE8DF] bg-white shadow-card overflow-hidden">
      {/* 1. Chat Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-[#EBE8DF] bg-white z-10">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#174D3A] text-white shadow-sm shadow-[#174D3A]/20">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base font-bold text-[#252824]">{society?.name || 'Society Cart'} Group Chat</h2>
              <Badge
                size="sm"
                variant={activeRound.status === 'open' ? 'primary' : 'neutral'}
                pulseDot={activeRound.status === 'open'}
              >
                Round #{activeRound.roundNumber} {activeRound.status.toUpperCase()}
              </Badge>
            </div>
            <p className="text-[11px] text-[#827F76] flex items-center gap-2 mt-0.5">
              <span>{society?.totalFlats || '100+'} Flats</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-[#174D3A] font-semibold">
                <Clock className="h-3 w-3" /> Closes {activeRound.deadlineText}
              </span>
            </p>
          </div>
        </div>

        {/* Right side: Live Connection Status Pill */}
        <div className="flex items-center gap-2">
          {connectionState === 'connected' ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#EBF2EE] border border-[#174D3A]/20 text-[11px] font-bold text-[#174D3A]">
              <span className="h-2 w-2 rounded-full bg-[#174D3A] animate-pulse" />
              <Wifi className="h-3.5 w-3.5 text-[#174D3A]" />
              <span className="hidden sm:inline">Nexconn Live</span>
            </div>
          ) : connectionState === 'connecting' || connectionState === 'reconnecting' ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-[11px] font-bold text-amber-800">
              <Loader2 className="h-3.5 w-3.5 text-amber-600 animate-spin" />
              <span className="hidden sm:inline">Connecting...</span>
            </div>
          ) : connectionState === 'error' ? (
            <button
              onClick={() => reconnect()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-200 text-[11px] font-bold text-rose-800 hover:bg-rose-100 transition-colors shadow-xs"
              title="Click to reconnect"
            >
              <RotateCcw className="h-3.5 w-3.5 text-rose-600" />
              <span>Reconnect</span>
            </button>
          ) : isAuthenticated ? (
            <button
              onClick={() => reconnect()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#FAF9F6] border border-[#DFDAD0] text-[11px] font-semibold text-[#827F76] hover:bg-[#F3F0E8] transition-colors"
              title="Click to connect"
            >
              <WifiOff className="h-3.5 w-3.5 text-[#827F76]" />
              <span className="hidden sm:inline">Connecting to Chat</span>
            </button>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#EBF2EE] border border-[#174D3A]/20 text-[11px] font-semibold text-[#174D3A]">
              <Sparkles className="h-3.5 w-3.5 text-[#174D3A]" />
              <span className="hidden sm:inline">Live Chat</span>
            </div>
          )}
        </div>
      </div>

      {/* 2. Banner: Active Round Status Banner */}
      {isRoundOpen ? (
        <div className="bg-[#EBF2EE] px-4 py-2.5 border-b border-[#174D3A]/15 flex flex-wrap items-center justify-between gap-2 text-xs text-[#174D3A]">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-[#174D3A] animate-pulse" />
            <span className="font-bold">🛒 Round #{activeRound.roundNumber}:</span>
            <span>{activeRound.title}</span>
            <span className="hidden sm:inline text-[#174D3A]/60">•</span>
            <span className="hidden sm:inline font-medium">Shopping: {activeRound.shopVisitDate}</span>
          </div>
          <div className="flex items-center gap-1.5 font-bold bg-white/90 px-2.5 py-1 rounded-lg border border-[#174D3A]/20">
            <Clock className="h-3.5 w-3.5 text-[#174D3A]" />
            <span>Closes {activeRound.deadlineText}</span>
          </div>
        </div>
      ) : (
        <div className="bg-[#F3F0E8] px-4 py-2 border-b border-[#DFDAD0] flex items-center justify-between text-xs text-[#827F76]">
          <div className="flex items-center gap-2">
            <Lock className="h-3.5 w-3.5 text-[#827F76]" />
            <span className="font-medium">
              Grocery ordering is currently closed. Community discussion is active.
            </span>
          </div>
          <span className="text-[11px] font-semibold text-[#827F76]">Wait for next round</span>
        </div>
      )}

      {/* 2.1 Phase 5: AI Order Review / Clarification Action Banner */}
      {activeReviewOrder && (
        <div
          className={`px-4 py-2.5 border-b flex items-center justify-between gap-3 text-xs animate-in fade-in duration-200 ${
            activeReviewOrder.status === 'needs_clarification'
              ? 'bg-[#C87D25] text-white font-medium border-amber-600'
              : 'bg-[#174D3A] text-white font-medium border-[#113A2B]'
          }`}
        >
          <div className="flex items-center gap-2 min-w-0">
            {activeReviewOrder.status === 'needs_clarification' ? (
              <HelpCircle className="h-4 w-4 shrink-0 animate-bounce" />
            ) : (
              <Sparkles className="h-4 w-4 shrink-0 text-emerald-200" />
            )}
            <span className="truncate">
              {activeReviewOrder.status === 'needs_clarification'
                ? `Clarification needed on your grocery order: "${activeReviewOrder.clarification_prompt || 'Unspecified item/qty'}"`
                : `AI has parsed ${activeReviewOrder.items.length} items from your request! Confirmation required.`}
            </span>
          </div>
          <button
            onClick={() => setSelectedOrderForReview(activeReviewOrder)}
            className="shrink-0 px-3 py-1 bg-white text-[#252824] rounded-lg font-bold text-[11px] hover:bg-[#FAF9F6] transition-colors shadow-xs flex items-center gap-1.5"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>{activeReviewOrder.status === 'needs_clarification' ? 'Clarify Now' : 'Review & Confirm'}</span>
          </button>
        </div>
      )}

      {/* 3. Error Banner (if any) */}
      {(chatError || sendError) && (
        <div className="px-4 py-2.5 bg-rose-50 border-b border-rose-200 flex items-center justify-between gap-2 text-xs text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
            <span>{sendError || chatError}</span>
          </div>
          {chatError && (
            <button
              onClick={() => reconnect()}
              className="shrink-0 px-2.5 py-1 rounded-lg bg-rose-100 hover:bg-rose-200 text-rose-800 font-bold text-[11px] transition-colors flex items-center gap-1"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Retry</span>
            </button>
          )}
        </div>
      )}

      {/* 4. Messages Stream Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-[#FAF9F6]">
        {/* Loading History Indicator */}
        {isLoadingHistory && (
          <div className="flex items-center justify-center py-6 gap-2 text-xs text-[#827F76]">
            <Loader2 className="h-4 w-4 animate-spin text-[#174D3A]" />
            <span>Loading message history from Nexconn...</span>
          </div>
        )}

        {/* Date Separator */}
        {!isLoadingHistory && (
          <div className="flex items-center justify-center my-2">
            <span className="px-3 py-1 rounded-full bg-[#F3F0E8] text-[11px] font-semibold text-[#827F76] border border-[#DFDAD0]">
              Today, {activeRound.deadlineText}
            </span>
          </div>
        )}

        {/* Empty State */}
        {!isLoadingHistory && messages.length === 0 && (
          <div className="text-center py-12 space-y-2">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#EBF2EE] text-[#174D3A]">
              <Building2 className="h-6 w-6" />
            </div>
            <h3 className="text-xs font-bold text-[#252824]">Welcome to {society?.name || 'Society Cart'} Chat!</h3>
            <p className="text-[11px] text-[#827F76] max-w-sm mx-auto">
              No messages posted in this round yet. Post your grocery requirements in plain text to pool bulk wholesale orders!
            </p>
          </div>
        )}

        {messages.map((msg) => {
          const isCurrentUser = msg.isSelf;
          const isVolunteer = msg.senderRole === 'volunteer';
          const isBot = msg.isSystemBot || msg.senderRole === 'bot';

          // Bot / AI Assistant Interpretation Card
          if (isBot) {
            return (
              <div key={msg.id} className="flex items-start gap-3 max-w-xl mx-auto my-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-[#EBF2EE] border border-[#174D3A]/20 text-[#174D3A] mt-1 shadow-xs">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="flex-1 rounded-2xl bg-white border border-[#DFDAD0] p-4 shadow-soft text-left">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-[#174D3A] flex items-center gap-1.5">
                      {msg.senderName}{' '}
                      <span className="text-[10px] bg-[#EBF2EE] text-[#174D3A] px-2 py-0.5 rounded-full font-bold">
                        Assistant
                      </span>
                    </span>
                    <span className="text-[10px] text-[#827F76]">{msg.timestamp}</span>
                  </div>
                  <p className="text-xs text-[#252824] leading-relaxed whitespace-pre-wrap">{msg.text}</p>

                  {/* Extracted Structured Grocery Chips (if present) */}
                  {msg.structuredItems && msg.structuredItems.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-[#EBE8DF] flex flex-wrap gap-1.5">
                      {msg.structuredItems.map((item, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1 text-[11px] font-medium bg-[#EBF2EE] text-[#174D3A] border border-[#174D3A]/20 px-2.5 py-1 rounded-lg"
                        >
                          <CheckCircle2 className="h-3 w-3 text-[#174D3A]" />
                          <strong>{item.name}:</strong> {item.quantity}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          }

          // Volunteer Announcement Message (Distinct Banner Style)
          if (isVolunteer && !isCurrentUser) {
            return (
              <div key={msg.id} className="flex items-start gap-3 max-w-xl mr-auto">
                <Avatar name={msg.senderName} src={msg.avatarUrl} size="sm" roleTag="volunteer" />
                <div className="rounded-2xl bg-[#F8F6F0] border border-[#DFDAD0] p-4 text-left shadow-soft">
                  <div className="flex items-center justify-between gap-4 mb-1">
                    <span className="text-xs font-bold text-[#174D3A] flex items-center gap-1.5">
                      {msg.senderName}
                      <span className="text-[10px] bg-[#174D3A] text-white px-2 py-0.5 rounded-md font-bold">
                        VOLUNTEER {msg.senderFlat ? `(${msg.senderFlat})` : ''}
                      </span>
                    </span>
                    <span className="text-[10px] text-[#827F76]">{msg.timestamp}</span>
                  </div>
                  <p className="text-xs text-[#252824] leading-relaxed font-medium whitespace-pre-wrap">{msg.text}</p>
                </div>
              </div>
            );
          }

          // Regular Resident Message
          return (
            <div
              key={msg.id}
              className={`flex items-start gap-2.5 max-w-lg ${
                isCurrentUser ? 'ml-auto flex-row-reverse text-right' : 'mr-auto text-left'
              }`}
            >
              <Avatar name={msg.senderName} src={msg.avatarUrl} size="sm" roleTag={msg.senderRole} />
              <div
                className={`rounded-2xl p-4 shadow-soft transition-all ${
                  isCurrentUser
                    ? 'bg-[#174D3A] text-white rounded-tr-xs'
                    : 'bg-white border border-[#EBE8DF] text-[#252824] rounded-tl-xs'
                }`}
              >
                <div
                  className={`flex items-center gap-2 mb-1.5 text-[11px] ${
                    isCurrentUser ? 'text-white/80 justify-end' : 'text-[#827F76] justify-start'
                  }`}
                >
                  <span className="font-bold">{isCurrentUser ? 'You' : msg.senderName}</span>
                  {msg.senderFlat && <span>• Flat {msg.senderFlat}</span>}
                  {msg.isGroceryOrder && (
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      isCurrentUser ? 'bg-white/20 text-white' : 'bg-[#EBF2EE] text-[#174D3A] border border-[#174D3A]/20'
                    }`}>
                      🛒 Order
                    </span>
                  )}
                  <span>• {msg.timestamp}</span>
                </div>
                <p className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* 5. Quick Suggestions Bar */}
      <div className="px-4 py-2 bg-[#FAF9F6] border-t border-[#EBE8DF] flex items-center gap-2 overflow-x-auto text-xs">
        <span className="text-[11px] font-bold text-[#827F76] shrink-0">Quick format:</span>
        {quickTemplates.map((tpl, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setInputMessage(tpl)}
            className="shrink-0 px-2.5 py-1 rounded-xl bg-white border border-[#DFDAD0] text-[#252824] hover:border-[#174D3A] hover:text-[#174D3A] text-[11px] transition-colors shadow-2xs"
          >
            {tpl}
          </button>
        ))}
      </div>

      {/* 6. Message Input Bar with Order Mode Switcher */}
      <form onSubmit={handleSend} className="p-3 sm:p-4 bg-white border-t border-[#EBE8DF]">
        <div className="flex flex-col gap-2">
          {/* Submission Mode Selector */}
          <div className="flex items-center justify-between text-xs px-1">
            <div className="flex items-center gap-2">
              {isRoundOpen ? (
                <button
                  type="button"
                  onClick={() => setAsGroceryOrder(!asGroceryOrder)}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold transition-all ${
                    asGroceryOrder
                      ? 'bg-[#EBF2EE] text-[#174D3A] border border-[#174D3A]/25'
                      : 'bg-[#F3F0E8] text-[#827F76] border border-[#DFDAD0]'
                  }`}
                >
                  <ShoppingCart className="h-3.5 w-3.5" />
                  <span>{asGroceryOrder ? '🛒 Grocery Order Mode (Active)' : '💬 Regular Chat Mode'}</span>
                </button>
              ) : (
                <div className="flex items-center gap-1.5 text-[#827F76] font-medium">
                  <Lock className="h-3.5 w-3.5" />
                  <span>Submissions closed for Round #{activeRound.roundNumber}</span>
                </div>
              )}
            </div>
            {isRoundOpen && asGroceryOrder && (
              <span className="text-[11px] text-[#174D3A] font-semibold hidden sm:inline">
                Links to Round #{activeRound.roundNumber} bulk manifest
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={isSending}
              placeholder={
                isRoundOpen && asGroceryOrder
                  ? `Submit grocery items for Flat ${currentUser.flatNumber} (e.g. 5 kg rice, 2L oil)...`
                  : `Message ${society?.name || 'society'} group chat...`
              }
              className="flex-1 rounded-2xl border border-[#DFDAD0] bg-[#FAF9F6] px-4 py-3 text-sm text-[#252824] placeholder:text-[#827F76]/60 focus:bg-white focus:border-[#174D3A] focus:outline-none focus:ring-2 focus:ring-[#174D3A]/15 transition-all"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isSending}
              className={`flex h-12 px-5 shrink-0 items-center justify-center gap-2 rounded-2xl text-white font-medium text-xs sm:text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm ${
                isRoundOpen && asGroceryOrder
                  ? 'bg-[#174D3A] hover:bg-[#113A2B] shadow-[#174D3A]/20'
                  : 'bg-[#252824] hover:bg-black'
              }`}
              aria-label="Send message"
            >
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span className="hidden sm:inline font-bold">
                    {isRoundOpen && asGroceryOrder ? 'Order' : 'Send'}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Phase 5: Structured Order Review Modal */}
      <OrderReviewModal
        order={selectedOrderForReview}
        isOpen={!!selectedOrderForReview}
        onClose={() => setSelectedOrderForReview(null)}
        onOrderUpdated={handleOrderUpdated}
      />
    </div>
  );
};
