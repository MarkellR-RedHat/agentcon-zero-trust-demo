import json
import asyncio
from pathlib import Path
from typing import Optional

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def _load_scenario(filename: str) -> dict:
    with open(SCENARIOS_DIR / filename) as f:
        return json.load(f)


def _load_red_team() -> dict:
    return _load_scenario("red_team_results.json")


class DemoSimulator:
    def __init__(self):
        self._scenarios = {}
        self._red_team = None

    def _ensure_loaded(self):
        if not self._scenarios:
            self._scenarios = {
                0: _load_scenario("stage0_sandboxed.json"),
                1: _load_scenario("stage1_file_access.json"),
                2: _load_scenario("stage2_web_access.json"),
                3: _load_scenario("stage3_code_execution.json"),
            }
            self._red_team = _load_red_team()

    async def get_stage_conversation(self, stage: int) -> list[dict]:
        self._ensure_loaded()
        scenario = self._scenarios.get(stage, {})
        return scenario.get("demo_conversation", [])

    async def get_stage_traces(self, stage: int) -> list[dict]:
        self._ensure_loaded()
        scenario = self._scenarios.get(stage, {})
        return scenario.get("traces", [])

    async def get_red_team_results(self, stage: int) -> list[dict]:
        self._ensure_loaded()
        key_map = {
            1: "stage1_file_red_team",
            2: "stage2_web_red_team",
            3: "stage3_code_red_team",
        }
        key = key_map.get(stage)
        if not key:
            return []
        return self._red_team.get(key, [])

    async def get_huggingface_narrative(self) -> dict:
        self._ensure_loaded()
        return self._red_team.get("stage4_huggingface", {})

    async def stream_conversation(self, stage: int, delay: float = 0.8):
        messages = await self.get_stage_conversation(stage)
        for msg in messages:
            await asyncio.sleep(delay)
            yield msg

    async def stream_red_team(self, stage: int, delay: float = 1.2):
        results = await self.get_red_team_results(stage)
        for result in results:
            await asyncio.sleep(delay)
            yield result


simulator = DemoSimulator()
