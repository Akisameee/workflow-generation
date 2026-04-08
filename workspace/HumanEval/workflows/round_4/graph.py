from typing import Literal
import workspace.HumanEval.workflows.template.operator as operator
import workspace.HumanEval.workflows.round_4.prompt as prompt_custom
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
        Implementation of the workflow with self-correction loop and ensemble selection.
        """
        max_attempts = 3
        solutions = []
        for attempt in range(max_attempts):
            # Generate initial or refined solution
            if attempt == 0:
                solution = await self.custom_code_generate(problem=problem, entry_point=entry_point, instruction="")
            else:
                solution = await self.custom_code_generate(
                    problem=problem,
                    entry_point=entry_point,
                    instruction=f"Refine this code based on test errors: {refined_solution}"
                )
            # Test the solution
            test_result = await self.test(problem=problem, solution=solution['response'], entry_point=entry_point)
            solutions.append(test_result['solution'])
            if test_result['result']:
                return test_result['solution'], self.llm.get_usage_summary()["total_cost"]
            else:
                if attempt < max_attempts - 1:
                    refined_solution = test_result['solution']
        # If no solution passed, use ensemble to select the best one
        best_solution = await self.sc_ensemble(solutions=solutions, problem=problem)
        return best_solution['response'], self.llm.get_usage_summary()["total_cost"]
