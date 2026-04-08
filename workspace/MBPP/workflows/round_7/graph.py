from typing import Literal
import workspace.MBPP.workflows.template.operator as operator
import workspace.MBPP.workflows.round_7.prompt as prompt_custom
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

    async def __call__(self, problem: str, entry_point:str):
        # Generate initial solution
        solution = await self.custom_code_generate(problem=problem, entry_point=entry_point, instruction=prompt_custom.CODE_GENERATION_PROMPT)
        code = solution['response']
        solutions = [code]
        
        for attempt in range(2):
            test_result = await self.test(problem=problem, solution=code, entry_point=entry_point)
            if test_result['result']:
                return test_result['solution'], self.llm.get_usage_summary()["total_cost"]
            corrected = await self.custom(input=f"Problem: {problem}\nPrevious code: {code}\nTest errors: {test_result.get('errors', 'Unknown')}", instruction=prompt_custom.CORRECTION_PROMPT)
            code = corrected['response']
            solutions.append(code)
        
        attempts_str = "\n---\n".join(solutions)
        final_input = f"Problem: {problem}\nPrevious attempts:\n{attempts_str}"
        final_solution = await self.custom(input=final_input, instruction=prompt_custom.FINAL_CORRECTION_PROMPT)
        test_result = await self.test(problem=problem, solution=final_solution['response'], entry_point=entry_point)
        return test_result['solution'], self.llm.get_usage_summary()["total_cost"]
