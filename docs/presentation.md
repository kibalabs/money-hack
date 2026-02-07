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

## Li.FI

TODO
