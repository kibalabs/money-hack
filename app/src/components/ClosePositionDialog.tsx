import React from 'react';

import { Alignment, Button, Dialog, Direction, Link, LoadingSpinner, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';
import { Position } from '../client/resources';
import { useGlobals } from '../GlobalsContext';

interface IClosePositionDialogProps {
  position: Position;
  agentId?: string;
  onCloseClicked: () => void;
  onClosePositionSuccess: () => void;
}

const formatUsd = (value: number): string => {
  if (value >= 1000) {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${value.toFixed(2)}`;
};


export function ClosePositionDialog(props: IClosePositionDialogProps): React.ReactElement {
  const { accountAddress, authToken } = useAuth();
  const { moneyHackClient } = useGlobals();
  const [isConfirmed, setIsConfirmed] = React.useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [transactionHash, setTransactionHash] = React.useState<string | null>(null);
  const [isSuccess, setIsSuccess] = React.useState<boolean>(false);

  const handleClosePositionClicked = React.useCallback(async (): Promise<void> => {
    if (!accountAddress || !authToken) return;
    if (!isConfirmed) {
      setIsConfirmed(true);
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await moneyHackClient.getClosePositionTransactions(accountAddress, authToken, props.agentId);
      if (result.transactionHash) {
        setTransactionHash(result.transactionHash);
      }
      setIsSuccess(true);
    } catch (caughtError) {
      console.error('Close position failed:', caughtError);
      setError(caughtError instanceof Error ? caughtError.message : 'Failed to close position. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }, [accountAddress, authToken, isConfirmed, moneyHackClient]);

  if (isSuccess) {
    return (
      <Dialog
        onCloseClicked={props.onCloseClicked}
        isOpen={true}
        maxHeight='calc(min(90vh, 500px))'
        maxWidth='calc(min(90vw, 480px))'
      >
        <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
          <Text variant='header2'>Position Closed</Text>
          <Spacing />
          <Text variant='success' alignment={TextAlignment.Center}>Your position has been successfully closed.</Text>
          <Text variant='note' alignment={TextAlignment.Center}>All collateral has been withdrawn and debt repaid.</Text>
          {transactionHash && (
            <React.Fragment>
              <Spacing />
              <Link text='View transaction on Basescan' target={`https://basescan.org/tx/${transactionHash}`} />
            </React.Fragment>
          )}
          <Spacing variant={PaddingSize.Wide} />
          <Button variant='primary' text='Done' onClicked={props.onClosePositionSuccess} isFullWidth={true} />
        </Stack>
      </Dialog>
    );
  }

  return (
    <Dialog
      onCloseClicked={props.onCloseClicked}
      isOpen={true}
      maxHeight='calc(min(90vh, 500px))'
      maxWidth='calc(min(90vw, 480px))'
    >
      <Stack direction={Direction.Vertical} shouldAddGutters={true}>
        <Text variant='header2'>Close Position</Text>
        <Spacing />
        <Text>This will execute the following steps:</Text>
        <Stack direction={Direction.Vertical} shouldAddGutters={true} paddingHorizontal={PaddingSize.Default}>
          <Text variant='note'>1. Withdraw USDC from the yield vault</Text>
          <Text variant='note'>2. Repay the USDC loan on Morpho</Text>
          <Text variant='note'>3. Withdraw your collateral from Morpho</Text>
        </Stack>
        <Spacing />
        <Stack direction={Direction.Vertical} shouldAddGutters={true}>
          <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
            <Text variant='note'>Collateral to withdraw</Text>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Text variant='bold'>{formatUsd(props.position.collateralValueUsd)}</Text>
          </Stack>
          <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
            <Text variant='note'>Debt to repay</Text>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Text variant='bold'>{formatUsd(props.position.borrowValueUsd)}</Text>
          </Stack>
          <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
            <Text variant='note'>Vault balance</Text>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Text variant='bold'>{formatUsd(props.position.vaultBalanceUsd)}</Text>
          </Stack>
        </Stack>
        {isConfirmed && !isSubmitting && !error && (
          <React.Fragment>
            <Spacing />
            <Text variant='note-warning' alignment={TextAlignment.Center}>
              Are you sure? This action cannot be undone. Your agent will stop earning yield.
            </Text>
          </React.Fragment>
        )}
        {isSubmitting && (
          <React.Fragment>
            <Spacing />
            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true}>
              <LoadingSpinner />
              <Text variant='note' alignment={TextAlignment.Center}>Closing position... This may take a moment.</Text>
            </Stack>
          </React.Fragment>
        )}
        {error && (
          <React.Fragment>
            <Spacing />
            <Text variant='error' alignment={TextAlignment.Center}>{error}</Text>
          </React.Fragment>
        )}
        <Spacing variant={PaddingSize.Default} />
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} contentAlignment={Alignment.Center} isFullWidth={true}>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='tertiary'
              text={isConfirmed ? 'Back' : 'Cancel'}
              onClicked={isConfirmed && !isSubmitting ? (): void => setIsConfirmed(false) : props.onCloseClicked}
              isEnabled={!isSubmitting}
              isFullWidth={true}
            />
          </Stack.Item>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='destructive'
              text={isConfirmed ? 'Confirm Close' : 'Close Position'}
              onClicked={handleClosePositionClicked}
              isLoading={isSubmitting}
              isFullWidth={true}
            />
          </Stack.Item>
        </Stack>
      </Stack>
    </Dialog>
  );
}
