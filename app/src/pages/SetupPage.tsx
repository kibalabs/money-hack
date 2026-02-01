import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, Image, InputType, KibaIcon, PaddingSize, SelectableView, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';
import { useToastManager } from '@kibalabs/ui-react-toast';

import { useAuth } from '../AuthContext';
import { CollateralAsset } from '../client/resources';
import { useGlobals } from '../GlobalsContext';

const LTV_OPTIONS = [
  { value: 0.65, label: '65%', description: 'Conservative' },
  { value: 0.70, label: '70%', description: 'Moderate' },
  { value: 0.75, label: '75%', description: 'Standard' },
  { value: 0.80, label: '80%', description: 'Aggressive' },
];

export function SetupPage(): React.ReactElement {
  const { accountAddress, authToken, isWeb3AccountLoggedIn } = useAuth();
  const { moneyHackClient } = useGlobals();
  const navigator = useNavigator();
  const toastManager = useToastManager();

  const [step, setStep] = React.useState<'telegram' | 'collateral' | 'ltv' | 'deposit'>('telegram');
  const [telegramHandle, setTelegramHandle] = React.useState<string>('');
  const [selectedCollateral, setSelectedCollateral] = React.useState<CollateralAsset | null>(null);
  const [targetLtv, setTargetLtv] = React.useState<number>(0.75);
  const [depositAmount, setDepositAmount] = React.useState<string>('');
  const [collaterals, setCollaterals] = React.useState<CollateralAsset[]>([]);
  const [isLoading, setIsLoading] = React.useState<boolean>(false);
  const [isLoadingCollaterals, setIsLoadingCollaterals] = React.useState<boolean>(true);

  React.useEffect(() => {
    if (!isWeb3AccountLoggedIn) {
      navigator.navigateTo('/');
    }
  }, [isWeb3AccountLoggedIn, navigator]);

  React.useEffect(() => {
    const loadCollaterals = async (): Promise<void> => {
      if (!accountAddress || !authToken) return;
      try {
        setIsLoadingCollaterals(true);
        const supportedCollaterals = await moneyHackClient.getSupportedCollaterals(authToken);
        setCollaterals(supportedCollaterals);
        if (supportedCollaterals.length > 0) {
          setSelectedCollateral(supportedCollaterals[0]);
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

  const handleTelegramNext = React.useCallback((): void => {
    setStep('collateral');
  }, []);

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

  const handleDeposit = React.useCallback(async (): Promise<void> => {
    if (!accountAddress || !selectedCollateral || !authToken) return;

    const amount = parseFloat(depositAmount);
    if (Number.isNaN(amount) || amount <= 0) {
      toastManager.showTextToast('Please enter a valid deposit amount', 'error');
      return;
    }

    setIsLoading(true);
    try {
      await moneyHackClient.updateUserConfig(
        accountAddress,
        telegramHandle || null,
        targetLtv,
        authToken,
      );

      const collateralAmount = BigInt(Math.floor(amount * (10 ** selectedCollateral.decimals)));
      await moneyHackClient.createPosition(
        accountAddress,
        selectedCollateral.address,
        collateralAmount,
        targetLtv,
        authToken,
      );

      toastManager.showTextToast('Position created successfully!', 'success');
      navigator.navigateTo('/agent');
    } catch (error) {
      console.error('Failed to create position:', error);
      toastManager.showTextToast('Failed to create position', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [accountAddress, authToken, selectedCollateral, depositAmount, telegramHandle, targetLtv, moneyHackClient, toastManager, navigator]);

  const handleBack = React.useCallback((): void => {
    if (step === 'collateral') setStep('telegram');
    else if (step === 'ltv') setStep('collateral');
    else if (step === 'deposit') setStep('ltv');
  }, [step]);

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
      <Text variant='note'>
        Step
        {step === 'telegram' ? '1' : step === 'collateral' ? '2' : step === 'ltv' ? '3' : '4'}
        {' '}
        of 4
      </Text>
      <Spacing variant={PaddingSize.Wide} />

      {step === 'telegram' && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Telegram Notifications</Text>
          <Text alignment={TextAlignment.Center}>Enter your Telegram handle to receive position updates and alerts (optional)</Text>
          <Spacing />
          <SingleLineInput
            inputType={InputType.Text}
            value={telegramHandle}
            onValueChanged={setTelegramHandle}
            placeholderText='@yourusername'
            inputWrapperVariant='dialogInput'
          />
          <Spacing />
          <Button variant='primary' text='Continue' onClicked={handleTelegramNext} isFullWidth={true} />
          <Button variant='tertiary' text='Skip for now' onClicked={handleTelegramNext} />
        </Stack>
      )}

      {step === 'collateral' && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Select Collateral</Text>
          <Text alignment={TextAlignment.Center}>Choose which asset you want to deposit as collateral</Text>
          <Spacing />
          {isLoadingCollaterals ? (
            <Text>Loading collaterals...</Text>
          ) : (
            <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
              {collaterals.map((collateral): React.ReactElement => (
                <Box key={collateral.address} isFullWidth={true}>
                  <SelectableView
                    isSelected={selectedCollateral?.address === collateral.address}
                    isFullWidth={true}
                    onClicked={(): void => setSelectedCollateral(collateral)}
                  >
                    <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true}>
                      {collateral.logoUri && (
                        <Box width='32px' height='32px'>
                          <Image source={collateral.logoUri} alternativeText={collateral.symbol} isFullWidth={true} isFullHeight={true} />
                        </Box>
                      )}
                      <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                        <Text variant='bold'>{collateral.symbol}</Text>
                        <Text variant='note'>{collateral.name}</Text>
                      </Stack>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      {selectedCollateral?.address === collateral.address && (
                        <KibaIcon iconId='ion-checkmark-circle' _color='var(--kiba-color-primary)' />
                      )}
                    </Stack>
                  </SelectableView>
                </Box>
              ))}
            </Stack>
          )}
          <Spacing />
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
            <Button variant='secondary' text='Back' onClicked={handleBack} />
            <Stack.Item growthFactor={1} shrinkFactor={1}>
              <Button variant='primary' text='Continue' onClicked={handleCollateralNext} isFullWidth={true} isEnabled={!!selectedCollateral} />
            </Stack.Item>
          </Stack>
        </Stack>
      )}

      {step === 'ltv' && (
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} maxWidth='400px' isFullWidth={true}>
          <Text variant='header3' alignment={TextAlignment.Center}>Target LTV</Text>
          <Text alignment={TextAlignment.Center}>Select your target Loan-to-Value ratio. Higher LTV means more borrowing but higher liquidation risk.</Text>
          <Spacing />
          <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
            {LTV_OPTIONS.map((option): React.ReactElement => (
              <Box key={option.value} isFullWidth={true}>
                <SelectableView
                  isSelected={targetLtv === option.value}
                  isFullWidth={true}
                  onClicked={(): void => setTargetLtv(option.value)}
                >
                  <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true}>
                    <Text variant='bold'>{option.label}</Text>
                    <Text variant='note'>{option.description}</Text>
                    <Stack.Item growthFactor={1} shrinkFactor={1} />
                    {targetLtv === option.value && (
                      <KibaIcon iconId='ion-checkmark-circle' _color='var(--kiba-color-primary)' />
                    )}
                  </Stack>
                </SelectableView>
              </Box>
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
          </Stack>
          <SingleLineInput
            inputType={InputType.Number}
            value={depositAmount}
            onValueChanged={setDepositAmount}
            placeholderText='0.00'
            inputWrapperVariant='dialogInput'
          />
          <Spacing />
          <Box variant='card' isFullWidth={true}>
            <Stack direction={Direction.Vertical} shouldAddGutters={true} paddingHorizontal={PaddingSize.Default} paddingVertical={PaddingSize.Default}>
              <Text variant='note'>Summary</Text>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Telegram:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>{telegramHandle || 'Not set'}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Collateral:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>{selectedCollateral.symbol}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Target LTV:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>
                  {(targetLtv * 100).toFixed(0)}
                  %
                </Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Est. USDC Borrow:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>
                  $
                  {calculateBorrowAmount()}
                </Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text>Est. Yield APY:</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text variant='bold'>~8%</Text>
              </Stack>
            </Stack>
          </Box>
          <Spacing />
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
            <Button variant='secondary' text='Back' onClicked={handleBack} />
            <Stack.Item growthFactor={1} shrinkFactor={1}>
              <Button
                variant='primary'
                text='Deposit & Start Earning'
                onClicked={handleDeposit}
                isFullWidth={true}
                isLoading={isLoading}
                isEnabled={!!depositAmount && parseFloat(depositAmount) > 0}
              />
            </Stack.Item>
          </Stack>
        </Stack>
      )}
    </Stack>
  );
}
