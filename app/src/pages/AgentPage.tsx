import React from 'react';

import { useLocalStorageState, useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';
import { useToastManager } from '@kibalabs/ui-react-toast';

import { useAuth } from '../AuthContext';
import { Agent, AgentAction, ChatMessage, CrossChainAction, EnsConstitution, MarketData, Position, Wallet } from '../client/resources';
import { AgentTerminal } from '../components/AgentTerminal';
import { CrossChainPanel } from '../components/CrossChainPanel';
import { DepositDialog } from '../components/DepositDialog';
import { DepositUsdcDialog } from '../components/DepositUsdcDialog';
import { FloatingChat } from '../components/FloatingChat';
import { PositionDashboard } from '../components/PositionDashboard';
import { WithdrawDialog } from '../components/WithdrawDialog';
import { useGlobals } from '../GlobalsContext';

export function AgentPage(): React.ReactElement {
  const { accountAddress, authToken, isWeb3AccountLoggedIn, logout } = useAuth();
  const { moneyHackClient, localStorageClient } = useGlobals();
  const navigator = useNavigator();
  const toastManager = useToastManager();

  const [position, setPosition] = React.useState<Position | null>(null);
  const [marketData, setMarketData] = React.useState<MarketData | null>(null);
  const [agent, setAgent] = React.useState<Agent | null>(null);
  const [wallet, setWallet] = React.useState<Wallet | null>(null);
  const [agentActions, setAgentActions] = React.useState<AgentAction[]>([]);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [isLoadingActions, setIsLoadingActions] = React.useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = React.useState<boolean>(false);
  const [isWithdrawDialogOpen, setIsWithdrawDialogOpen] = React.useState<boolean>(false);
  const [isDepositDialogOpen, setIsDepositDialogOpen] = React.useState<boolean>(false);
  const [isDepositUsdcDialogOpen, setIsDepositUsdcDialogOpen] = React.useState<boolean>(false);
  const [constitution, setConstitution] = React.useState<EnsConstitution | null>(null);
  const [crossChainActions, setCrossChainActions] = React.useState<CrossChainAction[]>([]);
  const hasLoadedRef = React.useRef<boolean>(false);
  const [conversationId, setConversationId] = useLocalStorageState(`borrowbot-${accountAddress || 'default'}-conversationId`, localStorageClient);

  React.useEffect((): void => {
    if (!conversationId && accountAddress) {
      setConversationId(crypto.randomUUID());
    }
  }, [conversationId, setConversationId, accountAddress]);

  const loadData = React.useCallback(async (showLoading: boolean = true): Promise<void> => {
    if (!accountAddress || !authToken) return;
    if (showLoading) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }
    try {
      const [fetchedPosition, fetchedMarketData, fetchedAgent] = await Promise.all([
        moneyHackClient.getPosition(accountAddress, authToken),
        moneyHackClient.getMarketData(),
        moneyHackClient.getAgent(accountAddress, authToken),
      ]);
      if (!fetchedPosition) {
        navigator.navigateTo('/setup');
        return;
      }
      setPosition(fetchedPosition);
      setMarketData(fetchedMarketData);
      setAgent(fetchedAgent);
      // Fetch wallet balance for deposit functionality
      try {
        const fetchedWallet = await moneyHackClient.getWallet(accountAddress, authToken);
        setWallet(fetchedWallet);
      } catch (walletError) {
        console.error('Failed to load wallet:', walletError);
      }
      // Fetch ENS constitution
      try {
        const fetchedConstitution = await moneyHackClient.getEnsConstitution(accountAddress, authToken);
        setConstitution(fetchedConstitution);
      } catch (constitutionError) {
        console.error('Failed to load ENS constitution:', constitutionError);
      }
      // Fetch cross-chain actions
      try {
        const fetchedCrossChainActions = await moneyHackClient.getCrossChainActions(accountAddress, 10, authToken);
        setCrossChainActions(fetchedCrossChainActions);
      } catch (ccError) {
        console.error('Failed to load cross-chain actions:', ccError);
      }
    } catch (error) {
      console.error('Failed to load position:', error);
      toastManager.showTextToast('Failed to load position data', 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountAddress, authToken, moneyHackClient]);

  const loadAgentActions = React.useCallback(async (showLoading: boolean = true): Promise<void> => {
    if (!agent || !authToken) return;
    if (showLoading) {
      setIsLoadingActions(true);
    }
    try {
      const actions = await moneyHackClient.getAgentThoughts(agent.agentId, 100, 24, authToken);
      setAgentActions(actions);
    } catch (error) {
      console.error('Failed to load agent actions:', error);
    } finally {
      if (showLoading) {
        setIsLoadingActions(false);
      }
    }
  }, [agent, authToken, moneyHackClient]);

  React.useEffect(() => {
    if (!isWeb3AccountLoggedIn) {
      navigator.navigateTo('/');
      return;
    }
    if (hasLoadedRef.current) return;
    hasLoadedRef.current = true;
    loadData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isWeb3AccountLoggedIn]);

  // Load agent actions initially and poll every 10 seconds
  React.useEffect(() => {
    if (!agent) return undefined;
    loadAgentActions(true); // Show loading on initial load
    const intervalId = setInterval(() => {
      loadAgentActions(false); // Don't show loading on background polls
    }, 10000); // Poll every 10 seconds
    return (): void => {
      clearInterval(intervalId);
    };
  }, [agent, loadAgentActions]);

  const handleRefreshClicked = React.useCallback((): void => {
    loadData(false);
  }, [loadData]);

  const handleWithdrawClicked = React.useCallback((): void => {
    setIsWithdrawDialogOpen(true);
  }, []);

  const handleDepositClicked = React.useCallback((): void => {
    setIsDepositDialogOpen(true);
  }, []);

  const handleDepositUsdcClicked = React.useCallback((): void => {
    setIsDepositUsdcDialogOpen(true);
  }, []);

  const handleWithdrawConfirmed = React.useCallback(async (amount: bigint): Promise<void> => {
    if (!accountAddress || !authToken) return;
    try {
      await moneyHackClient.getWithdrawTransactions(accountAddress, amount, authToken);
      toastManager.showTextToast('Withdrawal submitted successfully', 'success');
      setIsWithdrawDialogOpen(false);
      loadData(false);
    } catch (error) {
      console.error('Withdrawal failed:', error);
      toastManager.showTextToast('Withdrawal failed. Please try again.', 'error');
      setIsWithdrawDialogOpen(false);
    }
  }, [accountAddress, authToken, moneyHackClient, toastManager, loadData]);

  const handleDepositSuccess = React.useCallback((): void => {
    setIsDepositDialogOpen(false);
    loadData(false);
  }, [loadData]);

  const handleDepositUsdcSuccess = React.useCallback((): void => {
    setIsDepositUsdcDialogOpen(false);
    loadData(false);
  }, [loadData]);

  const latestCriticalMessage = React.useMemo((): string | null => {
    const criticalAction = agentActions.find(
      (a) => a.actionType === 'notification'
        && (a.value === 'critical_ltv_warning' || a.value === 'insufficient_vault_warning'),
    );
    if (!criticalAction) return null;
    return (criticalAction.details as Record<string, unknown>)?.message as string ?? null;
  }, [agentActions]);

  const handleClosePositionClicked = React.useCallback((): void => {
    toastManager.showTextToast('Close position functionality coming soon', 'info');
  }, [toastManager]);

  const handleSendChatMessage = React.useCallback(async (message: string): Promise<ChatMessage[]> => {
    if (!accountAddress || !authToken || !agent || !conversationId) {
      throw new Error('Not authenticated');
    }
    const response = await moneyHackClient.sendChatMessage(
      accountAddress,
      agent.agentId,
      message,
      conversationId,
      authToken,
    );
    return response.messages;
  }, [accountAddress, authToken, agent, moneyHackClient, conversationId]);

  const handleLoadChatHistory = React.useCallback(async (): Promise<ChatMessage[]> => {
    if (!accountAddress || !authToken || !agent || !conversationId) {
      return [];
    }
    try {
      const response = await moneyHackClient.getChatHistory(
        accountAddress,
        agent.agentId,
        conversationId,
        50,
        authToken,
      );
      return response.messages;
    } catch (error) {
      console.error('Failed to load chat history:', error);
      return [];
    }
  }, [accountAddress, authToken, agent, moneyHackClient, conversationId]);

  if (!isWeb3AccountLoggedIn || isLoading) {
    return (
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true}>
        <Text>Loading...</Text>
      </Stack>
    );
  }

  if (!position) {
    return (
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} shouldAddGutters={true}>
        <Text>No position found</Text>
        <Button text='Set Up Position' variant='primary' onClicked={(): void => navigator.navigateTo('/setup')} />
      </Stack>
    );
  }

  return (
    <Stack
      direction={Direction.Vertical}
      childAlignment={Alignment.Center}
      contentAlignment={Alignment.Start}
      shouldAddGutters={true}
      paddingHorizontal={PaddingSize.Wide2}
      paddingVertical={PaddingSize.Wide2}
      isFullHeight={true}
    >
      <PositionDashboard
        position={position}
        marketData={marketData}
        agent={agent}
        onRefreshClicked={handleRefreshClicked}
        onDepositClicked={handleDepositClicked}
        onDepositUsdcClicked={handleDepositUsdcClicked}
        onWithdrawClicked={handleWithdrawClicked}
        onClosePositionClicked={handleClosePositionClicked}
        isRefreshing={isRefreshing}
        latestCriticalMessage={latestCriticalMessage}
      />

      {constitution && constitution.ensName && (
        <Box className='statCard' maxWidth='600px' isFullWidth={true}>
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
              <Text variant='bold'>ENS Constitution</Text>
              <Stack.Item growthFactor={1} shrinkFactor={1} />
              <Text variant='note'>{constitution.ensName}</Text>
            </Stack>
          </Stack>
        </Box>
      )}

      <CrossChainPanel
        actions={crossChainActions}
        isLoading={isLoading}
      />

      <Box maxWidth='600px' isFullWidth={true} style={{ marginTop: '32px' }}>
        <AgentTerminal
          agent={agent}
          actions={agentActions}
          isLoading={isLoadingActions}
        />
      </Box>

      <Spacing variant={PaddingSize.Wide2} />
      <Box maxWidth='600px' isFullWidth={true}>
        <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
          <Text variant='note'>
            Connected:
            {' '}
            {accountAddress?.slice(0, 6)}
            ...
            {accountAddress?.slice(-4)}
          </Text>
          <Button text='Disconnect' variant='tertiary-small' onClicked={logout} />
        </Stack>
      </Box>

      {isWithdrawDialogOpen && position && (
        <WithdrawDialog
          position={position}
          onCloseClicked={(): void => setIsWithdrawDialogOpen(false)}
          onWithdrawConfirmed={handleWithdrawConfirmed}
        />
      )}

      {isDepositDialogOpen && position && wallet && agent && (
        <DepositDialog
          position={position}
          agentWalletAddress={agent.walletAddress}
          availableBalance={wallet.assetBalances.find((b) => b.assetAddress.toLowerCase() === position.collateralAsset.address.toLowerCase())?.balance || 0n}
          onCloseClicked={(): void => setIsDepositDialogOpen(false)}
          onDepositSuccess={handleDepositSuccess}
        />
      )}

      {isDepositUsdcDialogOpen && position && wallet && agent && (
        <DepositUsdcDialog
          position={position}
          agentWalletAddress={agent.walletAddress}
          availableUsdcBalance={wallet.assetBalances.find((b) => b.assetAddress.toLowerCase() === '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913')?.balance || 0n}
          onCloseClicked={(): void => setIsDepositUsdcDialogOpen(false)}
          onDepositSuccess={handleDepositUsdcSuccess}
        />
      )}

      {agent && (
        <FloatingChat
          agent={agent}
          onSendMessage={handleSendChatMessage}
          onLoadHistory={handleLoadChatHistory}
        />
      )}
    </Stack>
  );
}
