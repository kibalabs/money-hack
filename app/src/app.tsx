import React from 'react';

import { LocalStorageClient, Requester } from '@kibalabs/core';
import { IRoute, MockStorage, Router, SubRouter, useFavicon, useInitialization } from '@kibalabs/core-react';
import { KibaApp } from '@kibalabs/ui-react';
import { ToastContainer, useToastManager } from '@kibalabs/ui-react-toast';
import { Web3AccountControlProvider, web3Initialize } from '@kibalabs/web3-react';

import './theme.scss';
import { AuthProvider } from './AuthContext';
import { MoneyHackClient } from './client/client';
import { ContainingView } from './components/ContainingView';
import { GlobalsProvider, IGlobals } from './GlobalsContext';
import { PageDataProvider } from './PageDataContext';
import { AgentPage, AccountPage, HomePage, SetupPage } from './pages';
import { getIsNextVersion, usePrefersDarkMode } from './util';

declare global {
  export interface Window {
    KRT_API_URL?: string;
    KRT_IS_NEXT?: string;
    KRT_IMPERSONATED_WALLET?: string;
  }
}

const requester = new Requester();
const apiRequester = new Requester();
const baseUrl = typeof window !== 'undefined' && window.KRT_API_URL ? window.KRT_API_URL : 'https://borrowbot-api.kibalabs.com';
const moneyHackClient = new MoneyHackClient(apiRequester, baseUrl);
const localStorageClient = new LocalStorageClient(typeof window !== 'undefined' ? window.localStorage : new MockStorage());
const sessionStorageClient = new LocalStorageClient(typeof window !== 'undefined' ? window.sessionStorage : new MockStorage());
// const queryClient = new QueryClient({
//   defaultOptions: {
//     queries: {
//       staleTime: 5 * 60 * 1000,
//       gcTime: 10 * 60 * 1000,
//       retry: (failureCount: number, error: Error): boolean => {
//         if (error instanceof Error && (error.message.includes('401') || error.message.includes('403'))) {
//           return false;
//         }
//         return failureCount < 3;
//       },
//       refetchOnWindowFocus: true,
//       refetchOnReconnect: false,
//     },
//   },
// });

web3Initialize({
  reownConfig: {
    projectId: '0598a4ef2b432d9fc33d4a8756ac4e10',
    name: 'Money Hack',
    description: 'Money Hack — AI-powered wealth management',
    url: typeof window !== 'undefined' ? window.location.origin : 'https://app.money-hack.xyz',
    icons: ['https://app.money-hack.xyz/assets/icon-dark.png'],
  },
});

const globals: IGlobals = {
  requester,
  localStorageClient,
  moneyHackClient,
  sessionStorageClient,
};

const routes: IRoute<IGlobals>[] = [
  { path: '/setup', page: SetupPage },
  { path: '/account', page: AccountPage },
  { path: '/agent', page: AgentPage },
  { path: '/', page: HomePage },
];

interface IAppProps {
  staticPath?: string;
  pageData?: unknown | undefined | null;
}

export function App(props: IAppProps): React.ReactElement {
  const toastManager = useToastManager();
  const prefersDarkMode = usePrefersDarkMode();
  const isNextVersion = getIsNextVersion();

  const faviconUrl = isNextVersion && !prefersDarkMode ? '/assets/icon.png' : '/assets/icon-dark.png';
  useFavicon(faviconUrl);

  const isInitialized = useInitialization((): void => {
    // if (typeof window !== 'undefined') {
    //   try {
    //     Clarity.init('skc2ocvzdn');
    //   } catch (error: unknown) {
    //     console.error('Failed to initialize Clarity:', error);
    //   }
    // }
  });

  const onWeb3AccountError = React.useCallback((error: Error): void => {
    toastManager.showTextToast(error.message, 'error');
  }, [toastManager]);

  return (
    <KibaApp isFullPageApp={true}>
      <PageDataProvider initialData={props.pageData}>
        <GlobalsProvider globals={globals}>
          {/* <QueryClientProvider client={queryClient}> */}
          <Router staticPath={props.staticPath}>
            <Web3AccountControlProvider localStorageClient={localStorageClient} onError={onWeb3AccountError}>
              <AuthProvider>
                {isInitialized && (
                  <ContainingView>
                    <SubRouter routes={routes} />
                  </ContainingView>
                )}
                <ToastContainer />
              </AuthProvider>
            </Web3AccountControlProvider>
          </Router>
          {/* <ReactQueryDevtools initialIsOpen={false} /> */}
          {/* </QueryClientProvider> */}
        </GlobalsProvider>
      </PageDataProvider>
    </KibaApp>
  );
}
