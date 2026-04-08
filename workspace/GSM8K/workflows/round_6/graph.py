from typing import Literal
import workspace.GSM8K.workflows.template.operator as operator
import workspace.GSM8K.workflows.round_6.prompt as prompt_custom
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

    async def __call__(self, problem: str):
        """
        Implementation of the workflow
        """
        # Generate initial solution
        solution = await self.custom(input=problem, instruction=prompt_custom.SOLVE_PROMPT)
        initial_solution = solution['response']
        
        # Use Programmer to verify and compute the solution via code execution
        programmer_operator = operator.Programmer()
        programmer_result = await programmer_operator(problem=problem, analysis=initial_solution)
        corrected = programmer_result['output']
        
        return corrected, self.llm.get_usage_summary()["total_cost"]
