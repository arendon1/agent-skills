import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from scripts.unified_bridge import NotebookLMBridge


@pytest.fixture
def mock_notebooklm_client():
    with patch("scripts.unified_bridge.NotebookLMClient") as MockClient:
        client_instance = MagicMock()

        # Mock submodules
        client_instance.notebooks = AsyncMock()
        client_instance.sources = AsyncMock()
        client_instance.chat = AsyncMock()
        client_instance.research = AsyncMock()
        client_instance.artifacts = AsyncMock()
        client_instance._core = AsyncMock()

        # Async interactions
        MockClient.from_storage = AsyncMock(return_value=client_instance)

        yield client_instance


@pytest.mark.asyncio
async def test_bridge_context_manager(mock_notebooklm_client):
    async with NotebookLMBridge("dummy_storage") as bridge:
        assert bridge.client == mock_notebooklm_client
        mock_notebooklm_client._core.open.assert_awaited_once()

    mock_notebooklm_client._core.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_notebooks(mock_notebooklm_client):
    # Setup mock data definition
    notebook_mock = MagicMock()
    notebook_mock.id = "123"
    notebook_mock.title = "Test Notebook"
    mock_notebooklm_client.notebooks.list.return_value = [notebook_mock]

    async with NotebookLMBridge("dummy_storage") as bridge:
        notebooks = await bridge.list_notebooks()

    assert len(notebooks) == 1
    assert notebooks[0]["id"] == "123"
    assert notebooks[0]["title"] == "Test Notebook"
    assert notebooks[0]["url"] == "https://notebooklm.google.com/notebook/123"


@pytest.mark.asyncio
async def test_create_notebook(mock_notebooklm_client):
    notebook_mock = MagicMock()
    notebook_mock.id = "456"
    notebook_mock.title = "New Title"
    mock_notebooklm_client.notebooks.create.return_value = notebook_mock

    async with NotebookLMBridge("dummy_storage") as bridge:
        notebook = await bridge.create_notebook("New Title")

    assert notebook["id"] == "456"
    assert notebook["title"] == "New Title"
    mock_notebooklm_client.notebooks.create.assert_awaited_once_with(title="New Title")


@pytest.mark.asyncio
async def test_add_source_url(mock_notebooklm_client):
    mock_notebooklm_client.sources.add_url.return_value = {"status": "success"}

    async with NotebookLMBridge("dummy_storage") as bridge:
        result = await bridge.add_source("123", url="http://example.com")

    assert result == {"status": "success"}
    mock_notebooklm_client.sources.add_url.assert_awaited_once_with(
        "123", "http://example.com"
    )


@pytest.mark.asyncio
async def test_ask_question(mock_notebooklm_client):
    response_mock = MagicMock()
    response_mock.answer = "This is the answer"
    mock_notebooklm_client.chat.ask.return_value = response_mock

    async with NotebookLMBridge("dummy_storage") as bridge:
        answer = await bridge.ask("123", "What is what?")

    assert answer == "This is the answer"
    mock_notebooklm_client.chat.ask.assert_awaited_once_with("123", "What is what?")


@pytest.mark.asyncio
async def test_generate_artifact_audio(mock_notebooklm_client):
    status_mock = MagicMock()
    status_mock.task_id = "task_1"
    mock_notebooklm_client.artifacts.generate_audio.return_value = status_mock

    async with NotebookLMBridge("dummy_storage") as bridge:
        result = await bridge.generate_artifact("123", "audio")

    assert result == "Audio generation complete"
    mock_notebooklm_client.artifacts.generate_audio.assert_awaited_once_with("123")
    mock_notebooklm_client.artifacts.wait_for_completion.assert_awaited_once_with(
        "123", "task_1"
    )


@pytest.mark.asyncio
async def test_generate_artifact_quiz(mock_notebooklm_client):
    status_mock = MagicMock()
    status_mock.task_id = "task_2"
    mock_notebooklm_client.artifacts.generate_quiz.return_value = status_mock

    async with NotebookLMBridge("dummy_storage") as bridge:
        result = await bridge.generate_artifact("123", "quiz")

    assert result == "Quiz generation complete"
    mock_notebooklm_client.artifacts.generate_quiz.assert_awaited_once_with("123")
    mock_notebooklm_client.artifacts.wait_for_completion.assert_awaited_once_with(
        "123", "task_2"
    )


@pytest.mark.asyncio
async def test_generate_artifact_mind_map(mock_notebooklm_client):
    mock_notebooklm_client.artifacts.generate_mind_map.return_value = "Mindmap content"

    async with NotebookLMBridge("dummy_storage") as bridge:
        result = await bridge.generate_artifact("123", "mind-map")

    assert result == "Mindmap content"
    mock_notebooklm_client.artifacts.generate_mind_map.assert_awaited_once_with("123")
