import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Direction, Image, LoadingSpinner, MarkdownText, PaddingSize, SingleLineInput, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';
import { Agent, CollateralAsset, MarketData, Wallet } from '../client/resources';
import { ContainingView } from '../components/ContainingView';
import { GlowingButton, GlowingText } from '../components/GlowingButton';
import { LoadingIndicator } from '../components/LoadingIndicator';
import { StepProgress } from '../components/StepProgress';
import { useGlobals } from '../GlobalsContext';

import './CreateAgentPage.scss';

const DEFAULT_EMOJIS = ['🤖', '🧠', '💰', '🏦', '💎', '📈', '🚀', '🔮', '🦌', '🦊', '🐻', '🦁'];

const getRandomEmoji = (): string => {
  return DEFAULT_EMOJIS[Math.floor(Math.random() * DEFAULT_EMOJIS.length)];
};

interface IEmojiPickerProps {
  emojis: string[];
  selectedEmoji: string;
  onEmojiSelected: (emoji: string) => void;
}

function EmojiPicker(props: IEmojiPickerProps): React.ReactElement {
  return (
    <Stack direction={Direction.Horizontal} shouldWrapItems={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldAddGutters={true}>
      {props.emojis.map((emoji) => (
        <button
          key={emoji}
          type='button'
          className={`emojiOption ${emoji === props.selectedEmoji ? 'selected' : ''}`}
          onClick={() => props.onEmojiSelected(emoji)}
        >
          <Text variant='larger'>{emoji}</Text>
        </button>
      ))}
    </Stack>
  );
}

type Step = 'collateral' | 'agent';

const formatBalance = (balance: bigint, decimals: number): string => {
  const divisor = BigInt(10 ** decimals);
  const integerPart = balance / divisor;
  const fractionalPart = balance % divisor;
  const fractionalStr = fractionalPart.toString().padStart(decimals, '0').slice(0, 4);
  if (integerPart === 0n && fractionalPart === 0n) {
    return '0';
  }
  if (integerPart === 0n) {
    return `0.${fractionalStr}`;
  }
  return `${integerPart.toLocaleString()}.${fractionalStr}`;
};

const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

export function CreateAgentPage(): React.ReactElement {
  const navigator = useNavigator();
  const { moneyHackClient } = useGlobals();
  const { accountAddress, authToken, isWeb3AccountLoggedIn } = useAuth();
  const [currentStep, setCurrentStep] = React.useState<Step>('collateral');
  const [collaterals, setCollaterals] = React.useState<CollateralAsset[] | null>(null);
  const [selectedCollateral, setSelectedCollateral] = React.useState<CollateralAsset | null>(null);
  const [agentName, setAgentName] = React.useState<string>('BorrowBot 1');
  const [selectedEmoji, setSelectedEmoji] = React.useState<string>(getRandomEmoji);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoadingCollaterals, setIsLoadingCollaterals] = React.useState<boolean>(true);
  const [isCreatingAgent, setIsCreatingAgent] = React.useState<boolean>(false);
  const [existingAgent, setExistingAgent] = React.useState<Agent | null>(null);
  const [marketData, setMarketData] = React.useState<MarketData | null>(null);
  const [userWallet, setUserWallet] = React.useState<Wallet | null>(null);
  React.useEffect((): void => {
    if (!accountAddress || !authToken) {
      navigator.navigateTo('/');
      return;
    }
    const loadData = async (): Promise<void> => {
      try {
        const [fetchedCollaterals, fetchedAgent, fetchedMarketData, fetchedWallet] = await Promise.all([
          moneyHackClient.getSupportedCollaterals(authToken),
          moneyHackClient.getAgent(accountAddress, authToken),
          moneyHackClient.getMarketData(),
          moneyHackClient.getWallet(accountAddress, authToken),
        ]);
        setCollaterals(fetchedCollaterals);
        setMarketData(fetchedMarketData);
        setUserWallet(fetchedWallet);
        if (fetchedAgent) {
          setExistingAgent(fetchedAgent);
          setAgentName(fetchedAgent.name);
          setSelectedEmoji(fetchedAgent.emoji);
        }
      } catch (caughtError) {
        console.error('Failed to load data:', caughtError);
        setError('Failed to load collaterals');
      } finally {
        setIsLoadingCollaterals(false);
      }
    };
    loadData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountAddress, authToken]);
  const onCollateralSelected = (collateral: CollateralAsset): void => {
    setSelectedCollateral(collateral);
    setError(null);
  };
  const onContinueToAgent = (): void => {
    if (!selectedCollateral) {
      setError('Please select a collateral asset');
      return;
    }
    setCurrentStep('agent');
    setError(null);
  };
  const onBackToCollateral = (): void => {
    setCurrentStep('collateral');
    setError(null);
  };
  const onAgentNameChanged = (value: string): void => {
    setAgentName(value);
    setError(null);
  };
  const onEmojiSelected = (emoji: string): void => {
    setSelectedEmoji(emoji);
  };
  const onCreateAgentClicked = async (): Promise<void> => {
    if (!agentName.trim()) {
      setError('Please enter a name for your agent');
      return;
    }
    if (!selectedCollateral) {
      setError('Please select a collateral asset');
      return;
    }
    if (!accountAddress || !authToken) {
      setError('Not logged in');
      return;
    }
    setIsCreatingAgent(true);
    setError(null);
    try {
      let agent = existingAgent;
      if (!agent) {
        agent = await moneyHackClient.createAgent(accountAddress, agentName.trim(), selectedEmoji, authToken);
      }
      const params = new URLSearchParams({
        collateral: selectedCollateral.address,
        agentId: agent.agentId,
        agentWalletAddress: agent.walletAddress,
        agentName: agent.name,
        agentEmoji: agent.emoji,
      });
      navigator.navigateTo(`/fund-agent?${params.toString()}`);
    } catch (caughtError) {
      console.error('Failed to create agent:', caughtError);
      setError('Failed to create agent. Please try again.');
    } finally {
      setIsCreatingAgent(false);
    }
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
  if (isLoadingCollaterals) {
    return (
      <ContainingView>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} isFullWidth={true}>
          <LoadingSpinner />
          <Spacing />
          <Text>Loading collaterals...</Text>
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
              <StepProgress currentStep={currentStep === 'collateral' ? 1 : 2} totalSteps={4} />
            </Box>
            <Spacing variant={PaddingSize.Default} />
            {currentStep === 'collateral' && (
              <React.Fragment>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldWrapItems={true}>
                  <Text variant='header1'>Choose&nbsp;</Text>
                  <GlowingText variant='header1'>Collateral</GlowingText>
                </Stack>
                <Text variant='passive'>Select the asset you want to use as collateral. Your agent will borrow against it and put the funds to work.</Text>
                <Spacing variant={PaddingSize.Default} />
                <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
                  {collaterals?.map((collateral): React.ReactElement => {
                    const collateralMarket = marketData?.collateralMarkets.find((m) => m.collateralAddress.toLowerCase() === collateral.address.toLowerCase());
                    const userBalance = userWallet?.assetBalances.find((b) => b.assetAddress.toLowerCase() === collateral.address.toLowerCase());
                    const balanceDisplay = userBalance ? formatBalance(userBalance.balance, userBalance.assetDecimals) : '0';
                    const hasBalance = userBalance && userBalance.balance > 0n;
                    return (
                      <button
                        key={collateral.address}
                        type='button'
                        className={`collateralCard ${selectedCollateral?.address === collateral.address ? 'selected' : ''}`}
                        onClick={(): void => onCollateralSelected(collateral)}
                      >
                        <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
                          <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
                            <Box width='40px' height='40px'>
                              {collateral.logoUri && (
                                <Image source={collateral.logoUri} alternativeText={collateral.symbol} isFullWidth={true} isFullHeight={true} />
                              )}
                            </Box>
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                              <Text variant='bold'>{collateral.symbol}</Text>
                              <Text variant='note'>{collateral.name}</Text>
                            </Stack>
                            <Stack.Item growthFactor={1} shrinkFactor={1} />
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
                              <Text variant={hasBalance ? 'bold' : 'note'}>
                                {balanceDisplay}
                                {' '}
                                {collateral.symbol}
                              </Text>
                              <Text variant='note'>
                                {userBalance ? `$${userBalance.balanceUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$0.00'}
                              </Text>
                            </Stack>
                            {selectedCollateral?.address === collateral.address && (
                              <Text variant='success'>✓</Text>
                            )}
                          </Stack>
                          <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true}>
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                              <Text variant='small-bold'>{collateralMarket ? formatPercent(collateralMarket.maxLtv) : '-'}</Text>
                              <Text variant='note'>Max LTV</Text>
                            </Stack>
                            <Stack.Item growthFactor={1} shrinkFactor={1} />
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.Center}>
                              <Text variant='small-bold'>{collateralMarket ? formatPercent(collateralMarket.borrowApy) : '-'}</Text>
                              <Text variant='note'>Borrow Rate</Text>
                            </Stack>
                            <Stack.Item growthFactor={1} shrinkFactor={1} />
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
                              <Text variant='small-bold' className='yieldApy'>{marketData ? formatPercent(marketData.yieldApy) : '-'}</Text>
                              <Text variant='note'>Yield APY</Text>
                            </Stack>
                          </Stack>
                        </Stack>
                      </button>
                    );
                  })}
                </Stack>
                <Spacing variant={PaddingSize.Wide} />
                {error && (
                  <Text variant='error' alignment={TextAlignment.Center}>{error}</Text>
                )}
                <GlowingButton
                  variant='primary-large'
                  text='Continue'
                  onClicked={onContinueToAgent}
                  isEnabled={!!selectedCollateral}
                  isFullWidth={true}
                />
              </React.Fragment>
            )}
            {currentStep === 'agent' && (
              <React.Fragment>
                <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldWrapItems={true}>
                  <Text variant='header1'>Create Your&nbsp;</Text>
                  <GlowingText variant='header1'>Agent</GlowingText>
                </Stack>
                <Text variant='passive'>Give your agent a name and personality. You can always change these later.</Text>
                <Spacing variant={PaddingSize.Default} />
                <Text variant='note'>Agent Name</Text>
                <SingleLineInput
                  label='Agent Name'
                  placeholderText='BorrowBot 1'
                  value={agentName}
                  onValueChanged={onAgentNameChanged}
                />
                <Spacing />
                <Text variant='note'>Agent Icon</Text>
                <EmojiPicker
                  emojis={DEFAULT_EMOJIS}
                  selectedEmoji={selectedEmoji}
                  onEmojiSelected={onEmojiSelected}
                />
                <Spacing variant={PaddingSize.Wide} />
                <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Start} contentAlignment={Alignment.Start} isFullWidth={true}>
                  <Box width='24px'>
                    <Text>ℹ️</Text>
                  </Box>
                  <Stack.Item growthFactor={1} shrinkFactor={1}>
                    <MarkdownText textVariant='note' source={`You'll deposit **${selectedCollateral?.symbol}** as collateral. Your agent will borrow against it and put the funds to work in yield vaults.`} />
                  </Stack.Item>
                </Stack>
                <Spacing variant={PaddingSize.Default} />
                {error && (
                  <Text variant='error' alignment={TextAlignment.Center}>{error}</Text>
                )}
                <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
                  <Stack.Item shrinkFactor={0}>
                    <GlowingButton
                      variant='secondary'
                      text='Back'
                      onClicked={onBackToCollateral}
                      isEnabled={!isCreatingAgent}
                    />
                  </Stack.Item>
                  <Stack.Item growthFactor={1} shrinkFactor={1}>
                    <GlowingButton
                      variant='primary-large'
                      text={isCreatingAgent ? 'Creating...' : (existingAgent ? 'Continue' : 'Create Agent')}
                      onClicked={onCreateAgentClicked}
                      isEnabled={agentName.trim() !== '' && !isCreatingAgent}
                      isFullWidth={true}
                      isLoading={isCreatingAgent}
                    />
                  </Stack.Item>
                </Stack>
              </React.Fragment>
            )}
          </Stack>
        </Box>
      </Stack>
    </ContainingView>
  );
}
