/**
 * Nexconn Web SDK client managing real-time connection lifecycle,
 * channel messaging, and message history for Society Cart.
 */

import {
  NCEngine,
  ConnectionStatusHandler,
  MessageHandler,
  GroupChannel,
  BaseChannel,
  GroupChannelIdentifier,
  SendTextMessageParams,
  AreaCode,
  ConnectionStatus,
  Message,
} from '@nexconn/chat';
import { NexconnConnectionState, NexconnChatMessage } from './nexconnTypes';

type ConnectionStateListener = (state: NexconnConnectionState) => void;
type MessageListener = (message: NexconnChatMessage) => void;

class NexconnClientService {
  private isInitialized = false;
  private currentUserId = '';
  private activeGroupId = '';
  private activeToken = '';
  private connectionState: NexconnConnectionState = 'disconnected';

  private stateListeners = new Set<ConnectionStateListener>();
  private messageListeners = new Set<MessageListener>();

  /**
   * Initializes the Nexconn SDK once during the application lifecycle.
   */
  public initialize(appKey: string): void {
    if (this.isInitialized) return;

    try {
      NCEngine.initialize({
        appKey,
        areaCode: AreaCode.SG,
      });

      // Register connection status handler
      NCEngine.addConnectionStatusHandler(
        'society_cart_connection',
        new ConnectionStatusHandler({
          onConnectionStatusChanged: ({ status }) => {
            let mappedState: NexconnConnectionState = 'disconnected';
            switch (status) {
              case ConnectionStatus.CONNECTED:
                mappedState = 'connected';
                break;
              case ConnectionStatus.CONNECTING:
                mappedState = 'connecting';
                break;
              case ConnectionStatus.DISCONNECTED:
                mappedState = 'disconnected';
                break;
              default:
                mappedState = 'reconnecting';
                break;
            }
            this.setConnectionState(mappedState);
          },
        })
      );

      // Register incoming message event handler
      NCEngine.addMessageHandler(
        'society_cart_messages',
        new MessageHandler({
          onMessageReceived: ({ messages }) => {
            if (!messages || messages.length === 0) return;

            for (const rawMsg of messages) {
              const parsed = this.parseRawMessage(rawMsg);
              if (parsed) {
                this.messageListeners.forEach((listener) => listener(parsed));
              }
            }
          },
        })
      );

      this.isInitialized = true;
    } catch (err) {
      console.error('[NexconnClient] Initialization error:', err);
      this.setConnectionState('error');
    }
  }

  /**
   * Connects the authenticated user to the Nexconn network with their server-issued token.
   */
  public async connect(token: string, userId: string, groupId: string): Promise<boolean> {
    if (!token) return false;

    // Avoid reconnecting if already connected with the same session
    if (this.connectionState === 'connected' && this.activeToken === token && this.activeGroupId === groupId) {
      return true;
    }

    this.currentUserId = userId;
    this.activeGroupId = groupId;
    this.activeToken = token;
    this.setConnectionState('connecting');

    try {
      const result = await NCEngine.connect({ token });
      if (result && result.isOk) {
        this.setConnectionState('connected');
        return true;
      }

      console.warn('[NexconnClient] Connect returned non-ok result:', result);
      this.setConnectionState('error');
      return false;
    } catch (err) {
      console.error('[NexconnClient] Failed to connect:', err);
      this.setConnectionState('error');
      return false;
    }
  }

  /**
   * Disconnects the user and cleans up the active session.
   */
  public async disconnect(): Promise<void> {
    if (this.connectionState === 'disconnected') return;

    try {
      await NCEngine.disconnect();
    } catch (err) {
      console.warn('[NexconnClient] Disconnect warning:', err);
    } finally {
      this.currentUserId = '';
      this.activeGroupId = '';
      this.activeToken = '';
      this.setConnectionState('disconnected');
    }
  }

  /**
   * Sends a text message to the society's group channel.
   */
  public async sendMessage(
    groupId: string,
    text: string,
    senderProfile?: { name: string; flatNumber: string; role?: string }
  ): Promise<NexconnChatMessage> {
    if (!text.trim()) {
      throw new Error('Message text cannot be empty');
    }

    const group = new GroupChannel(groupId);
    const params = new SendTextMessageParams({ text: text.trim() });

    const result = await group.sendMessage(params);

    if (!result || !result.isOk || !result.data) {
      const errMsg = (result as any)?.error?.message || 'Failed to send message to Nexconn channel';
      throw new Error(errMsg);
    }

    const sentMessage = result.data;
    const timeString = new Date(sentMessage.sentTime || Date.now()).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    return {
      id: sentMessage.messageId || `msg_${Date.now()}`,
      senderId: this.currentUserId,
      senderName: senderProfile?.name || 'You',
      senderFlat: senderProfile?.flatNumber,
      senderRole: (senderProfile?.role as any) || 'resident',
      timestamp: timeString,
      sentTime: sentMessage.sentTime || Date.now(),
      text: text.trim(),
      isSelf: true,
      isSystemBot: false,
    };
  }

  /**
   * Loads recent message history from the Nexconn group channel.
   */
  public async fetchMessageHistory(
    groupId: string,
    pageSize = 40,
    memberLookup?: Record<string, { name: string; flatNumber: string; role?: string }>
  ): Promise<NexconnChatMessage[]> {
    try {
      const query = BaseChannel.createMessagesQuery({
        channelIdentifier: new GroupChannelIdentifier(groupId),
        pageSize,
      });

      const result = await query.loadNextPage();

      if (!result || !result.isOk || !result.data) {
        return [];
      }

      const rawList: Array<Message<any>> = result.data.data || [];
      const parsedList: NexconnChatMessage[] = [];

      for (const m of rawList) {
        const parsed = this.parseRawMessage(m, memberLookup);
        if (parsed) {
          parsedList.push(parsed);
        }
      }

      // Sort chronologically ascending
      return parsedList.sort((a, b) => a.sentTime - b.sentTime);
    } catch (err) {
      console.warn('[NexconnClient] Could not fetch channel history:', err);
      return [];
    }
  }

  /**
   * Subscribe to connection status changes.
   */
  public onConnectionStateChange(listener: ConnectionStateListener): () => void {
    this.stateListeners.add(listener);
    listener(this.connectionState);
    return () => this.stateListeners.delete(listener);
  }

  /**
   * Subscribe to real-time incoming messages.
   */
  public onMessage(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  public getConnectionState(): NexconnConnectionState {
    return this.connectionState;
  }

  private setConnectionState(newState: NexconnConnectionState) {
    if (this.connectionState === newState) return;
    this.connectionState = newState;
    this.stateListeners.forEach((listener) => listener(newState));
  }

  /**
   * Formats a raw Nexconn Message into Society Cart's message shape.
   */
  private parseRawMessage(
    raw: Message<any>,
    memberLookup?: Record<string, { name: string; flatNumber: string; role?: string }>
  ): NexconnChatMessage | null {
    if (!raw) return null;

    const senderId = raw.senderUserId || '';
    const isSelf = senderId === this.currentUserId;
    const isBot = senderId === 'society_cart_bot';

    const contentText =
      raw.content?.text ||
      raw.content?.content ||
      (typeof raw.content === 'string' ? raw.content : '');

    if (!contentText && !isBot) return null;

    const member = memberLookup ? memberLookup[senderId] : undefined;

    const sentTime = raw.sentTime || Date.now();
    const timeString = new Date(sentTime).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    return {
      id: raw.messageId || `msg_${sentTime}_${Math.random()}`,
      senderId,
      senderName: isBot
        ? 'Society Cart Assistant'
        : isSelf
        ? 'You'
        : member?.name || `Resident (${senderId.slice(-4)})`,
      senderFlat: member?.flatNumber,
      senderRole: isBot ? 'bot' : (member?.role as any) || 'resident',
      timestamp: timeString,
      sentTime,
      text: contentText,
      isSelf,
      isSystemBot: isBot,
    };
  }
}

export const nexconnClient = new NexconnClientService();
