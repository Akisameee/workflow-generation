INITIAL_SOLVE_PROMPT = """
Solve the following math problem step by step. Show all your work and reasoning.
At the end, put your final answer in a boxed environment: \\boxed{answer}.
Make sure to simplify the answer completely.

Problem:
"""

REVIEW_PROMPT = """
You are a math teacher reviewing a student's solution. Check the following solution carefully:

1. Verify if the approach and reasoning are mathematically correct
2. Check for calculation errors
3. Ensure the final answer is properly formatted in a \\boxed{} environment
4. If you find any errors, provide a corrected solution with clear explanations
5. If the solution is already correct, simply output the same \\boxed{answer}

Provide your final reviewed answer below:
"""