## Overall

TODO

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

**Live demo:** User deposits WETH from Ethereum mainnet → LI.FI Composer bridges + converts to WETH on Base → agent wallet receives it → agent auto-deploys into Morpho position → user later withdraws USDC to Arbitrum → agent executes LI.FI bridge on Base via paymaster.

### Pitch (30 seconds)

BorrowBot uses LI.FI as its cross-chain access layer — making a Base-native lending agent accessible from every chain. Users deposit collateral from Ethereum, Arbitrum, Optimism, or any supported chain. LI.FI Composer routes the funds to Base and delivers them directly to the agent's wallet. The agent then autonomously deploys the collateral into a Morpho Blue position and starts earning yield. When the user wants to withdraw, the agent pulls USDC from the vault on Base and uses LI.FI Composer to bridge it to whichever chain the user wants — all executed autonomously on Base using the Coinbase Paymaster for gas. The agent never needs native gas tokens on any chain.

LI.FI isn't just a bridge — it's how an autonomous agent on Base serves users on every chain.

### How It Works

**Cross-Chain Strategy: Any Chain → Base (Agent) → Any Chain**

| Step | Chain | Action | LI.FI Role |
|------|-------|--------|------------|
| 1. Deposit collateral | Any → Base | User deposits from any chain | **LI.FI Composer** (bridge + convert) |
| 2. Auto-deploy | Base | Agent detects idle assets, deploys into Morpho + vault | — |
| 3. Monitor LTV | Base | Agent checks every 5 min, auto-rebalances | — |
| 4. Earn yield | Base | USDC earning in Yo vault | — |
| 5. Withdraw | Base → Any | User requests withdrawal to any chain | **LI.FI Composer** (bridge out) |
| 6. Deliver | Destination | USDC/tokens arrive in user's wallet | — |

**Cross-Chain Deposit Flow (User-Initiated)**

1. User opens LI.FI Widget in BorrowBot frontend
2. Selects source chain + source token (e.g., ETH on Ethereum, USDC on Arbitrum)
3. LI.FI Composer routes: source chain token → bridge → Base collateral asset → agent wallet
4. User signs one transaction on source chain (user pays gas there)
5. Agent's 5-minute worker loop detects idle assets in wallet → auto-deploys into Morpho position
6. Cross-chain deposit tracked in DB, visible in dashboard

**Cross-Chain Withdrawal Flow (Agent-Executed)**

1. User requests withdrawal via API: amount, destination chain, destination address
2. Agent checks LTV safety (same as existing withdraw flow)
3. Agent withdraws USDC from Yo vault on Base
4. Agent approves USDC to LI.FI router + executes LI.FI Composer bridge tx — **all on Base, gas paid by Coinbase Paymaster**
5. LI.FI bridges USDC to destination chain → delivers to user's wallet
6. Agent polls LI.FI `/status` API to track completion, notifies user via Telegram

**Cross-Chain Action States**

| State | Meaning |
|-------|---------|
| `pending` | Action created, awaiting execution or bridge initiation |
| `in_flight` | Bridge transaction submitted, waiting for cross-chain delivery |
| `completed` | Funds delivered to destination |
| `failed` | Bridge failed — agent notifies user, retries on next cycle |

### Why This Wins

**"Best AI x LI.FI Smart App" ($2,000)**
- Not a one-shot integration — LI.FI is used for **both deposit ingestion and withdrawal delivery**, making it central to the product
- The agent **autonomously executes** LI.FI Composer transactions on Base for withdrawals — a true AI × LI.FI workflow
- Agent tracks bridge status via `/status` API and sends Telegram notifications on completion/failure
- Combined with ENS constitution governance and autonomous LTV management — full agentic DeFi stack

**"Best Use of LI.FI Composer" ($2,500)**
- **Deposit direction**: LI.FI Widget + Composer routes any chain/token → Base collateral asset → agent wallet in a single user transaction
- **Withdrawal direction**: Agent uses LI.FI Composer to route Base USDC → any destination chain/token → user wallet, executed on Base via paymaster
- Demonstrates Composer in both user-initiated and agent-autonomous contexts
- Cross-chain action log shows route details: bridge used, source/dest chains, amounts, status

### Architecture

- **LiFiClient**: REST wrapper (`money_hack/external/lifi_client.py`) calling `https://li.quest/v1/quote` and `/status`
- **CrossChainManager**: Handles cross-chain withdrawals (agent-executed on Base) and deposit tracking with DB-backed action log
- **LI.FI Widget**: Frontend component (`LiFiDepositDialog.tsx`) for user-initiated cross-chain deposits
- **Worker integration**: 5-minute loop polls in-flight LI.FI actions and updates status
- **Paymaster**: All agent-executed bridge transactions on Base use Coinbase Paymaster — agent never needs ETH
