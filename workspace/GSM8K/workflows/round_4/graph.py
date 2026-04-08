from typing import Literal
import workspace.GSM8K.workflows.template.operator as operator
import workspace.GSM8K.workflows.round_4.prompt as prompt_custom
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
        Implementation of the workflow with self-consistency
        """
        # Generate multiple solution attempts
        solutions = []
        for i in range(3):
            solution = await self.custom(
                input=problem, 
                instruction=prompt_custom.MATH_REASONING_PROMPT
            )
            solutions.append(solution['response'])
        
        # Use self-consistency to select best answer
        final_solution = await self.sc_ensemble(
            solutions=solutions,
            problem=problem
        )
        
        return final_solution['response'], self.llm.get_usage_summary()["total_cost"]
