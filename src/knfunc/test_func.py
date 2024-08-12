import asyncio
import random
from mindwm.model.events import CloudEvent, IoDocumentEvent, IoDocument
from uuid import uuid4
import unittest

knfunc = __import__("func")

class TestFunc(unittest.IsolatedAsyncioTestCase):
  async def test_func(self):
    iodoc = IoDocument(
        id=str(uuid4()),
        input="uptime",
        output="17:23:21  up 3 days 22:18,  4 users,  load average: 0.44, 0.56, 0.52",
        ps1="> "
    )
    iodoc_event = IoDocumentEvent(data=iodoc)

    traceId = ''.join(random.choice('0123456789abcdef') for n in range(32))
    spanId = ''.join(random.choice('0123456789abcdef') for n in range(16))
    event = CloudEvent(
        id=str(uuid4()),
        data=iodoc_event,
        subject="uptime",
        source="mindwm.pion.mindwm-stg1.tmux.L3Zhci90bXV4L21pbmR3bQ==.c32d56f3-6257-3201-3eab-c1ae8ff3891b.0.2.iodocumen",
        traceparent=f"00-{traceId}-{spanId}-01",
    )
    body = await knfunc.func(event)
    return body
#    self.assertTrue(r)

if __name__ == "__main__":
  unittest.main()
