import React from 'react';

import { ISingleAnyChildProps, useLocation, useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Direction, Stack } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';

interface IContainingViewProps extends ISingleAnyChildProps {
  className?: string;
}

export function ContainingView(props: IContainingViewProps): React.ReactElement {
  const location = useLocation();
  const navigator = useNavigator();
  const { isWeb3AccountConnecting, isWeb3AccountLoggedIn } = useAuth();

  React.useEffect((): void => {
    if (isWeb3AccountLoggedIn && location.pathname === '/') {
      navigator.navigateTo('/agents');
    }
    if (!isWeb3AccountConnecting && !isWeb3AccountLoggedIn && (location.pathname === '/agent' || location.pathname === '/agents')) {
      navigator.navigateTo('/');
    }
  }, [isWeb3AccountConnecting, isWeb3AccountLoggedIn, location.pathname, navigator]);

  // Show loading while checking connection status
  if (isWeb3AccountConnecting) {
    return (
      <Box className={props.className} variant='blank' isScrollableVertically={true} isFullWidth={true} isFullHeight={true}>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true}>
          <div>Loading...</div>
        </Stack>
      </Box>
    );
  }

  return (
    <Box className={props.className} variant='blank' isScrollableVertically={true} isFullWidth={true}>{props.children}</Box>
  );
}
