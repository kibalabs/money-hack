import React from 'react';

import { Alignment, Box, Button, Direction, InputType, LoadingSpinner, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useOnSwitchToWeb3ChainIdClicked, useWeb3, useWeb3Transaction } from '@kibalabs/web3-react';
// eslint-disable-next-line import/no-extraneous-dependencies
import { ethers } from 'ethers';

import { useAuth } from '../AuthContext';
import { AssetBalance } from '../client/resources';
import { formatBalance } from '../util';
import { BASE_CHAIN_ID } from '../util/constants';

interface IDepositFormProps {
  assetBalance: AssetBalance | null | undefined;
  agentWalletAddress: string;
  onDepositSuccess: () => void;
  isLoadingBalance?: boolean;
}

export function DepositForm(props: IDepositFormProps): React.ReactElement {
  const web3 = useWeb3();
  const { accountSigner, chainId } = useAuth();
  const onSwitchToWeb3ChainIdClicked = useOnSwitchToWeb3ChainIdClicked();
  const [transactionDetails, setTransactionPromise, _, clearTransaction] = useWeb3Transaction();
  const assetDecimals = props.assetBalance?.assetDecimals || 18;
  const assetSymbol = props.assetBalance?.assetSymbol || 'ETH';
  const userBalanceValue = props.assetBalance?.balance || 0n;
  const userBalanceNumber = Number(userBalanceValue) / (10 ** assetDecimals);
  const [amount, setAmount] = React.useState<string>('');
  const [hasInitializedAmount, setHasInitializedAmount] = React.useState<boolean>(false);
  React.useEffect((): void => {
    if (!hasInitializedAmount && userBalanceNumber > 0 && !props.isLoadingBalance) {
      setAmount(userBalanceNumber.toString());
      setHasInitializedAmount(true);
    }
  }, [userBalanceNumber, hasInitializedAmount, props.isLoadingBalance]);
  const amountNumber = parseFloat(amount) || 0;
  const amountBigInt = React.useMemo((): bigint => {
    try {
      if (Number.isNaN(amountNumber) || amountNumber <= 0) {
        return 0n;
      }
      return BigInt(Math.floor(amountNumber * (10 ** assetDecimals)));
    } catch {
      return 0n;
    }
  }, [amountNumber, assetDecimals]);
  const isAmountValid = amountBigInt > 0n && amountBigInt <= userBalanceValue;
  const isWalletTransferring = transactionDetails.transactionPromise != null || transactionDetails.transaction != null;
  const transferError = transactionDetails?.error;
  const transferSuccessReceipt = transactionDetails?.receipt;
  const isTransferring = isWalletTransferring;
  const isSuccess = !!transferSuccessReceipt;
  const createDepositTransaction = React.useCallback(async (assetAddress: string, transferAmount: string, decimals: number): Promise<void> => {
    if (!accountSigner || !web3) {
      throw new Error('Wallet not connected');
    }
    const amountToTransfer = BigInt((Number(transferAmount) * 10 ** decimals).toFixed(0));
    const tokenAbi = ['function transfer(address to, uint256 amount) public returns (bool)'];
    const tokenContract = new ethers.Contract(assetAddress, tokenAbi, accountSigner);
    const transactionPromise = tokenContract.transfer(props.agentWalletAddress, amountToTransfer);
    setTransactionPromise(transactionPromise);
  }, [accountSigner, web3, props.agentWalletAddress, setTransactionPromise]);
  const onDepositClicked = async (): Promise<void> => {
    if (!isAmountValid || !props.assetBalance) {
      return;
    }
    try {
      await createDepositTransaction(props.assetBalance.assetAddress, amount, props.assetBalance.assetDecimals);
    } catch (newTransferError: unknown) {
      console.error('Transfer failed:', newTransferError);
    }
  };
  const onMaxClicked = (): void => {
    setAmount(userBalanceNumber.toString());
  };
  const onDoneClicked = (): void => {
    clearTransaction();
    props.onDepositSuccess();
  };
  const onRetryClicked = (): void => {
    clearTransaction();
  };
  const needsNetworkSwitch = chainId !== BASE_CHAIN_ID;
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
  if (needsNetworkSwitch) {
    return (
      <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center} isFullWidth={true}>
        <Text variant='note' alignment={TextAlignment.Center}>You need to switch to Base network to make this transaction.</Text>
        <Spacing />
        <Button variant='primary' text='Switch Network' onClicked={(): Promise<void> => onSwitchToWeb3ChainIdClicked(BASE_CHAIN_ID)} isFullWidth={true} />
      </Stack>
    );
  }
  return (
    <Stack direction={Direction.Vertical} isFullWidth={true}>
      <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
        <Text variant='note'>Your balance:</Text>
        <Spacing variant={PaddingSize.Narrow} />
        {props.isLoadingBalance ? (
          <Box variant='shimmer' height='1.25rem' width='8rem' />
        ) : (
          <Text variant='value'>{`${formatBalance(userBalanceValue, assetDecimals)} ${assetSymbol}`}</Text>
        )}
        <Stack.Item growthFactor={1} shrinkFactor={1}>
          <Spacing />
        </Stack.Item>
        <Button variant='tertiary-small' text='Max' onClicked={onMaxClicked} isEnabled={!props.isLoadingBalance} />
      </Stack>
      {props.isLoadingBalance ? (
        <Box variant='shimmer' height='2.5rem' isFullWidth={true} />
      ) : (
        <SingleLineInput
          inputType={InputType.Number}
          value={amount}
          onValueChanged={setAmount}
          placeholderText={`Amount in ${assetSymbol}`}
        />
      )}
      <Spacing variant={PaddingSize.Narrow} />
      <Button variant='primary' text='Deposit to Agent' onClicked={onDepositClicked} isFullWidth={true} isEnabled={isAmountValid && !props.isLoadingBalance} />
    </Stack>
  );
}
