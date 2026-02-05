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

#### Autonomous Actions
1. **Self-Healing**: If LTV > Target/Critical, check available funds in Yield Vault.
    - **If sufficient**: Automatically withdraw from vault and repay debt to restore target LTV. Log action.
    - **If insufficient**: Mark as "User Action Required" and send urgent alert.

#### Communication Triggers
- **Action Taken** (Telegram): "I detected High LTV and automatically withdrew $X from yield vault to repay debt. Position is now healthy at Y% LTV."
- **Urgent** (Telegram): "Critical Risk: LTV is high and yield balance is insufficient to fix it. Please deposit more collateral immediately."
- **Daily Digest** (Telegram): "Everything is healthy. Earned $X today. Current LTV Y%. No action needed."

#### Implementation
- Cron job every 5 minutes checks all active positions
- Logic flow: Check Health -> Try Self-Heal -> Alert if failed
- Daily Summary: Run once per day per user (store last_daily_digest timestamp in `tbl_agent_actions` or similar)
- Rate limit alerts: Avoid spamming if user hasn't acted yet (e.g., remind every 4 hours for critical)

### 🔲 Phase 14: Agent Thoughts (Live Stream UI)

* **Goal**: Show the agent's reasoning process in real-time to make it feel alive and intelligent.

#### UI Design
- New `/agent/thoughts` page or expandable panel on AgentPage
- Live feed of agent observations and decisions
- Entries: timestamp, thought type (observation/decision/action), content
- Auto-scroll, typewriter effect for new entries

#### Thought Categories
1. **Observations**: "Checking your position... LTV is 72.3%, healthy ✓"
2. **Analysis**: "ETH dropped 3% in the last hour. Monitoring closely."
3. **Decisions**: "LTV within target range, no action needed."
4. **Actions**: "Executing auto-repay: withdrawing $50 from vault to reduce debt."

#### Implementation
- Backend: Log thoughts to `tbl_agent_thoughts` during background worker runs
- Thoughts are pre-templated strings with variable interpolation (minimal LLM cost)
- Only use LLM for user-facing messages, not internal thoughts
- Frontend: Poll `/thoughts` endpoint or use SSE for live updates
- Show last 24 hours of thoughts, paginated

### 🔲 Phase 15: USDC Withdrawals

* **Goal**: Allow users to withdraw earned USDC from the vault while maintaining position safety.

#### Safety Logic
- Calculate max safe withdrawal: `vault_balance - buffer_for_repay`
- If withdrawal would push LTV above 85%: block with explanation
- If withdrawal pushes LTV above target: warn user, require confirmation
- If withdrawal pushes LTV above 80%: urgent warning, require explicit "I understand" confirmation

#### Post-Withdrawal Behavior
- Background worker increases monitoring frequency for risky positions
- Immediate LTV recalculation after withdrawal
- If LTV critical: send urgent Telegram message
- Auto-repay may trigger if LTV exceeds safe threshold

#### Implementation
- `POST /v1/users/{addr}/withdraw` with amount
- Return transaction calldata for vault withdrawal
- Frontend: withdrawal dialog with LTV impact preview
- Show estimated new LTV, health factor after withdrawal

### 🔲 Phase 16: Auto-Optimizer (Yield Maximizer)

* **Goal**: Safely increase leverage when LTV is low to maximize capital efficiency ("Looping").

#### Logic
1. **Trigger**: `Current LTV` < `Target LTV - Buffer` (e.g., Target 70%, Current 60%).
2. **Action**:
   - Calculate amount to borrow to return to Target LTV.
   - Borrow USDC against existing collateral.
   - Deposit borrowed USDC into Yield Vault immediately.
3. **Constraint**: Only execute if `Expected Yield > Borrow Cost + Gas Fees`.

#### Safety
- **Volatility Check**: Do not optimize if price has moved > 2% in last hour.
- **Minimum Size**: Do not optimize for trivial amounts (< $100 gain).
- **User Control**: Feature must be explicitly enabled by user (`enable_auto_optimize` = True). Default is OFF.

#### Communication
- **Notification**: "Market moved in your favor. I borrowed $X more and deposited it to earn yield. Expected extra profit: $Y/year."

---

### 🔲 Phase 17: ENS Basescan Labels

* **Goal**: Configure reverse resolution so agent wallets display their ENS name on block explorers.

### 🔲 Phase 18: Uniswap Integration

* **Goal**: Expand asset support by using Uniswap for automated swaps between collateral types and yield rewards.

### 🔲 Phase 19: Agent Wallet & Security (Stretch)

* **Goal**: Use ERC-4337 smart wallets to restrict agent permissions to only approved protocol adapters.

---

## 🤖 AI Interaction Design

* **Engine**: Google Gemini via a non-streaming and streaming API.
* **Capabilities**: The agent can read position data, fetch market rates, view its own action history, and execute one write action: **updating the target LTV**.
* **Context**: The agent is programmed to never guess values and always use its tool-calling suite for real-time data.

**Would you like me to expand on the "Next Steps" (Phases 12-14) with specific technical requirements?**
