import React from 'react';

import { useLocation, useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, IconButton, KibaIcon, LinkBase, LoadingSpinner, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';
import { AssetBalance, CollateralAsset, CollateralMarketData, MarketData, Wallet } from '../client/resources';
import { ContainingView } from '../components/ContainingView';
import { DepositForm } from '../components/DepositForm';
import { GlowingButton, GlowingText } from '../components/GlowingButton';
import { LiFiDepositDialog } from '../components/LiFiDepositDialog';
import { LoadingIndicator } from '../components/LoadingIndicator';
import { StepProgress } from '../components/StepProgress';
import { useGlobals } from '../GlobalsContext';
import { formatBalance } from '../util';

import './FundAgentPage.scss';

interface LtvOption {
  value: number;
  label: string;
  description: string;
  riskLevel: 'low' | 'medium' | 'high';
}

const LTV_OPTIONS: LtvOption[] = [
  { value: 0.5, label: '50%', description: 'Conservative - Lower risk', riskLevel: 'low' },
  { value: 0.65, label: '65%', description: 'Balanced - Moderate risk', riskLevel: 'medium' },
  { value: 0.75, label: '75%', description: 'Aggressive - Higher risk', riskLevel: 'high' },
];

export function FundAgentPage(): React.ReactElement {
  const navigator = useNavigator();
  const location = useLocation();
  const { moneyHackClient } = useGlobals();
  const { accountAddress, authToken, isWeb3AccountLoggedIn } = useAuth();
  const urlParams = new URLSearchParams(location?.search || '');
  const collateralAddress = urlParams.get('collateral');
  const agentId = urlParams.get('agentId');
  const agentWalletAddress = urlParams.get('agentWalletAddress');
  const agentName = urlParams.get('agentName') || 'BorrowBot 1';
  const agentEmoji = urlParams.get('agentEmoji') || '🤖';
  const [collateral, setCollateral] = React.useState<CollateralAsset | null>(null);
  const [agentWallet, setAgentWallet] = React.useState<Wallet | null>(null);
  const [marketData, setMarketData] = React.useState<MarketData | null>(null);
  const [targetLtv, setTargetLtv] = React.useState<number>(0.65);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = React.useState<boolean>(false);
  const [userWallet, setUserWallet] = React.useState<Wallet | null>(null);
  const [isLoadingUserWallet, setIsLoadingUserWallet] = React.useState<boolean>(true);
  const [isLiFiDialogOpen, setIsLiFiDialogOpen] = React.useState<boolean>(false);
  React.useEffect((): void => {
    if (!accountAddress || !authToken || !collateralAddress || !agentId || !agentWalletAddress) {
      navigator.navigateTo('/create-agent');
      return;
    }
    const loadData = async (): Promise<void> => {
      try {
        const [fetchedCollaterals, fetchedAgentWallet, fetchedMarketData] = await Promise.all([
          moneyHackClient.getSupportedCollaterals(authToken),
          moneyHackClient.getWallet(agentWalletAddress, authToken),
          moneyHackClient.getMarketData(),
        ]);
        const selectedCollateral = fetchedCollaterals.find((c) => c.address.toLowerCase() === collateralAddress.toLowerCase());
        if (!selectedCollateral) {
          setError('Selected collateral not found');
          return;
        }
        setCollateral(selectedCollateral);
        setAgentWallet(fetchedAgentWallet);
        setMarketData(fetchedMarketData);
      } catch (caughtError) {
        console.error('Failed to load data:', caughtError);
        setError('Failed to load data');
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountAddress, authToken, collateralAddress, agentId, agentWalletAddress]);
  React.useEffect((): void => {
    if (!accountAddress || !authToken) return;
    const loadUserWallet = async (): Promise<void> => {
      setIsLoadingUserWallet(true);
      try {
        const fetchedUserWallet = await moneyHackClient.getWallet(accountAddress, authToken);
        setUserWallet(fetchedUserWallet);
      } catch (userWalletError) {
        console.error('Failed to load user wallet:', userWalletError);
      } finally {
        setIsLoadingUserWallet(false);
      }
    };
    loadUserWallet();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountAddress, authToken]);
  const handleRefresh = async (): Promise<void> => {
    if (!authToken || !agentWalletAddress || isRefreshing) return;
    setIsRefreshing(true);
    try {
      const [fetchedWallet, fetchedMarketData] = await Promise.all([
        moneyHackClient.getWallet(agentWalletAddress, authToken),
        moneyHackClient.getMarketData(),
      ]);
      setAgentWallet(fetchedWallet);
      setMarketData(fetchedMarketData);
    } catch (refreshError) {
      console.error('Failed to refresh:', refreshError);
    } finally {
      setIsRefreshing(false);
    }
  };
  const collateralBalance = React.useMemo((): AssetBalance | null => {
    if (!agentWallet || !collateral) return null;
    return agentWallet.assetBalances.find((b) => b.assetAddress.toLowerCase() === collateral.address.toLowerCase()) || null;
  }, [agentWallet, collateral]);
  const userCollateralBalance = React.useMemo((): AssetBalance | null => {
    if (!userWallet || !collateral) return null;
    return userWallet.assetBalances.find((b) => b.assetAddress.toLowerCase() === collateral.address.toLowerCase()) || null;
  }, [userWallet, collateral]);
  const hasCollateral = React.useMemo((): boolean => {
    return (collateralBalance?.balance || 0n) > 0n;
  }, [collateralBalance]);
  const collateralMarketData = React.useMemo((): CollateralMarketData | null => {
    if (!marketData || !collateral) return null;
    return marketData.collateralMarkets.find((c) => c.collateralAddress.toLowerCase() === collateral.address.toLowerCase()) || null;
  }, [marketData, collateral]);
  const estimatedBorrowAmount = React.useMemo((): number => {
    if (!collateralBalance) return 0;
    return collateralBalance.balanceUsd * targetLtv;
  }, [collateralBalance, targetLtv]);
  const netApy = React.useMemo((): number => {
    if (!marketData || !collateralMarketData) return 0;
    const yieldApy = marketData.yieldApy;
    const borrowApy = collateralMarketData.borrowApy;
    return (yieldApy - borrowApy) * targetLtv;
  }, [marketData, collateralMarketData, targetLtv]);
  const estimatedYearlyYield = React.useMemo((): number => {
    return estimatedBorrowAmount * netApy;
  }, [estimatedBorrowAmount, netApy]);
  const handleDepositSuccess = async (): Promise<void> => {
    await handleRefresh();
    if (accountAddress && authToken) {
      try {
        const fetchedUserWallet = await moneyHackClient.getWallet(accountAddress, authToken);
        setUserWallet(fetchedUserWallet);
      } catch (userWalletError) {
        console.error('Failed to refresh user wallet:', userWalletError);
      }
    }
  };
  const handleLiFiSuccess = async (): Promise<void> => {
    setIsLiFiDialogOpen(false);
    await handleRefresh();
  };
  const handleContinue = (): void => {
    if (!hasCollateral || !collateral || !collateralBalance) {
      setError('Please send collateral to your agent wallet first');
      return;
    }
    const params = new URLSearchParams({
      collateral: collateral.address,
      amount: collateralBalance.balance.toString(),
      ltv: targetLtv.toString(),
      agentId: agentId || '',
      agentName,
      agentEmoji,
    });
    navigator.navigateTo(`/deploy-agent?${params.toString()}`);
  };
  const handleBack = (): void => {
    navigator.navigateTo('/create-agent');
  };
  if (!isWeb3AccountLoggedIn) {
    return (
      <ContainingView>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} isFullWidth={true}>
          <LoadingIndicator />
        </Stack>
      </ContainingView>
    );
  }
  if (isLoading) {
    return (
      <ContainingView>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} isFullWidth={true}>
          <LoadingSpinner />
          <Spacing />
          <Text>Loading...</Text>
        </Stack>
      </ContainingView>
    );
  }
  if (!collateral || !agentWalletAddress) {
    return (
      <ContainingView>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} isFullWidth={true}>
          <Text variant='error'>Missing required data</Text>
          <Spacing />
          <Button variant='primary' text='Go Back' onClicked={handleBack} />
        </Stack>
      </ContainingView>
    );
  }
  return (
    <ContainingView>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} isFullWidth={true}>
        <Box maxWidth='600px' isFullWidth={true}>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Fill} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide2}>
            <Box maxWidth='300px'>
              <StepProgress currentStep={3} totalSteps={4} />
            </Box>
            <Spacing variant={PaddingSize.Default} />
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldWrapItems={true} shouldAddGutters={true}>
              <Text variant='header1'>Fund</Text>
              <Text variant='header1'>{agentEmoji}</Text>
              <GlowingText variant='header1'>{agentName}</GlowingText>
            </Stack>
            <Text variant='passive'>Send collateral to your agent&apos;s wallet. Your agent will use it to borrow and earn yield.</Text>
            <Spacing variant={PaddingSize.Default} />
            <Box variant='card' className='balanceCard'>
              <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingVertical={PaddingSize.Wide} paddingHorizontal={PaddingSize.Wide}>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true}>
                  <Text>Agent Balance</Text>
                  <IconButton
                    variant='small'
                    icon={<KibaIcon iconId='ion-refresh' variant='small' />}
                    onClicked={handleRefresh}
                    isEnabled={!isRefreshing}
                  />
                </Stack>
                {isRefreshing ? (
                  <Box variant='shimmer' height='4.1rem' width='10rem' />
                ) : (
                  <Stack direction={Direction.Horizontal} childAlignment={Alignment.Baseline} contentAlignment={Alignment.Center} shouldAddGutters={true} defaultGutter={PaddingSize.Narrow}>
                    <Text variant='value-extraLarge'>{formatBalance(collateralBalance?.balance || 0n, collateral.decimals)}</Text>
                    <Spacing variant={PaddingSize.Narrow} />
                    <Text variant='large'>{collateral.symbol}</Text>
                  </Stack>
                )}
                <Text variant='note'>{`$${(collateralBalance?.balanceUsd || 0).toFixed(2)}`}</Text>
                {hasCollateral ? (
                  <LinkBase onClicked={handleContinue}>
                    <Box variant='success-cardSmall' className='statusBadge' isFullWidth={false}>
                      <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Default} paddingVertical={PaddingSize.Narrow}>
                        <Text variant='note-success'>Ready to deploy</Text>
                        <KibaIcon iconId='ion-arrow-forward' variant='small-success' />
                      </Stack>
                    </Box>
                  </LinkBase>
                ) : (
                  <Box variant='warning-cardSmall' className='statusBadge' isFullWidth={false}>
                    <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} paddingHorizontal={PaddingSize.Default} paddingVertical={PaddingSize.Narrow}>
                      <KibaIcon iconId='ion-time-outline' variant='small-warning' />
                      <Text variant='note-warning'>Waiting for deposit</Text>
                    </Stack>
                  </Box>
                )}
              </Stack>
            </Box>
            <Spacing variant={PaddingSize.Wide} />
            <Text variant='header3'>Deposit from Your Wallet</Text>
            <Stack direction={Direction.Vertical}>
              <DepositForm
                assetBalance={userCollateralBalance}
                agentWalletAddress={agentWalletAddress}
                onDepositSuccess={handleDepositSuccess}
                isLoadingBalance={isLoadingUserWallet}
              />
            </Stack>
            <Spacing variant={PaddingSize.Default} />
            <Text variant='header3'>Convert from Any Chain</Text>
            <Text variant='note'>Bridge and swap any token from any chain directly to your agent</Text>
            <Button variant='primary' text='Open Bridge/Swap' onClicked={(): void => setIsLiFiDialogOpen(true)} isFullWidth={true} />
            <Spacing />
            <Text variant='header3'>Borrow Strategy</Text>
            <Text variant='note'>Select how much to borrow against your collateral</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
              {LTV_OPTIONS.map((option): React.ReactElement => (
                <button
                  key={option.value}
                  type='button'
                  className={`ltvCard ${targetLtv === option.value ? 'selected' : ''} ${option.riskLevel}`}
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
            {hasCollateral && (
              <React.Fragment>
                <Spacing />
                <Box variant='card' className='summaryCard' isFullWidth={true}>
                  <Stack direction={Direction.Vertical} shouldAddGutters={true} paddingHorizontal={PaddingSize.Default} paddingVertical={PaddingSize.Default}>
                    <Text variant='bold'>Summary & Forecast</Text>
                    <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                      <Text>Collateral:</Text>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      <Text variant='bold'>{`${formatBalance(collateralBalance?.balance || 0n, collateral.decimals)} ${collateral.symbol}`}</Text>
                    </Stack>
                    <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                      <Text>Target LTV:</Text>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      <Text variant='bold'>{`${(targetLtv * 100).toFixed(0)}%`}</Text>
                    </Stack>
                    <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                      <Text>Est. Borrow:</Text>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      <Text variant='bold'>{`$${estimatedBorrowAmount.toFixed(2)} USDC`}</Text>
                    </Stack>
                    <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                      <Text>Borrow APY:</Text>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      <Text variant='bold'>
                        {collateralMarketData ? `${(collateralMarketData.borrowApy * 100).toFixed(2)}%` : '~3%'}
                      </Text>
                    </Stack>
                    <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                      <Text>{`Yield APY (${marketData?.yieldVaultName || 'Vault'}):`}</Text>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      <Text variant='bold'>
                        {marketData ? `${(marketData.yieldApy * 100).toFixed(2)}%` : '~8%'}
                      </Text>
                    </Stack>
                    <Spacing variant={PaddingSize.Narrow} />
                    <Box variant='divider' isFullWidth={true} />
                    <Spacing variant={PaddingSize.Narrow} />
                    <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                      <Text variant='bold'>Net APY:</Text>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      <GlowingText variant='bold'>{`${(netApy * 100).toFixed(2)}%`}</GlowingText>
                    </Stack>
                    <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
                      <Text variant='bold'>Est. Yearly Yield:</Text>
                      <Stack.Item growthFactor={1} shrinkFactor={1} />
                      <GlowingText variant='bold'>{`$${estimatedYearlyYield.toFixed(2)}`}</GlowingText>
                    </Stack>
                  </Stack>
                </Box>
              </React.Fragment>
            )}
            <Spacing variant={PaddingSize.Default} />
            {error && (
              <Text variant='error' alignment={TextAlignment.Center}>{error}</Text>
            )}
            <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
              <Stack.Item shrinkFactor={0}>
                <Button variant='secondary' text='Back' onClicked={handleBack} />
              </Stack.Item>
              <Stack.Item growthFactor={1} shrinkFactor={1}>
                <GlowingButton
                  variant='primary-large'
                  text={hasCollateral ? 'Deploy Agent' : 'Waiting for deposit...'}
                  onClicked={handleContinue}
                  isEnabled={hasCollateral}
                  isFullWidth={true}
                />
              </Stack.Item>
            </Stack>
          </Stack>
        </Box>
      </Stack>
      {isLiFiDialogOpen && collateral && (
        <LiFiDepositDialog
          agentWalletAddress={agentWalletAddress}
          targetAssetAddress={collateral.address}
          onCloseClicked={(): void => setIsLiFiDialogOpen(false)}
          onDepositSuccess={handleLiFiSuccess}
        />
      )}
    </ContainingView>
  );
}
