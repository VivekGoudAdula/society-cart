import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import { useApp } from './AppContext';
import { api } from '../services/api';
import { nexconnClient } from '../services/nexconn/nexconnClient';
import { NexconnChatMessage, NexconnConnectionState } from '../services/nexconn/nexconnTypes';
import { isLikelyGroceryMessage } from '../utils/groceryDetector';

export interface ChatContextType {
  connectionState: NexconnConnectionState;
  messages: NexconnChatMessage[];
  isLoadingHistory: boolean;
  activeGroupId: string | null;
  error: string | null;
  sendMessage: (text: string, asGroceryOrder?: boolean) => Promise<{ success: boolean; error?: string }>;
  refreshHistory: () => Promise<void>;
  reconnect: () => Promise<void>;
  clearChat: () => void;
}

export const ChatContext = createContext<ChatContextType | undefined>(undefined);

/**
 * Chat Provider managing real-time Nexconn group chat connection,
 * incoming message event dispatch, and message history synchronization.
 */
export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const {
    user,
    activeSocietyPair,
    isAuthenticated,
    currentUser,
    currentActiveRound,
    refreshActiveRound,
  } = useApp();

  const [connectionState, setConnectionState] = useState<NexconnConnectionState>('disconnected');
  const [messages, setMessages] = useState<NexconnChatMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const memberLookupRef = useRef<Record<string, { name: string; flatNumber: string; role?: string }>>({});

  const clearChat = useCallback(() => {
    setMessages([]);
    setActiveGroupId(null);
    setConnectionState('disconnected');
    memberLookupRef.current = {};
    nexconnClient.disconnect();
  }, []);

  /**
   * Refreshes the resident member lookup map to populate sender names and flat numbers.
   */
  const updateMemberLookup = async (societyId: string) => {
    try {
      const members = await api.societies.getMembers(societyId);
      const map: Record<string, { name: string; flatNumber: string; role?: string }> = {};
      for (const m of members) {
        map[m.user_id] = {
          name: m.user_name || 'Resident',
          flatNumber: m.flat_number,
          role: m.role,
        };
      }
      memberLookupRef.current = map;
      nexconnClient.setMemberLookup(map);
    } catch {
      // Fallback: lookup remains empty if unauthenticated
    }
  };

  /**
   * Loads message history from the Nexconn group channel with strict deduplication.
   */
  const refreshHistory = useCallback(async () => {
    if (!activeGroupId) return;
    setIsLoadingHistory(true);
    try {
      const history = await nexconnClient.fetchMessageHistory(
        activeGroupId,
        50,
        memberLookupRef.current
      );
      setMessages((prev) => {
        // Merge existing and fetched history with message ID deduplication
        const map = new Map<string, NexconnChatMessage>();
        for (const m of prev) {
          map.set(m.id, m);
        }
        for (const m of history) {
          map.set(m.id, m);
        }
        return Array.from(map.values()).sort((a, b) => a.sentTime - b.sentTime);
      });
    } catch (err: any) {
      console.warn('[ChatContext] Error loading message history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [activeGroupId]);

  /**
   * Explicitly reconnects to the society chat channel with refreshed token credentials.
   */
  const reconnect = useCallback(async () => {
    if (!isAuthenticated || !activeSocietyPair?.society.id) return;
    setError(null);
    setConnectionState('connecting');

    try {
      const societyId = activeSocietyPair.society.id;
      const tokenRes = await api.chat.getToken(societyId);
      setActiveGroupId(tokenRes.group_id);
      await updateMemberLookup(societyId);

      nexconnClient.initialize(tokenRes.app_key);
      const connected = await nexconnClient.connect(
        tokenRes.token,
        tokenRes.user_id,
        tokenRes.group_id
      );

      if (connected) {
        setConnectionState('connected');
        await refreshHistory();
      } else {
        setConnectionState('error');
        setError('Failed to establish Nexconn connection.');
      }
    } catch (err: any) {
      console.error('[ChatContext] Reconnect failed:', err);
      setConnectionState('error');
      setError(err.message || 'Failed to reconnect to group chat.');
    }
  }, [isAuthenticated, activeSocietyPair?.society.id, refreshHistory]);

  // Connect to Nexconn when authenticated and active society is present
  useEffect(() => {
    let unsubscribeState: (() => void) | null = null;
    let unsubscribeMsg: (() => void) | null = null;
    let isSubscribed = true;

    const connectToSocietyChat = async () => {
      if (!isAuthenticated || !activeSocietyPair?.society.id) {
        setConnectionState('disconnected');
        setActiveGroupId(null);
        setMessages([]);
        nexconnClient.disconnect();
        return;
      }

      const societyId = activeSocietyPair.society.id;
      setError(null);

      try {
        // 1. Refresh member roster to display sender identities accurately
        await updateMemberLookup(societyId);

        // 2. Fetch user-specific chat token and channel credentials from backend
        const tokenRes = await api.chat.getToken(societyId);
        if (!isSubscribed) return;
        setActiveGroupId(tokenRes.group_id);

        // 3. Initialize Nexconn SDK with public App Key
        nexconnClient.initialize(tokenRes.app_key);

        // 4. Register event listeners before connecting
        let prevConnectionState: NexconnConnectionState = 'disconnected';
        unsubscribeState = nexconnClient.onConnectionStateChange((state) => {
          if (!isSubscribed) return;
          setConnectionState(state);

          if (state === 'connected' && prevConnectionState !== 'connected' && prevConnectionState !== 'connecting') {
            refreshHistory();
          }
          prevConnectionState = state;
        });

        unsubscribeMsg = nexconnClient.onMessage((newMsg) => {
          if (!isSubscribed) return;
          // If message is a system bot announcement or round update, trigger active round refresh
          if (newMsg.isSystemBot || newMsg.text.includes('Grocery Round') || newMsg.text.includes('ROUND')) {
            refreshActiveRound();
          }

          setMessages((prev) => {
            if (prev.some((m) => m.id === newMsg.id)) {
              return prev;
            }
            return [...prev, newMsg];
          });
        });

        // 5. Connect user to Nexconn edge
        const connected = await nexconnClient.connect(
          tokenRes.token,
          tokenRes.user_id,
          tokenRes.group_id
        );

        if (connected && isSubscribed) {
          // 6. Fetch recent channel message history
          setIsLoadingHistory(true);
          const history = await nexconnClient.fetchMessageHistory(
            tokenRes.group_id,
            50,
            memberLookupRef.current
          );
          if (isSubscribed) {
            setMessages(history);
            setIsLoadingHistory(false);
          }
        }
      } catch (err: any) {
        if (!isSubscribed) return;
        console.error('[ChatContext] Failed to connect to society chat:', err);
        setError(err.message || 'Failed to connect to group chat.');
        setConnectionState('error');
      }
    };

    connectToSocietyChat();

    return () => {
      isSubscribed = false;
      if (unsubscribeState) unsubscribeState();
      if (unsubscribeMsg) unsubscribeMsg();
    };
  }, [isAuthenticated, activeSocietyPair?.society.id, user?.id, refreshHistory]);

  /**
   * Sends a text message to the society's group chat.
   * If an active grocery round is open, grocery-related requests automatically
   * trigger backend reservation and AI extraction without manual user friction.
   */
  const sendMessage = async (
    text: string,
    asGroceryOrder?: boolean
  ): Promise<{ success: boolean; error?: string }> => {
    if (!text.trim()) return { success: false, error: 'Message cannot be empty.' };

    const isRoundOpen = currentActiveRound?.status === 'open';
    const isGrocery = isRoundOpen && (asGroceryOrder !== undefined ? asGroceryOrder : isLikelyGroceryMessage(text));

    if (!isAuthenticated || !activeGroupId) {
      return { success: false, error: 'You are not connected to this society chat.' };
    }

    try {
      let clientSubmissionId: string | null = null;
      const isGrocerySubmission = isGrocery && !!activeSocietyPair?.society.id && !!currentActiveRound;

      // 1. Race-Safe Reservation Step: Pre-register order with backend before chat dispatch
      if (isGrocerySubmission) {
        clientSubmissionId = `sub_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        try {
          await api.rounds.reserveSubmission(
            activeSocietyPair!.society.id,
            currentActiveRound!.id,
            {
              submission_id: clientSubmissionId,
              raw_text: text.trim(),
            }
          );
        } catch (reserveErr: any) {
          console.warn('[ChatContext] Order reservation rejected by backend:', reserveErr);
          return {
            success: false,
            error: reserveErr.message || 'Grocery order reservation rejected. The round may be closed or expired.',
          };
        }
      }

      // 2. Dispatch message to Nexconn Group Chat
      let confirmedMsg;
      try {
        confirmedMsg = await nexconnClient.sendMessage(activeGroupId, text.trim(), {
          name: currentUser.name,
          flatNumber: currentUser.flatNumber,
          role: currentUser.role,
        });
      } catch (sendErr: any) {
        if (isGrocerySubmission && clientSubmissionId) {
          api.rounds
            .failSubmission(activeSocietyPair!.society.id, currentActiveRound!.id, clientSubmissionId, {
              reason: sendErr.message || 'Nexconn chat dispatch failed',
            })
            .catch((err) => console.warn('[ChatContext] Failed to record reservation failure:', err));
        }
        throw sendErr;
      }

      // 3. Confirm reservation with real Nexconn message ID
      if (isGrocerySubmission && clientSubmissionId) {
        try {
          await api.rounds.confirmSubmission(
            activeSocietyPair!.society.id,
            currentActiveRound!.id,
            clientSubmissionId,
            {
              message_id: confirmedMsg.id,
            }
          );
          confirmedMsg.isGroceryOrder = true;
          refreshActiveRound();
        } catch (confirmErr: any) {
          console.warn('[ChatContext] Order confirmation failed:', confirmErr);
          return {
            success: false,
            error: confirmErr.message || 'Chat message sent, but failed to confirm grocery round reservation.',
          };
        }
      }

      setMessages((prev) => {
        if (prev.some((m) => m.id === confirmedMsg.id)) {
          return prev;
        }
        return [...prev, confirmedMsg];
      });
      return { success: true };
    } catch (err: any) {
      console.error('[ChatContext] Send message failed:', err);
      setError(err.message || 'Failed to send message.');
      return { success: false, error: err.message || 'Failed to send message.' };
    }
  };

  return (
    <ChatContext.Provider
      value={{
        connectionState,
        messages,
        isLoadingHistory,
        activeGroupId,
        error,
        sendMessage,
        refreshHistory,
        reconnect,
        clearChat,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};
