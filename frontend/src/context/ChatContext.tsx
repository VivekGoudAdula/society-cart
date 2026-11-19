import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useApp } from './AppContext';
import { api } from '../services/api';
import { nexconnClient } from '../services/nexconn/nexconnClient';
import { NexconnChatMessage, NexconnConnectionState } from '../services/nexconn/nexconnTypes';
import { mockChatMessages } from '../data/mockData';

interface ChatContextType {
  connectionState: NexconnConnectionState;
  messages: NexconnChatMessage[];
  isLoadingHistory: boolean;
  activeGroupId: string | null;
  error: string | null;
  sendMessage: (text: string) => Promise<boolean>;
  refreshHistory: () => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

/**
 * Chat Provider managing real-time Nexconn group chat connection,
 * incoming message event dispatch, and message history synchronization.
 */
export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, activeSocietyPair, isAuthenticated, currentUser } = useApp();

  const [connectionState, setConnectionState] = useState<NexconnConnectionState>('disconnected');
  const [messages, setMessages] = useState<NexconnChatMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const memberLookupRef = useRef<Record<string, { name: string; flatNumber: string; role?: string }>>({});

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
    } catch {
      // Fallback: lookup remains empty if unauthenticated
    }
  };

  /**
   * Loads message history from the Nexconn group channel.
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
      setMessages(history);
    } catch (err: any) {
      console.warn('[ChatContext] Error loading message history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [activeGroupId]);

  // Connect to Nexconn when authenticated and active society is present
  useEffect(() => {
    let unsubscribeState: (() => void) | null = null;
    let unsubscribeMsg: (() => void) | null = null;

    const connectToSocietyChat = async () => {
      if (!isAuthenticated || !activeSocietyPair?.society.id) {
        // Fallback for demo preview
        setConnectionState('disconnected');
        setActiveGroupId(null);
        setMessages(
          mockChatMessages.map((m) => ({
            id: m.id,
            senderId: m.senderId,
            senderName: m.senderName,
            senderRole: m.senderRole,
            senderFlat: m.senderFlat,
            avatarUrl: m.avatarUrl,
            timestamp: m.timestamp,
            sentTime: Date.now(),
            text: m.text,
            isSelf: m.senderId === currentUser.id,
            isSystemBot: m.senderRole === 'bot',
            structuredItems: m.structuredItems,
          }))
        );
        return;
      }

      const societyId = activeSocietyPair.society.id;
      setError(null);

      try {
        // 1. Fetch user-specific chat token and channel credentials from backend
        const tokenRes = await api.chat.getToken(societyId);
        setActiveGroupId(tokenRes.group_id);

        // 2. Refresh member roster to display sender identities accurately
        await updateMemberLookup(societyId);

        // 3. Initialize Nexconn SDK with public App Key
        nexconnClient.initialize(tokenRes.app_key);

        // 4. Register event listeners before connecting
        unsubscribeState = nexconnClient.onConnectionStateChange((state) => {
          setConnectionState(state);
        });

        unsubscribeMsg = nexconnClient.onMessage((newMsg) => {
          setMessages((prev) => {
            // Avoid duplicate message insertions
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

        if (connected) {
          // 6. Fetch recent channel message history
          setIsLoadingHistory(true);
          const history = await nexconnClient.fetchMessageHistory(
            tokenRes.group_id,
            50,
            memberLookupRef.current
          );
          setMessages(history);
          setIsLoadingHistory(false);
        }
      } catch (err: any) {
        console.error('[ChatContext] Failed to connect to society chat:', err);
        setError(err.message || 'Failed to connect to group chat.');
        setConnectionState('error');
      }
    };

    connectToSocietyChat();

    return () => {
      if (unsubscribeState) unsubscribeState();
      if (unsubscribeMsg) unsubscribeMsg();
    };
  }, [isAuthenticated, activeSocietyPair?.society.id, user?.id]);

  /**
   * Sends a confirmed text message to the society's group chat.
   */
  const sendMessage = async (text: string): Promise<boolean> => {
    if (!text.trim()) return false;

    if (!isAuthenticated || !activeGroupId) {
      // In simulated demo mode, append message locally
      const simulated: NexconnChatMessage = {
        id: `sim_${Date.now()}`,
        senderId: currentUser.id,
        senderName: currentUser.name,
        senderFlat: currentUser.flatNumber,
        senderRole: currentUser.role,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sentTime: Date.now(),
        text: text.trim(),
        isSelf: true,
        isSystemBot: false,
      };
      setMessages((prev) => [...prev, simulated]);
      return true;
    }

    try {
      const confirmedMsg = await nexconnClient.sendMessage(activeGroupId, text.trim(), {
        name: currentUser.name,
        flatNumber: currentUser.flatNumber,
        role: currentUser.role,
      });

      setMessages((prev) => {
        if (prev.some((m) => m.id === confirmedMsg.id)) {
          return prev;
        }
        return [...prev, confirmedMsg];
      });
      return true;
    } catch (err: any) {
      console.error('[ChatContext] Send message failed:', err);
      setError(err.message || 'Failed to send message.');
      return false;
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
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = (): ChatContextType => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
