import React from 'react';

import { Alignment, Button, Direction, PaddingSize, Stack, Text } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';

export function AgentPage(): React.ReactElement {
  const { accountAddress, logout } = useAuth();

  return (
    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide} paddingVertical={PaddingSize.Wide2}>
      <Text variant='header2'>Wallet Connected!</Text>
      <Text>
        Connected wallet:
        {accountAddress}
      </Text>
      <Button text='Disconnect' variant='secondary' onClicked={logout} />
    </Stack>
  );
}
