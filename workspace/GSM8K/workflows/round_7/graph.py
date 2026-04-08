from typing import Literal
import workspace.GSM8K.workflows.template.operator as operator
import workspace.GSM8K.workflows.round_7.prompt as prompt_custom
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
        self.sc_ensemble = operator.ScEnsemble(self.llm)

    async def __call__(self, problem: str):
        """
        Implementation of the workflow
        """
        # Generate multiple initial solutions for self-consistency
        initial_solutions = []
        for _ in range(3):
            solution = await self.custom(input=problem, instruction=prompt_custom.SOLVE_PROMPT)
            initial_solutions.append(solution['response'])
        
        # Use self-consistency to select the best solution
        selected_solution = await self.sc_ensemble.sc_ensemble(solutions=initial_solutions, problem=problem)
        initial_solution = selected_solution['response']
        
        # Review and correct the selected solution
        review_input = f"Problem: {problem}\n\nSelected Solution: {initial_solution}"
        corrected = await self.custom(input=review_input, instruction=prompt_custom.REVIEW_PROMPT)
        
        return corrected['response'], self.llm.get_usage_summary()["total_cost"]
