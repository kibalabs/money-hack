import React from 'react';

import { Alignment, Box, Button, Dialog, Direction, getVariant, Image, KibaIcon, PaddingSize, SelectableView, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { Eip6963ProviderDetail, useIsReownInitialized, useOnLinkWeb3AccountsClicked, useWeb3OnBaseLoginClicked, useWeb3OnLoginClicked, useWeb3OnReownLoginClicked, useWeb3Providers } from '@kibalabs/web3-react';

import { useAuth } from '../AuthContext';

import './HomePage.scss';

interface IProviderDialogProps {
  isOpen: boolean;
  providers: Eip6963ProviderDetail[];
  onProviderSelected: (provider: Eip6963ProviderDetail) => void;
  onSignInWithBaseClicked: () => void;
  onSignInWithReownClicked: () => void;
  isReownAvailable: boolean;
  onClose: () => void;
}

function ProviderDialog(props: IProviderDialogProps): React.ReactElement {
  const hasProviders = props.providers.length > 0;
  return (
    <Dialog
      isOpen={props.isOpen}
      onCloseClicked={props.onClose}
      isClosableByBackdrop={true}
      isClosableByEscape={true}
      maxWidth='calc(min(90%, 600px))'
      maxHeight='90%'
    >
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide} paddingVertical={PaddingSize.Wide}>
        <Text variant='header2' alignment={TextAlignment.Center}>Connect Wallet</Text>
        <Spacing />
        {hasProviders && (
          <React.Fragment>
            {props.providers.map((provider: Eip6963ProviderDetail): React.ReactElement => (
              <Box key={provider.info.uuid} maxWidth='400px'>
                <SelectableView onClicked={(): void => props.onProviderSelected(provider)} isSelected={false} isFullWidth={true}>
                  <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
                    <Box width='2.5rem' height='2.5rem'>
                      <Image source={provider.info.icon} alternativeText={`${provider.info.name} icon`} isFullWidth={true} isFullHeight={true} />
                    </Box>
                    <Spacing variant={PaddingSize.Wide} />
                    <Stack.Item growthFactor={1} shrinkFactor={1}>
                      <Stack direction={Direction.Vertical} childAlignment={Alignment.Start} isFullWidth={true}>
                        <Text variant={getVariant(provider.info.uuid !== 'ethers' && 'bold')}>{provider.info.name}</Text>
                        {provider.info.uuid !== 'ethers' && (
                          <Text variant='note'>Installed</Text>
                        )}
                      </Stack>
                    </Stack.Item>
                    <Spacing variant={PaddingSize.Wide} />
                    <KibaIcon iconId='ion-arrow-forward' _color={provider.info.uuid !== 'ethers' ? 'var(--kiba-color-background-light95)' : 'var(--kiba-color-background-light75)'} />
                  </Stack>
                </SelectableView>
              </Box>
            ))}
          </React.Fragment>
        )}
        <Box maxWidth='400px'>
          <SelectableView onClicked={props.onSignInWithBaseClicked} isSelected={false} isFullWidth={true}>
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
              <Box width='2.5rem' height='2.5rem'>
                <Image source='https://www.base.org/document/apple-touch-icon.png' alternativeText='Base icon' isFullWidth={true} isFullHeight={true} />
              </Box>
              <Spacing variant={PaddingSize.Wide} />
              <Stack.Item growthFactor={1} shrinkFactor={1}>
                <Text variant={getVariant('bold')}>Sign in with Base</Text>
              </Stack.Item>
              <Spacing variant={PaddingSize.Wide} />
              <KibaIcon iconId='ion-arrow-forward' _color='var(--kiba-color-background-light95)' />
            </Stack>
          </SelectableView>
        </Box>
        {props.isReownAvailable && (
          <Box maxWidth='400px'>
            <SelectableView onClicked={props.onSignInWithReownClicked} isSelected={false} isFullWidth={true}>
              <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
                <Box width='2.5rem' height='2.5rem'>
                  <Image source='https://walletconnect.network/icon.png' alternativeText='WalletConnect icon' isFullWidth={true} isFullHeight={true} />
                </Box>
                <Spacing variant={PaddingSize.Wide} />
                <Stack.Item growthFactor={1} shrinkFactor={1}>
                  <Text variant={getVariant('bold')}>Connect with WalletConnect</Text>
                </Stack.Item>
                <Spacing variant={PaddingSize.Wide} />
                <KibaIcon iconId='ion-arrow-forward' _color='var(--kiba-color-background-light95)' />
              </Stack>
            </SelectableView>
          </Box>
        )}
        {!hasProviders && (
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true}>
            <Spacing />
            <Text alignment={TextAlignment.Center}>You don&apos;t have any Web3 wallets installed.</Text>
            <Spacing />
            <Text alignment={TextAlignment.Center}>A Web3 wallet lets you securely store, send, and receive crypto assets.</Text>
            <Spacing />
            <Text>We recommend:</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Box maxWidth='400px'>
              <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true} defaultGutter={PaddingSize.Wide}>
                <SelectableView isSelected={false} isFullWidth={true} onClicked={() => window.open('https://www.coinbase.com/en-gb/wallet/articles/getting-started-extension', '_blank')}>
                  <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
                    <Box width='2.5rem' height='2.5rem'>
                      <Image source='https://avatars.githubusercontent.com/u/1885080?s=200&v=4' alternativeText='Coinbase Wallet icon' isFullWidth={true} isFullHeight={true} />
                    </Box>
                    <Spacing variant={PaddingSize.Wide} />
                    <Stack.Item growthFactor={1} shrinkFactor={1}>
                      <Text variant='bold'>Coinbase Wallet</Text>
                    </Stack.Item>
                    <Spacing variant={PaddingSize.Wide} />
                    <KibaIcon iconId='ion-arrow-forward' />
                  </Stack>
                </SelectableView>
                <SelectableView isSelected={false} isFullWidth={true} onClicked={() => window.open('https://metamask.io/en-GB', '_blank')}>
                  <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
                    <Box width='2.5rem' height='2.5rem'>
                      <Image source='https://metamask.io/favicons/default/favicon.svg' alternativeText='MetaMask icon' isFullWidth={true} isFullHeight={true} />
                    </Box>
                    <Spacing variant={PaddingSize.Wide} />
                    <Stack.Item growthFactor={1} shrinkFactor={1}>
                      <Text variant='bold'>MetaMask</Text>
                    </Stack.Item>
                    <Spacing variant={PaddingSize.Wide} />
                    <KibaIcon iconId='ion-arrow-forward' />
                  </Stack>
                </SelectableView>
              </Stack>
            </Box>
            <Spacing />
          </Stack>
        )}
        <Spacing />
        <Button variant='tertiary-passive' text='Cancel' onClicked={props.onClose} />
      </Stack>
    </Dialog>
  );
}

export function HomePage(): React.ReactElement {
  const { isWeb3AccountConnected, isWeb3AccountLoggedIn, logout } = useAuth();
  const [web3Providers, chooseEip1193Provider] = useWeb3Providers();
  const onLinkAccountsClicked = useOnLinkWeb3AccountsClicked();
  const onSignInWithBaseClicked = useWeb3OnBaseLoginClicked();
  const onSignInWithReownClicked = useWeb3OnReownLoginClicked();
  const onAccountLoginClicked = useWeb3OnLoginClicked();
  const isReownInitialized = useIsReownInitialized();
  const [isProviderDialogOpen, setIsProviderDialogOpen] = React.useState(false);
  const [isLoggingIn, setIsLoggingIn] = React.useState<boolean>(false);

  React.useEffect(() => {
    if (isWeb3AccountLoggedIn) {
      window.location.href = '/create-agent';
    }
  }, [isWeb3AccountLoggedIn]);

  const onConnectWalletClicked = React.useCallback((): void => {
    setIsProviderDialogOpen(true);
  }, []);

  const onSignInWithBaseButtonClicked = async (): Promise<void> => {
    await onSignInWithBaseClicked(8453, 'I have read and agree to the Terms of Service', 'Money Hack', 'https://app.money-hack.xyz/assets/icon.png');
  };

  const onSignInWithReownButtonClicked = async (): Promise<void> => {
    setIsProviderDialogOpen(false);
    await onSignInWithReownClicked();
  };

  const onProviderSelected = React.useCallback(async (provider: Eip6963ProviderDetail): Promise<void> => {
    chooseEip1193Provider(provider.info.rdns);
    setIsProviderDialogOpen(false);
    await onLinkAccountsClicked();
  }, [chooseEip1193Provider, onLinkAccountsClicked]);

  const onLoginClicked = async (): Promise<void> => {
    setIsLoggingIn(true);
    await onAccountLoginClicked('I have read and agree to the Terms of Service');
    setIsLoggingIn(false);
  };

  return (
    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide} paddingVertical={PaddingSize.Wide2} isFullHeight={true}>
      {isWeb3AccountConnected ? (
        <React.Fragment>
          <Text variant='note'>You&apos;re almost there...</Text>
          <Button variant='primary' text='Sign to log in' onClicked={onLoginClicked} isLoading={isLoggingIn} />
          <Button variant='tertiary' text='Disconnect wallet' onClicked={logout} />
        </React.Fragment>
      ) : (
        <React.Fragment>
          <Text variant='header2'>Money Hack</Text>
          <Text>Connect your wallet to get started</Text>
          <Button text='Connect Wallet' variant='primary' onClicked={onConnectWalletClicked} />
        </React.Fragment>
      )}
      <ProviderDialog
        isOpen={isProviderDialogOpen}
        providers={web3Providers}
        onProviderSelected={onProviderSelected}
        onSignInWithBaseClicked={onSignInWithBaseButtonClicked}
        onSignInWithReownClicked={onSignInWithReownButtonClicked}
        isReownAvailable={isReownInitialized}
        onClose={(): void => setIsProviderDialogOpen(false)}
      />
    </Stack>
  );
}
