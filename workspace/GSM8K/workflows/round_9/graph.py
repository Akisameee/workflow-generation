from typing import Literal
import workspace.GSM8K.workflows.template.operator as operator
import workspace.GSM8K.workflows.round_9.prompt as prompt_custom
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
        Implementation of the optimized workflow
        """
        # Generate multiple initial solutions with different approaches
        solution_list = []
        # Approach 1: Standard step-by-step solution
        sol1 = await self.custom(input=problem, instruction=prompt_custom.SOLVE_STANDARD)
        solution_list.append(sol1['response'])
        # Approach 2: Alternative perspective solution
        sol2 = await self.custom(input=problem, instruction=prompt_custom.SOLVE_ALTERNATIVE)
        solution_list.append(sol2['response'])
        # Approach 3: Critical assumption check solution
        sol3 = await self.custom(input=problem, instruction=prompt_custom.SOLVE_ASSUMPTIONS)
        solution_list.append(sol3['response'])
        
        # Use self-consistency ensemble to select the best solution
        selected = await self.sc_ensemble(solutions=solution_list, problem=problem)
        selected_solution = selected['response']
        
        # Final review and correction of the selected solution
        review_input = f"Problem: {problem}\n\nSelected Solution: {selected_solution}"
        final = await self.custom(input=review_input, instruction=prompt_custom.REVIEW_FINAL)
        
        return final['response'], self.llm.get_usage_summary()["total_cost"]
