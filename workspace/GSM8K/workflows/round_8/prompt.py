SOLVE_PROMPT = """
Solve the following math problem step by step. Ensure your final answer is placed within a box using the format \boxed{final_answer}.
"""

REVIEW_PROMPT = """
You are an expert math solver. Carefully review the provided solution for the math problem. First, read the problem statement and the generated solution. Identify any errors in understanding the problem, reasoning steps, or calculations. Pay special attention to the conditions and units in the problem. If there are errors, provide a corrected step-by-step solution with explanations. If the solution is correct, confirm it. Finally, output the final answer in the format: \boxed{final_answer}. Ensure that the final answer is numerically correct and matches the problem requirements.
"""