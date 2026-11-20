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
 * Residents post grocery needs and receive AI interpretations and confirmations in real time.
 */
export const SocietyChatPage: React.FC = () => {
  const { currentUser, society, activeRound, isAuthenticated } = useApp();
  const { connectionState, messages, isLoadingHistory, sendMessage, error: chatError } = useChat();

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
      // Trigger order refresh after sending
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
    (o) => o.status === 'needs_clarification' || o.status === 'awaiting_confirmation'
  );

  const quickTemplates = [
    '5 kg sona masoori rice and 2 litre sunflower oil',
    `3 kg onions and 2 kg potatoes for Flat ${currentUser.flatNumber}`,
    'Naaku 2 packets Aashirvaad atta kavali',
    `${currentUser.flatNumber}: 1 packet tata tea gold and 1 kg sugar`,
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] max-w-5xl mx-auto rounded-2xl border border-[#E6ECE8] bg-white shadow-xs overflow-hidden">
      {/* 1. Chat Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-[#E6ECE8] bg-white z-10">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#23865B] text-white">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-[#18231E]">{society.name} Group Chat</h2>
              <Badge
                size="sm"
                variant={activeRound.status === 'open' ? 'success' : 'neutral'}
                pulseDot={activeRound.status === 'open'}
              >
                Round #{activeRound.roundNumber} {activeRound.status.toUpperCase()}
              </Badge>
            </div>
            <p className="text-[11px] text-[#718078] flex items-center gap-2">
              <span>{society.totalFlats} Flats</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-emerald-700 font-medium">
                <Clock className="h-3 w-3" /> Closes {activeRound.deadlineText}
              </span>
            </p>
          </div>
        </div>

        {/* Right side: Live Connection Status Pill */}
        <div className="flex items-center gap-2">
          {connectionState === 'connected' ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200/80 text-[11px] font-bold text-emerald-800">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <Wifi className="h-3.5 w-3.5 text-emerald-600" />
              <span className="hidden sm:inline">Nexconn Live</span>
            </div>
          ) : connectionState === 'connecting' || connectionState === 'reconnecting' ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200/80 text-[11px] font-bold text-amber-800">
              <Loader2 className="h-3.5 w-3.5 text-amber-600 animate-spin" />
              <span className="hidden sm:inline">Connecting...</span>
            </div>
          ) : isAuthenticated ? (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-[11px] font-semibold text-slate-600">
              <WifiOff className="h-3.5 w-3.5 text-slate-400" />
              <span className="hidden sm:inline">Connecting to Chat</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 border border-indigo-200 text-[11px] font-semibold text-indigo-700">
              <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
              <span className="hidden sm:inline">Demo Sandbox</span>
            </div>
          )}
        </div>
      </div>

      {/* 2. Banner: Active Round Status Banner */}
      {isRoundOpen ? (
        <div className="bg-emerald-50 px-4 py-2.5 border-b border-emerald-200/80 flex flex-wrap items-center justify-between gap-2 text-xs text-emerald-900">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold">🛒 Round #{activeRound.roundNumber}:</span>
            <span>{activeRound.title}</span>
            <span className="hidden sm:inline text-emerald-700">•</span>
            <span className="hidden sm:inline text-emerald-700 font-medium">Shopping: {activeRound.shopVisitDate}</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-800 font-semibold bg-white/80 px-2.5 py-1 rounded-lg border border-emerald-200">
            <Clock className="h-3.5 w-3.5 text-emerald-600" />
            <span>Closes {activeRound.deadlineText}</span>
          </div>
        </div>
      ) : (
        <div className="bg-slate-100/90 px-4 py-2 border-b border-slate-200 flex items-center justify-between text-xs text-slate-700">
          <div className="flex items-center gap-2">
            <Lock className="h-3.5 w-3.5 text-slate-500" />
            <span className="font-medium">
              Grocery ordering is currently closed. Community discussion is enabled.
            </span>
          </div>
          <span className="text-[11px] font-semibold text-slate-500">Wait for next round</span>
        </div>
      )}

      {/* 2.1 Phase 5: AI Order Review / Clarification Action Banner */}
      {activeReviewOrder && (
        <div
          className={`px-4 py-2.5 border-b flex items-center justify-between gap-3 text-xs animate-fade-in ${
            activeReviewOrder.status === 'needs_clarification'
              ? 'bg-amber-500 text-white font-medium border-amber-600'
              : 'bg-emerald-700 text-white font-medium border-emerald-800'
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
            className="shrink-0 px-3 py-1 bg-white text-gray-900 rounded-lg font-bold text-[11px] hover:bg-gray-100 transition-colors shadow-xs flex items-center gap-1.5"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>{activeReviewOrder.status === 'needs_clarification' ? 'Clarify Now' : 'Review & Confirm'}</span>
          </button>
        </div>
      )}

      {/* 3. Error Banner (if any) */}
      {(chatError || sendError) && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-200 flex items-center gap-2 text-xs text-red-800">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <span>{sendError || chatError}</span>
        </div>
      )}

      {/* 4. Messages Stream Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-[#F8FAF9]/50">
        {/* Loading History Indicator */}
        {isLoadingHistory && (
          <div className="flex items-center justify-center py-6 gap-2 text-xs text-[#718078]">
            <Loader2 className="h-4 w-4 animate-spin text-[#23865B]" />
            <span>Loading message history from Nexconn...</span>
          </div>
        )}

        {/* Date Separator */}
        {!isLoadingHistory && (
          <div className="flex items-center justify-center my-2">
            <span className="px-3 py-1 rounded-full bg-slate-100 text-[11px] font-semibold text-[#718078]">
              Today, {activeRound.deadlineText}
            </span>
          </div>
        )}

        {/* Empty State */}
        {!isLoadingHistory && messages.length === 0 && (
          <div className="text-center py-12 space-y-2">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#EAF5EE] text-[#196B48]">
              <Building2 className="h-6 w-6" />
            </div>
            <h3 className="text-xs font-bold text-[#18231E]">Welcome to {society.name} Chat!</h3>
            <p className="text-[11px] text-[#718078] max-w-sm mx-auto">
              No messages posted in this round yet. Be the first to share your grocery requirements with your neighbors!
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
              <div key={msg.id} className="flex items-start gap-3 max-w-xl mx-auto my-2">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 mt-1">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="flex-1 rounded-2xl bg-white border border-indigo-100 p-4 shadow-xs text-left">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-indigo-900 flex items-center gap-1.5">
                      {msg.senderName}{' '}
                      <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.2 rounded font-semibold">
                        System Assistant
                      </span>
                    </span>
                    <span className="text-[10px] text-slate-400">{msg.timestamp}</span>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">{msg.text}</p>

                  {/* Extracted Structured Grocery Chips (if present) */}
                  {msg.structuredItems && msg.structuredItems.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-indigo-50 flex flex-wrap gap-1.5">
                      {msg.structuredItems.map((item, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1 text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-1 rounded-lg"
                        >
                          <CheckCircle2 className="h-3 w-3 text-emerald-600" />
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
                <div className="rounded-2xl bg-emerald-50/80 border border-emerald-200 p-4 text-left shadow-xs">
                  <div className="flex items-center justify-between gap-4 mb-1">
                    <span className="text-xs font-bold text-emerald-950 flex items-center gap-1.5">
                      {msg.senderName}
                      <span className="text-[10px] bg-emerald-200/80 text-emerald-900 px-1.5 py-0.2 rounded font-bold">
                        VOLUNTEER {msg.senderFlat ? `(${msg.senderFlat})` : ''}
                      </span>
                    </span>
                    <span className="text-[10px] text-emerald-700">{msg.timestamp}</span>
                  </div>
                  <p className="text-xs text-emerald-900 leading-relaxed font-medium">{msg.text}</p>
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
                className={`rounded-2xl p-3.5 shadow-xs transition-all ${
                  isCurrentUser
                    ? 'bg-[#23865B] text-white rounded-tr-xs'
                    : 'bg-white border border-[#E6ECE8] text-[#18231E] rounded-tl-xs'
                }`}
              >
                <div
                  className={`flex items-center gap-2 mb-1 text-[11px] ${
                    isCurrentUser ? 'text-emerald-100 justify-end' : 'text-[#718078] justify-start'
                  }`}
                >
                  <span className="font-bold">{isCurrentUser ? 'You' : msg.senderName}</span>
                  {msg.senderFlat && <span>• Flat {msg.senderFlat}</span>}
                  {msg.isGroceryOrder && (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      isCurrentUser ? 'bg-white/20 text-white' : 'bg-emerald-100 text-emerald-800'
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
      <div className="px-4 py-2 bg-slate-50 border-t border-[#E6ECE8] flex items-center gap-2 overflow-x-auto text-xs">
        <span className="text-[11px] font-bold text-slate-500 shrink-0">Quick format:</span>
        {quickTemplates.map((tpl, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setInputMessage(tpl)}
            className="shrink-0 px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-[#23865B] hover:text-[#23865B] text-[11px] transition-colors"
          >
            {tpl}
          </button>
        ))}
      </div>

      {/* 6. Message Input Bar with Order Mode Switcher */}
      <form onSubmit={handleSend} className="p-3 sm:p-4 bg-white border-t border-[#E6ECE8]">
        <div className="flex flex-col gap-2">
          {/* Submission Mode Selector */}
          <div className="flex items-center justify-between text-xs px-1">
            <div className="flex items-center gap-2">
              {isRoundOpen ? (
                <button
                  type="button"
                  onClick={() => setAsGroceryOrder(!asGroceryOrder)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                    asGroceryOrder
                      ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                      : 'bg-slate-100 text-slate-600 border border-slate-200'
                  }`}
                >
                  <ShoppingCart className="h-3.5 w-3.5" />
                  <span>{asGroceryOrder ? '🛒 Grocery Order Mode (Active)' : '💬 Regular Chat Mode'}</span>
                </button>
              ) : (
                <div className="flex items-center gap-1.5 text-slate-500 font-medium">
                  <Lock className="h-3.5 w-3.5" />
                  <span>Submissions closed for Round #{activeRound.roundNumber}</span>
                </div>
              )}
            </div>
            {isRoundOpen && asGroceryOrder && (
              <span className="text-[11px] text-emerald-700 font-medium">
                Links to Round #{activeRound.roundNumber} shopping list
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
                  : `Message ${society.name} group chat...`
              }
              className="flex-1 rounded-xl border border-[#E6ECE8] bg-[#F8FAF9] px-4 py-3 text-sm text-[#18231E] placeholder:text-slate-400 focus:bg-white focus:border-[#23865B] focus:outline-none focus:ring-2 focus:ring-[#23865B]/20 transition-all"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isSending}
              className={`flex h-11 px-4 shrink-0 items-center justify-center gap-2 rounded-xl text-white font-medium text-xs sm:text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm ${
                isRoundOpen && asGroceryOrder
                  ? 'bg-[#23865B] hover:bg-[#196B48] shadow-[#23865B]/20'
                  : 'bg-slate-700 hover:bg-slate-800'
              }`}
              aria-label="Send message"
            >
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span className="hidden sm:inline">
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
