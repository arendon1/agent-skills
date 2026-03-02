import asyncio
import json
from pathlib import Path
from notebooklm import NotebookLMClient
from notebooklm.rpc import RPCMethod


async def dump_notebook(notebook_id):
    STATE_FILE = Path(
        "C:/Users/andres.rendon/Documents/Prompts/skills/notebooklm-skill/data/browser_state/state.json"
    )
    client = await NotebookLMClient.from_storage(str(STATE_FILE))
    async with client:
        # GET_NOTEBOOK call
        params = [notebook_id, None, [2], None, 0]
        result = await client._core.rpc_call(
            RPCMethod.GET_NOTEBOOK,  # Fixed to use enum
            params,
            source_path=f"/notebook/{notebook_id}",
        )
        print(f"DEBUG: Notebook data for {notebook_id}:")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import sys

    nid = sys.argv[1] if len(sys.argv) > 1 else "190835f6-9bed-43a0-ad1c-358deffee9a7"
    asyncio.run(dump_notebook(nid))
