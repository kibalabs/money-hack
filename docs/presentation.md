## Overall

### Description

BorrowBot is a fully autonomous DeFi agent that lives on Base. You deposit collateral (WETH or cbBTC) from any chain, and the agent takes over — it borrows USDC against your collateral via Morpho Blue, deposits the USDC into a yield vault (40acres), and then monitors your position 24/7, auto-rebalancing every 5 minutes to maximize yield while keeping you safe from liquidation. If prices drop and your LTV spikes, the agent pulls funds from the vault and repays your debt before you even notice. If markets are calm and your LTV is low, it borrows more to increase your yield. When you want your money back, the agent bridges it to whichever chain you want — Ethereum, Arbitrum, Optimism — all executed on Base with gas paid by the Coinbase Paymaster. You never pay gas.

What makes BorrowBot different from other DeFi dashboards is that it's genuinely autonomous. The agent has its own wallet (Coinbase CDP + EIP-7702 smart wallet), its own ENS identity (`name.borrowbott.eth`), and its own on-chain constitution — ENS text records that the owner sets as guardrails (max LTV, minimum yield spread, kill switch). The agent reads its constitution before every action cycle and governs itself accordingly. You can change your agent's behavior from any ENS interface and it obeys within 5 minutes. The agent writes its status back to ENS too — what it last did, when it last checked — creating a verifiable on-chain audit trail.

Cross-chain access is powered by LI.FI. Users deposit from any chain using the embedded LI.FI Widget (Composer routes the funds to Base automatically). For withdrawals, the agent itself fetches a LI.FI quote, approves USDC to the LI.FI Diamond, and executes the bridge transaction — all via ERC-4337 UserOperations with paymaster sponsorship. The agent communicates proactively through Telegram — sending alerts on rebalancing, liquidation warnings, and cross-chain bridge status. There's also a Gemini-powered chat interface where you can ask your agent about your position, and it responds with real data using a tool-calling agentic loop.

### How It's Made

The backend is Python with FastAPI, PostgreSQL, and an asyncio worker loop that runs every 5 minutes. The worker reads all active positions from the DB, fetches live on-chain data (Morpho collateral/borrow amounts, ERC-4626 vault balances, wallet token balances via Alchemy), reads the agent's ENS constitution from mainnet, and then decides what to do. The decision engine (`LtvManager`) compares current LTV to target, checks profitability gates (yield APY vs borrow APR, minimum annual gain threshold, price volatility suppression using 1h/24h historical data from Alchemy), and outputs an action: auto-repay, auto-optimize, or do nothing.

Agent wallets are EOAs created via Coinbase CDP, then upgraded to smart wallets using EIP-7702 delegation to the Coinbase Smart Wallet implementation. This lets us batch multiple contract calls into a single UserOperation. All transactions go through a Coinbase Bundler with `shouldSponsorGas=True` — the paymaster covers everything. The bundler validates every call target against a whitelist (Morpho, USDC, Yo Vault, LI.FI Diamond, ENS Resolver) to prevent the agent from being used for unintended operations.

ENS integration was one of the hackier parts. Each agent gets a subname under `borrowbott.eth` registered via NameWrapper on mainnet. We batch 8 `setText` calls into a single `resolver.multicall()` transaction to save gas. The agent reads constitution records (max-ltv, min-spread, pause) from mainnet every cycle, and writes status back (last-action, last-check). We hit a critical bug early on — Python's `hashlib.sha3_256` uses NIST SHA-3, not keccak256. ENS uses keccak for `namehash()`. Everything looked correct but resolved to garbage until we switched to `eth_utils.keccak`.

LI.FI is used in both directions. Deposits use the `@lifi/widget` React component embedded in the frontend, configured with `toChain=Base`, `toAddress=agentWallet`. The agent's worker loop auto-detects idle wallet assets and deploys them into the Morpho position. For withdrawals, the backend calls the LI.FI quote API (`/v1/quote` with `toAddress` set to the user's destination wallet), stores the quote's transaction request data, then executes two UserOperations: one to withdraw USDC from the vault, another to approve+bridge via the LI.FI Diamond (`0x1231DEB6...`). The worker polls `/v1/status` each cycle to track bridge completion and sends Telegram notifications.

The AI chat uses Gemini with a tool-calling loop. Tools are pluggable (`ChatTool` base class) — the bot can look up position data, get market rates, preview withdrawals, and check price analysis. It loops up to 10 iterations, executing tools and feeding results back to the LLM until it produces a final response. Same loop powers both the web chat widget and the Telegram bot.

The frontend is React/TypeScript with the @kibalabs/ui-react component library. The agent dashboard shows a live LTV gauge, yield spread, assets-vs-debt breakdown, an "agent terminal" that displays the agent's recent actions with a typing animation (makes it feel alive), a cross-chain activity panel, ENS constitution display, and a floating chat window. The setup flow is a multi-page wizard: choose collateral → name your agent → fund via LI.FI or direct deposit → deploy (5-tx batch: approve collateral → supply to Morpho → borrow USDC → approve USDC → deposit to vault).

## ENS: The Agent's On-Chain Constitution

**Live on mainnet:** [borrowman1.borrowbott.eth](https://app.ens.domains/borrowman1.borrowbott.eth)

### Pitch (30 seconds)

Every BorrowBot agent gets an ENS subname under `borrowbott.eth` — registered via the NameWrapper on Ethereum mainnet. The owner sets guardrails — max LTV, minimum yield spread, position caps, even a kill switch — as ENS text records. The agent reads its constitution before every action cycle and governs itself accordingly. You can change your agent's risk tolerance from *any* ENS-compatible interface, and the agent obeys within 5 minutes. It's a decentralized, permissionless control plane for autonomous DeFi agents.

ENS is not just a naming service — it's the governance layer for the agentic economy.

### How It Works

**Owner Sets the Rules (ENS Text Records on Mainnet)**

| Record | Example | What It Does |
|--------|---------|--------------|
| `com.borrowbot.max-ltv` | `"0.80"` | Agent never borrows above 80% LTV |
| `com.borrowbot.min-spread` | `"0.005"` | Agent won't optimize unless yield > borrow + 0.5% |
| `com.borrowbot.max-position-usd` | `"50000"` | Agent stops growing the position at $50K |
| `com.borrowbot.allowed-collateral` | `"cbBTC,WETH"` | Restricts which collateral types the agent can use |
| `com.borrowbot.pause` | `"true"` | Emergency kill switch — agent halts all actions |

**Agent Reads Constitution Every 5 Minutes**
1. Reads ENS text records from the Public Resolver on Ethereum mainnet
2. If `pause=true` → halts all autonomous actions
3. If LTV exceeds `max-ltv` → forces repay even if within normal thresholds
4. If yield spread < `min-spread` → suppresses optimization

**Agent Writes Status Back to ENS (On-Chain Audit Trail)**

| Record | Example | Purpose |
|--------|---------|---------|
| `com.borrowbot.status` | `"active"` | Current agent state |
| `com.borrowbot.last-action` | `"auto-repay: LTV 82% → 75%"` | What the agent just did |
| `com.borrowbot.last-check` | `"2026-02-07T14:30:00Z"` | Proof the agent is alive |

### Architecture

- **Parent name:** `borrowbott.eth` — wrapped in the ENS NameWrapper, managed by the deployer
- **Subnames:** Each agent gets `<name>.borrowbott.eth` via `NameWrapper.setSubnodeRecord` (human-readable labels, proper ENS UI resolution)
- **Text records:** All constitution + status records are set in a single `resolver.multicall()` transaction (8 setText calls batched into 1 tx for gas efficiency)
- **Authorization:** Deployer is the NameWrapper token owner of each subname, so it can call `setText` on the Public Resolver

### Why This Wins

- **Not an afterthought** — ENS text records are the actual mechanism the agent uses to make decisions
- **Novel pattern** — AI agents with ENS identities that publish their own operating parameters on-chain
- **Works from any ENS UI** — the owner doesn't need our app to change agent behavior
- **Verifiable constraints** — anyone can look up the agent's name and see its rules
- **On-chain audit trail** — agent status is permanently recorded in text records
- **Gas efficient** — all records batched into a single multicall transaction

## Uniswap

TODO

## Li.FI: Cross-Chain Access Layer

### Pitch (30 seconds)

BorrowBot is a Base-native lending agent — but users don't need to be on Base. LI.FI makes the agent accessible from every chain. A user on Ethereum deposits WETH via the embedded LI.FI Widget — Composer bridges it to Base and delivers it to the agent's wallet. The agent auto-detects the idle collateral, deploys it into Morpho Blue, borrows USDC, deposits to a yield vault — all autonomously. When the user wants their yield back on Arbitrum, they request a cross-chain withdrawal. The agent withdraws USDC from the vault, approves it to the LI.FI Diamond (`0x1231DEB6...`), and executes the bridge transaction — all on Base, all gas-sponsored by Coinbase Paymaster via ERC-4337. The agent never holds ETH on any chain.

LI.FI isn't just a bridge — it's how an autonomous agent on Base serves users on every chain.

### How It Works

**Deposit: Any Chain → Base Agent Wallet (User-Initiated)**

The frontend embeds the `@lifi/widget` React component (`LiFiDepositDialog.tsx`) configured with:
- `toChain`: Base (8453)
- `toToken`: collateral asset (WETH/cbBTC) or USDC on Base
- `toAddress`: the agent's CDP-managed wallet
- `integrator`: "BorrowBot"

The user picks any source chain and token. LI.FI Composer finds the optimal route (bridge + swap if needed) and the user signs one transaction on the source chain. Funds arrive in the agent wallet on Base. The agent's 5-minute worker loop (`check_positions_once`) detects idle wallet balances and auto-deploys them: supply collateral to Morpho → borrow USDC at target LTV → deposit USDC to Yo vault.

The frontend calls `POST /cross-chain-deposit` to record the action in `tbl_cross_chain_actions` for dashboard tracking.

**Withdraw: Base → Any Chain (Agent-Executed)**

The user calls `POST /cross-chain-withdraw` with amount, destination chain, destination token, and destination address. The agent (`execute_cross_chain_withdraw`) then:

1. **Checks safety** — vault balance sufficient, LTV won't breach hard max after withdrawal
2. **Gets LI.FI quote** — `CrossChainManager.prepare_cross_chain_withdrawal()` calls `https://li.quest/v1/quote` with `fromChain=8453`, `fromToken=USDC`, `toChain=<dest>`, `toToken=<dest token>`, `toAddress=<user wallet>`. Stores the quote's `transactionRequest` (to, data, value) and `approvalAddress` in the DB.
3. **Withdraws from vault** — sends a UserOperation via Coinbase Bundler to redeem shares from the Yo USDC Vault (`0x0000000f2eB9f69274678c76222B35eEc7588a65`)
4. **Bridges via LI.FI** — sends a second UserOperation with two calls batched:
   - `approve(approvalAddress, amount)` on USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
   - Call the LI.FI Diamond (`0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE`) with the quote's calldata
5. **Tracks status** — stores the txHash, sets status to `in_flight`. The worker polls `https://li.quest/v1/status` each cycle and updates to `completed` or `failed`. On failure, sends a Telegram alert.

Both UserOperations use `shouldSponsorGas=True` — the Coinbase Paymaster pays all gas. The LI.FI Diamond is whitelisted in the bundler's `WHITELISTED_ADDRESSES`.

**Cross-Chain Action Tracking**

All cross-chain activity is stored in `tbl_cross_chain_actions`:

| Field | Example |
|-------|---------|
| `action_type` | `deposit` or `withdraw` |
| `from_chain` / `to_chain` | `1` → `8453` (deposit) or `8453` → `42161` (withdraw) |
| `amount` | `50000000` (50 USDC, 6 decimals) |
| `tx_hash` | Bridge transaction hash |
| `bridge_name` | e.g. `across`, `stargate` (from LI.FI quote) |
| `status` | `pending` → `in_flight` → `completed` / `failed` |
| `details` | Quote data, approval address, estimated output |

The `CrossChainPanel` component on the dashboard shows recent actions with chain names, bridge, amount, status, and tx hash.

### Why This Wins

**"Best AI x LI.FI Smart App" ($2,000)**
- LI.FI is used in **both directions** — deposit ingestion and withdrawal delivery — making it central to the product, not an afterthought
- The agent **autonomously executes** LI.FI transactions on Base for withdrawals — it fetches quotes, approves tokens, calls the Diamond, and tracks bridge status without human intervention
- Integrated with the full agentic stack: ENS constitution governance, autonomous LTV monitoring, Telegram notifications
- Agent never needs gas on any chain — Coinbase Paymaster sponsors all execution on Base

**"Best Use of LI.FI Composer" ($2,500)**
- **Deposits**: LI.FI Widget embedded in frontend, configured with `toAddress=agentWallet` — Composer routes any chain/token to Base in a single user transaction
- **Withdrawals**: Agent calls LI.FI quote API to get optimal route, then executes the Composer transaction on Base via ERC-4337 UserOperation — no manual bridging
- Both directions demonstrated: user-initiated (widget) and agent-autonomous (backend)
- Cross-chain action log provides full transparency: bridge name, route, estimated output, live status

### Architecture

- **`LiFiClient`** (`lifi_client.py`): REST wrapper calling `/v1/quote` (with `toAddress` for recipient routing) and `/v1/status`
- **`CrossChainManager`** (`cross_chain_yield_manager.py`): `prepare_cross_chain_withdrawal()` gets LI.FI quotes and stores them; `record_cross_chain_deposit()` tracks inbound deposits; `check_pending_actions()` polls bridge status
- **`execute_cross_chain_withdraw()`** (`agent_manager.py`): Orchestrates vault withdrawal → USDC approve → LI.FI Diamond call, all via `_send_user_operation()` with paymaster
- **`LiFiDepositDialog`** (`LiFiDepositDialog.tsx`): Embeds `@lifi/widget` for user-initiated cross-chain deposits
- **`CrossChainPanel`** (`CrossChainPanel.tsx`): Dashboard component showing deposit/withdraw history with status
- **Worker loop** (`worker.py`): Every 5 minutes, polls `check_pending_actions()` to advance bridge status and notify on completion/failure
- **Bundler whitelist** (`coinbase_bundler.py`): LI.FI Diamond `0x1231DEB6...` whitelisted for agent UserOperations
