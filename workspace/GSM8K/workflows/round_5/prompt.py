SOLVE_PROMPT = """
Solve the following math problem step by step. Ensure your final answer is placed within a box: \boxed{<final_answer>}.
"""

REVIEW_PROMPT = """
Carefully review the solution provided for the math problem. Check all reasoning steps and calculations for errors. If you find an error, correct it and provide the correct final answer. If the solution is correct, confirm it. Output ONLY the corrected (or confirmed) final answer in the format: \boxed{<final_answer>}.
"""