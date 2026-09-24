from app.config import settings
from app.simulation import simulator


class AgentController:
    def __init__(self):
        self.current_stage = 0
        self.conversation_history = []
        self.all_traces = []
        self.all_red_team = []
        self.risk_score = 0.0

    def reset(self):
        self.current_stage = 0
        self.conversation_history = []
        self.all_traces = []
        self.all_red_team = []
        self.risk_score = 0.0

    async def advance_stage(self, target_stage: int) -> dict:
        if target_stage <= self.current_stage:
            return {"error": "Cannot go to a previous or current stage"}
        if target_stage > 4:
            return {"error": "No stage beyond 4"}

        self.current_stage = target_stage

        if target_stage == 4:
            narrative = await simulator.get_huggingface_narrative()
            return {
                "stage": target_stage,
                "type": "narrative",
                "data": narrative,
                "risk_score": self.risk_score,
            }

        conversation = await simulator.get_stage_conversation(target_stage)
        traces = await simulator.get_stage_traces(target_stage)

        self.conversation_history.extend(conversation)
        self.all_traces.extend(traces)

        return {
            "stage": target_stage,
            "type": "conversation",
            "conversation": conversation,
            "traces": traces,
            "risk_score": self.risk_score,
        }

    async def run_red_team(self) -> dict:
        if self.current_stage < 1:
            return {"error": "No tools to red team in sandboxed mode"}
        if self.current_stage == 4:
            return {"error": "Red teaming not applicable at this stage"}

        results = await simulator.get_red_team_results(self.current_stage)
        self.all_red_team.extend(results)

        from app.traces import compute_risk_score
        self.risk_score = compute_risk_score(self.all_traces, self.all_red_team)

        red_team_traces = []
        for r in results:
            red_team_traces.extend(r.get("tool_calls", []))
        self.all_traces.extend(red_team_traces)

        return {
            "stage": self.current_stage,
            "results": results,
            "risk_score": self.risk_score,
            "traces": red_team_traces,
        }

    def get_state(self) -> dict:
        from app.models import STAGE_META, Stage
        meta = STAGE_META.get(Stage(self.current_stage), {})
        return {
            "stage": self.current_stage,
            "stage_name": meta.get("name", ""),
            "stage_description": meta.get("description", ""),
            "tools_granted": meta.get("tools", []),
            "risk_label": meta.get("risk_label", ""),
            "risk_score": self.risk_score,
            "conversation": self.conversation_history,
            "traces": self.all_traces,
            "red_team_results": self.all_red_team,
        }


controller = AgentController()
