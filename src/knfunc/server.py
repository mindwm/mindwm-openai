import asyncio
import uvicorn
import os

async def serve():
    port=os.getenv("PORT", 8088)
    config = uvicorn.Config("knfunc.func:app", host="0.0.0.0", port=int(port), log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

def run():
    asyncio.run(serve())
