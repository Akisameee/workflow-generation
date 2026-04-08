from typing import Literal
import workspace.MBPP.workflows.template.operator as operator
import workspace.MBPP.workflows.round_4.prompt as prompt_custom
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
        self.sc_ensemble = operator.ScEnsemble(self.llm)  # Added ScEnsemble operator

    async def __call__(self, problem: str, entry_point:str):
        # Generate initial solution
        solution = await self.custom_code_generate(problem=problem, entry_point=entry_point, instruction=prompt_custom.CODE_GENERATION_PROMPT)
        code = solution['response']
        solutions = [code]  # Store initial solution
        
        # Test and retry up to 2 times if it fails
        for attempt in range(2):
            test_result = await self.test(problem=problem, solution=code, entry_point=entry_point)
            if test_result['result']:
                return test_result['solution'], self.llm.get_usage_summary()["total_cost"]
            # Use custom operator to analyze errors and generate corrected code
            corrected = await self.custom(input=f"Problem: {problem}\nPrevious code: {code}\nTest errors: {test_result.get('errors', 'Unknown')}", instruction=prompt_custom.CORRECTION_PROMPT)
            code = corrected['response']
            solutions.append(code)  # Store corrected solution
        
        # Use ScEnsemble to select the best solution from all generated codes
        selected = await self.sc_ensemble(solutions=solutions, problem=problem)
        test_result = await self.test(problem=problem, solution=selected['response'], entry_point=entry_point)
        return test_result['solution'], self.llm.get_usage_summary()["total_cost"]
