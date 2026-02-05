import React from 'react';

import { Alignment, Box, Button, Direction, IconButton, InputType, KibaIcon, Markdown, SingleLineInput, Stack, Text } from '@kibalabs/ui-react';

import { Agent, ChatMessage } from '../client/resources';

import './FloatingChat.scss';

const SUGGESTED_PROMPTS = [
  "What's my current position?",
  "What's my health factor?",
  'What are the current rates?',
  'Why did you take that action?',
];

interface IFloatingChatProps {
  agent: Agent;
  onSendMessage: (message: string) => Promise<ChatMessage[]>;
  onLoadHistory: () => Promise<ChatMessage[]>;
}

export function FloatingChat(props: IFloatingChatProps): React.ReactElement {
  const { agent, onSendMessage, onLoadHistory } = props;
  const [isOpen, setIsOpen] = React.useState(false);
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [hasLoadedHistory, setHasLoadedHistory] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = React.useCallback((): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  React.useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  React.useEffect(() => {
    if (isOpen && !hasLoadedHistory) {
      setHasLoadedHistory(true);
      onLoadHistory().then((history) => {
        setMessages(history);
      }).catch(console.error);
    }
  }, [isOpen, hasLoadedHistory, onLoadHistory]);

  const handleSendMessage = React.useCallback(async (messageText: string): Promise<void> => {
    if (!messageText.trim() || isLoading) return;
    const userMessage = new ChatMessage(
      Date.now(),
      new Date(),
      true,
      messageText,
    );
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    try {
      const newMessages = await onSendMessage(messageText);
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.messageId !== userMessage.messageId);
        return [...withoutTemp, ...newMessages];
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = new ChatMessage(
        Date.now() + 1,
        new Date(),
        false,
        'Sorry, I encountered an error. Please try again.',
      );
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, onSendMessage]);

  const handleKeyDown = React.useCallback((key: string): void => {
    if (key === 'Enter') {
      handleSendMessage(inputValue);
    }
  }, [handleSendMessage, inputValue]);

  const handlePromptClick = React.useCallback((prompt: string): void => {
    handleSendMessage(prompt);
  }, [handleSendMessage]);

  return (
    <div className='floating-chat'>
      {isOpen && (
        <div className='chat-window'>
          <div className='chat-header'>
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
              <Text variant='bold'>{agent.emoji}</Text>
              <Text variant='bold'>{agent.name}</Text>
            </Stack>
            <IconButton
              icon={<KibaIcon iconId='ion-close' />}
              onClicked={(): void => setIsOpen(false)}
            />
          </div>

          <div className='messages-container'>
            {messages.length === 0 && !isLoading && (
              <Box key='initial' className='message-bubble agent'>
                <Text>Hi! I&apos;m your BorrowBot assistant. Ask me about your position, rates, or any actions I&apos;ve taken.</Text>
              </Box>
            )}
            {messages.map((message: ChatMessage): React.ReactElement => (
              <Box key={message.messageId} className={`message-bubble ${message.isUser ? 'user' : 'agent'}`}>
                <Markdown shouldForceBlock={true} shouldForceWrapper={true} source={message.content} />
              </Box>
            ))}
            {isLoading && (
              <Box className='message-bubble agent' isFullWidth={false}>
                <Box className='typing-indicator' isFullWidth={false}>
                  <span />
                  <span />
                  <span />
                </Box>
              </Box>
            )}
            <div ref={messagesEndRef} />
          </div>
          {messages.length === 0 && !isLoading && (
            <div className='suggested-prompts'>
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type='button'
                  className='prompt-chip'
                  onClick={(): void => handlePromptClick(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}
          <div className='input-container'>
            <Box shouldClipContent={false} isFullWidth={true}>
              <SingleLineInput
                inputType={InputType.Text}
                value={inputValue}
                onValueChanged={setInputValue}
                onKeyDown={handleKeyDown}
                placeholderText='Ask your agent...'
                isEnabled={!isLoading}
              />
            </Box>
            <Button
              text='Send'
              variant='primary'
              onClicked={(): void => { handleSendMessage(inputValue); }}
              isEnabled={!isLoading && inputValue.trim().length > 0}
            />
          </div>
        </div>
      )}

      <button
        type='button'
        className='chat-bubble'
        onClick={(): void => setIsOpen(!isOpen)}
      >
        {isOpen ? '✕' : agent.emoji}
      </button>
    </div>
  );
}
