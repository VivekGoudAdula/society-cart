import React, { createContext, useContext, useState, useMemo } from 'react';
import {
  UserProfile,
  UserRole,
  Society,
  OrderRound,
  GroceryItem,
  ChatMessage,
  ResidentBill,
  ActivityNotification,
} from '../types';
import {
  mockSociety,
  mockResidentUser,
  mockVolunteerUser,
  mockActiveRound,
  mockPastRounds,
  mockGroceryItems,
  mockChatMessages,
  mockResidentBill,
  mockNotifications,
} from '../data/mockData';

interface AppContextType {
  currentUser: UserProfile;
  currentRole: UserRole;
  switchRole: (role: UserRole) => void;
  society: Society;
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
 * Global application state provider for Phase 1 demo mode.
 * Allows seamless switching between Resident and Volunteer roles.
 */
export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRole, setCurrentRole] = useState<UserRole>('resident');
  const [activeRound, setActiveRound] = useState<OrderRound>(mockActiveRound);
  const [groceryItems, setGroceryItems] = useState<GroceryItem[]>(mockGroceryItems);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(mockChatMessages);
  const [notifications, setNotifications] = useState<ActivityNotification[]>(mockNotifications);

  // Set user profile based on active role
  const currentUser = useMemo(() => {
    return currentRole === 'resident' ? mockResidentUser : mockVolunteerUser;
  }, [currentRole]);

  const switchRole = (newRole: UserRole) => {
    setCurrentRole(newRole);
  };

  const closeActiveRound = () => {
    setActiveRound((prev) => ({
      ...prev,
      status: 'closed',
      deadlineText: 'Closed Today',
    }));
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

    // If a resident submitted an order message, simulate an AI bot confirmation response after a short delay
    if (currentUser.role === 'resident' && text.toLowerCase().includes('kg') || text.toLowerCase().includes('litre') || text.toLowerCase().includes('packet')) {
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
        currentUser,
        currentRole,
        switchRole,
        society: mockSociety,
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
