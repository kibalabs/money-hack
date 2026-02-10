import React from 'react';

import { useLocation, useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Button, Direction, KibaIcon, Link, LinkBase, LoadingSpinner, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';
import { ContainingView } from '../components/ContainingView';
import { GlowingText } from '../components/GlowingButton';
import { LoadingIndicator } from '../components/LoadingIndicator';
import { StepProgress } from '../components/StepProgress';
import { useGlobals } from '../GlobalsContext';

import './DeployAgentPage.scss';

type DeployStep = 'initializing' | 'approving' | 'depositing' | 'borrowing' | 'vaulting' | 'complete';

interface DeployStepInfo {
  id: DeployStep;
  label: string;
  activeLabel: string;
}

const DEPLOY_STEPS: DeployStepInfo[] = [
  { id: 'initializing', label: 'Initializing agent wallet', activeLabel: 'Initializing agent wallet...' },
  { id: 'depositing', label: 'Depositing collateral', activeLabel: 'Depositing collateral...' },
  { id: 'borrowing', label: 'Borrowing USDC', activeLabel: 'Borrowing USDC...' },
  { id: 'vaulting', label: 'Depositing to yield vault', activeLabel: 'Depositing to yield vault...' },
  { id: 'approving', label: 'Setting on-chain constitution with ENS', activeLabel: 'Setting on-chain constitution with ENS...' },
];

export function DeployAgentPage(): React.ReactElement {
  const navigator = useNavigator();
  const location = useLocation();
  const { moneyHackClient } = useGlobals();
  const { accountAddress, authToken, isWeb3AccountLoggedIn } = useAuth();
  const urlParams = new URLSearchParams(location?.search || '');
  const collateralAddress = urlParams.get('collateral') || '';
  const amountStr = urlParams.get('amount') || '0';
  const ltvStr = urlParams.get('ltv') || '0.65';
  const agentId = urlParams.get('agentId') || '';
  const agentName = urlParams.get('agentName') || 'BorrowBot 1';
  const agentEmoji = urlParams.get('agentEmoji') || '🤖';
  const [currentStepIndex, setCurrentStepIndex] = React.useState<number>(0);
  const [isDeploying, setIsDeploying] = React.useState<boolean>(false);
  const [isDeployed, setIsDeployed] = React.useState<boolean>(false);
  const [transactionHash, setTransactionHash] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const hasStartedRef = React.useRef<boolean>(false);
  const hasErrorRef = React.useRef<boolean>(false);
  React.useEffect((): void => {
    if (!accountAddress || !collateralAddress || amountStr === '0' || !agentId) {
      navigator.navigateTo('/create-agent');
    }
  }, [accountAddress, collateralAddress, amountStr, agentId, navigator]);
  const formatErrorMessage = (errorMessage: string): string => {
    if (errorMessage.includes('insufficient funds for gas')) {
      return 'Your agent wallet needs ETH for gas fees. Please send a small amount of ETH to the agent wallet address and try again.';
    }
    if (errorMessage.includes('execution reverted')) {
      return `Transaction failed: ${errorMessage.split('execution reverted:')[1]?.trim() || errorMessage}`;
    }
    return errorMessage;
  };
  const runDeployment = React.useCallback(async (): Promise<void> => {
    if (!accountAddress || !authToken || isDeploying || hasStartedRef.current || !agentId || hasErrorRef.current) return;
    hasStartedRef.current = true;
    setIsDeploying(true);
    setError(null);
    const ensStepIndex = DEPLOY_STEPS.length - 1;
    let stepInterval: ReturnType<typeof setInterval> | null = null;
    try {
      setCurrentStepIndex(0);
      stepInterval = setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev < ensStepIndex - 1) {
            return prev + 1;
          }
          return prev;
        });
      }, 3000);
      const result = await moneyHackClient.deployAgent(
        accountAddress,
        agentId,
        collateralAddress,
        BigInt(amountStr),
        parseFloat(ltvStr),
        authToken,
      );
      clearInterval(stepInterval);
      stepInterval = null;
      if (result.transactionHash) {
        setTransactionHash(result.transactionHash);
      }
      // ENS registration as the final step (non-blocking)
      setCurrentStepIndex(ensStepIndex);
      try {
        await moneyHackClient.registerEns(
          accountAddress,
          agentId,
          collateralAddress,
          parseFloat(ltvStr),
          authToken,
        );
      } catch (ensError) {
        console.error('ENS registration failed (non-blocking):', ensError);
      }
      setCurrentStepIndex(DEPLOY_STEPS.length);
      setIsDeployed(true);
    } catch (caughtError) {
      if (stepInterval) clearInterval(stepInterval);
      console.error('Deployment failed:', caughtError);
      const errorMessage = caughtError instanceof Error ? caughtError.message : 'Deployment failed. Please try again.';
      setError(formatErrorMessage(errorMessage));
      hasErrorRef.current = true;
    } finally {
      setIsDeploying(false);
    }
  }, [accountAddress, authToken, isDeploying, agentId, moneyHackClient, collateralAddress, amountStr, ltvStr]);
  React.useEffect((): void => {
    if (accountAddress && authToken && !hasStartedRef.current && agentId && !hasErrorRef.current) {
      runDeployment();
    }
  }, [accountAddress, authToken, agentId, runDeployment]);
  const onRetryClicked = (): void => {
    hasStartedRef.current = false;
    hasErrorRef.current = false;
    setError(null);
    setCurrentStepIndex(0);
    runDeployment();
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
  return (
    <ContainingView>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} isFullWidth={true}>
        <Box maxWidth='600px' isFullWidth={true}>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Start} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide2}>
            <Box maxWidth='300px'>
              <StepProgress currentStep={4} totalSteps={4} />
            </Box>
            <Spacing variant={PaddingSize.Default} />
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldWrapItems={true}>
              <Text variant='header1'>Deploying&nbsp;</Text>
              <GlowingText variant='header1'>{`${agentEmoji} ${agentName}`}</GlowingText>
            </Stack>
            <Text variant='passive'>Your agent is executing transactions to set up your lending position.</Text>
            <Spacing variant={PaddingSize.Wide2} />
            <Stack.Item alignment={Alignment.Center}>
              <Box className={`logoContainer ${isDeploying ? 'animating' : ''} ${isDeployed ? 'completed' : ''}`}>
                <Box className='logoInner'>
                  <Text variant='header1'>{agentEmoji}</Text>
                </Box>
                {isDeploying && !isDeployed && (
                  <React.Fragment>
                    <Box className='pulseRing ring1' />
                    <Box className='pulseRing ring2' />
                  </React.Fragment>
                )}
              </Box>
            </Stack.Item>
            {!isDeployed ? (
              <React.Fragment>
                <Spacing variant={PaddingSize.Wide} />
                <Stack.Item alignment={Alignment.Center}>
                  <Box maxWidth='18rem'>
                    <Stack direction={Direction.Vertical} childAlignment={Alignment.Start} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true} defaultGutter={PaddingSize.Wide}>
                      {DEPLOY_STEPS.map((step: DeployStepInfo, index: number): React.ReactElement => {
                        const isCompleted = index < currentStepIndex;
                        const isActive = index === currentStepIndex && isDeploying;
                        const isPending = index > currentStepIndex;
                        return (
                          <Stack key={step.id} direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start}>
                            <Box className={`deployStepIndicator ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''} ${isPending ? 'pending' : ''}`}>
                              {isCompleted ? (
                                <KibaIcon iconId='ion-checkmark' variant='small' />
                              ) : isActive ? (
                                <LoadingSpinner variant='small' />
                              ) : (
                                <Text variant='note'>{index + 1}</Text>
                              )}
                            </Box>
                            <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                              <Text variant={isActive ? 'bold' : isPending ? 'passive' : 'default'}>{isActive ? step.activeLabel : step.label}</Text>
                            </Stack>
                          </Stack>
                        );
                      })}
                    </Stack>
                  </Box>
                </Stack.Item>
                {error && (
                  <React.Fragment>
                    <Spacing variant={PaddingSize.Wide} />
                    <Stack.Item alignment={Alignment.Center}>
                      <Text variant='error'>{error}</Text>
                    </Stack.Item>
                    <Spacing />
                    <Stack.Item alignment={Alignment.Center}>
                      <Button variant='primary' text='Retry Deployment' onClicked={onRetryClicked} />
                    </Stack.Item>
                  </React.Fragment>
                )}
              </React.Fragment>
            ) : (
              <React.Fragment>
                <Spacing variant={PaddingSize.Wide} />
                <Stack.Item alignment={Alignment.Center}>
                  <Text variant='success-large-bold'>Agent Deployed!</Text>
                </Stack.Item>
                <Stack.Item alignment={Alignment.Center}>
                  <Text>Your agent is now earning yield on your USDC</Text>
                </Stack.Item>
                {transactionHash && (
                  <Stack.Item alignment={Alignment.Center}>
                    <Link text='View transaction on Basescan' target={`https://basescan.org/tx/${transactionHash}`} />
                  </Stack.Item>
                )}
                <Spacing variant={PaddingSize.Wide} />
                <Text variant='header3'>What&apos;s Next?</Text>
                <Spacing variant={PaddingSize.Narrow} />
                <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
                  <LinkBase className='actionCard actionCardHighlight' target='/account' isFullWidth={true}>
                    <Stack direction={Direction.Horizontal} isFullWidth={true} isFullHeight={true} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Default} paddingHorizontal={PaddingSize.Default}>
                      <Box className='actionCardIcon'>
                        <KibaIcon iconId='ion-notifications' />
                      </Box>
                      <Stack.Item growthFactor={1} shrinkFactor={1}>
                        <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                          <Text variant='bold'>Get Notified</Text>
                          <Text variant='note'>Connect Telegram to get alerts when your agent makes moves</Text>
                        </Stack>
                      </Stack.Item>
                      <Text variant='note-bold-success'>Connect</Text>
                      <Spacing />
                    </Stack>
                  </LinkBase>
                  <LinkBase className='actionCard' target='/agents' isFullWidth={true}>
                    <Stack direction={Direction.Horizontal} isFullWidth={true} isFullHeight={true} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Default} paddingHorizontal={PaddingSize.Default}>
                      <Box className='actionCardIcon'>
                        <KibaIcon iconId='ion-trending-up' />
                      </Box>
                      <Stack.Item growthFactor={1} shrinkFactor={1}>
                        <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                          <Text variant='bold'>View Position</Text>
                          <Text variant='note'>Monitor your lending position and accrued yield</Text>
                        </Stack>
                      </Stack.Item>
                      <Text variant='note-bold-success'>View</Text>
                      <Spacing />
                    </Stack>
                  </LinkBase>
                  <LinkBase className='actionCard' target='/account' isFullWidth={true}>
                    <Stack direction={Direction.Horizontal} isFullWidth={true} isFullHeight={true} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} paddingVertical={PaddingSize.Default} paddingHorizontal={PaddingSize.Default}>
                      <Box className='actionCardIcon'>
                        <KibaIcon iconId='ion-settings' />
                      </Box>
                      <Stack.Item growthFactor={1} shrinkFactor={1}>
                        <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                          <Text variant='bold'>Account Settings</Text>
                          <Text variant='note'>Adjust LTV preferences and notification settings</Text>
                        </Stack>
                      </Stack.Item>
                      <Text variant='note-bold-success'>Settings</Text>
                      <Spacing />
                    </Stack>
                  </LinkBase>
                </Stack>
              </React.Fragment>
            )}
          </Stack>
        </Box>
      </Stack>
    </ContainingView>
  );
}
