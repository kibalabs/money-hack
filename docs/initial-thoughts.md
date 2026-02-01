im doing this hackathon this week: https://ethglobal.com/events/hackmoney2026

these are the prize categories, i can only apply for 3:
- Uniswap: Build on Uniswap v4 to explore agent-driven financial systems. Projects may involve agents that programmatically interact with Uniswap v4 pools for liquidity management, trade execution, routing, coordination, or other behaviors enabled by onchain state. Submissions should emphasize reliability, transparency, and composability over speculative intelligence. The use of Hooks is optional and encouraged where it meaningfully supports the design.
- Li.Fi: Awarded to the project that most creatively uses LI.FI Composer to orchestrate multi-step DeFi workflows in a single, user-friendly experience. Examples Ideas: Cross-chain deposit into a vault, staged leverage/hedging strategies, or multi-step LP provisioning with a single sign | Deposit from any chain into a single restaking or yield strategy | Turn any asset on any EVM chain into a Perps margin position on a specific chain.
- ENS: ENS is often thought of as simple name <> address mapping, but really its much more flexible! Names can store arbitrary data via text records, decentralized websites via content hash and more.This prize goes to the most creative application of ENS in DeFi. This could be some sort of swap preferences stored in text records, DEX contracts that are named via ENS, decentralized interfaces or anything else.

I want to make a project where users give money to an agent and ask it to manage taking out an overcollateralized loan against on one asset against another. then they can swap the loaned money out to usdc and we will ear them ~7%-10% yield on that with the best vault on chain. I'm hoping to build this on base. I want to use my open sourced AgentWalletKit framework (https://agentwalletkit.tokenpage.xyz) to build the onchain components of the agent wallet.

Here's a conversation i had with a user of my existing product (agents for onchain yield generation on uscd) where we talked about how this new project might work:

Me: This is great, I'm actually doing a Hackathon next week where I was planning to try out a new type of agent.. I think this is a great candidate for something to try. Does this sound good to you: User selects an asset to loan out and deposits to agent (on either mainnet or base). user will select what asset they want to take out and Agent will find the best loan opportunity to take from it (not sure what the params are here but will learn as I do it I think). Then user deposits usdc on base as "collateral cover". If the user chose usdc on base as the loaned asset they might not need to do this step. Then agent monitors loan position and converts + bridges + deposits collateral to keep the loan covered.

knotnumb:  You plan on using USDC as the deposit token and then swap to the preferred collateral token? Will you only set it up to then borrow against the same collateral. ie deposit USDC, agent Finds a good rate using WETH as collateral to then Borrow WETH? Or will you do cross borrowing? ie deposit USDC, agent swaps to WETH as collateral to borrow USDC? The options really are endless. What i would find very useful is as follows.
1/ Agent looks for low borrow rates accross various platforms and returns with the best borrow rates.
2/ The borrow rates can be for various Collaterals from a list of say 3 or 4. Like WETH, WBTC, cbBTC, USDC etc
3/ Agent also shows the relative LTV for each of the collateral choices, which vary widely ie from 50% to 90%.
4/ the user chooses the collateral they want to deposit, then the borrow LTV they are happy with.
The agent does the borrow and the you could set up auto looping on same collateral/borrow when chosen. personally i don't really like doing this due to the slower unwinding process, especially when sometimes there is a lockup period on collateral deposits. but it could be a choice.
Then the agent monitors the LTV ratio for you. You can set parameters on what LTV you want the agent to sell some of the borrowed token to pay back the collateral when the collateral price falls. And conversely set the agent to borrow more if the LTV drops due to the Collateral token rising in price.
I'll leave it there for now. i need a beer. But i'll monitor any feedback/questions you have about my ideas.
Rereading all the messages looks like i have pretty much just repeated your original plan.
Just thinking, one of the important parameters that i use is AUM and liquidity. There are some very juicy rates, but normally in low AUM and liquidity vaults, which i'm not willing to risk. Maybe i'd put a 1-5 % allotment in something like that but iy would have to have some history first.


Can you please help me think through the spec of this project and what we might build here. we only have 1 week to implement this so we need to be focused on a minimal viable product that can demo the core idea.
