import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, Image, InputType, KibaIcon, Link, LoadingSpinner, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useToastManager } from '@kibalabs/ui-react-toast';
import { useWeb3Transaction } from '@kibalabs/web3-react';

import { useAuth } from '../AuthContext';
import { AssetBalance, CollateralAsset, CollateralMarketData, MarketData, PositionTransactions, TransactionCall, Wallet } from '../client/resources';
import { useGlobals } from '../GlobalsContext';

import './SetupPage.scss';

const LTV_OPTIONS = [
  { value: 0.65, label: '65%', description: 'Conservative' },
  { value: 0.70, label: '70%', description: 'Moderate' },
  { value: 0.75, label: '75%', description: 'Standard' },
  { value: 0.80, label: '80%', description: 'Aggressive' },
];

export function SetupPage(): React.ReactElement {
  const { accountAddress, accountSigner, authToken, isWeb3AccountLoggedIn } = useAuth();
  const { moneyHackClient } = useGlobals();
  const navigator = useNavigator();
  const toastManager = useToastManager();
  const [transactionDetails, setTransactionPromise, _, clearTransaction] = useWeb3Transaction();

  const [step, setStep] = React.useState<'collateral' | 'ltv' | 'deposit' | 'telegram' | 'executing'>('collateral');
  const [telegramChatId, setTelegramChatId] = React.useState<string | null>(null);
  const [isTelegramConnecting, setIsTelegramConnecting] = React.useState<boolean>(false);
  const [selectedCollateral, setSelectedCollateral] = React.useState<CollateralAsset | null>(null);
  const [targetLtv, setTargetLtv] = React.useState<number>(0.75);
  const [depositAmount, setDepositAmount] = React.useState<string>('');
  const [collaterals, setCollaterals] = React.useState<CollateralAsset[]>([]);
  const [marketData, setMarketData] = React.useState<MarketData | null>(null);
  const [wallet, setWallet] = React.useState<Wallet | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(false);
  const [isLoadingCollaterals, setIsLoadingCollaterals] = React.useState<boolean>(true);
  const [positionTransactions, setPositionTransactions] = React.useState<PositionTransactions | null>(null);
  const [currentTxIndex, setCurrentTxIndex] = React.useState<number>(0);
  const [completedTxHashes, setCompletedTxHashes] = React.useState<string[]>([]);
  const [transactionError, setTransactionError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!isWeb3AccountLoggedIn) {
      navigator.navigateTo('/');
    }
  }, [isWeb3AccountLoggedIn, navigator]);

  React.useEffect(() => {
    const handleTelegramCallback = async (): Promise<void> => {
      const params = new URLSearchParams(window.location.search);
      const secretCode = params.get('telegramSecret');
      if (!secretCode || !accountAddress || !authToken) return;
      try {
        const authData = {
          id: params.get('id'),
          first_name: params.get('first_name'),
          last_name: params.get('last_name'),
          username: params.get('username'),
          photo_url: params.get('photo_url'),
          auth_date: params.get('auth_date'),
          hash: params.get('hash'),
        };
        const filteredAuthData = Object.fromEntries(Object.entries(authData).filter(([, v]) => v != null));
        const result = await moneyHackClient.verifyTelegramCode(accountAddress, secretCode, filteredAuthData, authToken);
        setTelegramChatId(String(result.telegramChatId));
        toastManager.showTextToast('Telegram connected successfully!', 'success');
        window.history.replaceState({}, document.title, window.location.pathname);
      } catch (error) {
        console.error('Failed to verify Telegram code:', error);
        toastManager.showTextToast('Failed to connect Telegram. Please try again.', 'error');
      }
    };
    handleTelegramCallback();
  }, [accountAddress, authToken, moneyHackClient, toastManager]);

  React.useEffect(() => {
    const loadCollaterals = async (): Promise<void> => {
      if (!accountAddress || !authToken) return;
      try {
        setIsLoadingCollaterals(true);
        const [supportedCollaterals, fetchedMarketData, fetchedWallet] = await Promise.all([
          moneyHackClient.getSupportedCollaterals(authToken),
          moneyHackClient.getMarketData(),
          moneyHackClient.getWallet(accountAddress, authToken),
        ]);
        setCollaterals(supportedCollaterals);
        setMarketData(fetchedMarketData);
        setWallet(fetchedWallet);
        const firstWithBalance = supportedCollaterals.find((collateral) => {
          const balance = fetchedWallet.assetBalances.find((b) => b.assetAddress.toLowerCase() === collateral.address.toLowerCase());
          return balance && balance.balance > 0n;
        });
        if (firstWithBalance) {
          setSelectedCollateral(firstWithBalance);
        }
      } catch (error) {
        console.error('Failed to load collaterals:', error);
        toastManager.showTextToast('Failed to load supported collaterals', 'error');
      } finally {
        setIsLoadingCollaterals(false);
      }
    };
    loadCollaterals();
  }, [accountAddress, authToken, moneyHackClient, toastManager]);

  const getCollateralMarketData = React.useCallback((collateralAddress: string): CollateralMarketData | null => {
    if (!marketData) return null;
    return marketData.collateralMarkets.find((m) => m.collateralAddress.toLowerCase() === collateralAddress.toLowerCase()) ?? null;
  }, [marketData]);

  const getAssetBalance = React.useCallback((collateralAddress: string): AssetBalance | null => {
    if (!wallet) return null;
    return wallet.assetBalances.find((ab) => ab.assetAddress.toLowerCase() === collateralAddress.toLowerCase()) ?? null;
  }, [wallet]);

  const formatBalance = React.useCallback((balance: bigint, decimals: number): string => {
    const balanceNum = Number(balance) / (10 ** decimals);
    if (balanceNum === 0) return '0';
    if (balanceNum < 0.0001) return '<0.0001';
    if (balanceNum < 1) return balanceNum.toFixed(4);
    if (balanceNum < 1000) return balanceNum.toFixed(4);
    return balanceNum.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }, []);

  const selectedCollateralBalance = React.useMemo((): AssetBalance | null => {
    if (!selectedCollateral) return null;
    return getAssetBalance(selectedCollateral.address);
  }, [selectedCollateral, getAssetBalance]);

  const handleMaxClicked = React.useCallback((): void => {
    if (!selectedCollateralBalance || !selectedCollateral) return;
    const balanceNum = Number(selectedCollateralBalance.balance) / (10 ** selectedCollateral.decimals);
    setDepositAmount(balanceNum.toString());
  }, [selectedCollateralBalance, selectedCollateral]);

  const handleCollateralNext = React.useCallback((): void => {
    if (!selectedCollateral) {
      toastManager.showTextToast('Please select a collateral type', 'error');
      return;
    }
    setStep('ltv');
  }, [selectedCollateral, toastManager]);

  const handleLtvNext = React.useCallback((): void => {
    setStep('deposit');
  }, []);

  const handleDepositNext = React.useCallback((): void => {
    const amount = parseFloat(depositAmount);
    if (Number.isNaN(amount) || amount <= 0) {
      toastManager.showTextToast('Please enter a valid deposit amount', 'error');
      return;
    }
    setStep('telegram');
  }, [depositAmount, toastManager]);

  const handleConnectTelegram = React.useCallback(async (): Promise<void> => {
    if (!accountAddress || !authToken) return;
    try {
      setIsTelegramConnecting(true);
      const loginUrl = await moneyHackClient.getTelegramLoginUrl(accountAddress, authToken);
      window.location.href = loginUrl;
    } catch (error) {
      console.error('Failed to get Telegram login URL:', error);
      toastManager.showTextToast('Failed to connect Telegram. Please try again.', 'error');
      setIsTelegramConnecting(false);
    }
  }, [accountAddress, authToken, moneyHackClient, toastManager]);

  const handleCreatePosition = React.useCallback(async (): Promise<void> => {
    if (!accountAddress || !selectedCollateral || !authToken || !accountSigner) return;
    if (!telegramChatId) {
      toastManager.showTextToast('Please connect your Telegram to continue', 'error');
      return;
    }
    const amount = parseFloat(depositAmount);
    if (Number.isNaN(amount) || amount <= 0) {
      toastManager.showTextToast('Please enter a valid deposit amount', 'error');
      return;
    }
    setIsLoading(true);
    setTransactionError(null);
    try {
      const collateralAmount = BigInt(Math.floor(amount * (10 ** selectedCollateral.decimals)));
      const transactions = await moneyHackClient.getPositionTransactions(
        accountAddress,
        selectedCollateral.address,
        collateralAmount,
        targetLtv,
        authToken,
      );
      setPositionTransactions(transactions);
      setCurrentTxIndex(0);
      setCompletedTxHashes([]);
      setStep('executing');
    } catch (error) {
      console.error('Failed to prepare position:', error);
      toastManager.showTextToast('Failed to prepare position', 'error');
      setIsLoading(false);
    }
  }, [accountAddress, accountSigner, authToken, selectedCollateral, depositAmount, telegramChatId, targetLtv, moneyHackClient, toastManager]);

  const executeNextTransaction = React.useCallback(async (): Promise<void> => {
    if (!positionTransactions || !accountSigner || currentTxIndex >= positionTransactions.transactions.length) return;
    const tx = positionTransactions.transactions[currentTxIndex];
    try {
      const transactionPromise = accountSigner.sendTransaction({
        to: tx.to,
        data: tx.data,
        value: BigInt(tx.value),
      });
      setTransactionPromise(transactionPromise);
    } catch (error) {
      console.error('Failed to send transaction:', error);
      setTransactionError(error instanceof Error ? error.message : 'Transaction failed');
    }
  }, [positionTransactions, accountSigner, currentTxIndex, setTransactionPromise]);

  const handleFinishPosition = React.useCallback(async (): Promise<void> => {
    if (!accountAddress || !selectedCollateral || !authToken) return;
    try {
      const amount = parseFloat(depositAmount);
      const collateralAmount = BigInt(Math.floor(amount * (10 ** selectedCollateral.decimals)));
      await moneyHackClient.createPosition(accountAddress, selectedCollateral.address, collateralAmount, targetLtv, authToken);
      toastManager.showTextToast('Position created successfully!', 'success');
      navigator.navigateTo('/agent');
    } catch (error) {
      console.error('Failed to save position:', error);
      toastManager.showTextToast('Failed to save position', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [accountAddress, authToken, selectedCollateral, depositAmount, targetLtv, moneyHackClient, toastManager, navigator]);

  React.useEffect((): void => {
    if (step !== 'executing' || !positionTransactions) return;
    if (transactionDetails.receipt) {
      setCompletedTxHashes((prev) => [...prev, transactionDetails.receipt!.hash]);
      clearTransaction();
      if (currentTxIndex + 1 >= positionTransactions.transactions.length) {
        handleFinishPosition();
      } else {
        setCurrentTxIndex((prev) => prev + 1);
      }
    } else if (transactionDetails.error) {
      setTransactionError(transactionDetails.error.message || 'Transaction failed');
    }
  }, [step, positionTransactions, transactionDetails, currentTxIndex, clearTransaction, handleFinishPosition]);

  React.useEffect((): void => {
    if (step === 'executing' && positionTransactions && currentTxIndex < positionTransactions.transactions.length && !transactionDetails.transactionPromise && !transactionDetails.receipt && !transactionError) {
      executeNextTransaction();
    }
  }, [step, positionTransactions, currentTxIndex, transactionDetails, transactionError, executeNextTransaction]);

  const getTransactionLabel = React.useCallback((index: number): string => {
    const labels = ['Approve collateral', 'Supply collateral', 'Borrow USDC', 'Approve USDC', 'Deposit to vault'];
    return labels[index] || `Transaction ${index + 1}`;
  }, []);

  const handleBack = React.useCallback((): void => {
    if (step === 'ltv') setStep('collateral');
    else if (step === 'deposit') setStep('ltv');
    else if (step === 'telegram') setStep('deposit');
  }, [step]);

  const getStepNumber = (): string => {
    if (step === 'collateral') return '1';
    if (step === 'ltv') return '2';
    if (step === 'deposit') return '3';
    return '4';
  };

  const calculateBorrowAmount = (): string => {
    const amount = parseFloat(depositAmount);
    if (Number.isNaN(amount) || amount <= 0) return '0.00';
    const collateralValueUsd = amount * 3500;
    const borrowAmount = collateralValueUsd * targetLtv;
    return borrowAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  if (!isWeb3AccountLoggedIn) {
    return <Text>Redirecting...</Text>;
  }

  return (
    <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide2} paddingVertical={PaddingSize.Wide2} isFullHeight={true}>
      <Text variant='header2'>Set Up BorrowBot</Text>
      <Text variant='note'>{`Step ${getStepNumber()} of 4`}</Text>
      <Spacing variant={PaddingSize.Wide} />

      {step === 'collateral' && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Select Collateral</Text>
          <Text alignment={TextAlignment.Center}>Choose which asset you want to deposit as collateral</Text>
          <Spacing />
          {isLoadingCollaterals ? (
            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true}>
              <Text>Loading collaterals...</Text>
              <Text variant='note'>Fetching live rates from Morpho & 40acres</Text>
            </Stack>
          ) : (
            <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
              {collaterals.map((collateral: CollateralAsset): React.ReactElement => {
                const collateralMarket = getCollateralMarketData(collateral.address);
                const assetBalance = getAssetBalance(collateral.address);
                const hasBalance = assetBalance && assetBalance.balance > 0n;
                const isDisabled = !hasBalance;
                return (
                  <button
                    key={collateral.address}
                    type='button'
                    className={`selectionCard ${selectedCollateral?.address === collateral.address ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                    onClick={(): void => { if (!isDisabled) setSelectedCollateral(collateral); }}
                    disabled={isDisabled}
                  >
                    <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true}>
                      {collateral.logoUri && (
                        <Box width='32px' height='32px'>
                          <Image source={collateral.logoUri} alternativeText={collateral.symbol} isFullWidth={true} isFullHeight={true} />
                        </Box>
                      )}
                      <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                        <Text variant='bold'>{collateral.symbol}</Text>
                        {hasBalance ? (
                          <Text variant='note'>{`Balance: ${formatBalance(assetBalance.balance, collateral.decimals)} ($${assetBalance.balanceUsd.toFixed(2)})`}</Text>
                        ) : (
                          <Text variant='note'>No balance</Text>
                        )}
                        {collateralMarket && (
                          <Text variant='note'>
                            {`Borrow: ${(collateralMarket.borrowApy * 100).toFixed(2)}% • Max LTV: ${(collateralMarket.maxLtv * 100).toFixed(0)}%`}
                          </Text>
                        )}
                      </Stack>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      {selectedCollateral?.address === collateral.address && (
                        <KibaIcon iconId='ion-checkmark-circle' variant='large' />
                      )}
                    </Stack>
                  </button>
                );
              })}
              {marketData && (
                <Box isFullWidth={true}>
                  <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Default} paddingVertical={PaddingSize.Narrow}>
                    <Text variant='default'>{`Yield vault: ${marketData.yieldVaultName}`}</Text>
                    <Text variant='default-success'>{`${(marketData.yieldApy * 100).toFixed(2)}% APY`}</Text>
                  </Stack>
                </Box>
              )}
            </Stack>
          )}
          <Spacing />
          <Button variant='primary' text='Continue' onClicked={handleCollateralNext} isFullWidth={true} isEnabled={!!selectedCollateral} />
        </Stack>
      )}

      {step === 'ltv' && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Target LTV</Text>
          <Text alignment={TextAlignment.Center}>Select your target Loan-to-Value ratio. Higher LTV means more borrowing but higher liquidation risk.</Text>
          <Spacing />
          <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
            {LTV_OPTIONS.map((option): React.ReactElement => (
              <button
                key={option.value}
                type='button'
                className={`ltvCard ${targetLtv === option.value ? 'selected' : ''}`}
                onClick={(): void => setTargetLtv(option.value)}
              >
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true}>
                  <Text variant='bold'>{option.label}</Text>
                  <Text variant='note'>{option.description}</Text>
                  <Stack.Item growthFactor={1} shrinkFactor={1} />
                  {targetLtv === option.value && (
                    <KibaIcon iconId='ion-checkmark-circle' variant='large' />
                  )}
                </Stack>
              </button>
            ))}
          </Stack>
          <Spacing />
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
            <Button variant='secondary' text='Back' onClicked={handleBack} />
            <Stack.Item growthFactor={1} shrinkFactor={1}>
              <Button variant='primary' text='Continue' onClicked={handleLtvNext} isFullWidth={true} />
            </Stack.Item>
          </Stack>
        </Stack>
      )}

      {step === 'deposit' && selectedCollateral && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Deposit Collateral</Text>
          <Text alignment={TextAlignment.Center}>
            Enter the amount of
            {' '}
            {selectedCollateral.symbol}
            {' '}
            to deposit
          </Text>
          <Spacing />
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true} isFullWidth={true}>
            {selectedCollateral.logoUri && (
              <Box width='24px' height='24px'>
                <Image source={selectedCollateral.logoUri} alternativeText={selectedCollateral.symbol} isFullWidth={true} isFullHeight={true} />
              </Box>
            )}
            <Text variant='bold'>{selectedCollateral.symbol}</Text>
            {selectedCollateralBalance && (
              <Stack.Item growthFactor={1} shrinkFactor={1}>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
                  <Text variant='note'>{`Balance: ${formatBalance(selectedCollateralBalance.balance, selectedCollateral.decimals)} ($${selectedCollateralBalance.balanceUsd.toFixed(2)})`}</Text>
                  <Stack.Item growthFactor={1} shrinkFactor={1} />
                  <Button variant='tertiary-small' text='Max' onClicked={handleMaxClicked} isEnabled={selectedCollateralBalance.balance > 0n} />
                </Stack>
              </Stack.Item>
            )}
          </Stack>
          <SingleLineInput
            inputType={InputType.Number}
            value={depositAmount}
            onValueChanged={setDepositAmount}
            placeholderText='0.00'
            inputWrapperVariant='dialogInput'
          />
          <Spacing />
          <Box isFullWidth={true}>
            <Stack direction={Direction.Vertical} shouldAddGutters={true} paddingHorizontal={PaddingSize.Default} paddingVertical={PaddingSize.Default}>
              <Text variant='note'>Summary</Text>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Collateral:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>{selectedCollateral.symbol}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Target LTV:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>{`${(targetLtv * 100).toFixed(0)}%`}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Est. USDC Borrow:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>{`$${calculateBorrowAmount()}`}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Borrow APY:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>
                  {getCollateralMarketData(selectedCollateral.address) ? `${(getCollateralMarketData(selectedCollateral.address)!.borrowApy * 100).toFixed(2)}%` : '~3%'}
                </Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>{`Yield APY (${marketData?.yieldVaultName ?? '40acres'}):`}</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>
                  {marketData ? `${(marketData.yieldApy * 100).toFixed(2)}%` : '~8%'}
                </Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Est. Net APY:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold-success'>
                  {marketData && getCollateralMarketData(selectedCollateral.address)
                    ? `${((marketData.yieldApy - getCollateralMarketData(selectedCollateral.address)!.borrowApy) * 100).toFixed(2)}%`
                    : '~5%'}
                </Text>
              </Stack>
            </Stack>
          </Box>
          <Spacing />
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
            <Button variant='secondary' text='Back' onClicked={handleBack} />
            <Stack.Item growthFactor={1} shrinkFactor={1}>
              <Button
                variant='primary'
                text='Continue'
                onClicked={handleDepositNext}
                isFullWidth={true}
                isEnabled={!!depositAmount && parseFloat(depositAmount) > 0}
              />
            </Stack.Item>
          </Stack>
        </Stack>
      )}

      {step === 'telegram' && selectedCollateral && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Connect Telegram</Text>
          <Spacing />
          <Text alignment={TextAlignment.Center}>BorrowBot monitors your position 24/7 and automatically adjusts your loan to prevent liquidation. Telegram notifications are required so you stay informed about important actions taken on your behalf.</Text>
          <Spacing />
          <Text alignment={TextAlignment.Center} variant='note'>You will receive alerts for: position adjustments, LTV warnings, yield updates, and any actions requiring your attention.</Text>
          <Spacing />
          {telegramChatId ? (
            <Box width='100%'>
              <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true} isFullWidth={true}>
                <Text alignment={TextAlignment.Left}>✓ Telegram connected</Text>
              </Stack>
            </Box>
          ) : (
            <Button
              variant='secondary'
              text='Connect Telegram'
              onClicked={handleConnectTelegram}
              isFullWidth={true}
              isLoading={isTelegramConnecting}
            />
          )}
          <Spacing />
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
            <Button variant='secondary' text='Back' onClicked={handleBack} />
            <Stack.Item growthFactor={1} shrinkFactor={1}>
              <Button
                variant='primary'
                text='Create Position'
                onClicked={handleCreatePosition}
                isFullWidth={true}
                isLoading={isLoading}
                isEnabled={!!telegramChatId}
              />
            </Stack.Item>
          </Stack>
        </Stack>
      )}

      {step === 'executing' && positionTransactions && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Creating Position</Text>
          <Spacing />
          <Text alignment={TextAlignment.Center}>Please confirm each transaction in your wallet to complete the position setup.</Text>
          <Spacing variant={PaddingSize.Wide} />
          {positionTransactions.transactions.map((tx: TransactionCall, index: number) => (
            // eslint-disable-next-line react/no-array-index-key
            <Stack key={`tx-${index}`} direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true} childAlignment={Alignment.Center}>
              <Box variant='rounded' shouldClipContent={true} width='24px' height='24px'>
                {index < completedTxHashes.length ? (
                  <KibaIcon iconId='ion-checkmark-circle' variant='small' />
                ) : index === currentTxIndex && transactionDetails.transactionPromise ? (
                  <LoadingSpinner variant='small' />
                ) : (
                  <Text>{index + 1}</Text>
                )}
              </Box>
              <Stack.Item growthFactor={1} shrinkFactor={1}>
                <Text>{getTransactionLabel(index)}</Text>
              </Stack.Item>
              {index < completedTxHashes.length && (
                <Link text='View' target={`https://basescan.org/tx/${completedTxHashes[index]}`} />
              )}
            </Stack>
          ))}
          {transactionError && (
            <React.Fragment>
              <Spacing />
              <Text variant='error' alignment={TextAlignment.Center}>{transactionError}</Text>
              <Spacing />
              <Button
                variant='secondary'
                text='Retry'
                onClicked={() => {
                  setTransactionError(null);
                  clearTransaction();
                  executeNextTransaction();
                }}
              />
            </React.Fragment>
          )}
        </Stack>
      )}
    </Stack>
  );
}
