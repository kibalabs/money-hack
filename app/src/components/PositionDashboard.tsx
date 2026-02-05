import React from 'react';

import { Alignment, Box, Button, Direction, EqualGrid, Image, KibaIcon, PaddingSize, Spacing, Stack, Text, TextAlignment } from '@kibalabs/ui-react';

import { CollateralMarketData, MarketData, Position } from '../client/resources';

import './PositionDashboard.scss';

interface IPositionDashboardProps {
  position: Position;
  marketData: MarketData | null;
  onRefreshClicked: () => void;
  onWithdrawClicked: () => void;
  onClosePositionClicked: () => void;
  isRefreshing: boolean;
}

const formatUsd = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(2)}K`;
  }
  return `$${value.toFixed(2)}`;
};

const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

const formatAmount = (amount: bigint, decimals: number): string => {
  const value = Number(amount) / (10 ** decimals);
  if (value === 0) return '0';
  if (value < 0.0001) return '<0.0001';
  if (value < 1) return value.toFixed(4);
  if (value < 1000) return value.toFixed(4);
  return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
};

const getHealthStatus = (ltv: number, maxLtv: number): 'healthy' | 'warning' | 'danger' => {
  const ratio = ltv / maxLtv;
  if (ratio >= 0.95) return 'danger';
  if (ratio >= 0.85) return 'warning';
  return 'healthy';
};

const getHealthPercent = (ltv: number, maxLtv: number): number => {
  return Math.min((ltv / maxLtv) * 100, 100);
};

export function PositionDashboard(props: IPositionDashboardProps): React.ReactElement {
  const collateralMarket = React.useMemo((): CollateralMarketData | null => {
    if (!props.marketData) return null;
    return props.marketData.collateralMarkets.find(
      (m) => m.collateralAddress.toLowerCase() === props.position.collateralAsset.address.toLowerCase(),
    ) ?? null;
  }, [props.marketData, props.position.collateralAsset.address]);

  const maxLtv = collateralMarket?.maxLtv ?? 0.86;
  const healthStatus = getHealthStatus(props.position.currentLtv, maxLtv);
  const healthPercent = getHealthPercent(props.position.currentLtv, maxLtv);

  const borrowApy = collateralMarket?.borrowApy ?? 0;
  const yieldApy = props.marketData?.yieldApy ?? 0;
  const netSpread = yieldApy - borrowApy;

  return (
    <Stack className='positionDashboard' direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
      <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} isFullWidth={true}>
        <Text variant='header2'>Position Dashboard</Text>
        <Stack.Item growthFactor={1} shrinkFactor={1} />
        <Button
          variant='tertiary-small'
          iconLeft={<KibaIcon iconId='ion-refresh' />}
          text='Refresh'
          onClicked={props.onRefreshClicked}
          isLoading={props.isRefreshing}
        />
      </Stack>

      <Spacing variant={PaddingSize.Default} />

      {/* Collateral Info */}
      <Box className='statCard' isFullWidth={true}>
        <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
          {props.position.collateralAsset.logoUri && (
            <Box width='40px' height='40px'>
              <Image
                source={props.position.collateralAsset.logoUri}
                alternativeText={props.position.collateralAsset.symbol}
                isFullWidth={true}
                isFullHeight={true}
              />
            </Box>
          )}
          <Stack direction={Direction.Vertical}>
            <Text variant='header3'>{props.position.collateralAsset.symbol}</Text>
            <Text variant='note'>{props.position.collateralAsset.name}</Text>
          </Stack>
          <Stack.Item growthFactor={1} shrinkFactor={1} />
          <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
            <Text variant='bold'>
              {formatAmount(props.position.collateralAmount, props.position.collateralAsset.decimals)}
            </Text>
            <Text variant='note'>{formatUsd(props.position.collateralValueUsd)}</Text>
          </Stack>
        </Stack>
      </Box>

      {/* LTV & Health */}
      <Box className='statCard' isFullWidth={true}>
        <Stack direction={Direction.Vertical} shouldAddGutters={true}>
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Start}>
            <Text variant='bold'>Loan-to-Value</Text>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <div className='ltvDisplay'>
              <Text variant='bold'>{formatPercent(props.position.currentLtv)}</Text>
              <span className={`ltvBadge ${healthStatus}`}>
                {healthStatus === 'healthy' && 'Healthy'}
                {healthStatus === 'warning' && 'Warning'}
                {healthStatus === 'danger' && 'At Risk'}
              </span>
            </div>
          </Stack>
          <div className='healthGauge'>
            <div
              className={`healthFill ${healthStatus}`}
              style={{ width: `${healthPercent}%` }}
            />
          </div>
          <Stack direction={Direction.Horizontal} contentAlignment={Alignment.Start}>
            <Text variant='note'>{`Target: ${formatPercent(props.position.targetLtv)}`}</Text>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Text variant='note'>{`Max: ${formatPercent(maxLtv)}`}</Text>
          </Stack>
        </Stack>
      </Box>

      {/* Key Stats */}
      <EqualGrid shouldAddGutters={true} childSizeResponsive={{ base: 6, medium: 6 }}>
        <Box className='statCard'>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
            <Text variant='note' alignment={TextAlignment.Center}>USDC Borrowed</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Text variant='bold-large' alignment={TextAlignment.Center}>{formatUsd(props.position.borrowValueUsd)}</Text>
          </Stack>
        </Box>
        <Box className='statCard'>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
            <Text variant='note' alignment={TextAlignment.Center}>Vault Balance</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Text variant='bold-large' alignment={TextAlignment.Center}>{formatUsd(props.position.vaultBalanceUsd)}</Text>
          </Stack>
        </Box>
        <Box className='statCard'>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
            <Text variant='note' alignment={TextAlignment.Center}>Yield Earned</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Text variant='bold-large-success' alignment={TextAlignment.Center}>{formatUsd(props.position.accruedYieldUsd)}</Text>
          </Stack>
        </Box>
        <Box className='statCard'>
          <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} contentAlignment={Alignment.Center}>
            <Text variant='note' alignment={TextAlignment.Center}>Health Factor</Text>
            <Spacing variant={PaddingSize.Narrow} />
            <Text variant='bold-large' alignment={TextAlignment.Center}>{props.position.healthFactor.toFixed(2)}</Text>
          </Stack>
        </Box>
      </EqualGrid>

      {/* Rate Comparison */}
      <Box className='statCard' isFullWidth={true}>
        <Stack direction={Direction.Vertical} shouldAddGutters={true}>
          <Text variant='bold'>Rate Comparison</Text>
          <Spacing variant={PaddingSize.Narrow} />
          <div className='rateComparison'>
            <div className='rateRow'>
              <Text>Borrow APY</Text>
              <Text variant='bold'>{formatPercent(borrowApy)}</Text>
            </div>
            <div className='rateRow'>
              <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
                <Text>Yield APY</Text>
                {props.marketData && (
                  <Text variant='note'>
                    (
                    {props.marketData.yieldVaultName}
                    )
                  </Text>
                )}
              </Stack>
              <Text variant='bold-success'>{formatPercent(yieldApy)}</Text>
            </div>
            <div className='rateRow netSpread'>
              <Text variant='bold'>Net Spread</Text>
              <Text variant={netSpread >= 0 ? 'bold-success' : 'bold-error'}>
                {netSpread >= 0 ? '+' : ''}
                {formatPercent(netSpread)}
              </Text>
            </div>
          </div>
        </Stack>
      </Box>

      {/* Actions */}
      <Spacing variant={PaddingSize.Default} />
      <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
        <Stack.Item growthFactor={1} shrinkFactor={1}>
          <Button
            variant='tertiary'
            text='Withdraw USDC'
            onClicked={props.onWithdrawClicked}
            isFullWidth={true}
          />
        </Stack.Item>
        <Stack.Item growthFactor={1} shrinkFactor={1}>
          <Button
            variant='tertiary'
            text='Close Position'
            onClicked={props.onClosePositionClicked}
            isFullWidth={true}
          />
        </Stack.Item>
      </Stack>
    </Stack>
  );
}
