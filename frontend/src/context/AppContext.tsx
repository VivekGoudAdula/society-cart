import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import {
  UserProfile,
  UserRole,
  Society,
  OrderRound,
  GroceryItem,
  ChatMessage,
  ResidentBill,
  ActivityNotification,
  UserSocietyPair,
  ApiSociety,
  ApiMembership,
  ApiOrderRound,
} from '../types';
import {
  mockPastRounds,
  mockResidentBill,
} from '../data/mockData';
import { api, getAuthToken, setAuthToken } from '../services/api';
import { nexconnClient } from '../services/nexconn/nexconnClient';

interface AppContextType {
  // Auth & Identity
  user: { id: string; name: string; email: string; phone?: string } | null;
  isAuthenticated: boolean;
  isLoadingSession: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (name: string, email: string, password: string, phone?: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;

  // Societies & Memberships
  userSocieties: UserSocietyPair[];
  activeSocietyPair: UserSocietyPair | null;
  setActiveSocietyId: (societyId: string) => void;
  createSociety: (data: {
    name: string;
    address: string;
    city: string;
    state?: string;
    country?: string;
    total_flats?: number;
    creator_flat_number: string;
  }) => Promise<{ success: boolean; society?: ApiSociety; membership?: ApiMembership; error?: string }>;
  joinSociety: (data: {
    invite_code: string;
    flat_number: string;
    role?: string;
  }) => Promise<{ success: boolean; society?: ApiSociety; membership?: ApiMembership; error?: string }>;

  // Current profile & roles
  currentUser: UserProfile;
  currentRole: UserRole;
  switchRole: (role: UserRole) => void;
  society: Society;

  // Grocery rounds & chat
  currentActiveRound: ApiOrderRound | null;
  isLoadingActiveRound: boolean;
  refreshActiveRound: () => Promise<void>;
  createRound: (data: {
    title: string;
    description?: string;
    deadline_at: string;
    shopping_date: string;
  }) => Promise<{ success: boolean; round?: ApiOrderRound; error?: string }>;
  openRound: (roundId: string) => Promise<{ success: boolean; round?: ApiOrderRound; error?: string }>;
  closeRound: (roundId: string) => Promise<{ success: boolean; round?: ApiOrderRound; error?: string }>;
  activeRound: OrderRound;
  pastRounds: OrderRound[];
  closeActiveRound: () => void;
  groceryItems: GroceryItem[];
  toggleItemPurchased: (itemId: string) => void;
  chatMessages: ChatMessage[];
  sendChatMessage: (text: string) => void;
  residentBill: ResidentBill;
  notifications: ActivityNotification[];
  markNotificationsRead: () => void;
  unreadNotificationsCount: number;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

/**
 * Global application state provider managing real authentication,
 * active apartment society memberships, and grocery ordering state.
 */
export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Real backend auth & membership states
  const [user, setUser] = useState<{ id: string; name: string; email: string; phone?: string } | null>(null);
  const [userSocieties, setUserSocieties] = useState<UserSocietyPair[]>([]);
  const [activeSocietyPair, setActiveSocietyPair] = useState<UserSocietyPair | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(true);

  // Application view/role state
  const [currentRole, setCurrentRole] = useState<UserRole>('resident');
  const [currentActiveRound, setCurrentActiveRound] = useState<ApiOrderRound | null>(null);
  const [isLoadingActiveRound, setIsLoadingActiveRound] = useState(false);
  const [groceryItems, setGroceryItems] = useState<GroceryItem[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [notifications, setNotifications] = useState<ActivityNotification[]>([]);

  const isAuthenticated = useMemo(() => !!user, [user]);

  /**
   * Fetches the real active grocery order round for the currently active society.
   */
  const refreshActiveRound = useCallback(async () => {
    if (!activeSocietyPair?.society.id) {
      setCurrentActiveRound(null);
      return;
    }
    setIsLoadingActiveRound(true);
    try {
      const round = await api.rounds.getActive(activeSocietyPair.society.id);
      setCurrentActiveRound(round);
    } catch {
      setCurrentActiveRound(null);
    } finally {
      setIsLoadingActiveRound(false);
    }
  }, [activeSocietyPair?.society.id]);

  useEffect(() => {
    if (activeSocietyPair?.society.id) {
      refreshActiveRound();
    } else {
      setCurrentActiveRound(null);
    }
  }, [activeSocietyPair?.society.id, refreshActiveRound]);

  /**
   * Refreshes the user's active session, societies, and memberships.
   */
  const refreshSession = async () => {
    try {
      const data = await api.auth.getMe();
      setUser(data.user);
      const societies = data.societies || [];
      setUserSocieties(societies);

      if (societies.length > 0) {
        const savedSocietyId = localStorage.getItem('society_cart_active_society_id');
        const matched = societies.find((item: UserSocietyPair) => item.society.id === savedSocietyId);
        const chosen = matched || societies[0];
        setActiveSocietyPair(chosen);
        setCurrentRole(chosen.membership.role);
      } else {
        setActiveSocietyPair(null);
      }
    } catch {
      setUser(null);
      setUserSocieties([]);
      setActiveSocietyPair(null);
      setAuthToken(null);
    }
  };

  // Restore authenticated session on mount
  useEffect(() => {
    const initSession = async () => {
      const token = getAuthToken();
      if (token) {
        await refreshSession();
      }
      setIsLoadingSession(false);
    };

    initSession();
  }, []);

  /**
   * Switch the active society when the user belongs to multiple societies.
   */
  const setActiveSocietyId = (societyId: string) => {
    const matched = userSocieties.find((pair) => pair.society.id === societyId);
    if (matched) {
      setActiveSocietyPair(matched);
      setCurrentRole(matched.membership.role);
      localStorage.setItem('society_cart_active_society_id', societyId);
    }
  };

  /**
   * Log into account via email & password.
   */
  const login = async (email: string, password: string) => {
    try {
      const res = await api.auth.login({ email, password });
      setAuthToken(res.access_token);
      await refreshSession();
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || 'Login failed' };
    }
  };

  /**
   * Register a new user account.
   */
  const register = async (name: string, email: string, password: string, phone?: string) => {
    try {
      const res = await api.auth.register({ name, email, password, phone });
      setAuthToken(res.access_token);
      await refreshSession();
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || 'Registration failed' };
    }
  };

  /**
   * Log out of current session.
   */
  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // Ignore network errors on logout
    }
    try {
      await nexconnClient.disconnect();
    } catch {
      // Ignore disconnect errors
    }
    setAuthToken(null);
    setUser(null);
    setUserSocieties([]);
    setActiveSocietyPair(null);
    setCurrentRole('resident');
    setCurrentActiveRound(null);
    setChatMessages([]);
    setGroceryItems([]);
    setNotifications([]);
    localStorage.removeItem('society_cart_active_society_id');
  };

  /**
   * Create an apartment society (assigns creator as Admin).
   */
  const createSociety = async (data: {
    name: string;
    address: string;
    city: string;
    state?: string;
    country?: string;
    total_flats?: number;
    creator_flat_number: string;
  }) => {
    try {
      const res = await api.societies.create(data);
      await refreshSession();
      return { success: true, society: res.society, membership: res.membership };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to create society' };
    }
  };

  /**
   * Join an apartment society with an invite code and flat number.
   */
  const joinSociety = async (data: { invite_code: string; flat_number: string; role?: string }) => {
    try {
      const res = await api.societies.join(data);
      await refreshSession();
      return { success: true, society: res.society, membership: res.membership };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to join society' };
    }
  };

  // Derive current user profile from real user + membership when authenticated
  const currentUser: UserProfile = useMemo(() => {
    if (user && activeSocietyPair) {
      return {
        id: user.id,
        name: user.name,
        email: user.email,
        phone: user.phone || '',
        flatNumber: activeSocietyPair.membership.flat_number,
        societyId: activeSocietyPair.society.id,
        societyName: activeSocietyPair.society.name,
        role: currentRole,
        avatarUrl: undefined,
      };
    }
    // Clean unauthenticated fallback
    return {
      id: '',
      name: 'Guest Resident',
      flatNumber: '',
      societyId: '',
      societyName: '',
      role: 'resident',
      email: '',
      phone: '',
    };
  }, [user, activeSocietyPair, currentRole]);

  // Derive society data
  const society: Society = useMemo(() => {
    if (activeSocietyPair) {
      return {
        id: activeSocietyPair.society.id,
        name: activeSocietyPair.society.name,
        locality: activeSocietyPair.society.address,
        city: activeSocietyPair.society.city,
        totalFlats: activeSocietyPair.society.total_flats || 100,
        inviteCode: activeSocietyPair.society.invite_code,
        activeRoundId: currentActiveRound?.id || '',
      };
    }
    return {
      id: '',
      name: '',
      locality: '',
      city: '',
      totalFlats: 0,
      inviteCode: '',
      activeRoundId: '',
    };
  }, [activeSocietyPair, currentActiveRound?.id]);

  const switchRole = (newRole: UserRole) => {
    setCurrentRole(newRole);
  };

  // Map real backend active round to the OrderRound interface
  const activeRound: OrderRound = useMemo(() => {
    if (currentActiveRound) {
      const deadlineDate = new Date(currentActiveRound.deadline_at);
      const deadlineFormatted =
        deadlineDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
        ' on ' +
        deadlineDate.toLocaleDateString([], { day: 'numeric', month: 'short' });

      return {
        id: currentActiveRound.id,
        roundNumber: currentActiveRound.round_number,
        title: currentActiveRound.title,
        status: currentActiveRound.status === 'open' ? 'open' : 'closed',
        deadlineText: deadlineFormatted,
        shopVisitDate: currentActiveRound.shopping_date,
        volunteerName: 'Society Volunteer',
        volunteerFlat: 'Volunteer Desk',
        participatingFlatsCount: currentActiveRound.submissions_count || 0,
        totalItemsCount: currentActiveRound.submissions_count || 0,
        estimatedTotalValue: 0,
      };
    }
    return {
      id: '',
      roundNumber: 0,
      title: 'No Active Grocery Round',
      status: 'closed',
      deadlineText: 'Ordering Closed',
      shopVisitDate: 'Pending Next Round',
      volunteerName: 'Society Volunteer',
      volunteerFlat: 'Volunteer Desk',
      participatingFlatsCount: 0,
      totalItemsCount: 0,
      estimatedTotalValue: 0,
    };
  }, [currentActiveRound]);

  const createRound = async (data: {
    title: string;
    description?: string;
    deadline_at: string;
    shopping_date: string;
  }) => {
    if (!activeSocietyPair?.society.id) return { success: false, error: 'No active society selected' };
    try {
      const res = await api.rounds.create(activeSocietyPair.society.id, data);
      return { success: true, round: res };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to create round' };
    }
  };

  const openRound = async (roundId: string) => {
    if (!activeSocietyPair?.society.id) return { success: false, error: 'No active society selected' };
    try {
      const res = await api.rounds.open(activeSocietyPair.society.id, roundId);
      await refreshActiveRound();
      return { success: true, round: res };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to open round' };
    }
  };

  const closeRound = async (roundId: string) => {
    if (!activeSocietyPair?.society.id) return { success: false, error: 'No active society selected' };
    try {
      const res = await api.rounds.close(activeSocietyPair.society.id, roundId);
      await refreshActiveRound();
      return { success: true, round: res };
    } catch (err: any) {
      return { success: false, error: err.message || 'Failed to close round' };
    }
  };

  const closeActiveRound = async () => {
    if (currentActiveRound) {
      await closeRound(currentActiveRound.id);
    }
  };

  const toggleItemPurchased = (itemId: string) => {
    setGroceryItems((prev) =>
      prev.map((item) =>
        item.id === itemId ? { ...item, isPurchased: !item.isPurchased } : item
      )
    );
  };

  const sendChatMessage = (text: string) => {
    if (!text.trim()) return;

    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      senderId: currentUser.id,
      senderName: currentUser.name,
      senderRole: currentUser.role,
      senderFlat: currentUser.flatNumber,
      avatarUrl: currentUser.avatarUrl,
      timestamp: timeString,
      text: text.trim(),
    };

    setChatMessages((prev) => [...prev, newMsg]);

    // Simulated assistant feedback for demonstration
    if (
      currentUser.role === 'resident' &&
      (text.toLowerCase().includes('kg') ||
        text.toLowerCase().includes('litre') ||
        text.toLowerCase().includes('packet'))
    ) {
      setTimeout(() => {
        const botMsg: ChatMessage = {
          id: `bot_${Date.now()}`,
          senderId: 'bot_assistant',
          senderName: 'Society Cart AI',
          senderRole: 'bot',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: `Extracted order for Flat ${currentUser.flatNumber}: Items noted for volunteer consolidation.`,
          isBotInterpretation: true,
          structuredItems: [
            { name: 'Parsed Request', quantity: text.trim().slice(0, 32) + '...' },
          ],
        };
        setChatMessages((prev) => [...prev, botMsg]);
      }, 700);
    }
  };

  const markNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const unreadNotificationsCount = useMemo(() => {
    return notifications.filter((n) => !n.read).length;
  }, [notifications]);

  return (
    <AppContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoadingSession,
        login,
        register,
        logout,
        refreshSession,
        userSocieties,
        activeSocietyPair,
        setActiveSocietyId,
        createSociety,
        joinSociety,
        currentUser,
        currentRole,
        switchRole,
        society,
        currentActiveRound,
        isLoadingActiveRound,
        refreshActiveRound,
        createRound,
        openRound,
        closeRound,
        activeRound,
        pastRounds: mockPastRounds,
        closeActiveRound,
        groceryItems,
        toggleItemPurchased,
        chatMessages,
        sendChatMessage,
        residentBill: mockResidentBill,
        notifications,
        markNotificationsRead,
        unreadNotificationsCount,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
