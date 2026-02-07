import React from 'react';

import { Alignment, Box, Direction, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';

import { CrossChainAction } from '../client/resources';

const CHAIN_NAMES: Record<number, string> = {
  1: 'Ethereum',
  8453: 'Base',
  42161: 'Arbitrum',
  10: 'Optimism',
  137: 'Polygon',
};

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b',
  in_flight: '#3b82f6',
  completed: '#10b981',
  failed: '#ef4444',
};

interface CrossChainPanelProps {
  actions: CrossChainAction[];
  isLoading: boolean;
}

export function CrossChainPanel({ actions, isLoading }: CrossChainPanelProps): React.ReactElement {
  if (isLoading) {
    return (
      <Box className='statCard' maxWidth='600px' isFullWidth={true}>
        <Text variant='note'>Loading cross-chain activity...</Text>
      </Box>
    );
  }

  if (actions.length === 0) {
    return (
      <Box className='statCard' maxWidth='600px' isFullWidth={true}>
        <Stack direction={Direction.Vertical} shouldAddGutters={true}>
          <Text variant='bold'>Cross-Chain (LI.FI)</Text>
          <Text variant='note'>No cross-chain activity yet. Deposit from any chain or withdraw to any chain using LI.FI.</Text>
        </Stack>
      </Box>
    );
  }

  return (
    <Box className='statCard' maxWidth='600px' isFullWidth={true}>
      <Stack direction={Direction.Vertical} shouldAddGutters={true}>
        <Text variant='bold'>Cross-Chain (LI.FI)</Text>
        {actions.slice(0, 5).map((action) => {
          const amountUsd = Number(action.amount) / 1e6;
          const fromChainName = CHAIN_NAMES[action.fromChain] || `Chain ${action.fromChain}`;
          const toChainName = CHAIN_NAMES[action.toChain] || `Chain ${action.toChain}`;
          const statusColor = STATUS_COLORS[action.status] || '#6b7280';
          const isDeposit = action.actionType === 'deposit';
          return (
            <Box key={action.actionId}>
              <Stack direction={Direction.Vertical} shouldAddGutters={true}>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
                  <Text variant='note-bold'>
                    {isDeposit ? 'Deposit' : 'Withdraw'}
                  </Text>
                  <Stack.Item growthFactor={1} shrinkFactor={1} />
                  <Text variant='note' style={{ color: statusColor, fontWeight: 600 }}>
                    {action.status.toUpperCase()}
                  </Text>
                </Stack>
                <Stack direction={Direction.Horizontal} shouldAddGutters={true}>
                  <Text variant='note'>
                    {`$${amountUsd.toFixed(2)} USDC`}
                  </Text>
                  <Text variant='note'>•</Text>
                  <Text variant='note'>
                    {`${fromChainName} → ${toChainName}`}
                  </Text>
                  {action.bridgeName && (
                    <React.Fragment>
                      <Text variant='note'>•</Text>
                      <Text variant='note'>{`via ${action.bridgeName}`}</Text>
                    </React.Fragment>
                  )}
                </Stack>
                {action.txHash && (
                  <Text variant='note' style={{ fontSize: '11px', opacity: 0.6 }}>
                    {`tx: ${action.txHash.slice(0, 10)}...${action.txHash.slice(-6)}`}
                  </Text>
                )}
              </Stack>
              <Spacing variant={PaddingSize.Narrow} />
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}
