import json
from pathlib import Path
from typing import Dict, Optional

import workspace.GSM8K.workflows.round_18.prompt as prompt_custom
import workspace.GSM8K.workflows.template.operator as operator
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
        self.sc_ensemble = operator.ScEnsemble(self.llm)
        self.programmer = operator.Programmer(self.llm)
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
        used_memory_keys,
    ) -> None:
        if not self.use_explicit_memory:
            return

        log_record = {
            "workflow_name": self.name,
            "task_id": task_id or "unknown",
            "memory_keys": memory.keys(),
            "memory_summary": self._summarize_memory(memory),
            "used_memory_keys": list(used_memory_keys),
        }
        logger.info(f"[WorkflowMemory] {json.dumps(log_record, ensure_ascii=False)}")

        if self.memory_log_path:
            log_path = Path(self.memory_log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(log_record, ensure_ascii=False) + "\n")

    async def __call__(self, problem: str, task_id: Optional[str] = None):
        """
        Implementation of the optimized workflow
        """
        solution_list = []
        memory = WorkflowMemoryStore() if self.use_explicit_memory else None

        sol1 = await self.custom(input=problem, instruction=prompt_custom.SOLVE_STANDARD)
        if memory is not None:
            memory.add(step_name="solve_standard", key="solution_list", value=sol1["response"], kind="solution")
        else:
            solution_list.append(sol1["response"])

        sol2 = await self.custom(input=problem, instruction=prompt_custom.SOLVE_ALTERNATIVE)
        if memory is not None:
            memory.add(step_name="solve_alternative", key="solution_list", value=sol2["response"], kind="solution")
        else:
            solution_list.append(sol2["response"])

        sol3 = await self.custom(input=problem, instruction=prompt_custom.SOLVE_ASSUMPTIONS)
        if memory is not None:
            memory.add(step_name="solve_assumptions", key="solution_list", value=sol3["response"], kind="solution")
        else:
            solution_list.append(sol3["response"])

        prog_verify = await self.programmer(problem=problem, analysis="")
        prog_solution = (
            f"Programmer computed answer: {prog_verify['output']}. "
            "Explanation: This was derived through direct code execution based on the problem statement."
        )
        if memory is not None:
            memory.add(step_name="programmer_verify", key="solution_list", value=prog_solution, kind="solution")
            memory.add(
                step_name="programmer_verify",
                key="independent_prog_output",
                value=prog_verify["output"],
                kind="programmer_output",
            )
            solution_list = memory.values("solution_list")
            solution_list_text = memory.render("solution_list")
            independent_prog_output = memory.get("independent_prog_output")
        else:
            solution_list.append(prog_solution)
            independent_prog_output = prog_verify["output"]

        if memory is not None:
            self._emit_memory_log(
                memory=memory,
                task_id=task_id,
                used_memory_keys=["solution_list", "independent_prog_output"],
            )
            selected = await self.sc_ensemble(
                solutions=solution_list,
                problem=problem,
                solutions_text=solution_list_text,
            )
        else:
            selected = await self.sc_ensemble(solutions=solution_list, problem=problem)
        selected_solution = selected["response"]

        review_input = (
            f"Problem: {problem}\n\n"
            f"Selected Solution: {selected_solution}\n\n"
            f"Independent Programmer Output: {independent_prog_output}"
        )
        final = await self.custom(input=review_input, instruction=prompt_custom.REVIEW_FINAL)

        validation = await self.programmer(problem=problem, analysis=selected_solution)
        if validation["output"].strip() and validation["output"].strip() != "None":
            try:
                prog_answer = float(validation["output"])
                import re

                match = re.search(r"\\boxed{([^}]+)}", final["response"])
                if match:
                    review_answer = match.group(1)
                    try:
                        review_num = float(review_answer)
                        if abs(prog_answer - review_num) / (abs(review_num) + 1e-9) > 0.001:
                            final["response"] = final["response"].replace(
                                f"\\boxed{{{review_answer}}}",
                                f"\\boxed{{{prog_answer}}}",
                            )
                    except ValueError:
                        pass
            except (ValueError, TypeError):
                pass

        return final["response"], self.llm.get_usage_summary()["total_cost"]
