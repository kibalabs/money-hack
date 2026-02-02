# BorrowBot: Automated Overcollateralized Lending Agent on Base

## Implementation Status

### ✅ Phase 1: Foundation (Complete)

#### Frontend (app/)
- **Wallet Connection**: Full WalletConnect/Base wallet integration with SIWE login
- **Setup Screen (4-step wizard)**:
  - Step 1: Collateral selection (WETH, cbBTC) with logos
  - Step 2: Target LTV selection (65%, 70%, 75%, 80%)
  - Step 3: Deposit amount with summary preview (collateral, LTV, estimated borrow, APY)
  - Step 4: Telegram connection (required - explains why notifications are needed for autonomous agent)
- **Auth Context**: Proper signature-based auth token generation (base64 encoded SIWE message + signature)
- **API Client**: `MoneyHackClient` with typed endpoints for all position operations
- **Navigation Flow**: HomePage → (login) → SetupPage → (create position) → AgentPage

#### Backend (api/)
- **API Endpoints**: Full REST API for collaterals, user config, positions, wallet balances, market data
- **Signature Validation**: Full SIWE + ERC-1271 smart wallet signature verification
- **Resource Models**: CollateralAsset, Position, UserConfig, Wallet, CollateralMarketData with Pydantic
- **Price Feeds**: Real-time collateral price fetching via Alchemy/Moralis APIs

### ✅ Phase 2: Market Data Integration (Complete)

#### Morpho Integration (morpho/)
- **MorphoClient**: GraphQL client for Morpho Blue API
- **Market Data**: Fetch borrow APY, max LTV (LLTV), utilization, supply/borrow totals
- **Market Selection**: Automatically select best market by liquidity for collateral/USDC pairs
- **Supported Methods**: `get_market()`, `get_borrow_apy()`, `get_max_ltv()`, `get_markets_for_collateral()`

#### 40acres Vault Integration (forty_acres/)
- **FortyAcresClient**: On-chain vault interaction via ERC-4626 ABI
- **Vault Info**: Fetch vault name, symbol, asset, decimals, total assets
- **APY Calculation**: Calculate real APY from share price oracle updates over time
- **Supported Methods**: `get_vault_info()`, `get_yield_apy()`

#### API Endpoint
- **`GET /v1/market-data`**: Returns all collateral markets (borrow APY, max LTV) + vault yield APY

---

## Remaining Phases

### ✅ Phase 3: Dashboard & Position Display (Complete)

**Goal**: Show users their active position with real-time data

#### Frontend
- **PositionDashboard Component**: Full dashboard with collateral info, LTV gauge, key stats grid, rate comparison
- **Health Status Indicators**: Visual gauge with healthy/warning/danger states based on LTV vs max LTV
- **Market Rates Display**: Shows borrow APY, yield APY, and net spread
- **Action Buttons**: Refresh, Withdraw USDC, Close Position (UI ready, functionality placeholder)

#### Backend
- **In-Memory Position Storage**: Positions persisted in `_positions` dict (per server instance)
- **Position Refresh on Read**: `get_position()` refreshes collateral value and recalculates LTV with live prices
- **User Config Storage**: `_userConfigs` dict stores telegram handle and preferred LTV

---

### ✅ Phase 4: On-Chain Position Creation (Complete)

**Goal**: Actually execute supply/borrow/deposit transactions on-chain

**Implementation Notes (File-Based Approach):**
- Using file store instead of database to avoid networking complexity
- Transactions are built by backend, signed by user in frontend via @kibalabs/web3-react
- Market params (oracle, IRM, LLTV) fetched from Morpho GraphQL API

#### Backend
- **✅ TransactionBuilder**: Encodes Morpho supply/borrow + 40acres vault deposit transactions
- **✅ MorphoClient**: Fetches market params including oracle, IRM, LLTV from GraphQL
- **✅ GET /v1/users/{addr}/position/transactions endpoint**: Returns list of TransactionCall objects
- **✅ Morpho Supply**: Supply collateral to Morpho market (encoded tx)
- **✅ Morpho Borrow**: Borrow USDC against collateral (encoded tx)
- **✅ 40acres Vault Deposit**: Deposit borrowed USDC into 40acres vault (encoded tx)
- **✅ Transaction Batching**: 5 transactions (approve collateral, supply, borrow, approve USDC, deposit)

#### Frontend
- **✅ getPositionTransactions API method**: Fetches transaction list from backend
- **✅ Transaction Signing**: Sequential signing via useWeb3Transaction + accountSigner
- **✅ Transaction Flow**: Progress UI showing each step with checkmarks/spinners
- **✅ Transaction Status**: Pending/confirmed states with Basescan links
- **✅ Error Handling**: Retry button on failed transactions
- **✅ USD Balance Display**: Shows wallet balance in USD value alongside token amount

---

### ✅ Phase 4B: Telegram OAuth Integration (Complete)

**Goal**: Implement proper Telegram OAuth-style connection instead of just username input

#### Backend
- **✅ TelegramClient**: OAuth-style authentication with secret code verification
  - Generates login URL with secret code
  - Verifies Telegram auth data via HMAC SHA256 signature
  - Links wallet address to Telegram chat_id for messaging
  - Webhook/webhook configuration support

- **✅ API Endpoints**:
  - `GET /v1/users/{userAddress}/telegram/login-url` → Returns OAuth login URL
  - `POST /v1/users/{userAddress}/telegram/verify-code` → Verifies secret + auth data
  - `DELETE /v1/users/{userAddress}/telegram` → Removes Telegram connection

- **✅ UserConfig Updates**:
  - Added `telegram_chat_id` (required for sending messages)
  - Kept `telegram_handle` (optional, for display)
  - File-based persistence

#### Frontend
- **✅ OAuth Flow**: User clicks "Connect Telegram" button → Opens Telegram bot OAuth
- **✅ Callback Handling**: Parses telegram auth data from URL query params
- **✅ SetupPage Integration**: Telegram connection in the 4-step setup wizard
- **✅ UI Feedback**: Shows "Telegram connected ✓" after successful linking
- **✅ Client Methods**: getTelegramLoginUrl, verifyTelegramCode, disconnectTelegram

---

### 🔲 Phase 5: Withdrawals & Position Management

**Goal**: Allow users to withdraw USDC and close positions

#### Frontend
- **Withdrawal Modal**: Input amount, show projected LTV after withdrawal, safety warnings
- **Close Position UI**: Confirm unwind with summary of returned assets

#### Backend
- **Safe Withdrawal Calculation**: Compute max withdrawable amount while maintaining healthy LTV
- **40acres Vault Withdraw**: Withdraw USDC from vault
- **Morpho Repay**: Repay USDC debt
- **Morpho Withdraw Collateral**: Return collateral to user

---

### 🔲 Phase 6: Autonomous LTV Management

**Goal**: Agent automatically maintains healthy positions

#### Background Worker
- **LTV Monitoring**: Periodic position health checks (every 5-10 min)
- **Auto-Repay**: When LTV exceeds target, withdraw from vault and repay debt
- **Auto-Borrow**: When LTV drops significantly below target (and profitable), borrow more and deposit to vault
- **Profitability Gate**: Only take action if yield APY > borrow APR + estimated fees

---

### 🔲 Phase 7: Telegram Notifications

**Goal**: Keep users informed of position changes

#### Backend
- **Notification Service**: Send messages via Telegram Bot API to linked chat_id
- **Notification Types**:
  - Position opened confirmation
  - LTV adjustment alerts (auto-repay/auto-borrow)
  - Critical warnings (LTV approaching liquidation)
  - Position closed confirmation
  - Yield updates and earnings summaries

#### Integration
- Notifications triggered from background worker (Phase 6)
- Graceful degradation if user hasn't connected Telegram

---

### 🔲 Phase 8: Agent Wallet & Security (Stretch)

**Goal**: Use ERC-4337 agent wallets for secure autonomous execution

#### Smart Contracts
- **AgentWalletKit Integration**: Create agent wallet per user
- **Adapter Registry**: Restrict agent to only approved protocol interactions (Morpho, 40acres vault)
- **User Approval**: User signs UserOp to authorize agent actions

---

## Implementation Complete ✓

**Phase 4**: Full on-chain position creation with sequential transaction signing
**Phase 4B**: Complete Telegram OAuth integration with SetupPage flow

### What's Next?
- **Phase 5**: Position management (withdrawals, closing)
- **Phase 6**: Autonomous LTV monitoring and adjustments via background worker
- **Phase 7**: Telegram message notifications via Bot API
- **Phase 8**: ERC-4337 agent wallet for decentralized autonomous execution

---

## Executive Summary
BorrowBot is an MVP onchain agent built with AgentWalletKit that enables users to deposit collateral (WETH or cbBTC) on Base, secure an overcollateralized USDC loan via Morpho, and earn ~7-10% yield by depositing the borrowed USDC into 40acres vault. The agent autonomously monitors and adjusts the loan's LTV ratio for safety and profitability, sending Telegram notifications for updates and urgent actions. Users can withdraw USDC partially or fully, with safeguards to maintain position health. All actions are signed by the user with sequential transaction flows. This demo-focused project emphasizes reliability, transparency, and composability for DeFi yield optimization.

## Background Information
### Key Onchain Concepts
- **Overcollateralized Lending**: In DeFi protocols like Morpho, users deposit assets (collateral) worth more than the borrowed amount to secure loans. The Loan-to-Value (LTV) ratio (borrow amount / collateral value) must stay below a threshold (e.g., 75-85%) to avoid liquidation, where the protocol sells collateral to repay the loan if LTV exceeds the liquidation threshold (e.g., 90%). Collateral and borrow values are determined by onchain oracles (e.g., Chainlink) for real-time pricing.
- **Yield Vaults**: Smart contracts like 40acres vault aggregate and optimize yield on stablecoins (e.g., USDC) by lending across protocols, offering APY (e.g., 7-10%) net of fees and risks. Deposits earn interest automatically, with withdrawals possible anytime.
- **Onchain Agents**: Using frameworks like AgentWalletKit, agents are smart contract wallets (via ERC-4337) that execute predefined actions securely. Adapters restrict interactions to approved protocols (e.g., Morpho supply/borrow, 40acres vault deposit/withdraw), ensuring transparency and preventing unauthorized actions.
- **Batching and Orchestration**: Tools like Li.Fi compose multi-step transactions (e.g., supply collateral + borrow + deposit to vault) into one user-signed batch, reducing gas and complexity.
- **ENS (Ethereum Name Service)**: Beyond name resolution, ENS text records store arbitrary data (e.g., user preferences like LTV thresholds or Telegram handles) onchain, enabling composable, decentralized configurations.
- **Monitoring and Notifications**: Offchain scripts poll onchain state (e.g., Morpho health factor) and trigger agent actions via UserOps. Integrations like Telegram bots provide offchain alerts for user awareness without constant app interaction.
- **Profitability**: Actions are gated by checks ensuring yield APY exceeds borrow APR + fees (e.g., 8% yield > 3% borrow interest), maintaining net positive returns.

These concepts enable trustless, automated DeFi strategies while mitigating risks like liquidation through proactive adjustments.

## App Description
BorrowBot is a web-based dApp (built with React) that enables users to deposit collateral, open lending positions, and earn yield on borrowed USDC. The app provides a 4-step setup wizard for new positions: connect wallet, connect Telegram (via OAuth), select collateral, and enter LTV. Backend handles position creation with sequential transaction signing. A simple dashboard shows position details and withdrawal controls. Background automation monitors positions for LTV adjustments and sends Telegram notifications. Security relies on file-based storage and user-controlled transaction signing. The MVP supports WETH and cbBTC collaterals, focuses on USDC borrows/yields, and prioritizes safe, profitable operations.

## User Screens and Background Operations
### User Screens (Web App)
The app features a wallet-connected interface with a 4-step setup wizard and dashboard:
1. **Setup Step 1 - Collateral**: Connect wallet (e.g., via WalletConnect). Select collateral (WETH or cbBTC from dropdown). View available balance with USD value.
2. **Setup Step 2 - LTV**: Choose target LTV (65% conservative to 80% aggressive). Shows risk description for each level.
3. **Setup Step 3 - Deposit Amount**: Enter deposit amount. View projected borrow amount and yield estimate. "Max" button fills with available balance.
4. **Setup Step 4 - Telegram**: Click "Connect Telegram" button → Opens Telegram OAuth flow → User authenticates with bot → Returns to app with chat_id linked. Displays "Telegram connected ✓" when successful.
5. **Position Creation**: Final "Create Position" button triggers 5 sequential transactions (approve, supply, borrow, approve USDC, deposit to vault). Progress UI shows each step with checkmarks and spinners.
6. **Dashboard Screen**: Real-time view of position (fetched onchain): Collateral type/value, borrow amount, current LTV, health factor, vault balance, accrued yield, estimated APY. Buttons for "Withdraw USDC" (slider with max safe amount), "Unwind Position" (full close), and "Refresh" for updates.

3. **Withdrawal Screen**: Modal from dashboard; user inputs USDC amount. Displays projected post-withdrawal LTV and warnings if risky. Confirm triggers agent execution.
4. **Notifications Link**: Simple page to confirm Telegram setup and view recent alerts (pulled from app logs for demo).

User experience is hands-off post-setup: App for active management, Telegram for passive updates.

### Background Operations
- **Onchain Execution**: All agent actions (e.g., supply to Morpho, borrow USDC, deposit to 40acres vault) use AgentWalletKit adapters for security. Batched via Li.Fi Composer for multi-step efficiency. ENS reads preferences onchain (e.g., view functions to fetch text records). Uniswap v4 used only if non-USDC swaps needed (rare in MVP).
- **Offchain Monitoring**: Node.js script runs periodically (every 5-10 min, or 2 min post-withdrawal). Queries Morpho view functions (e.g., getPosition for LTV/health) using Web3.js. If adjustment threshold met (LTV >75% or <65%), script signs and submits UserOp to trigger agent (e.g., withdraw from 40acres vault + repay to Morpho). Profitability checked via rate queries (Morpho borrow APR vs. 40acres vault APY).
- **Notifications**: Integrated Telegram bot (using Telegram API) hooked to agent events and monitor script. Sends formatted messages for actions, summaries, and alerts. Handles stored in ENS for user-specific routing.
- **Safeguards**: LTV buffers (e.g., 10%) prevent over-borrowing. Adjustments skipped if unprofitable or insufficient funds, triggering user alerts instead.

## Example User/Agent Flows
Below are detailed flows illustrating user interactions, position creation, and future autonomous management. Assumptions: Base chain, Morpho for lending (LTV limits: WETH ~75-85%, cbBTC ~70-80%), 40acres vault for yield (~7-10% APY), borrow APR ~2-5%).

### Flow 1: Deposit cbBTC to Earn Yield on USDC
- **User Actions**: In app, 4-step setup: (1) connect wallet, select cbBTC, (2) choose 75% LTV, (3) enter $100k deposit, (4) connect Telegram via OAuth. Click "Create Position".
- **Frontend/Backend**: Builds and signs 5 transactions sequentially: Approve cbBTC, supply to Morpho, borrow $75k USDC, approve USDC, deposit to 40acres vault. Progress UI shows each step with checkmark/spinner. All 5 signed by user.
- **Notifications**: Telegram: "Position opened: cbBTC $100k, USDC borrow $75k, LTV 75%, vault earning ~8%."
- **Scenario: Collateral Price Drops (Future - Phase 6)**: Offchain script detects cbBTC drop to $90k (LTV ~83%). Checks profitability (yield 8% > borrow 3% + fees). Agent executes: Withdraw $5k USDC from 40acres vault, repay to Morpho. Telegram: "Alert: LTV 83%. Repaid $5k; new LTV 75%."
- **Scenario: Collateral Price Rises (Future - Phase 6)**: cbBTC rises to $110k (LTV ~68%). Script triggers borrow $5k more USDC, deposit to 40acres vault (profitable: extra yield > interest). Telegram: "Update: Borrowed $5k extra; LTV 75%; yield boost +$0.25/day."
- **User Close**: User clicks "Unwind" in dashboard. Frontend builds transactions to withdraw all USDC from 40acres vault, repay Morpho, return cbBTC. Telegram: "Closed: Returned cbBTC + yield minus fees."

### Flow 2: Deposit WETH with USDC Withdrawal
- **User Actions**: 4-step setup: select WETH, 75% LTV, $100k deposit, connect Telegram. Create position. Position opens as above.
- **Frontend/Backend**: Dashboard shows collateral value in USD. Sequential transactions create position with USD balance display.
- **User Withdrawal**: In app dashboard, enter $10k USDC request. Max safe calculated ($20k to keep LTV <85%). Builds and signs withdrawal transactions. Telegram: "Withdrew $10k; vault $65k; LTV 75%; yield reduced."
- **Scenario: Post-Withdrawal Price Drop (Future - Phase 6)**: Script detects WETH drop, LTV to 80%. Agent repays $5k using remaining vault. Telegram: "Adjusted: Repaid $5k; LTV 75%."
- **Scenario: Insufficient Funds for Adjustment (Future)**: After more withdrawals (vault low), LTV hits 87%. Agent can't repay fully—skips and alerts. Telegram: "Critical: LTV 87%, low vault. Deposit USDC or add WETH via app."
- **User Close**: Similar to Flow 1, with partial repay from remaining vault.

These flows demonstrate the 4-step setup with Telegram OAuth, sequential transaction signing, and future autonomous management keeping users informed.
