import React from 'react';

import { dateToString } from '@kibalabs/core';
import { Box, Text } from '@kibalabs/ui-react';

import { Agent, AgentAction } from '../client/resources';

import './AgentTerminal.scss';

const ACTIVITY_WORDS = [
  'thinking',
  'strategizing',
  'analyzing',
  'observing markets',
  'calculating yields',
  'evaluating risks',
  'monitoring vaults',
  'researching opportunities',
  'optimizing positions',
  'studying protocols',
  'comparing rates',
  'investigating strategies',
  'scanning markets',
  'contemplating moves',
  'weighing options',
  'deliberating',
  'processing data',
  'crunching numbers',
  'exploring vaults',
  'analyzing trends',
];

function useAnimatedActivity(): string {
  const [displayText, setDisplayText] = React.useState('');
  const [currentWordIndex, setCurrentWordIndex] = React.useState(0);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [charIndex, setCharIndex] = React.useState(0);

  React.useEffect(() => {
    const currentWord = ACTIVITY_WORDS[currentWordIndex];
    const fullText = `${currentWord}...`; // Include dots in the animated text
    const typingSpeed = isDeleting ? 50 : 100;
    const pauseDuration = 2500; // Pause for 2.5 seconds before deleting

    const timer = setTimeout(() => {
      if (!isDeleting && charIndex < fullText.length) {
        // Typing forward
        setDisplayText(fullText.substring(0, charIndex + 1));
        setCharIndex(charIndex + 1);
      } else if (!isDeleting && charIndex === fullText.length) {
        // Pause, then start deleting
        setTimeout(() => setIsDeleting(true), pauseDuration);
      } else if (isDeleting && charIndex > 0) {
        // Deleting backward
        setDisplayText(fullText.substring(0, charIndex - 1));
        setCharIndex(charIndex - 1);
      } else if (isDeleting && charIndex === 0) {
        // Move to next word
        setIsDeleting(false);
        setCurrentWordIndex((currentWordIndex + 1) % ACTIVITY_WORDS.length);
      }
    }, typingSpeed);

    return () => clearTimeout(timer);
  }, [charIndex, isDeleting, currentWordIndex]);

  return displayText;
}

interface AgentTerminalProps {
  agent: Agent | null;
  actions: AgentAction[];
  isLoading: boolean;
}

export function AgentTerminal(props: AgentTerminalProps): React.ReactElement {
  const terminalEndRef = React.useRef<HTMLDivElement>(null);
  const [displayedActions, setDisplayedActions] = React.useState<AgentAction[]>([]);
  const [newActionIds, setNewActionIds] = React.useState<Set<number>>(new Set());
  const animatedActivity = useAnimatedActivity();

  // Merge incoming actions with displayed actions, preserving existing ones
  React.useEffect(() => {
    if (props.actions.length === 0) return;

    const existingIds = new Set(displayedActions.map((action) => action.actionId));

    // Find actions that are new
    const newActions = props.actions.filter((action) => !existingIds.has(action.actionId));

    if (newActions.length === 0) return; // No new actions, nothing to do

    // Mark new actions for animation (only if we've already loaded initially)
    if (displayedActions.length > 0) {
      setNewActionIds(new Set(newActions.map((action) => action.actionId)));
      // Clear animation markers after animation completes
      setTimeout(() => setNewActionIds(new Set()), 1000);
    }

    // Sort all actions by date (oldest first) and update displayed list
    const allActions = [...displayedActions, ...newActions].sort(
      (a, b) => a.createdDate.getTime() - b.createdDate.getTime(),
    );
    setDisplayedActions(allActions);
  }, [props.actions, displayedActions]);

  React.useEffect(() => {
    // Auto-scroll to bottom when new actions arrive
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [displayedActions]);

  const formatActionContent = (action: AgentAction): string => {
    // Construct message from details object
    if (action.details.message) {
      return String(action.details.message);
    }
    if (action.value) {
      return action.value;
    }
    return JSON.stringify(action.details);
  };

  const isNewAction = (actionId: number): boolean => {
    return newActionIds.has(actionId);
  };

  return (
    <Box className='agent-terminal-container'>
      <Box style={{ padding: '16px' }}>
        {!props.agent && (
          <div className='agent-terminal-line'>
            <Text>No agent active</Text>
          </div>
        )}

        {displayedActions.map((action: AgentAction) => (
          <div key={action.actionId} className={`agent-terminal-line ${isNewAction(action.actionId) ? 'typing' : ''}`}>
            <span className='agent-terminal-timestamp'>{dateToString(action.createdDate, 'HH:mm:ss')}</span>
            <span className={`agent-terminal-action-type ${action.actionType}`}>
              [
              {action.actionType.toUpperCase()}
              ]
            </span>
            <span>{formatActionContent(action)}</span>
          </div>
        ))}

        {props.agent && newActionIds.size === 0 && !props.isLoading && (
          <div className='agent-terminal-line'>
            <span>
              {props.agent.name}
              {' '}
              is
              {' '}
              {animatedActivity}
            </span>
          </div>
        )}

        {/* {newActionIds.size === 0 && !props.isLoading && (
          <div className='agent-terminal-line'>
            <span className='agent-terminal-cursor' />
          </div>
        )} */}
        <div ref={terminalEndRef} />
      </Box>
    </Box>
  );
}
