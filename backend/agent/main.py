import asyncio
import logging
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

while str(BASE_DIR) in sys.path:
    sys.path.remove(str(BASE_DIR))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.config.env_loader import load_and_validate_env
from agent.core.assistant_core import install_agent_log_filters
from agent.manager.agent_manager import AgentManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    api_base_url, redis_url = load_and_validate_env()

    override_api = os.getenv("MEETING_API_URL_OVERRIDE")
    if override_api:
        api_base_url = override_api.rstrip("/")

    manager = AgentManager(api_base_url=api_base_url, redis_url=redis_url)

    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal (KeyboardInterrupt)")
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    install_agent_log_filters()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as exc:
        logger.critical("Fatal error in main: %s", exc, exc_info=exc)
        sys.exit(1)

