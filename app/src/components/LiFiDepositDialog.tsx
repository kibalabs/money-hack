import React from 'react';

import { Alignment, Box, Button, Dialog, Direction, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';
import { useToastManager } from '@kibalabs/ui-react-toast';
import { ChainType, LiFiWidget, Route, useWidgetEvents, WidgetConfig, WidgetEvent } from '@lifi/widget';

import { usePrefersDarkMode } from '../util';
import { BASE_CHAIN_ID, CHAIN_USDC_MAP } from '../util/constants';

import './LiFiWidget.css';

const getCssVar = (varName: string): string => {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
};

interface ILiFiDepositDialogProps {
  agentWalletAddress: string;
  targetAssetAddress: string;
  onCloseClicked: () => void;
  onDepositSuccess: () => void;
}

export function LiFiDepositDialog(props: ILiFiDepositDialogProps): React.ReactElement {
  const toastManager = useToastManager();
  const widgetEvents = useWidgetEvents();
  const [isWidgetLoading, setIsWidgetLoading] = React.useState<boolean>(true);
  const [widgetError, setWidgetError] = React.useState<string | null>(null);
  const prefersDarkMode = usePrefersDarkMode();
  const handleWidgetLoad = React.useCallback(() => {
    setIsWidgetLoading(false);
    setWidgetError(null);
  }, []);
  React.useEffect((): void => {
    handleWidgetLoad();
  }, [handleWidgetLoad]);
  const onRouteExecutionCompleted = React.useCallback((_route: Route): void => {
    toastManager.showTextToast('Transfer completed successfully!', 'success');
    props.onDepositSuccess();
  }, [toastManager, props]);
  React.useEffect((): (() => void) => {
    widgetEvents.on(WidgetEvent.RouteExecutionCompleted, onRouteExecutionCompleted);
    return (): void => widgetEvents.all.clear();
  }, [widgetEvents, onRouteExecutionCompleted]);
  const widgetConfig: WidgetConfig = React.useMemo(() => {
    const brandPrimary = getCssVar('--kiba-color-brand-primary');
    const brandSecondary = getCssVar('--kiba-color-brand-secondary');
    const background = getCssVar('--kiba-color-background');
    const backgroundLight05 = getCssVar('--kiba-color-background-light05');
    const text = getCssVar('--kiba-color-text');
    const textClear05 = getCssVar('--kiba-color-text-clear05');
    const textClear10 = getCssVar('--kiba-color-text-clear10');
    const success = getCssVar('--kiba-color-success');
    const warning = getCssVar('--kiba-color-warning');
    const error = getCssVar('--kiba-color-error');
    const borderRadius = getCssVar('--kiba-border-radius');
    const fontFamily = getCssVar('--kiba-font-family');
    return {
      integrator: 'BorrowBot',
      toChain: BASE_CHAIN_ID,
      toToken: props.targetAssetAddress || CHAIN_USDC_MAP[BASE_CHAIN_ID],
      toAddress: {
        name: 'Agent Wallet',
        address: props.agentWalletAddress,
        chainType: ChainType.EVM,
      },
      buildUrl: false,
      insurance: false,
      variant: 'compact',
      subvariant: 'default',
      appearance: prefersDarkMode ? 'dark' : 'light',
      theme: {
        typography: {
          fontFamily: fontFamily || '"IBM Plex Mono", monospace, sans-serif',
        },
        container: {
          borderRadius,
          display: 'flex',
          height: '100%',
        },
        shape: {
          borderRadius: 0,
          borderRadiusSecondary: 0,
        },
        colorSchemes: {
          light: {
            palette: {
              primary: { main: brandPrimary },
              secondary: { main: brandSecondary },
              background: { default: '#f5f5f5', paper: '#ffffff' },
              text: { primary: '#222222', secondary: '#666666' },
              success: { main: success },
              warning: { main: warning },
              error: { main: error },
              info: { main: '#888888' },
            },
          },
          dark: {
            palette: {
              primary: { main: brandPrimary },
              secondary: { main: brandSecondary },
              background: { default: backgroundLight05, paper: background },
              text: { primary: text, secondary: textClear05 },
              success: { main: success },
              warning: { main: warning },
              error: { main: error },
              info: { main: textClear10 },
              common: { white: '#ffffff' },
            },
          },
        },
      },
      hiddenUI: [
        'poweredBy',
        'appearance',
        'language',
        'toAddress',
        'toToken',
        'history',
        'gasRefuelMessage',
        'bridgesSettings',
        'drawerCloseButton',
      ],
    };
  }, [props.agentWalletAddress, props.targetAssetAddress, prefersDarkMode]);
  return (
    <Dialog
      onCloseClicked={props.onCloseClicked}
      isOpen={true}
      maxHeight='calc(min(90vh, 1200px))'
      maxWidth='calc(min(90vw, 600px))'
    >
      <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullHeight={true}>
        <Text variant='header2'>Deposit to Agent Wallet</Text>
        <Spacing variant={PaddingSize.Wide} />
        <Stack.Item growthFactor={1} shrinkFactor={1}>
          <Box className='swap-widget-container'>
            {isWidgetLoading ? (
              <Text>Loading Li.Fi widget...</Text>
            ) : widgetError ? (
              <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
                <Text variant='error'>{widgetError}</Text>
                <Button variant='tertiary' text='Retry' onClicked={() => window.location.reload()} />
              </Stack>
            ) : (
              <LiFiWidget
                integrator='borrowbot'
                config={widgetConfig}
              />
            )}
          </Box>
        </Stack.Item>
      </Stack>
    </Dialog>
  );
}
