import React from 'react';

import { Alignment, Box, Button, Dialog, Direction, InputType, PaddingSize, SingleLineInput, Spacing, Stack, Text } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';
import { Position, WithdrawPreview } from '../client/resources';
import { useGlobals } from '../GlobalsContext';

import './WithdrawDialog.scss';

interface IWithdrawDialogProps {
  position: Position;
  onCloseClicked: () => void;
  onWithdrawConfirmed: (amount: bigint) => void;
}

const USDC_DECIMALS = 6;

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

const formatUsdcRaw = (raw: bigint): string => {
  const isNeg = raw < 0n;
  const abs = isNeg ? -raw : raw;
  const whole = abs / BigInt(10 ** USDC_DECIMALS);
  const frac = abs % BigInt(10 ** USDC_DECIMALS);
  const fracStr = frac.toString().padStart(USDC_DECIMALS, '0').replace(/0+$/, '') || '0';
  return `${isNeg ? '-' : ''}${whole.toLocaleString()}.${fracStr}`;
};

const formatPercent = (value: number): string => `${(value * 100).toFixed(2)}%`;

export function WithdrawDialog(props: IWithdrawDialogProps): React.ReactElement {
  const { accountAddress, authToken } = useAuth();
  const { moneyHackClient } = useGlobals();

  const [amountText, setAmountText] = React.useState<string>('');
  const [preview, setPreview] = React.useState<WithdrawPreview | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = React.useState<boolean>(false);
  const [isConfirmStep, setIsConfirmStep] = React.useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [errorText, setErrorText] = React.useState<string | null>(null);

  const amountRaw = React.useMemo((): bigint | null => parseUsdcAmount(amountText), [amountText]);

  React.useEffect(() => {
    if (!accountAddress || !authToken || !amountRaw || amountRaw <= 0n) {
      setPreview(null);
      setErrorText(null);
      setIsConfirmStep(false);
      return undefined;
    }
    setIsLoadingPreview(true);
    setErrorText(null);
    setIsConfirmStep(false);
    const timer = setTimeout(async () => {
      try {
        const result = await moneyHackClient.getWithdrawPreview(accountAddress, amountRaw, authToken);
        setPreview(result);
      } catch (error: unknown) {
        setErrorText(error instanceof Error ? error.message : 'Failed to load preview');
        setPreview(null);
      } finally {
        setIsLoadingPreview(false);
      }
    }, 300);
    return (): void => clearTimeout(timer);
  }, [accountAddress, authToken, amountRaw, moneyHackClient]);

  const handleMaxClicked = React.useCallback((): void => {
    if (preview) {
      setAmountText(formatUsdcRaw(preview.maxSafeWithdraw));
    } else {
      setAmountText(formatUsdcRaw(props.position.vaultBalance));
    }
  }, [preview, props.position.vaultBalance]);

  const handleWithdrawClicked = React.useCallback((): void => {
    if (!preview || !amountRaw) return;
    if (preview.isWarning && !isConfirmStep) {
      setIsConfirmStep(true);
      return;
    }
    setIsSubmitting(true);
    props.onWithdrawConfirmed(amountRaw);
  }, [preview, amountRaw, isConfirmStep, props]);

  const vaultBalanceFormatted = formatUsdcRaw(props.position.vaultBalance);
  const afterVaultBalance = amountRaw ? props.position.vaultBalance - amountRaw : props.position.vaultBalance;

  return (
    <Dialog
      onCloseClicked={props.onCloseClicked}
      isOpen={true}
      maxHeight='calc(min(90vh, 700px))'
      maxWidth='calc(min(90vw, 480px))'
    >
      <Stack direction={Direction.Vertical} shouldAddGutters={true}>
        <Text variant='header2'>Withdraw USDC</Text>
        <Spacing variant={PaddingSize.Default} />

        <Box className='withdrawInfoCard'>
          <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
            <Text variant='note'>Vault Balance</Text>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Text variant='bold'>{`$${vaultBalanceFormatted}`}</Text>
          </Stack>
        </Box>

        <Stack direction={Direction.Vertical} shouldAddGutters={true}>
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center}>
            <Text variant='bold'>Amount (USDC)</Text>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Button variant='tertiary-small' text='Max Safe' onClicked={handleMaxClicked} />
          </Stack>
          <SingleLineInput
            inputType={InputType.Number}
            placeholderText='0.00'
            value={amountText}
            onValueChanged={setAmountText}
          />
        </Stack>

        {isLoadingPreview && (
          <Text variant='note'>Calculating...</Text>
        )}

        {preview && !isLoadingPreview && (
          <Box className={`withdrawPreviewCard ${preview.isBlocked ? 'danger' : preview.isWarning ? 'warning' : 'safe'}`}>
            <Stack direction={Direction.Vertical} shouldAddGutters={true}>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text variant='note'>Current LTV</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text>{formatPercent(preview.currentLtv)}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text variant='note'>Estimated New LTV</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text>{formatPercent(preview.estimatedNewLtv)}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text variant='note'>Target LTV</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text>{formatPercent(preview.targetLtv)}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text variant='note'>Vault After Withdrawal</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text>{`$${formatUsdcRaw(afterVaultBalance > 0n ? afterVaultBalance : 0n)}`}</Text>
              </Stack>
              <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                <Text variant='note'>Max Safe Withdraw</Text>
                <Stack.Item growthFactor={1} shrinkFactor={1} />
                <Text>{`$${formatUsdcRaw(preview.maxSafeWithdraw)}`}</Text>
              </Stack>

              {preview.warningMessage && (
                <React.Fragment>
                  <Spacing variant={PaddingSize.Narrow} />
                  <Text variant={preview.isBlocked ? 'error' : 'note-warning'}>{preview.warningMessage}</Text>
                </React.Fragment>
              )}
            </Stack>
          </Box>
        )}

        {errorText && (
          <Text variant='error'>{errorText}</Text>
        )}

        {isConfirmStep && preview?.isWarning && (
          <Box className='withdrawPreviewCard warning'>
            <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
              <Text variant='bold'>Are you sure?</Text>
              <Text variant='note'>This withdrawal reduces the agent&apos;s auto-repay buffer. If the market moves against you, the agent may not have enough USDC to protect your position.</Text>
            </Stack>
          </Box>
        )}

        <Spacing variant={PaddingSize.Default} />
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} contentAlignment={Alignment.Center} isFullWidth={true}>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='tertiary'
              text={isConfirmStep ? 'Back' : 'Cancel'}
              onClicked={isConfirmStep ? (): void => setIsConfirmStep(false) : props.onCloseClicked}
              isFullWidth={true}
            />
          </Stack.Item>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='primary'
              text={isConfirmStep ? 'Confirm Withdrawal' : 'Withdraw'}
              onClicked={handleWithdrawClicked}
              isEnabled={!!preview && !preview.isBlocked && !!amountRaw && amountRaw > 0n && !isLoadingPreview}
              isLoading={isSubmitting}
              isFullWidth={true}
            />
          </Stack.Item>
        </Stack>
      </Stack>
    </Dialog>
  );
}
