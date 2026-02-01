import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Button, Direction, PaddingSize, Stack, Text } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';
import { useGlobals } from '../GlobalsContext';

export function AgentPage(): React.ReactElement {
  const { accountAddress, authToken, isWeb3AccountLoggedIn, logout } = useAuth();
  const { moneyHackClient } = useGlobals();
  const navigator = useNavigator();
  const [hasPosition, setHasPosition] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    if (!isWeb3AccountLoggedIn) {
      navigator.navigateTo('/');
      return;
    }

    const checkPosition = async (): Promise<void> => {
      if (!accountAddress || !authToken) return;
      try {
        const position = await moneyHackClient.getPosition(accountAddress, authToken);
        if (!position) {
          navigator.navigateTo('/setup');
        } else {
          setHasPosition(true);
        }
      } catch (error) {
        console.error('Failed to check position:', error);
        navigator.navigateTo('/setup');
      }
    };
    checkPosition();
  }, [accountAddress, authToken, isWeb3AccountLoggedIn, moneyHackClient, navigator]);

  if (!isWeb3AccountLoggedIn || hasPosition === null) {
    return (
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true}>
        <Text>Loading...</Text>
      </Stack>
    );
  }

  return (
    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide} paddingVertical={PaddingSize.Wide2}>
      <Text variant='header2'>Dashboard</Text>
      <Text>
        Connected wallet:
        {' '}
        {accountAddress}
      </Text>
      <Text variant='note'>Position details coming soon...</Text>
      <Button text='Disconnect' variant='secondary' onClicked={logout} />
    </Stack>
  );
}
