import { useContext } from 'react';
import { ChatContext, ChatContextType } from '../context/ChatContext';

/**
 * Hook to access Nexconn society chat state and actions.
 */
export const useChat = (): ChatContextType => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

export default useChat;
