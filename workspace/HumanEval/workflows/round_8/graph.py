from typing import Literal
import workspace.HumanEval.workflows.template.operator as operator
import workspace.HumanEval.workflows.round_8.prompt as prompt_custom
from scripts.async_llm import create_llm_instance


from scripts.evaluator import DatasetType

class Workflow:
    def __init__(
        self,
        name: str,
        llm_config,
        dataset: DatasetType,
    ) -> None:
        self.name = name
        self.dataset = dataset
        self.llm = create_llm_instance(llm_config)
        self.custom = operator.Custom(self.llm)
        self.custom_code_generate = operator.CustomCodeGenerate(self.llm)
        self.test = operator.Test(self.llm)
        self.sc_ensemble = operator.ScEnsemble(self.llm)

    async def __call__(self, problem: str, entry_point: str):
        """
        Implementation of the workflow with self-correction loop.
        """
        max_attempts = 3
        solutions = []
        for attempt in range(max_attempts):
            # Generate initial solution
            solution = await self.custom_code_generate(problem=problem, entry_point=entry_point, instruction="")
            # Test and refine the solution
            test_result = await self.test(problem=problem, solution=solution['response'], entry_point=entry_point)
            solutions.append(test_result['solution'])
            if test_result['result']:
                return test_result['solution'], self.llm.get_usage_summary()["total_cost"]
            else:
                # Use the refined solution for the next attempt if available
                if attempt < max_attempts - 1:
                    refined_solution = test_result['solution']
                    solution = await self.custom_code_generate(
                        problem=problem,
                        entry_point=entry_point,
                        instruction=f"Refine this code based on test errors: {refined_solution}"
                    )
        # After loop, no solution passed, use ScEnsemble to pick the best
        best = await self.sc_ensemble(solutions=solutions, problem=problem)
        return best['response'], self.llm.get_usage_summary()["total_cost"]
