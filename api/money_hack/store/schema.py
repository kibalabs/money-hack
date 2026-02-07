import sqlalchemy
from sqlalchemy.dialects import postgresql as sqlalchemy_psql

from money_hack.model import Agent
from money_hack.model import AgentAction
from money_hack.model import AgentPosition
from money_hack.model import ChatEvent
from money_hack.model import User
from money_hack.model import UserWallet
from money_hack.store.entity_repository import EntityRepository

metadata = sqlalchemy.MetaData()

UsersTable = sqlalchemy.Table(
    'tbl_users',
    metadata,
    sqlalchemy.Column(key='userId', name='id', type_=sqlalchemy_psql.UUID, primary_key=True),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='username', name='username', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='telegramId', name='telegram_id', type_=sqlalchemy.Text, nullable=True),
    sqlalchemy.Column(key='telegramChatId', name='telegram_chat_id', type_=sqlalchemy.Text, nullable=True),
    sqlalchemy.Column(key='telegramUsername', name='telegram_username', type_=sqlalchemy.Text, nullable=True),
    sqlalchemy.UniqueConstraint('username', name='tbl_users_ux_username'),
)

UsersRepository = EntityRepository(table=UsersTable, modelClass=User)


UserWalletsTable = sqlalchemy.Table(
    'tbl_user_wallets',
    metadata,
    sqlalchemy.Column(key='userWalletId', name='id', type_=sqlalchemy_psql.UUID, primary_key=True),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='userId', name='user_id', type_=sqlalchemy_psql.UUID, nullable=False),
    sqlalchemy.Column(key='walletAddress', name='wallet_address', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.UniqueConstraint('walletAddress', name='tbl_user_wallets_ux_wallet_address'),
)

UserWalletsRepository = EntityRepository(table=UserWalletsTable, modelClass=UserWallet)


AgentsTable = sqlalchemy.Table(
    'tbl_agents',
    metadata,
    sqlalchemy.Column(key='agentId', name='id', type_=sqlalchemy_psql.UUID, primary_key=True),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='userId', name='user_id', type_=sqlalchemy_psql.UUID, nullable=False),
    sqlalchemy.Column(key='name', name='name', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='emoji', name='emoji', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='agentIndex', name='agent_index', type_=sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column(key='walletAddress', name='wallet_address', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='ensName', name='ens_name', type_=sqlalchemy.Text, nullable=True),
)

AgentsRepository = EntityRepository(table=AgentsTable, modelClass=Agent)


AgentPositionsTable = sqlalchemy.Table(
    'tbl_agent_positions',
    metadata,
    sqlalchemy.Column(key='agentPositionId', name='id', type_=sqlalchemy.Integer, autoincrement=True, primary_key=True, nullable=False),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='agentId', name='agent_id', type_=sqlalchemy_psql.UUID, nullable=False, index=True),
    sqlalchemy.Column(key='collateralAsset', name='collateral_asset', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='targetLtv', name='target_ltv', type_=sqlalchemy.Float, nullable=False),
    sqlalchemy.Column(key='morphoMarketId', name='morpho_market_id', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='status', name='status', type_=sqlalchemy.Text, nullable=False),
)

AgentPositionsRepository = EntityRepository(table=AgentPositionsTable, modelClass=AgentPosition)


AgentActionsTable = sqlalchemy.Table(
    'tbl_agent_actions',
    metadata,
    sqlalchemy.Column(key='agentActionId', name='id', type_=sqlalchemy.Integer, autoincrement=True, primary_key=True, nullable=False),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='agentId', name='agent_id', type_=sqlalchemy_psql.UUID, nullable=False, index=True),
    sqlalchemy.Column(key='actionType', name='action_type', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='value', name='value', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='valueId', name='value_id', type_=sqlalchemy.Text, nullable=True),
    sqlalchemy.Column(key='details', name='details', type_=sqlalchemy_psql.JSONB, nullable=False),
)

AgentActionsRepository = EntityRepository(table=AgentActionsTable, modelClass=AgentAction)


ChatEventsTable = sqlalchemy.Table(
    'tbl_chat_events',
    metadata,
    sqlalchemy.Column(key='chatEventId', name='id', type_=sqlalchemy.Integer, autoincrement=True, primary_key=True, nullable=False),
    sqlalchemy.Column(key='createdDate', name='created_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='updatedDate', name='updated_date', type_=sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(key='userId', name='user_id', type_=sqlalchemy_psql.UUID, nullable=False, index=True),
    sqlalchemy.Column(key='agentId', name='agent_id', type_=sqlalchemy_psql.UUID, nullable=False, index=True),
    sqlalchemy.Column(key='conversationId', name='conversation_id', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='eventType', name='event_type', type_=sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(key='content', name='content', type_=sqlalchemy_psql.JSONB, nullable=False),
)

ChatEventsRepository = EntityRepository(table=ChatEventsTable, modelClass=ChatEvent)
