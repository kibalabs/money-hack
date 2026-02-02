import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, PaddingSize, Stack, Text } from '@kibalabs/ui-react';
import { useToastManager } from '@kibalabs/ui-react-toast';

import { useAuth } from '../AuthContext';
import { MarketData, Position } from '../client/resources';
import { PositionDashboard } from '../components/PositionDashboard';
import { useGlobals } from '../GlobalsContext';

export function AgentPage(): React.ReactElement {
  const { accountAddress, authToken, isWeb3AccountLoggedIn, logout } = useAuth();
  const { moneyHackClient } = useGlobals();
  const navigator = useNavigator();
  const toastManager = useToastManager();

  const [position, setPosition] = React.useState<Position | null>(null);
  const [marketData, setMarketData] = React.useState<MarketData | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = React.useState<boolean>(false);

  const loadData = React.useCallback(async (showLoading: boolean = true): Promise<void> => {
    if (!accountAddress || !authToken) return;

    if (showLoading) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }

    try {
      const [fetchedPosition, fetchedMarketData] = await Promise.all([
        moneyHackClient.getPosition(accountAddress, authToken),
        moneyHackClient.getMarketData(),
      ]);

      if (!fetchedPosition) {
        navigator.navigateTo('/setup');
        return;
      }

      setPosition(fetchedPosition);
      setMarketData(fetchedMarketData);
    } catch (error) {
      console.error('Failed to load position:', error);
      toastManager.showTextToast('Failed to load position data', 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [accountAddress, authToken, moneyHackClient, navigator, toastManager]);

  React.useEffect(() => {
    if (!isWeb3AccountLoggedIn) {
      navigator.navigateTo('/');
      return;
    }

    loadData();
  }, [isWeb3AccountLoggedIn, loadData, navigator]);

  const handleRefreshClicked = React.useCallback((): void => {
    loadData(false);
  }, [loadData]);

  const handleWithdrawClicked = React.useCallback((): void => {
    toastManager.showTextToast('Withdraw functionality coming soon', 'info');
  }, [toastManager]);

  const handleClosePositionClicked = React.useCallback((): void => {
    toastManager.showTextToast('Close position functionality coming soon', 'info');
  }, [toastManager]);

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
        onRefreshClicked={handleRefreshClicked}
        onWithdrawClicked={handleWithdrawClicked}
        onClosePositionClicked={handleClosePositionClicked}
        isRefreshing={isRefreshing}
      />

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
    </Stack>
  );
}
