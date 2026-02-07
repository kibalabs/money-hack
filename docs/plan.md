# BorrowBot: Automated Overcollateralized Lending Agent

## Project Overview

BorrowBot is an autonomous agent on **Base** that manages overcollateralized loans. Users deposit WETH or cbBTC, and the agent automatically borrows USDC via **Morpho Blue** to earn yield in **40acres vaults**. The agent's primary job is to monitor LTV (Loan-to-Value) and rebalance positions to maximize yield while preventing liquidation.

---

## 🛠 Phases of Implementation

### ✅ Phase 1: Foundation

* **Outcome**: Secure user onboarding and wallet connectivity.
* **Design Details**: 4-step setup wizard (Collateral → LTV → Deposit → Telegram). Uses SIWE for signature-based authentication and a typed API client for position operations.

### ✅ Phase 2: Market Data Integration

* **Outcome**: Real-time yield and risk assessment.
* **Design Details**: Integration with Morpho Blue (GraphQL) for borrow rates/LLTV and 40acres (ERC-4626) for vault APY. Automatically selects the most liquid markets for collateral/USDC pairs.

### ✅ Phase 3: Dashboard & Position Display

* **Outcome**: High-fidelity monitoring for the user.
* **Design Details**: Real-time dashboard featuring an LTV health gauge (Healthy/Warning/Danger) and net spread comparison (Yield APY vs. Borrow APR).

### ✅ Phase 4: On-Chain Position Creation

* **Outcome**: One-click execution of complex DeFi strategies.
* **Design Details**: Orchestrates a 5-transaction batch: Approve collateral → Supply to Morpho → Borrow USDC → Approve USDC → Deposit to Vault. Includes a progress UI to track each step.

### ✅ Phase 4B: Telegram OAuth Integration

* **Outcome**: Secure, verified communication channel.
* **Design Details**: Links wallet addresses to Telegram `chat_id` via a secret-code verification flow. Enables the agent to send proactive alerts to the correct user.

### ✅ Phase 4C: Database & Data Model

* **Outcome**: Persistent storage for autonomous management.
* **Design Details**: PostgreSQL schema tracking Users, Wallets, Agents, Positions, and an Audit Log of all agent actions.

### ✅ Phase 4D: Agent Creation Flow

* **Outcome**: Personalized agent identity.
* **Design Details**: Users name their agent and select an emoji. This creates a dedicated Agent record that powers the branded dashboard and ENS identity.

### ✅ Phase 4E: Telegram Webhook & Messaging

* **Outcome**: Two-way communication via Telegram.
* **Design Details**: Backend webhook handles incoming Telegram messages, routing them to the AI engine or using them for wallet-linking verification.

### ✅ Phase 5: Withdrawals & Position Management

* **Outcome**: Safe exit and liquidity access.
* **Design Details**: Logic to calculate "Max Safe Withdrawal" to ensure user actions don't trigger immediate liquidation. Supports partial USDC withdrawals or full position unwinding.

### ✅ Phase 6: Autonomous LTV Management

* **Outcome**: 24/7 risk mitigation without user intervention.
* **Design Details**: A background worker checks positions every 5 minutes.
* **Auto-Repay**: Triggered if LTV exceeds target (withdraws from vault to pay debt).
* **Auto-Borrow**: Triggered if LTV is significantly below target (borrows more to increase yield).

### ✅ Phase 7: Telegram Notifications

* **Outcome**: Real-time user awareness of agent activity.
* **Design Details**: Automated alerts for rebalancing events, critical liquidation warnings (80% of max LTV), and weekly yield summaries.

### ✅ Phase 8: ENS Integration

* **Outcome**: On-chain agent identity and configuration.
* **Design Details**: Agents receive `name.borrowbot.eth` subdomains. Target LTV and notification settings are stored in ENS text records for decentralized access.

### ✅ Phase 12: Auto-Navigate to Agent

* **Goal**: Direct returning users to their active dashboard instead of the setup wizard.

### ✅ Phase 13: Background Worker (Autonomous Monitoring & Action)

* **Goal**: A production-grade background process that monitors positions, autonomously fixes health issues, and communicates proactively.

### ✅ Phase 14: Agent Thoughts (Live Stream UI)

* **Goal**: Show the agent's reasoning process in real-time to make it feel alive and intelligent.

### ✅ Phase 15: USDC Withdrawals

* **Goal**: Allow users to withdraw earned USDC from the vault while maintaining position safety.

### 🔲 Phase 16: Auto-Optimizer (Yield Maximizer)

* **Goal**: Safely increase leverage when LTV is low to maximize capital efficiency ("Looping").

#### Implementation
- **Trigger**: In `LtvManager.check_position_ltv()`, when `currentLtv < targetLtv - 0.05` (existing auto_borrow), add profitability & volatility gates before executing.
- **Profitability gate**: Fetch yield APY and borrow APY, only optimize if `spread > 0` and projected annual gain > $100.
- **Volatility gate**: Use `PriceIntelligenceService` (Phase 16B) — suppress if 1h price change > 2% or 24h volatility (stddev) is elevated.
- **Always on**: No user toggle — optimization runs automatically for all positions when conditions are met.
- **Execution**: Reuses existing `build_auto_borrow_transactions()` — no new on-chain logic needed.
- **Notification**: `send_auto_optimize_success()` — includes borrow amount, new LTV, estimated extra yield/year, and price context.

---

### 🔲 Phase 16B: Historical Price Intelligence

* **Goal**: Give the agent historical price data to improve rebalancing and optimization decisions.

#### Implementation
- **Data source**: Alchemy Historical Prices API (already integrated in `AlchemyClient`) — no new API keys or subgraph needed.
- **New service**: `PriceIntelligenceService` in `blockchain_data/price_intelligence_service.py`.
  - `get_price_analysis(chainId, assetAddress)` → `PriceAnalysis` dataclass with: current price, 1h/24h/7d change %, 24h volatility (stddev of hourly samples), trend direction.
  - Uses Alchemy `tokens/historical` endpoint with hourly intervals for 24h and daily intervals for 7d.
  - In-memory cache (15 min TTL) to avoid repeated API calls.
- **New AI tool**: `GetPriceAnalysisTool` — agent can call `get_price_analysis(asset)` to get a structured price summary for chat responses.
- **Integration**: `LtvManager` receives `PriceIntelligenceService` and calls it during auto-optimize checks. Notifications include price context.

---

### 🔲 Phase 17: On-Chain Position Truth (Remove Stored Holdings)

* **Goal**: Always show live on-chain values for collateral, borrow, and vault balances — never rely on stale DB values.

#### Problem
`collateralAmount`, `borrowAmount`, and `vaultShares` are stored in `tbl_agent_positions` at creation/transaction time and only partially updated. When a user deposits collateral directly to the agent or external state changes occur (partial liquidation, interest accrual), the UI shows stale values.

#### Implementation
- **On-chain fetch**: Call Morpho Blue's `position(marketId, agentWallet)` contract function (already in `MORPHO_BLUE_ABI` but never called) to get live `collateral` and `borrowShares`. Call the vault's `balanceOf` + `convertToAssets` for live vault balance (already partially done via `_get_actual_vault_balance`).
- **Remove stored holdings**: Drop `collateralAmount`, `borrowAmount`, and `vaultShares` columns from `tbl_agent_positions`. Keep only: `agentId`, `collateralAsset`, `targetLtv`, `morphoMarketId`, `status`, timestamps.
- **New method**: Add `get_onchain_position(agentWallet, marketId)` to fetch collateral amount, borrow shares, and convert borrow shares to USDC amount using Morpho's `market()` function for the interest index.
- **Update `get_position()`**: Replace DB reads of collateral/borrow/vault with on-chain calls. Cache result briefly (e.g., 30s) to avoid redundant RPC calls.
- **Update `LtvManager`**: Use on-chain values for LTV calculation and rebalancing decisions instead of DB values.
- **Update transaction flows**: After deposit/borrow/repay/withdraw, no longer need to update holdings in DB — just invalidate cache.
- **Migration**: Alembic migration to drop the three columns.

---

### 🔲 Phase 18: ENS Basescan Labels

* **Goal**: Configure reverse resolution so agent wallets display their ENS name on block explorers.

### 🔲 Phase 19: Uniswap Integration

* **Goal**: Expand asset support by using Uniswap for automated swaps between collateral types and yield rewards.

### 🔲 Phase 20: Agent Wallet & Security (Stretch)

* **Goal**: Use ERC-4337 smart wallets to restrict agent permissions to only approved protocol adapters.
