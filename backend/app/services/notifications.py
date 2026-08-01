import json
from typing import Any

from app.core.redis import redis_client

RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def publish_notification(user_id: str, payload: dict[str, Any]) -> None:
    await redis_client.publish(f"notifications:{user_id}", json.dumps(payload, default=str))


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    redis_key = f"rate:{key}"
    count = await redis_client.eval(RATE_LIMIT_SCRIPT, 1, redis_key, window_seconds)
    return int(count) <= limit
