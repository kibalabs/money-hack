import asyncio

from core import logging
from core.exceptions import InternalServerErrorException
from core.exceptions import ServiceUnavailableException
from core.requester import KibaResponse
from core.requester import Requester
from core.util import json_util
from core.util.typing_util import JsonObject


class GeminiLLM:
    """LLM client for Google Gemini API."""

    def __init__(self, apiKey: str, requester: Requester, modelId: str = 'gemini-2.0-flash') -> None:
        self.apiKey = apiKey
        self.requester = requester
        self.endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{modelId}:generateContent'

    async def get_query(self, systemPrompt: str, prompt: str) -> JsonObject:
        """Build a query object for the Gemini API."""
        promptQuery: JsonObject = {
            'system_instruction': {'parts': [{'text': systemPrompt}]},
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'generationConfig': {
                'temperature': 0.7,
            },
        }
        return promptQuery

    async def get_next_step(self, promptQuery: JsonObject) -> JsonObject:
        """Send the query to Gemini and parse the JSON response."""
        maxRetries = 5
        retryDelaySeconds = 0.75
        headers = {'Content-Type': 'application/json'}
        response: KibaResponse | None = None
        for attemptNumber in range(1, maxRetries + 1):
            try:
                response = await self.requester.post(
                    url=f'{self.endpoint}?key={self.apiKey}',
                    headers=headers,
                    dataDict=promptQuery,
                    timeout=30,
                )
                break
            except ServiceUnavailableException as exception:
                if attemptNumber >= maxRetries:
                    logging.error(f'Gemini API unavailable after {attemptNumber} attempts, giving up: {exception.message}')
                    raise
                logging.warning(f'Gemini API unavailable (attempt {attemptNumber}/{maxRetries}), retrying in {retryDelaySeconds * attemptNumber}s: {exception.message}')
                await asyncio.sleep(retryDelaySeconds * attemptNumber)
        if not response:
            raise InternalServerErrorException('Gemini LLM failed after retries')
        responseJson = response.json()
        rawText = responseJson['candidates'][0]['content']['parts'][0]['text']
        jsonText = rawText.replace('```json', '', 1).replace('```', '', 1).strip()
        try:
            jsonDict = json_util.loads(jsonText)
        except Exception:
            logging.error(f'Error parsing JSON from Gemini response: {jsonText}')
            raise
        if not isinstance(jsonDict, dict):
            raise InternalServerErrorException(f'Gemini response is not a JSON object: {type(jsonDict)}')
        return jsonDict
