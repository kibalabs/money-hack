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

### ✅ Phase 16: Auto-Optimizer (Yield Maximizer)

* **Outcome**: Agent safely increases leverage when LTV is low to maximize capital efficiency. Profitability gates ensure optimization only runs when yield spread is positive. Auto-deploys idle wallet assets (collateral and USDC) into the position.

### ✅ Phase 17: On-Chain Position Truth (Remove Stored Holdings)

* **Outcome**: All position values (collateral, borrow, vault, wallet balances) are fetched live from on-chain. Dropped `collateralAmount`, `borrowAmount`, and `vaultShares` columns from the DB. Dashboard redesigned to show net position value, idle wallet assets, assets vs debt breakdown, and close-position cost.

---

### ✅ Phase 18: ENS as the Agent's On-Chain Constitution

* **Outcome**: ENS text records on Base L2 (Basenames) serve as a decentralized governance layer. Owners set guardrails (`com.borrowbot.max-ltv`, `com.borrowbot.min-spread`, `com.borrowbot.pause`, etc.) via ENS, and the agent reads its constitution before every action cycle. The agent writes status back (`com.borrowbot.status`, `com.borrowbot.last-action`, `com.borrowbot.last-check`). Fixed critical `namehash()` bug (was NIST SHA-3, now keccak256). Frontend constitution panel on AgentPage. Targets ETHGlobal "Most Creative Use of ENS for DeFi" prize.

### 🔲 Phase 19: Uniswap Integration

* **Goal**: Expand asset support by using Uniswap for automated swaps between collateral types and yield rewards.

### 🔲 Phase 20: Agent Wallet & Security (Stretch)

* **Goal**: Use ERC-4337 smart wallets to restrict agent permissions to only approved protocol adapters.
