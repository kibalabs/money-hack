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

### ✅ Phase 4C: Database & Data Model (Complete)

**Goal**: Migrate from file-based storage to PostgreSQL database to support proper user/agent management

#### Database Tables
- **tbl_users**: User accounts with Telegram linking
- **tbl_user_wallets**: Wallet ↔ User relationship
- **tbl_agents**: Autonomous lending agents (name, emoji, ENS subdomain)
- **tbl_agent_positions**: Morpho lending positions per agent
- **tbl_agent_actions**: Audit log of agent actions
- **tbl_chat_events**: Chat/notification history

#### Implementation
- Alembic migrations (matches agent-hack pattern)
- EntityRepository pattern for DB access
- DatabaseStore replaces FileStore in AgentManager

---

### ✅ Phase 4D: Agent Creation Flow (Complete)

**Goal**: Users create a named agent at the end of the setup flow

**Updated Setup Wizard (4-5 steps):**

1. **Step 1 - Collateral Selection**: Same as before (WETH, cbBTC)

2. **Step 2 - LTV Selection**: Same as before (65-80%)

3. **Step 3 - Deposit Amount**: Same as before (with preview)

4. **Step 4 - Connect Telegram** *(conditional)*:
   - Only shown if user doesn't already have Telegram linked
   - If already connected, skip to step 5
   - Uses existing OAuth flow

5. **Step 5 - Name Your Agent**:
   - Name input (e.g., "My Yield Bot", "WETH Farmer")
   - Emoji picker (🤖 💰 🚀 📈 🏦 💎 ⚡ 🔥 🌟 🎯)
   - Preview shows selected emoji + name
   - Creates Agent record in database with the position

**Backend Changes:**
- Add `POST /v1/users/{userAddress}/agents` - Create new agent with name + emoji
- Modify position creation to require agentId or create agent inline
- Load user config at start to check Telegram connection status

**Agent Dashboard Updates:**
- Shows agent name + emoji in header
- "My Agent: 🤖 WETH Farmer" style branding
- Agent-centric URLs: `/agent/{agentId}` instead of `/position`

---

### ✅ Phase 4E: Telegram Webhook & Message Handling (Complete)

**Goal**: Receive messages from Telegram users and route authentication data to the frontend

#### Backend
- **✅ POST /v1/telegram-webhook**: Telegram Bot API webhook endpoint
  - Receives message updates from Telegram Bot API
  - For unknown users: sends login link with secret code
  - For known users: updates chat_id, sends welcome message
  - Returns 200 OK to acknowledge receipt

- **✅ POST /v1/users/{userAddress}/telegram/secret-verify**: Verify secret code
  - Validates secret code from in-memory cache
  - Links wallet address to Telegram chat_id
  - Sends confirmation message to user

- **✅ GET /v1/users/{userAddress}/telegram/login-url**: Returns bot username
  - Returns @botUsername for frontend to open Telegram

#### Frontend
- **✅ Telegram Connection Flow**:
  - User clicks "Connect Telegram" → opens Telegram bot
  - User messages bot → bot sends link with telegramSecret
  - User clicks link → returns to app with telegramSecret param
  - Frontend calls telegramSecretVerify → linking complete

---

### ✅ Phase 5: Withdrawals & Position Management

**Goal**: Allow users to withdraw USDC and close positions

#### Frontend
- **Withdrawal Modal**: Input amount, show projected LTV after withdrawal, safety warnings
- **Close Position UI**: Confirm unwind with summary of returned assets

#### Backend
- **Safe Withdrawal Calculation**: Compute max withdrawable amount while maintaining healthy LTV
- **40acres Vault Withdraw**: Withdraw USDC from vault
- **Morpho Repay**: Repay USDC debt
- **Morpho Withdraw Collateral**: Return collateral to user

**Implementation Notes**:
- Added `encode_repay`, `encode_withdraw_collateral`, `encode_vault_withdraw` to transaction_builder.py
- Added `build_withdraw_transactions`, `build_close_position_transactions_from_market` to TransactionBuilder
- Implemented `get_withdraw_transactions` and `get_close_position_transactions` in AgentManager
- Updated API endpoints to return transaction lists for user signing
- Frontend updated to use new transaction-based withdrawal flow

---

### ✅ Phase 6: Autonomous LTV Management

**Goal**: Agent automatically maintains healthy positions

#### Background Worker
- **LTV Monitoring**: Periodic position health checks (every 5-10 min)
- **Auto-Repay**: When LTV exceeds target, withdraw from vault and repay debt
- **Auto-Borrow**: When LTV drops significantly below target (and profitable), borrow more and deposit to vault
- **Profitability Gate**: Only take action if yield APY > borrow APR + estimated fees
- **Action Logging**: All autonomous actions recorded in tbl_agent_actions for audit trail

**Implementation Notes**:
- Created `LtvManager` class in morpho/ltv_manager.py for LTV monitoring
- Added `check_position_ltv` to detect when action is needed (5% margin thresholds)
- Added `build_partial_repay_transactions` and `build_auto_borrow_transactions` to TransactionBuilder
- Worker loop checks all active positions every 5 minutes
- Actions logged to tbl_agent_actions with ltv_check action type
- Added `get_all_active_positions` to DatabaseStore

---

### ✅ Phase 7: Telegram Notifications

**Goal**: Keep users informed of position changes

#### Backend
- **Notification Service**: Send messages via Telegram Bot API to linked chat_id
- **Notification Types**:
  - Position opened confirmation (with agent name + emoji)
  - LTV adjustment alerts (auto-repay/auto-borrow)
  - Critical warnings (LTV approaching liquidation)
  - Position closed confirmation
  - Daily/weekly yield summaries

#### Integration
- Notifications triggered from background worker (Phase 6)
- Graceful degradation if user hasn't connected Telegram
- Messages stored in tbl_agent_actions for history

**Implementation Notes**:
- Created `NotificationService` class in notification_service.py
- Added notification methods to TelegramClient for different notification types
- Worker sends critical LTV warnings when position LTV reaches 80% of max LTV
- Notifications logged to tbl_agent_actions for audit trail
- Added `get_user` and `get_agent` methods to DatabaseStore

---

### ✅ Phase 8: ENS Integration (Hackathon Prize Category)

**Goal**: Creative use of ENS for agent identity and configuration

See [ens-integration.md](ens-integration.md) for detailed spec.

**Summary:**
- Agents get ENS subdomains under `borrowbot.eth` (e.g., `mybot.borrowbot.eth`)
- Agent config stored as ENS text records (LTV preferences, notification settings)
- On-chain readable by any protocol - composable DeFi identity
- Resolves to agent's smart wallet address

**Implementation Notes**:
- Created `EnsClient` class in external/ens_client.py
- Added `EnsAgentConfig` model for agent configuration text records
- Added ENS name validation and availability checking
- Added methods to build subdomain registration and text record transactions
- API endpoints: `/v1/ens/check-name`, `/v1/users/{addr}/ens/config-transactions`
- Agent creation can now reserve ENS names and store them in database

---

### 🔲 Phase 9: Agent Wallet & Security (Stretch)

**Goal**: Use ERC-4337 agent wallets for secure autonomous execution

#### Smart Contracts
- **AgentWalletKit Integration**: Create agent wallet per user
- **Adapter Registry**: Restrict agent to only approved protocol interactions (Morpho, 40acres vault)
- **User Approval**: User signs UserOp to authorize agent actions

---

## Implementation Priority (Hackathon Focus)

**Must Have (Demo-Ready):**
1. ✅ Phase 1-4B: Foundation complete
2. 🔲 Phase 4C: Database schema (users, agents, positions)
3. 🔲 Phase 4D: Agent creation flow (name + emoji)
4. 🔲 Phase 4E: Telegram webhook (complete OAuth flow)
5. 🔲 Phase 8: ENS integration (hackathon prize category)

**Nice to Have:**
- Phase 5: Withdrawals
- Phase 7: Telegram notifications

**Stretch:**
- Phase 6: Autonomous management
- Phase 9: ERC-4337 agent wallets

---

## Data Model Summary (matching agent-hack pattern)

```
┌─────────────────┐      ┌─────────────────┐
│    tbl_users    │      │  tbl_user_wallets│
│                 │      │                  │
│  id (UUID PK)   │◄────►│  user_id (FK)    │
│  username       │      │  wallet_address  │
│  telegram_id    │      └──────────────────┘
│  telegram_chat_id│
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐      ┌─────────────────────┐
│   tbl_agents    │      │  tbl_agent_positions │
│                 │      │                      │
│  id (UUID PK)   │◄────►│  agent_id (FK)       │
│  user_id (FK)   │      │  collateral_asset    │
│  name           │      │  borrow_amount       │
│  emoji          │      │  target_ltv          │
│  ens_name       │      │  vault_shares        │
└────────┬────────┘      └──────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐      ┌─────────────────┐
│ tbl_agent_actions│     │  tbl_chat_events │
│                 │      │                  │
│  agent_id (FK)  │      │  user_id (FK)    │
│  action_type    │      │  agent_id (FK)   │
│  value          │      │  event_type      │
│  details (JSON) │      │  content (JSON)  │
└─────────────────┘      └──────────────────┘
```

---

## Implementation Complete ✓

**Phase 4**: Full on-chain position creation with sequential transaction signing
**Phase 4B**: Complete Telegram OAuth integration with SetupPage flow

### What's Next?
1. **Phase 4C**: Database schema migration (PostgreSQL)
2. **Phase 4D**: Agent creation flow (name, emoji, ENS subdomain)
3. **Phase 4E**: Telegram webhook for complete OAuth flow
4. **Phase 8**: ENS integration for hackathon prize

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
