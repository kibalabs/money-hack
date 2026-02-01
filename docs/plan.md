# AgentLend: Automated Overcollateralized Lending Agent on Base

## Executive Summary
AgentLend is an MVP onchain agent built with AgentWalletKit that enables users to deposit collateral (WETH, WBTC, or cbBTC) on Base, secure an overcollateralized USDC loan via Morpho, and earn ~7-10% yield by depositing the borrowed USDC into the Gauntlet USD Alpha vault. The agent autonomously monitors and adjusts the loan's LTV ratio for safety and profitability, sending Telegram notifications for updates and urgent actions. Users can withdraw USDC partially or fully, with safeguards to maintain position health. All actions are batched via Li.Fi for efficiency, with ENS storing user preferences and optional Uniswap v4 swaps. This demo-focused project emphasizes reliability, transparency, and composability for the ETHGlobal HackMoney 2026 hackathon, targeting Uniswap, Li.Fi, and ENS prize categories.

## Background Information
### Key Onchain Concepts
- **Overcollateralized Lending**: In DeFi protocols like Morpho, users deposit assets (collateral) worth more than the borrowed amount to secure loans. The Loan-to-Value (LTV) ratio (borrow amount / collateral value) must stay below a threshold (e.g., 75-85%) to avoid liquidation, where the protocol sells collateral to repay the loan if LTV exceeds the liquidation threshold (e.g., 90%). Collateral and borrow values are determined by onchain oracles (e.g., Chainlink) for real-time pricing.
- **Yield Vaults**: Smart contracts like Gauntlet USD Alpha aggregate and optimize yield on stablecoins (e.g., USDC) by lending across protocols, offering APY (e.g., 7-10%) net of fees and risks. Deposits earn interest automatically, with withdrawals possible anytime.
- **Onchain Agents**: Using frameworks like AgentWalletKit, agents are smart contract wallets (via ERC-4337) that execute predefined actions securely. Adapters restrict interactions to approved protocols (e.g., Morpho supply/borrow, Gauntlet deposit/withdraw), ensuring transparency and preventing unauthorized actions.
- **Batching and Orchestration**: Tools like Li.Fi compose multi-step transactions (e.g., supply collateral + borrow + deposit to vault) into one user-signed batch, reducing gas and complexity.
- **ENS (Ethereum Name Service)**: Beyond name resolution, ENS text records store arbitrary data (e.g., user preferences like LTV thresholds or Telegram handles) onchain, enabling composable, decentralized configurations.
- **Monitoring and Notifications**: Offchain scripts poll onchain state (e.g., Morpho health factor) and trigger agent actions via UserOps. Integrations like Telegram bots provide offchain alerts for user awareness without constant app interaction.
- **Profitability**: Actions are gated by checks ensuring yield APY exceeds borrow APR + fees (e.g., 8% yield > 3% borrow interest), maintaining net positive returns.

These concepts enable trustless, automated DeFi strategies while mitigating risks like liquidation through proactive adjustments.

## App Description
AgentLend is a web-based dApp (built with Next.js) that interfaces with an onchain agent powered by AgentWalletKit on Base. Users connect their wallet to deposit collateral, open a lending position, and earn yield on borrowed USDC. The agent handles backend automation: opening positions, monitoring LTV, adjusting borrows/repays, and notifying via Telegram. The app provides a simple dashboard for viewing positions and initiating actions like withdrawals or unwinds. Background processes run via an offchain Node.js script for monitoring, ensuring the agent executes onchain only when needed. Security is enforced through AgentWalletKit's adapter registry, limiting interactions to Morpho, Gauntlet, Li.Fi, Uniswap v4, and ENS. The MVP supports three collaterals, focuses on USDC borrows/yields, and prioritizes safe, profitable operations.

## User Screens and Background Operations
### User Screens (Web App)
The app features a minimal, wallet-connected interface for user interactions:
1. **Setup Screen**: Connect wallet (e.g., via WalletConnect). Input Telegram handle (stored in ENS text record "telegram_handle:username"). Select collateral (WETH, WBTC, or cbBTC from dropdown). Enter target LTV (e.g., 75%, stored in ENS "preferred_ltv:75"). Deposit button approves and transfers collateral to the agent wallet.
2. **Dashboard Screen**: Real-time view of position details (fetched onchain): Collateral type/value, borrow amount, current LTV, health factor, vault balance, accrued yield, estimated APY. Buttons for "Withdraw USDC" (slider with max safe amount), "Unwind Position" (full close), and "Refresh" for updates.
3. **Withdrawal Screen**: Modal from dashboard; user inputs USDC amount. Displays projected post-withdrawal LTV and warnings if risky. Confirm triggers agent execution.
4. **Notifications Link**: Simple page to confirm Telegram setup and view recent alerts (pulled from app logs for demo).

User experience is hands-off post-setup: App for active management, Telegram for passive updates.

### Background Operations
- **Onchain Execution**: All agent actions (e.g., supply to Morpho, borrow USDC, deposit to Gauntlet) use AgentWalletKit adapters for security. Batched via Li.Fi Composer for multi-step efficiency. ENS reads preferences onchain (e.g., view functions to fetch text records). Uniswap v4 used only if non-USDC swaps needed (rare in MVP).
- **Offchain Monitoring**: Node.js script runs periodically (every 5-10 min, or 2 min post-withdrawal). Queries Morpho view functions (e.g., getPosition for LTV/health) using Web3.js. If adjustment threshold met (LTV >75% or <65%), script signs and submits UserOp to trigger agent (e.g., withdraw from Gauntlet + repay to Morpho). Profitability checked via rate queries (Morpho borrow APR vs. Gauntlet APY).
- **Notifications**: Integrated Telegram bot (using Telegram API) hooked to agent events and monitor script. Sends formatted messages for actions, summaries, and alerts. Handles stored in ENS for user-specific routing.
- **Safeguards**: LTV buffers (e.g., 10%) prevent over-borrowing. Adjustments skipped if unprofitable or insufficient funds, triggering user alerts instead.

## Example User/Agent Flows
Below are detailed flows illustrating user interactions, agent actions, and background processes. Assumptions: Base chain, Morpho for lending (LTV limits: WETH ~75-85%, WBTC/cbBTC ~70-80%), Gauntlet for yield (~7-10% APY), borrow APR ~2-5%.

### Flow 1: Deposit WBTC to Earn Yield on USDC
- **User Actions**: In app, connect wallet, select WBTC, input Telegram handle and 75% LTV, deposit $100k WBTC equivalent.
- **Agent/Background**: Creates agent wallet if needed. Batches via Li.Fi: Supply WBTC to Morpho (supply call), borrow $75k USDC (borrow call at 75% LTV), deposit to Gauntlet (deposit call). Telegram: "Position opened: WBTC $100k, USDC borrow $75k, LTV 75%, vault earning ~8%."
- **Scenario: Collateral Price Drops (Agent Covers Loan)**: Offchain script detects WBTC drop to $90k (LTV ~83%). Checks profitability (yield 8% > borrow 3% + fees). Agent executes: Withdraw $5k USDC from Gauntlet, repay to Morpho. Telegram: "Alert: LTV 83%. Repaid $5k; new LTV 75%."
- **Scenario: Collateral Price Rises (Agent Borrows More for Yield)**: WBTC rises to $110k (LTV ~68%). Script triggers borrow $5k more USDC, deposit to Gauntlet (profitable: extra yield > interest). Telegram: "Update: Borrowed $5k extra; LTV 75%; yield boost +$0.25/day."
- **User/Agent Close**: User clicks "Unwind" in app. Agent withdraws all USDC from Gauntlet, repays Morpho, returns WBTC. Telegram: "Closed: Returned WBTC + yield minus fees."

### Flow 2: Deposit WETH with USDC Withdrawal
- **User Actions**: Select WETH, deposit $100k equivalent, set 75% LTV. Position opens as above (borrow $75k USDC to vault).
- **Agent/Background**: Same as Flow 1 opening. Dashboard shows details.
- **User Withdrawal**: In app, request $10k USDC. Agent calculates max safe ($20k to keep LTV <85%). Executes: Withdraw $10k from Gauntlet, transfer to user. Telegram: "Withdrew $10k; vault $65k; LTV 75%; yield reduced."
- **Scenario: Post-Withdrawal Price Drop**: Script detects WETH drop, LTV to 80%. Agent repays $5k using remaining vault. Telegram: "Adjusted: Repaid $5k; LTV 75%."
- **Scenario: Insufficient Funds for Adjustment**: After more withdrawals (vault low), LTV hits 87%. Agent can't repay fully—skips and alerts. Telegram: "Critical: LTV 87%, low vault. Deposit USDC or add WETH via app."
- **User/Agent Close**: Similar to Flow 1, with partial repay from remaining vault.

These flows demonstrate the agent's autonomy in maintaining profitable, safe positions while keeping users informed via app and Telegram.
