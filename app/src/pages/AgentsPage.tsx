import React from 'react';

import { useNavigator } from '@kibalabs/core-react';
import { Alignment, Box, Direction, KibaIcon, LinkBase, LoadingSpinner, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';

import { useAuth } from '../AuthContext';
import { Agent } from '../client/resources';
import { ContainingView } from '../components/ContainingView';
import { GlowingButton, GlowingText } from '../components/GlowingButton';
import { useGlobals } from '../GlobalsContext';

export function AgentsPage(): React.ReactElement {
  const navigator = useNavigator();
  const { moneyHackClient } = useGlobals();
  const { accountAddress, authToken, isWeb3AccountLoggedIn } = useAuth();
  const [agents, setAgents] = React.useState<Agent[] | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  React.useEffect((): void => {
    if (!isWeb3AccountLoggedIn || !accountAddress || !authToken) {
      navigator.navigateTo('/');
      return;
    }
    const loadAgents = async (): Promise<void> => {
      try {
        const fetchedAgents = await moneyHackClient.getAgents(accountAddress, authToken);
        setAgents(fetchedAgents);
      } catch (error) {
        console.error('Failed to load agents:', error);
        setAgents([]);
      } finally {
        setIsLoading(false);
      }
    };
    loadAgents();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isWeb3AccountLoggedIn, accountAddress, authToken]);

  if (!isWeb3AccountLoggedIn) {
    return (
      <ContainingView>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} isFullWidth={true}>
          <LoadingSpinner />
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
          <Text>Loading agents...</Text>
        </Stack>
      </ContainingView>
    );
  }

  if (!agents || agents.length === 0) {
    return (
      <ContainingView>
        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullHeight={true} isFullWidth={true} shouldAddGutters={true} paddingHorizontal={PaddingSize.Wide2}>
          <Text variant='header2'>Welcome to BorrowBot</Text>
          <Text variant='passive'>Create your first AI agent to start earning yield on your collateral.</Text>
          <Spacing variant={PaddingSize.Wide} />
          <GlowingButton variant='primary-large' text='Create Your First Agent' onClicked={(): void => navigator.navigateTo('/create-agent')} />
        </Stack>
      </ContainingView>
    );
  }

  return (
    <ContainingView>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} isFullWidth={true}>
        <Box maxWidth='600px' isFullWidth={true}>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Fill} contentAlignment={Alignment.Start} shouldAddGutters={true} isFullWidth={true} paddingVertical={PaddingSize.Wide2} paddingHorizontal={PaddingSize.Wide2}>
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} shouldWrapItems={true}>
              <Text variant='header1'>Your&nbsp;</Text>
              <GlowingText variant='header1'>Agents</GlowingText>
            </Stack>
            <Spacing variant={PaddingSize.Default} />
            <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
              {agents.map((agent: Agent): React.ReactElement => (
                <LinkBase key={agent.agentId} onClicked={(): void => navigator.navigateTo(`/agent?agentId=${agent.agentId}`)} isFullWidth={true}>
                  <Box variant='card' isFullWidth={true}>
                    <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center} contentAlignment={Alignment.Start} isFullWidth={true} paddingVertical={PaddingSize.Default} paddingHorizontal={PaddingSize.Default}>
                      <Box width='48px' height='48px' variant='rounded'>
                        <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} isFullWidth={true} isFullHeight={true}>
                          <Text variant='header2'>{agent.emoji}</Text>
                        </Stack>
                      </Box>
                      <Stack.Item growthFactor={1} shrinkFactor={1}>
                        <Stack direction={Direction.Vertical} childAlignment={Alignment.Start}>
                          <Text variant='bold'>{agent.name}</Text>
                          {agent.ensName ? (
                            <Text variant='note'>{agent.ensName}</Text>
                          ) : (
                            <Text variant='note'>{`${agent.walletAddress.slice(0, 6)}...${agent.walletAddress.slice(-4)}`}</Text>
                          )}
                        </Stack>
                      </Stack.Item>
                      <KibaIcon iconId='ion-chevron-forward' />
                    </Stack>
                  </Box>
                </LinkBase>
              ))}
            </Stack>
            <Spacing variant={PaddingSize.Wide} />
            <GlowingButton variant='primary-large' text='Create New Agent' onClicked={(): void => navigator.navigateTo('/create-agent')} isFullWidth={true} />
          </Stack>
        </Box>
      </Stack>
    </ContainingView>
  );
}
