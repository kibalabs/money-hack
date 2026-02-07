import React from 'react';

import { Alignment, Box, Button, Dialog, Direction, InputType, Link, LoadingSpinner, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useWeb3, useWeb3Transaction } from '@kibalabs/web3-react';
import { ethers } from 'ethers';

import { useAuth } from '../AuthContext';
import { Position } from '../client/resources';

import './DepositUsdcDialog.scss';

const USDC_DECIMALS = 6;
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

interface IDepositUsdcDialogProps {
  position: Position;
  agentWalletAddress: string;
  availableUsdcBalance: bigint;
  onCloseClicked: () => void;
  onDepositSuccess: () => void;
}

const parseUsdcAmount = (text: string): bigint | null => {
  const trimmed = text.trim();
  if (!trimmed || trimmed === '.') return null;
  const parts = trimmed.split('.');
  if (parts.length > 2) return null;
  const wholePart = parts[0] || '0';
  const fracPart = (parts[1] || '').slice(0, USDC_DECIMALS).padEnd(USDC_DECIMALS, '0');
  try {
    return BigInt(wholePart) * BigInt(10 ** USDC_DECIMALS) + BigInt(fracPart);
  } catch {
    return null;
  }
};

const formatUsdcNumber = (raw: bigint): string => {
  const value = Number(raw) / (10 ** USDC_DECIMALS);
  if (value === 0) return '0';
  if (value < 0.01) return '<0.01';
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const formatPercent = (value: number): string => `${(value * 100).toFixed(2)}%`;

export function DepositUsdcDialog(props: IDepositUsdcDialogProps): React.ReactElement {
  const web3 = useWeb3();
  const { accountSigner } = useAuth();
  const [transactionDetails, setTransactionPromise, , clearTransaction] = useWeb3Transaction();
  const [amount, setAmount] = React.useState<string>('');
  const [hasInitialized, setHasInitialized] = React.useState<boolean>(false);

  const availableNumber = formatUsdcNumber(props.availableUsdcBalance);

  React.useEffect((): void => {
    if (!hasInitialized && props.availableUsdcBalance > 0n) {
      setAmount((Number(props.availableUsdcBalance) / (10 ** USDC_DECIMALS)).toString());
      setHasInitialized(true);
    }
  }, [props.availableUsdcBalance, hasInitialized]);

  const amountRaw = React.useMemo((): bigint | null => parseUsdcAmount(amount), [amount]);
  const isAmountValid = amountRaw != null && amountRaw > 0n && amountRaw <= props.availableUsdcBalance;
  const isTransferring = transactionDetails.transactionPromise != null || transactionDetails.transaction != null;
  const transferError = transactionDetails?.error;
  const transferReceipt = transactionDetails?.receipt;
  const isSuccess = !!transferReceipt;

  const onMaxClicked = (): void => {
    setAmount((Number(props.availableUsdcBalance) / (10 ** USDC_DECIMALS)).toString());
  };

  const onDepositClicked = async (): Promise<void> => {
    if (!isAmountValid || !amountRaw || !accountSigner || !web3) return;
    const tokenAbi = ['function transfer(address to, uint256 amount) public returns (bool)'];
    const tokenContract = new ethers.Contract(USDC_ADDRESS, tokenAbi, accountSigner);
    const transactionPromise = tokenContract.transfer(props.agentWalletAddress, amountRaw);
    setTransactionPromise(transactionPromise);
  };

  const onDoneClicked = (): void => {
    clearTransaction();
    props.onDepositSuccess();
  };

  const onRetryClicked = (): void => {
    clearTransaction();
  };

  // Estimate new LTV after deposit: agent will use USDC to repay debt
  const depositAmountUsd = amountRaw ? Number(amountRaw) / (10 ** USDC_DECIMALS) : 0;
  const newBorrowUsd = Math.max(0, props.position.borrowValueUsd - depositAmountUsd);
  const estimatedNewLtv = props.position.collateralValueUsd > 0
    ? newBorrowUsd / props.position.collateralValueUsd
    : 0;

  const renderContent = (): React.ReactElement => {
    if (transferError) {
      return (
        <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center} isFullWidth={true}>
          <Text variant='error' alignment={TextAlignment.Center}>Error processing deposit:</Text>
          <Text variant='error' alignment={TextAlignment.Center}>{transferError.message}</Text>
          <Spacing />
          <Button variant='tertiary' text='Try Again' onClicked={onRetryClicked} />
        </Stack>
      );
    }
    if (isSuccess) {
      return (
        <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center} isFullWidth={true}>
          <Text variant='success' alignment={TextAlignment.Center}>USDC deposited successfully!</Text>
          <Text variant='note' alignment={TextAlignment.Center}>Your agent will use this USDC to repay debt and restore your position health.</Text>
          <Spacing />
          {transferReceipt && (
            <Link text='View transaction' target={`https://basescan.org/tx/${transferReceipt.hash}`} />
          )}
          <Spacing />
          <Button variant='primary' text='Done' onClicked={onDoneClicked} isFullWidth={true} />
        </Stack>
      );
    }
    if (isTransferring) {
      return (
        <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center} isFullWidth={true}>
          <Text variant='note' alignment={TextAlignment.Center}>Processing deposit...</Text>
          <Text variant='note' alignment={TextAlignment.Center}>Please wait while your transaction is being processed.</Text>
          <Spacing />
          <LoadingSpinner />
          <Spacing />
          <Text variant='note' alignment={TextAlignment.Center}>Do not close this page.</Text>
        </Stack>
      );
    }
    return (
      <React.Fragment>
        <Box className='depositUsdcInfoCard'>
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
              <Text variant='note'>Current Debt</Text>
              <Stack.Item growthFactor={1} shrinkFactor={1} />
              <Text variant='bold'>{`$${formatUsdcNumber(props.position.borrowAmount)}`}</Text>
            </Stack>
            <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
              <Text variant='note'>Current LTV</Text>
              <Stack.Item growthFactor={1} shrinkFactor={1} />
              <Text variant='bold'>{formatPercent(props.position.currentLtv)}</Text>
            </Stack>
          </Stack>
        </Box>
        <Stack direction={Direction.Vertical} isFullWidth={true}>
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
            <Text variant='note'>Your USDC balance:</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Text variant='value'>
              $
              {availableNumber}
            </Text>
            <Stack.Item growthFactor={1} shrinkFactor={1}>
              <Spacing />
            </Stack.Item>
            <Button variant='tertiary-small' text='Max' onClicked={onMaxClicked} />
          </Stack>
          <SingleLineInput
            inputType={InputType.Number}
            placeholderText='Amount in USDC'
            value={amount}
            onValueChanged={setAmount}
          />
        </Stack>
        {amountRaw && amountRaw > 0n && isAmountValid && (
          <Box className='depositUsdcPreviewCard'>
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text variant='note'>Estimated New LTV</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold-success'>
                  {formatPercent(props.position.currentLtv)}
                  {' '}
                  &rarr;
                  {' '}
                  {formatPercent(estimatedNewLtv)}
                </Text>
              </Stack>
              <Text variant='note'>
                Your agent will use this USDC to repay debt and lower your LTV. This helps protect your position from liquidation.
              </Text>
            </Stack>
          </Box>
        )}
        {amountRaw && amountRaw > props.availableUsdcBalance && (
          <Text variant='error'>Amount exceeds available USDC balance</Text>
        )}
        <Spacing variant={PaddingSize.Default} />
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} contentAlignment={Alignment.Center} isFullWidth={true}>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='tertiary'
              text='Cancel'
              onClicked={props.onCloseClicked}
              isFullWidth={true}
            />
          </Stack.Item>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='primary'
              text='Deposit USDC'
              onClicked={onDepositClicked}
              isEnabled={isAmountValid && !!accountSigner}
              isFullWidth={true}
            />
          </Stack.Item>
        </Stack>
      </React.Fragment>
    );
  };

  return (
    <Dialog
      onCloseClicked={props.onCloseClicked}
      isOpen={true}
      maxHeight='calc(min(90vh, 600px))'
      maxWidth='calc(min(90vw, 480px))'
    >
      <Stack direction={Direction.Vertical} shouldAddGutters={true}>
        <Text variant='header2'>Deposit USDC</Text>
        <Text variant='note' alignment={TextAlignment.Center}>
          Send USDC to your agent to repay debt and improve position health
        </Text>
        <Spacing variant={PaddingSize.Default} />
        {renderContent()}
      </Stack>
    </Dialog>
  );
}
