# Yield Seeker Development Guide

## Project Overview
Yield Seeker is an AI-powered DeFi yield optimization platform where users create AI agents with EVM smart wallets. Agents autonomously move USDC between onchain vaults to maximize yield (~10% APY target), claim rewards, and reinvest automatically.

## Code Conventions
- Python: `snake_case` functions, `camelCase` variables
- TypeScript: `camelCase` functions and variables
- Error Handling: Avoid blanket try/catch - handle specific error scenarios
- Naming: Descriptive function/variable names over comments
- Database: Use repository pattern, avoid raw SQL in business logic
- Database tables: UUID primary keys for user-related entities, integer auto-increment for others
- Do not broadly catch exceptions unless there is a very specific reason to do so.
- Use named parameters wherever possible.
- Do not put newlines within functions.
- Do not put comments that are easily inferred from the code itself.
- Use explanative variable and function names instead of comments.

## Agent conventions
- Database schema migrations: use ./create-migration.sh "message" to create schema migrations, do not creat them manually. Do not run migrations in agentic workflows.
- Do not create test scripts, just write python code to execute in a console when necesarry.
- Use the makefile to run commands, e.g. `make test` to run tests, `make lint-fix` to run linters, etc.
- Do not try to compile each file manually, use the `make lint-fix` to check for syntax errors.
- Do not use placeholder values unless explcitly instructed to do so. Ask for clarification if unsure.
- Only run syntactic checks once the implementation is complete and verified with the user.
- We use envrc to manage environments in different directories. envrc only loads the environment when the directory is entered. You must cd into a directory in one command before running further commands.
- When running scripts don't pipe the output anywhere - nothing we are doing is that big.

## Key Files to Reference
- `api/agent_hack/api/v1_api.py`: All Pydantic data models
- `api/agent_hack/agent_manager.py`: Entry point for all backend business logic
- `api/agent_hack/store/schema.py`: Database table definitions
- `app/src/pages/AgentPerformancePage.tsx`: Main dashboard logic
