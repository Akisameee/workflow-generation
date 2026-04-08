import json
from pathlib import Path
from typing import Dict, Optional

import workspace.HumanEval.workflows.round_9.prompt as prompt_custom
import workspace.HumanEval.workflows.template.operator as operator
from scripts.async_llm import create_llm_instance
from scripts.evaluator import DatasetType
from scripts.logs import logger
from scripts.workflow_memory import WorkflowMemoryStore


class Workflow:
    def __init__(
        self,
        name: str,
        llm_config,
        dataset: DatasetType,
        use_explicit_memory: bool = False,
        memory_log_path: Optional[str] = None,
    ) -> None:
        self.name = name
        self.dataset = dataset
        self.llm = create_llm_instance(llm_config)
        self.custom = operator.Custom(self.llm)
        self.custom_code_generate = operator.CustomCodeGenerate(self.llm)
        self.test = operator.Test(self.llm)
        self.sc_ensemble = operator.ScEnsemble(self.llm)
        self.use_explicit_memory = use_explicit_memory
        self.memory_log_path = memory_log_path

    def _summarize_memory(self, memory: WorkflowMemoryStore) -> Dict[str, Dict[str, int]]:
        summary = {}
        for key in memory.keys():
            items = memory.get_all(key)
            summary[key] = {
                "count": len(items),
                "total_char_length": sum(len(str(item.value)) for item in items),
                "latest_char_length": len(str(items[-1].value)) if items else 0,
            }
        return summary

    def _emit_memory_log(
        self,
        memory: WorkflowMemoryStore,
        task_id: Optional[str],
        entry_point: str,
        used_memory_keys,
    ) -> None:
        if not self.use_explicit_memory:
            return

        memory_summary = self._summarize_memory(memory)
        log_record = {
            "workflow_name": self.name,
            "task_id": task_id or entry_point,
            "entry_point": entry_point,
            "memory_keys": memory.keys(),
            "memory_summary": memory_summary,
            "used_memory_keys": list(used_memory_keys),
        }

        logger.info(f"[WorkflowMemory] {json.dumps(log_record, ensure_ascii=False)}")

        if self.memory_log_path:
            log_path = Path(self.memory_log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(log_record, ensure_ascii=False) + "\n")

    async def __call__(self, problem: str, entry_point: str, task_id: Optional[str] = None):
        """
        Implementation of the workflow with self-correction loop.
        """
        max_attempts = 3
        stored_solutions = []
        memory = WorkflowMemoryStore() if self.use_explicit_memory else None

        for attempt in range(max_attempts):
            solution = await self.custom_code_generate(problem=problem, entry_point=entry_point, instruction="")
            test_result = await self.test(problem=problem, solution=solution["response"], entry_point=entry_point)

            if memory is not None:
                memory.add(
                    step_name="test_refine_loop",
                    key="stored_solutions",
                    value=test_result["solution"],
                    kind="solution",
                    metadata={"attempt": attempt, "entry_point": entry_point},
                )
            else:
                stored_solutions.append(test_result["solution"])

            if test_result["result"]:
                if memory is not None:
                    self._emit_memory_log(
                        memory=memory,
                        task_id=task_id,
                        entry_point=entry_point,
                        used_memory_keys=[],
                    )
                return test_result["solution"], self.llm.get_usage_summary()["total_cost"]

            if attempt < max_attempts - 1:
                refined_solution = test_result["solution"]
                solution = await self.custom_code_generate(
                    problem=problem,
                    entry_point=entry_point,
                    instruction=f"Refine this code based on test errors: {refined_solution}",
                )

        if memory is not None:
            stored_solutions = memory.values("stored_solutions")
            stored_solutions_text = memory.render("stored_solutions")
            self._emit_memory_log(
                memory=memory,
                task_id=task_id,
                entry_point=entry_point,
                used_memory_keys=["stored_solutions"],
            )
            sc_ensemble_result = await self.sc_ensemble(
                solutions=stored_solutions,
                problem=problem,
                solutions_text=stored_solutions_text,
            )
        else:
            sc_ensemble_result = await self.sc_ensemble(solutions=stored_solutions, problem=problem)

        return sc_ensemble_result["response"], self.llm.get_usage_summary()["total_cost"]
