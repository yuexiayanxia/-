import pytest
from codereflex.llm.client import LLMClient, MockLLMClient, LLMResponse


def test_llm_response_dataclass():
    r = LLMResponse(text="hello", usage={"total_tokens": 5})
    assert r.text == "hello"


@pytest.mark.asyncio
async def test_mock_client_returns_scripted():
    mock = MockLLMClient(script=['{"type":"write_file","params":{}}', '{"type":"run_validators","params":{}}'])
    r1 = await mock.complete([], "m")
    r2 = await mock.complete([], "m")
    assert r1.text == '{"type":"write_file","params":{}}'
    assert r2.text == '{"type":"run_validators","params":{}}'


@pytest.mark.asyncio
async def test_mock_client_exhausts_script():
    mock = MockLLMClient(script=["one"])
    await mock.complete([], "m")
    with pytest.raises(RuntimeError):
        await mock.complete([], "m")
