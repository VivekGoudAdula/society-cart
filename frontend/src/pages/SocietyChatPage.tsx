import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Clock,
  CheckCircle2,
  Building2,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Avatar } from '../components/common/Avatar';
import { Badge } from '../components/common/Badge';

/**
 * Screen 5: Society Chat Screen — Conversational interface where residents post grocery needs in natural language and the AI assistant extracts items.
 */
export const SocietyChatPage: React.FC = () => {
  const { currentUser, society, activeRound, chatMessages, sendChatMessage } = useApp();

  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;
    sendChatMessage(inputMessage);
    setInputMessage('');
  };

  const quickTemplates = [
    '5 kg sona masoori rice and 2 litre sunflower oil',
    '3 kg onions and 2 kg potatoes for Flat ' + currentUser.flatNumber,
    'Naaku 2 packets Aashirvaad atta kavali',
    'B-402: 1 packet tata tea gold and 1 kg sugar',
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
              <Badge size="sm" variant={activeRound.status === 'open' ? 'success' : 'neutral'} pulseDot={activeRound.status === 'open'}>
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

        {/* Volunteer Info Pill */}
        <div className="hidden sm:flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200/70">
          <Avatar name={activeRound.volunteerName} size="sm" roleTag="volunteer" />
          <div className="text-left text-[11px]">
            <p className="font-bold text-[#18231E] leading-tight">{activeRound.volunteerName}</p>
            <p className="text-slate-500 text-[10px]">Round Volunteer ({activeRound.volunteerFlat})</p>
          </div>
        </div>
      </div>

      {/* 2. Demo Disclaimer Banner */}
      <div className="bg-[#EAF5EE]/70 px-4 py-2 border-b border-[#23865B]/15 flex items-center justify-between text-xs text-[#196B48]">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 shrink-0 text-[#23865B]" />
          <span>
            <strong>Interactive UI Demo:</strong> Messages trigger local state updates and simulated assistant extraction. Real Nexconn Chat integration activates in Phase 3.
          </span>
        </div>
        <span className="text-[10px] bg-[#23865B] text-white px-2 py-0.5 rounded-md font-bold uppercase tracking-wider hidden md:inline-block">
          PHASE 1 PREVIEW
        </span>
      </div>

      {/* 3. Messages Stream Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-[#F8FAF9]/50">
        {/* Date Separator */}
        <div className="flex items-center justify-center my-2">
          <span className="px-3 py-1 rounded-full bg-slate-100 text-[11px] font-semibold text-[#718078]">
            Today, {activeRound.deadlineText}
          </span>
        </div>

        {chatMessages.map((msg) => {
          const isCurrentUser = msg.senderId === currentUser.id;
          const isVolunteer = msg.senderRole === 'volunteer';
          const isBot = msg.senderRole === 'bot';

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
                      {msg.senderName} <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.2 rounded font-semibold">AI Assistant</span>
                    </span>
                    <span className="text-[10px] text-slate-400">{msg.timestamp}</span>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">{msg.text}</p>

                  {/* Extracted Structured Grocery Chips */}
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
                        VOLUNTEER ({msg.senderFlat})
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
                  <span>• {msg.timestamp}</span>
                </div>
                <p className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* 4. Quick Suggestions Bar */}
      <div className="px-4 py-2 bg-slate-50 border-t border-[#E6ECE8] flex items-center gap-2 overflow-x-auto text-xs">
        <span className="text-[11px] font-bold text-slate-500 shrink-0">Try typing:</span>
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

      {/* 5. Message Input Bar */}
      <form onSubmit={handleSend} className="p-3 sm:p-4 bg-white border-t border-[#E6ECE8]">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={`Message ${society.name} (e.g. 5 kg rice, 1 litre oil, Flat ${currentUser.flatNumber})...`}
            className="flex-1 rounded-xl border border-[#E6ECE8] bg-[#F8FAF9] px-4 py-3 text-sm text-[#18231E] placeholder:text-slate-400 focus:bg-white focus:border-[#23865B] focus:outline-none focus:ring-2 focus:ring-[#23865B]/20 transition-all"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim()}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#23865B] text-white hover:bg-[#196B48] disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm shadow-[#23865B]/20"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
