from typing import Literal
import workspace.GSM8K.workflows.template.operator as operator
import workspace.GSM8K.workflows.round_15.prompt as prompt_custom
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
        self.programmer = operator.Programmer(self.llm)

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
        # Approach 4: Independent computational verification via Programmer
        prog_verify = await self.programmer(problem=problem, analysis="")
        prog_solution = f"Programmer computed answer: {prog_verify['output']}. Explanation: This was derived through direct code execution based on the problem statement."
        solution_list.append(prog_solution)
        
        # Use self-consistency ensemble to select the best solution
        selected = await self.sc_ensemble(solutions=solution_list, problem=problem)
        selected_solution = selected['response']
        
        # Final review and correction of the selected solution
        review_input = f"Problem: {problem}\n\nSelected Solution: {selected_solution}"
        final = await self.custom(input=review_input, instruction=prompt_custom.REVIEW_FINAL)
        
        # Post-review validation: use programmer to verify calculations
        validation = await self.programmer(problem=problem, analysis=selected_solution)
        # Only update final answer if programmer provides a valid numeric output
        if validation['output'].strip() and validation['output'].strip() != 'None':
            # Extract numeric value from programmer output
            try:
                prog_answer = float(validation['output'])
                # Extract final answer from review response using regex to find boxed content
                import re
                match = re.search(r'\\boxed{([^}]+)}', final['response'])
                if match:
                    review_answer = match.group(1)
                    # Attempt to convert the extracted answer to float, handling potential fractions or mixed numbers
                    try:
                        # If the answer is a fraction like "3/7", evaluate it
                        if '/' in review_answer:
                            from fractions import Fraction
                            review_num = float(Fraction(review_answer))
                        else:
                            review_num = float(review_answer)
                        # Replace if answers differ significantly (>0.1% relative error)
                        if abs(prog_answer - review_num) / (abs(review_num) + 1e-9) > 0.001:
                            # Format the programmer answer appropriately (e.g., as integer if it's a whole number)
                            if prog_answer.is_integer():
                                prog_answer_formatted = int(prog_answer)
                            else:
                                prog_answer_formatted = prog_answer
                            final['response'] = final['response'].replace(
                                f'\\boxed{{{review_answer}}}', 
                                f'\\boxed{{{prog_answer_formatted}}}'
                            )
                    except (ValueError, TypeError):
                        # If conversion fails, keep the original reviewed answer
                        pass
            except (ValueError, TypeError):
                pass
        
        return final['response'], self.llm.get_usage_summary()["total_cost"]
