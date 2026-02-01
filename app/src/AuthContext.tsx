import React from 'react';

import { IMultiAnyChildProps } from '@kibalabs/core-react';
import { useIsRestoringWeb3Session, useWeb3Account, useWeb3ChainId, useWeb3LoginSignature } from '@kibalabs/web3-react';

interface AuthContextType {
  isWeb3AccountConnecting: boolean;
  isWeb3AccountConnected: boolean;
  isWeb3AccountLoggedIn: boolean;
  accountAddress: string | undefined;
  chainId: number;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps extends IMultiAnyChildProps {
}

export function AuthProvider(props: AuthProviderProps): React.ReactElement {
  const account = useWeb3Account();
  const loginSignature = useWeb3LoginSignature();
  const chainId = useWeb3ChainId();
  const isRestoringWeb3Session = useIsRestoringWeb3Session();
  const accountAddress = account?.address;

  // isWeb3AccountConnecting is true while web3-react is still initializing OR restoring a previous session
  // Note: loginSignature is null (not undefined) when not logged in, so we check for both
  const isWeb3AccountConnecting = account === undefined || isRestoringWeb3Session;
  const isWeb3AccountConnected = account != null;
  const isWeb3AccountLoggedIn = account != null && loginSignature != null;

  const logout = React.useCallback((): void => {
    if (typeof window !== 'undefined') {
      localStorage.clear();
      sessionStorage.clear();
    }
    window.location.reload();
  }, []);

  const contextValue = React.useMemo(() => ({
    isWeb3AccountConnecting,
    isWeb3AccountConnected,
    isWeb3AccountLoggedIn,
    accountAddress,
    chainId: chainId || 8453,
    logout,
  }), [
    isWeb3AccountConnecting,
    isWeb3AccountConnected,
    isWeb3AccountLoggedIn,
    accountAddress,
    chainId,
    logout,
  ]);

  return (
    <AuthContext.Provider value={contextValue}>
      {props.children}
    </AuthContext.Provider>
  );
}

export const useAuth = (): AuthContextType => {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
