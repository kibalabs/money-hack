from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from core import logging
from core.util import json_util

from money_hack.agent.chat_history_store import ChatHistoryStore
from money_hack.agent.chat_tool import ChatTool
from money_hack.agent.gemini_llm import GeminiLLM
from money_hack.agent.runtime_state import RuntimeState
from money_hack.model import ChatEvent


class ChatBot:
    """Agentic chat bot that uses tools to answer user questions."""

    def __init__(  # type: ignore[explicit-any]
        self,
        llm: GeminiLLM,
        historyStore: ChatHistoryStore,
        tools: list[ChatTool[Any, Any]],
    ) -> None:
        self.llm = llm
        self.historyStore = historyStore
        self.tools = tools

    async def execute(
        self,
        systemPrompt: str,
        userPromptTemplate: str,
        runtimeState: RuntimeState,
        userMessage: str,
    ) -> AsyncIterator[ChatEvent]:
        """Execute the chat loop, yielding events as they occur."""
        previousEvents = await self.historyStore.list_events(
            userId=runtimeState.userId,
            agentId=runtimeState.agentId,
            conversationId=runtimeState.conversationId,
            maxEvents=50,
            shouldIncludeSteps=False,
            shouldIncludePrompts=False,
            shouldIncludeTools=False,
        )
        toolDescriptions = '\n'.join([f'{tool.name}: {tool.description}\n  Parameters: {json_util.dumps(tool.paramsSchema.model_json_schema())}' for tool in self.tools])
        eventStrings = [f'{event.eventType}: {json_util.dumps(event.content) if isinstance(event.content, dict) else event.content}' for event in previousEvents]
        historyContext = '\n'.join([eventString.replace('\n', '  ') for eventString in eventStrings]).strip()
        yield await self.historyStore.add_event(
            userId=runtimeState.userId,
            agentId=runtimeState.agentId,
            conversationId=runtimeState.conversationId,
            eventType='user',
            content=userMessage,
        )
        isComplete = False
        currentContext = ''
        lastMessage = None
        maxIterations = 10
        iteration = 0
        while not isComplete and iteration < maxIterations:
            iteration += 1
            formattedPrompt = userPromptTemplate.format(
                historyContext=historyContext or '(no previous messages)',
                currentContext=currentContext.strip() or '(empty)',
                tools=toolDescriptions,
                userMessage=userMessage,
            )
            promptQuery = await self.llm.get_query(systemPrompt=systemPrompt, prompt=formattedPrompt)
            yield await self.historyStore.add_event(
                userId=runtimeState.userId,
                agentId=runtimeState.agentId,
                conversationId=runtimeState.conversationId,
                eventType='prompt',
                content=promptQuery,
            )
            step = await self.llm.get_next_step(promptQuery=promptQuery)
            yield await self.historyStore.add_event(
                userId=runtimeState.userId,
                agentId=runtimeState.agentId,
                conversationId=runtimeState.conversationId,
                eventType='step',
                content=step,
            )
            isComplete = bool(step.get('isComplete', False))
            if step.get('tool'):
                toolName = str(step['tool'])
                tool = next((t for t in self.tools if t.name == toolName), None)
                if tool is None:
                    resultMessage = f'Unknown tool: {toolName}'
                else:
                    try:
                        params = tool.paramsSchema(**step.get('args', {}))
                        result = await tool.execute(runtimeState=runtimeState, params=params)
                        resultMessage = f'{toolName} complete, result: {result}'
                    except Exception as e:  # noqa: BLE001
                        logging.error(f'Tool execution error: {e}')
                        resultMessage = f'{toolName} failed: {e!s}'
                yield await self.historyStore.add_event(
                    userId=runtimeState.userId,
                    agentId=runtimeState.agentId,
                    conversationId=runtimeState.conversationId,
                    eventType='tool',
                    content=resultMessage,
                )
                currentContext += f'\nTool: {resultMessage}'
                isComplete = False
            elif step.get('message'):
                currentMessage = str(step['message'])
                if currentMessage == lastMessage:
                    logging.error('LLM repeated the same message, ending to prevent infinite loop')
                    isComplete = True
                else:
                    yield await self.historyStore.add_event(
                        userId=runtimeState.userId,
                        agentId=runtimeState.agentId,
                        conversationId=runtimeState.conversationId,
                        eventType='agent',
                        content=currentMessage,
                    )
                    currentContext += f'\nAgent: {currentMessage}'
                    lastMessage = currentMessage
            else:
                logging.error('LLM step did not contain tool or message')
                isComplete = True
        if iteration >= maxIterations:
            logging.warning(f'Chat loop reached max iterations ({maxIterations})')
