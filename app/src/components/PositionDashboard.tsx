import React from 'react';

import { Alignment, Box, Button, Direction, Image, KibaIcon, LinkBase, PaddingSize, Spacing, Stack, Text } from '@kibalabs/ui-react';

import { Agent, CollateralMarketData, EnsConstitution, MarketData, Position } from '../client/resources';

import './PositionDashboard.scss';

interface IPositionDashboardProps {
  position: Position;
  marketData: MarketData | null;
  agent: Agent | null;
  constitution: EnsConstitution | null;
  latestCriticalMessage: string | null;
  onRefreshClicked: () => void;
  onDepositClicked: () => void;
  onDepositUsdcClicked: () => void;
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

const formatExactAmount = (amount: bigint, decimals: number): string => {
  const whole = amount / BigInt(10 ** decimals);
  const fraction = amount % BigInt(10 ** decimals);
  const fractionText = fraction.toString().padStart(decimals, '0');
  return `${whole.toString()}.${fractionText}`;
};

const formatUsdcRaw = (amount: bigint): string => {
  const whole = amount / 1000000n;
  const fraction = amount % 1000000n;
  const fractionText = fraction.toString().padStart(6, '0');
  return `${whole.toString()}.${fractionText}`;
};

const getHealthStatus = (ltv: number, maxLtv: number, canAgentManage: boolean): 'healthy' | 'warning' | 'danger' => {
  const ratio = ltv / maxLtv;
  if (ratio >= 0.95) return canAgentManage ? 'warning' : 'danger';
  if (ratio >= 0.85) return canAgentManage ? 'healthy' : 'warning';
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
  const canAgentManage = props.position.vaultBalanceUsd > 0 && props.position.walletUsdcBalance === 0n;
  const healthStatus = getHealthStatus(props.position.currentLtv, maxLtv, canAgentManage);
  const healthPercent = getHealthPercent(props.position.currentLtv, maxLtv);

  const borrowApy = collateralMarket?.borrowApy ?? 0;
  const yieldApy = props.marketData?.yieldApy ?? 0;
  const netSpread = yieldApy - borrowApy;

  const totalAssetsUsd = props.position.collateralValueUsd
    + props.position.vaultBalanceUsd
    + props.position.walletCollateralBalanceUsd
    + props.position.walletUsdcBalanceUsd;
  const totalDebtUsd = props.position.borrowValueUsd;
  const netPositionUsd = totalAssetsUsd - totalDebtUsd;

  const closeShortfallRaw = React.useMemo((): bigint => {
    const availableUsdcRaw = props.position.vaultBalance + props.position.walletUsdcBalance;
    if (props.position.borrowAmount > availableUsdcRaw) {
      return props.position.borrowAmount - availableUsdcRaw;
    }
    return 0n;
  }, [props.position.borrowAmount, props.position.vaultBalance, props.position.walletUsdcBalance]);

  const usdcLogoUri = 'https://assets.coingecko.com/coins/images/6319/small/usdc.png';

  return (
    <Stack className='positionDashboard' direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
      <Stack direction={Direction.Vertical} childAlignment={Alignment.Center} shouldAddGutters={true} isFullWidth={true}>
        <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} contentAlignment={Alignment.Center} shouldAddGutters={true} isFullWidth={true}>
          <Text variant='header2'>{props.agent ? `${props.agent.emoji} ${props.agent.name}` : 'Position Dashboard'}</Text>
          <Stack.Item growthFactor={1} shrinkFactor={1} />
          <Button
            variant='tertiary-small'
            iconLeft={<KibaIcon iconId='ion-refresh' />}
            text='Refresh'
            onClicked={props.onRefreshClicked}
            isLoading={props.isRefreshing}
          />
        </Stack>
        {props.constitution && props.constitution.ensName && (
          <LinkBase
            target={`https://app.ens.domains/${props.constitution.ensName}`}
            isOpeningInNewTab={true}
          >
            <Text variant='note' style={{ color: '#3b82f6', textDecoration: 'underline' }}>
              {props.constitution.ensName}
            </Text>
          </LinkBase>
        )}
      </Stack>

      <Spacing variant={PaddingSize.Default} />

      {/* Critical LTV Warning */}
      {(healthStatus === 'danger' || (healthStatus === 'warning' && props.latestCriticalMessage)) && (
        <Box className={`criticalWarningBanner ${healthStatus}`} isFullWidth={true}>
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Text variant='bold'>
              {healthStatus === 'danger' ? 'Position At Risk' : 'Position Warning'}
            </Text>
            {props.latestCriticalMessage ? (
              <Text variant='note'>{props.latestCriticalMessage}</Text>
            ) : (
              <Text variant='note'>
                Your LTV is approaching the liquidation threshold. Deposit collateral or USDC to protect your position.
              </Text>
            )}
            <Stack direction={Direction.Horizontal} shouldAddGutters={true}>
              <Button
                variant='primary-small'
                text='Deposit USDC'
                onClicked={props.onDepositUsdcClicked}
              />
              <Button
                variant='tertiary-small'
                text='Deposit Collateral'
                onClicked={props.onDepositClicked}
              />
            </Stack>
          </Stack>
        </Box>
      )}

      {/* Net Position Summary */}
      <Box className='statCard' isFullWidth={true}>
        <Stack direction={Direction.Vertical} shouldAddGutters={true} childAlignment={Alignment.Center}>
          <Text variant='note'>Net Position Value</Text>
          <Text variant='header2'>{formatUsd(netPositionUsd)}</Text>
          <Stack direction={Direction.Horizontal} shouldAddGutters={true} childAlignment={Alignment.Center}>
            <Text variant='note'>
              {'Assets: '}
              {formatUsd(totalAssetsUsd)}
            </Text>
            <Text variant='note'>
              {'Debt: '}
              {formatUsd(totalDebtUsd)}
            </Text>
          </Stack>
        </Stack>
      </Box>


      {/* Assets (what you own) */}
      <Box className='statCard' isFullWidth={true}>
        <Stack direction={Direction.Vertical} shouldAddGutters={true}>
          <Text variant='bold'>Assets</Text>
          <Spacing variant={PaddingSize.Narrow} />
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
            {props.position.collateralAsset.logoUri && (
              <Box width='28px' height='28px'>
                <Image
                  source={props.position.collateralAsset.logoUri}
                  alternativeText={props.position.collateralAsset.symbol}
                  isFullWidth={true}
                  isFullHeight={true}
                />
              </Box>
            )}
            <Stack direction={Direction.Vertical}>
              <Text>
                {props.position.collateralAsset.symbol}
                {' Collateral'}
              </Text>
              <Text variant='note'>Locked in Morpho</Text>
            </Stack>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
              <Text variant='bold'>{formatUsd(props.position.collateralValueUsd)}</Text>
              <Text variant='note'>
                {formatExactAmount(props.position.collateralAmount, props.position.collateralAsset.decimals)}
                {' '}
                {props.position.collateralAsset.symbol}
              </Text>
            </Stack>
          </Stack>
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
            <Box width='28px' height='28px'>
              <Image
                source={usdcLogoUri}
                alternativeText='USDC'
                isFullWidth={true}
                isFullHeight={true}
              />
            </Box>
            <Stack direction={Direction.Vertical}>
              <Text>USDC in Vault</Text>
              <Text variant='note'>
                {'Earning '}
                {formatPercent(yieldApy)}
                {' APY'}
              </Text>
            </Stack>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
              <Text variant='bold'>{formatUsd(props.position.vaultBalanceUsd)}</Text>
              <Text variant='note'>
                {formatExactAmount(props.position.vaultBalance, 6)} USDC
              </Text>
            </Stack>
          </Stack>
          {props.position.walletUsdcBalance > 0n && (
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
              <Box width='28px' height='28px'>
                <Image
                  source={usdcLogoUri}
                  alternativeText='USDC'
                  isFullWidth={true}
                  isFullHeight={true}
                />
              </Box>
              <Stack direction={Direction.Vertical}>
                <Text>USDC in Wallet</Text>
                <Text variant='note'>Idle</Text>
              </Stack>
              <Stack.Item growthFactor={1} shrinkFactor={1} />
              <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
                <Text variant='bold'>{formatUsd(props.position.walletUsdcBalanceUsd)}</Text>
                <Text variant='note'>
                  {formatExactAmount(props.position.walletUsdcBalance, 6)} USDC
                </Text>
              </Stack>
            </Stack>
          )}
          {props.position.walletCollateralBalance > 0n && (
            <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
              {props.position.collateralAsset.logoUri && (
                <Box width='28px' height='28px'>
                  <Image
                    source={props.position.collateralAsset.logoUri}
                    alternativeText={props.position.collateralAsset.symbol}
                    isFullWidth={true}
                    isFullHeight={true}
                  />
                </Box>
              )}
              <Stack direction={Direction.Vertical}>
                <Text>{props.position.collateralAsset.symbol} in Wallet</Text>
                <Text variant='note'>Idle</Text>
              </Stack>
              <Stack.Item growthFactor={1} shrinkFactor={1} />
              <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
                <Text variant='bold'>{formatUsd(props.position.walletCollateralBalanceUsd)}</Text>
                <Text variant='note'>
                  {formatExactAmount(props.position.walletCollateralBalance, props.position.collateralAsset.decimals)}
                  {' '}
                  {props.position.collateralAsset.symbol}
                </Text>
              </Stack>
            </Stack>
          )}
        </Stack>
      </Box>

      {/* Debt (what you owe) */}
      <Box className='statCard' isFullWidth={true}>
        <Stack direction={Direction.Vertical} shouldAddGutters={true}>
          <Text variant='bold'>Debt</Text>
          <Spacing variant={PaddingSize.Narrow} />
          <Stack direction={Direction.Horizontal} childAlignment={Alignment.Center} shouldAddGutters={true}>
            <Box width='28px' height='28px'>
              <Image
                source={usdcLogoUri}
                alternativeText='USDC'
                isFullWidth={true}
                isFullHeight={true}
              />
            </Box>
            <Stack direction={Direction.Vertical}>
              <Text>USDC Loan</Text>
              <Text variant='note'>
                {'Costing '}
                {formatPercent(borrowApy)}
                {' APY'}
              </Text>
            </Stack>
            <Stack.Item growthFactor={1} shrinkFactor={1} />
            <Stack direction={Direction.Vertical} childAlignment={Alignment.End}>
              <Text variant='bold'>{formatUsd(props.position.borrowValueUsd)}</Text>
              <Text variant='note'>
                {formatExactAmount(props.position.borrowAmount, 6)} USDC
              </Text>
            </Stack>
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
                  <Text variant='note'>{`(${props.marketData.yieldVaultName})`}</Text>
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
      <Spacing variant={PaddingSize.Wide} />
      <Stack direction={Direction.Vertical} shouldAddGutters={true} isFullWidth={true}>
        {closeShortfallRaw > 0n && (
          <Stack direction={Direction.Vertical} shouldAddGutters={true}>
            <Text variant='note-warning'>You need {formatUsdcRaw(closeShortfallRaw)} USDC (${formatUsdcRaw(closeShortfallRaw)}) to fully repay the loan. Deposit more USDC before closing.</Text>
          </Stack>
        )}
        <Stack direction={Direction.Horizontal} shouldAddGutters={true} isFullWidth={true}>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='primary'
              text='Deposit Collateral'
              onClicked={props.onDepositClicked}
              isFullWidth={true}
            />
          </Stack.Item>
          <Stack.Item growthFactor={1} shrinkFactor={1}>
            <Button
              variant='primary'
              text='Deposit USDC'
              onClicked={props.onDepositUsdcClicked}
              isFullWidth={true}
            />
          </Stack.Item>
        </Stack>
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
    </Stack>
  );
}
