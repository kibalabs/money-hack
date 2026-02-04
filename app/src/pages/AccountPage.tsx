import React from 'react';

import { KibaException } from '@kibalabs/core';
import { useNavigator, useUrlQueryState } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, KibaIcon, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useToastManager } from '@kibalabs/ui-react-toast';

import { useAuth } from '../AuthContext';
import { UserConfig } from '../client/resources';
import { useGlobals } from '../GlobalsContext';

export function AccountPage(): React.ReactElement {
  const { accountAddress, authToken, isWeb3AccountLoggedIn } = useAuth();
  const { moneyHackClient } = useGlobals();
  const navigator = useNavigator();
  const toastManager = useToastManager();
  const [telegramSecret, setTelegramSecret] = useUrlQueryState('telegramSecret');
  const [userConfig, setUserConfig] = React.useState<UserConfig | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [isConnectingTelegram, setIsConnectingTelegram] = React.useState<boolean>(false);
  const [telegramBotUsername, setTelegramBotUsername] = React.useState<string | null>(null);
  const isProcessingTelegramSecretRef = React.useRef<boolean>(false);

  React.useEffect((): void => {
    if (!isWeb3AccountLoggedIn) {
      navigator.navigateTo('/');
    }
  }, [isWeb3AccountLoggedIn, navigator]);

  React.useEffect((): void => {
    const loadUserConfig = async (): Promise<void> => {
      if (!accountAddress || !authToken) return;
      try {
        setIsLoading(true);
        const fetchedUserConfig = await moneyHackClient.getUserConfig(accountAddress, authToken);
        setUserConfig(fetchedUserConfig);
      } catch (error) {
        console.error('Failed to load user config:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadUserConfig();
  }, [accountAddress, authToken, moneyHackClient]);

  React.useEffect((): void => {
    if (!accountAddress || !authToken || !telegramSecret) return;
    if (isProcessingTelegramSecretRef.current) return;
    setTelegramSecret(null);
    isProcessingTelegramSecretRef.current = true;
    const verifyTelegramSecret = async (): Promise<void> => {
      try {
        const result = await moneyHackClient.telegramSecretVerify(accountAddress, telegramSecret, authToken);
        setUserConfig(result);
        toastManager.showTextToast('✅ Telegram account connected successfully!', 'success');
      } catch (error) {
        console.error('Failed to verify Telegram secret:', error);
        const errorMessage = error instanceof KibaException ? error.message : 'Failed to connect Telegram account. Please try again.';
        toastManager.showTextToast(`⚠️ ${errorMessage}`, 'error');
      }
    };
    verifyTelegramSecret();
  }, [accountAddress, authToken, telegramSecret, setTelegramSecret, moneyHackClient, toastManager]);

  const onConnectTelegramClicked = async (): Promise<void> => {
    if (!accountAddress || !authToken) {
      toastManager.showTextToast('⚠️ Please connect your wallet first.', 'error');
      return;
    }
    setIsConnectingTelegram(true);
    try {
      const botUsername = await moneyHackClient.getTelegramLoginUrl(accountAddress, authToken);
      setTelegramBotUsername(botUsername);
    } catch (error) {
      console.error('Failed to get Telegram bot:', error);
      toastManager.showTextToast('⚠️ Failed to connect Telegram. Please try again.', 'error');
    } finally {
      setIsConnectingTelegram(false);
    }
  };

  const onDisconnectTelegramClicked = async (): Promise<void> => {
    if (!accountAddress || !authToken) return;
    setIsConnectingTelegram(true);
    try {
      const result = await moneyHackClient.disconnectTelegram(accountAddress, authToken);
      setUserConfig(result);
      setTelegramBotUsername(null);
      toastManager.showTextToast('✅ Telegram disconnected successfully!', 'success');
    } catch (error) {
      console.error('Failed to disconnect Telegram:', error);
      toastManager.showTextToast('⚠️ Failed to disconnect Telegram. Please try again.', 'error');
    } finally {
      setIsConnectingTelegram(false);
    }
  };

  if (isLoading) {
    return (
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} isFullHeight={true}>
        <Text>Loading...</Text>
      </Stack>
    );
  }

  const isTelegramConnected = !!userConfig?.telegramHandle;

  return (
    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} padding={PaddingSize.Wide2}>
      <Spacing variant={PaddingSize.Wide2} />
      <Text variant='header2' alignment={TextAlignment.Center}>Account Settings</Text>
      <Spacing variant={PaddingSize.Wide} />
      <Box variant='card' isFullWidth={true} maxWidth='500px'>
        <Stack direction={Direction.Vertical} shouldAddGutters={true} padding={PaddingSize.Wide}>
          <Text variant='header3'>Telegram Notifications</Text>
          <Text variant='note'>Connect your Telegram account to receive notifications about your positions.</Text>
          <Spacing />
          {isTelegramConnected ? (
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
                <KibaIcon iconId='ion-checkmark-circle' variant='success' />
                <Text>Connected as @{userConfig?.telegramHandle}</Text>
              </Stack>
              <Button
                variant='secondary'
                text='Disconnect Telegram'
                onClicked={onDisconnectTelegramClicked}
                isLoading={isConnectingTelegram}
              />
            </Stack>
          ) : telegramBotUsername ? (
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Text alignment={TextAlignment.Center}>
                Message our bot on Telegram to complete the connection:
              </Text>
              <Button
                variant='primary'
                text={`Open ${telegramBotUsername}`}
                target={`https://t.me/${telegramBotUsername.replace('@', '')}`}
                iconLeft={<KibaIcon iconId='ion-paper-plane' />}
              />
              <Button
                variant='tertiary'
                text='Cancel'
                onClicked={(): void => setTelegramBotUsername(null)}
              />
            </Stack>
          ) : (
            <Button
              variant='primary'
              text='Connect Telegram'
              onClicked={onConnectTelegramClicked}
              isLoading={isConnectingTelegram}
              iconLeft={<KibaIcon iconId='ion-paper-plane' />}
            />
          )}
        </Stack>
      </Box>
      <Spacing variant={PaddingSize.Wide2} />
      <Button
        variant='tertiary'
        text='Back to Home'
        onClicked={(): void => navigator.navigateTo('/')}
      />
    </Stack>
  );
}
