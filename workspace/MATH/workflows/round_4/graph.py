from typing import Literal
import workspace.MATH.workflows.template.operator as operator
import workspace.MATH.workflows.round_4.prompt as prompt_custom
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
        self.custom_solve = operator.Custom(self.llm)
        self.custom_review = operator.Custom(self.llm)

    async def __call__(self, problem: str):
        """
        Implementation of the workflow with solution review
        """
        # Step 1: Generate initial solution
        solution = await self.custom_solve(
            input=problem,
            instruction=prompt_custom.INITIAL_SOLVE_PROMPT
        )
        
        # Step 2: Review and correct if needed
        review = await self.custom_review(
            input=f"Problem: {problem}\n\nInitial Solution: {solution['response']}",
            instruction=prompt_custom.REVIEW_PROMPT
        )
        
        return review['response'], self.llm.get_usage_summary()["total_cost"]
