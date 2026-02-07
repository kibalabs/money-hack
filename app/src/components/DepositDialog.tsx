import React from 'react';

import { Alignment, Box, Button, Dialog, Direction, InputType, Link, LoadingSpinner, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useWeb3, useWeb3Transaction } from '@kibalabs/web3-react';
import { ethers } from 'ethers';

import { useAuth } from '../AuthContext';
import { Position } from '../client/resources';

import './DepositDialog.scss';

interface IDepositDialogProps {
  position: Position;
  agentWalletAddress: string;
  availableBalance: bigint;
  onCloseClicked: () => void;
  onDepositSuccess: () => void;
}

const parseCollateralAmount = (text: string, decimals: number): bigint | null => {
  const trimmed = text.trim();
  if (!trimmed || trimmed === '.') return null;
  const parts = trimmed.split('.');
  if (parts.length > 2) return null;
  const wholePart = parts[0] || '0';
  const fracPart = (parts[1] || '').slice(0, decimals).padEnd(decimals, '0');
  try {
    return BigInt(wholePart) * BigInt(10 ** decimals) + BigInt(fracPart);
  } catch {
    return null;
  }
};

const formatCollateralNumber = (raw: bigint, decimals: number): number => {
  return Number(raw) / (10 ** decimals);
};

const decimalWithCommas = (value: number): string => {
  if (value === 0) return '0';
  if (value < 0.0001) return '<0.0001';
  return value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 4 });
};

export function DepositDialog(props: IDepositDialogProps): React.ReactElement {
  const web3 = useWeb3();
  const { accountSigner } = useAuth();
  const [transactionDetails, setTransactionPromise, , clearTransaction] = useWeb3Transaction();
  const [amount, setAmount] = React.useState<string>('');
  const [hasInitialized, setHasInitialized] = React.useState<boolean>(false);
  const decimals = props.position.collateralAsset.decimals;
  const symbol = props.position.collateralAsset.symbol;
  const availableNumber = formatCollateralNumber(props.availableBalance, decimals);
  const currentCollateralNumber = formatCollateralNumber(props.position.collateralAmount, decimals);
  React.useEffect((): void => {
    if (!hasInitialized && availableNumber > 0) {
      setAmount(availableNumber.toString());
      setHasInitialized(true);
    }
  }, [availableNumber, hasInitialized]);
  const amountRaw = React.useMemo((): bigint | null => parseCollateralAmount(amount, decimals), [amount, decimals]);
  const isAmountValid = amountRaw != null && amountRaw > 0n && amountRaw <= props.availableBalance;
  const isTransferring = transactionDetails.transactionPromise != null || transactionDetails.transaction != null;
  const transferError = transactionDetails?.error;
  const transferReceipt = transactionDetails?.receipt;
  const isSuccess = !!transferReceipt;
  const onMaxClicked = (): void => {
    setAmount(availableNumber.toString());
  };
  const onDepositClicked = async (): Promise<void> => {
    if (!isAmountValid || !amountRaw || !accountSigner || !web3) return;
    const tokenAbi = ['function transfer(address to, uint256 amount) public returns (bool)'];
    const tokenContract = new ethers.Contract(props.position.collateralAsset.address, tokenAbi, accountSigner);
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
  const afterCollateral = amountRaw ? props.position.collateralAmount + amountRaw : props.position.collateralAmount;
  const afterCollateralNumber = formatCollateralNumber(afterCollateral, decimals);

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
          <Text variant='success' alignment={TextAlignment.Center}>Deposit successful!</Text>
          <Text variant='note' alignment={TextAlignment.Center}>Your transaction has been confirmed on the blockchain.</Text>
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
        <Box className='depositInfoCard'>
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
              <Text variant='note'>Current Collateral</Text>
              <Stack.Item growthFactor={1} shrinkFactor={1} />
              <Text variant='bold'>
                {decimalWithCommas(currentCollateralNumber)}
                {' '}
                {symbol}
              </Text>
            </Stack>
          </Stack>
        </Box>
        <Stack direction={Direction.Vertical} isFullWidth={true}>
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
            <Text variant='note'>Your balance:</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Text variant='value'>
              {decimalWithCommas(availableNumber)}
              {' '}
              {symbol}
            </Text>
            <Stack.Item growthFactor={1} shrinkFactor={1}>
              <Spacing />
            </Stack.Item>
            <Button variant='tertiary-small' text='Max' onClicked={onMaxClicked} />
          </Stack>
          <SingleLineInput
            inputType={InputType.Number}
            placeholderText={`Amount in ${symbol}`}
            value={amount}
            onValueChanged={setAmount}
          />
        </Stack>
        {amountRaw && amountRaw > 0n && isAmountValid && (
          <Box className='depositPreviewCard'>
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text variant='note'>After Deposit</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>
                  {decimalWithCommas(afterCollateralNumber)}
                  {' '}
                  {symbol}
                </Text>
              </Stack>
              <Text variant='note'>
                Depositing more collateral will lower your LTV and improve your position health.
              </Text>
            </Stack>
          </Box>
        )}
        {amountRaw && amountRaw > props.availableBalance && (
          <Text variant='error'>Amount exceeds available balance</Text>
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
              text='Deposit to Agent'
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
        <Text variant='header2'>Deposit Collateral</Text>
        <Text variant='note' alignment={TextAlignment.Center}>
          Add more
          {' '}
          {symbol}
          {' '}
          to improve your position health
        </Text>
        <Spacing variant={PaddingSize.Default} />
        {renderContent()}
      </Stack>
    </Dialog>
  );
}
