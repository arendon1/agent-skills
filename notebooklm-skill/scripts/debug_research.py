import asyncio
import json
import httpx
from pathlib import Path
from notebooklm import NotebookLMClient
from notebooklm.rpc.decoder import (
    strip_anti_xssi,
    parse_chunked_response,
    collect_rpc_ids,
)


async def debug_poll(notebook_id):
    # Match the bridge logic
    STATE_FILE = Path(
        "C:/Users/andres.rendon/Documents/Prompts/skills/notebooklm-skill/data/browser_state/state.json"
    )
    print(f"DEBUG: Using state file: {STATE_FILE}")

    client = await NotebookLMClient.from_storage(str(STATE_FILE))
    async with client:
        print(f"DEBUG: Using notebook: {notebook_id}")

        # Manually perform rpc call to see raw results
        rpc_id = "e3bVqc"
        params = [None, None, notebook_id]

        # Construct the body
        payload = {"f.req": json.dumps([[[rpc_id, json.dumps(params), None, "1"]]])}

        # Use httpx with the client's session
        async with httpx.AsyncClient(
            cookies=client._core._session.cookies, follow_redirects=True
        ) as session:
            response = await session.post(
                "https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute",
                params={"rpcids": rpc_id},
                data=payload,
            )
            print(f"DEBUG: Status: {response.status_code}")
            text = response.text
            cleaned = strip_anti_xssi(text)
            chunks = parse_chunked_response(cleaned)
            found_ids = collect_rpc_ids(chunks)
            print(f"DEBUG: Found RPC IDs: {found_ids}")

            for i, chunk in enumerate(chunks):
                print(f"DEBUG: Chunk {i}: {str(chunk)[:200]}...")

            if rpc_id not in found_ids:
                print(f"❌ RPC ID {rpc_id} NOT FOUND in response.")
            else:
                print(f"✅ RPC ID {rpc_id} FOUND!")


if __name__ == "__main__":
    import sys

    nid = sys.argv[1] if len(sys.argv) > 1 else "190835f6-9bed-43a0-ad1c-358deffee9a7"
    asyncio.run(debug_poll(nid))
