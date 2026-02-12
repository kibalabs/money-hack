# ruff: noqa: T201
import asyncio

from core import logging

import _path_fix  # type: ignore[import-not-found]  # noqa: F401
from money_hack.agent_manager import SUPPORTED_COLLATERALS
from money_hack.create_agent_manager import create_agent_manager
from money_hack.morpho.ltv_manager import LTV_MARGIN_UPPER

DELAY_SECONDS = 60


async def main() -> None:
    logging.init_basic_logging()
    agentManager = create_agent_manager()
    await agentManager.databaseStore.database.connect(poolSize=2)
    try:
        async with agentManager.databaseStore.database.create_context_connection():
            positions = await agentManager.databaseStore.get_all_active_positions()
            if not positions:
                print('No active positions found.')
                return
            position = positions[0]
            agent = await agentManager.databaseStore.get_agent(agentId=position.agentId)
            if not agent:
                print(f'Agent {position.agentId} not found.')
                return
            user = await agentManager.databaseStore.get_user(userId=agent.userId)
            if not user or not user.telegramChatId:
                print(f'User for agent {agent.agentId} has no telegram chat ID.')
                return
            chatId = user.telegramChatId
            collateral = next((c for c in SUPPORTED_COLLATERALS if c.address.lower() == position.collateralAsset.lower()), SUPPORTED_COLLATERALS[0])

            onchainCollateral, onchainBorrow, _borrowShares = await agentManager._get_onchain_position(
                agentWalletAddress=agent.walletAddress,
                morphoMarketId=position.morphoMarketId,
            )
            _vaultShares, vaultAssets = await agentManager._get_actual_vault_balance(agentWalletAddress=agent.walletAddress)
            priceUsd = await agentManager._get_asset_price(assetAddress=position.collateralAsset)
            collateralAmountHuman = onchainCollateral / (10 ** collateral.decimals)
            collateralValueUsd = collateralAmountHuman * priceUsd
            borrowValueUsd = onchainBorrow / 1e6
            currentLtv = borrowValueUsd / collateralValueUsd if collateralValueUsd > 0 else 0
            targetLtv = position.targetLtv
            highLtv = targetLtv + LTV_MARGIN_UPPER
            lowLtv = targetLtv - LTV_MARGIN_UPPER

            repayAmountUsd = (highLtv - targetLtv) * collateralValueUsd
            borrowAmountUsd = (targetLtv - lowLtv) * collateralValueUsd

            print(f'Agent: {agent.emoji} {agent.name}')
            print(f'Collateral: {collateralAmountHuman:.4f} {collateral.symbol} (${collateralValueUsd:,.2f})')
            print(f'Debt: ${borrowValueUsd:,.2f}')
            print(f'Current LTV: {currentLtv:.1%}, Target: {targetLtv:.1%}')
            print(f'Vault: ${vaultAssets / 1e6:,.2f}')
            print(f'Simulated repay: ${repayAmountUsd:,.2f} (high LTV {highLtv:.1%} -> {targetLtv:.1%})')
            print(f'Simulated borrow: ${borrowAmountUsd:,.2f} (low LTV {lowLtv:.1%} -> {targetLtv:.1%})')

            messages = [
                (
                    f'I detected your LTV was high ({highLtv:.1%}) and automatically withdrew ${repayAmountUsd:,.2f} '
                    f'from your yield vault to repay debt. Your position is now healthy at {targetLtv:.1%}.'
                ),
                (
                    f'Daily Update: Everything is healthy. 🟢\n'
                    f'Current LTV: {targetLtv:.1%}\n'
                    f'Collateral: ${collateralValueUsd:,.2f}\n'
                    f'Debt: ${borrowValueUsd:,.2f}\n'
                    f'No action needed.'
                ),
                (
                    f'Market conditions are favorable, so I borrowed an additional ${borrowAmountUsd:,.2f} USDC '
                    f'and deposited it into the yield vault to maximize your earnings. '
                    f'LTV moved from {lowLtv:.1%} to {targetLtv:.1%}.'
                ),
                (
                    f'Daily Update: Everything is healthy. 🟢\n'
                    f'Current LTV: {targetLtv:.1%}\n'
                    f'Collateral: ${collateralValueUsd:,.2f}\n'
                    f'Debt: ${borrowValueUsd:,.2f}\n'
                    f'No action needed.'
                ),
            ]

            for i, message in enumerate(messages):
                print(f'\n[{i + 1}/{len(messages)}] Sending: {message[:80]}...')
                await agentManager.telegramClient.send_message(chatId=chatId, text=message)
                print('  ✅ Sent!')
                if i < len(messages) - 1:
                    print(f'  Waiting {DELAY_SECONDS}s...')
                    await asyncio.sleep(DELAY_SECONDS)

            print('\nDemo complete!')
    finally:
        await agentManager.requester.close_connections()
        await agentManager.databaseStore.database.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
