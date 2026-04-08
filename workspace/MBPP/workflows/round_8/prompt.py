CODE_GENERATION_PROMPT = """
You are given a programming problem. Write a Python function that exactly matches the required function signature and solves the problem.
Ensure the code is syntactically correct, efficient, and passes all typical test cases.
Return only the function code without any additional text, comments, or explanations.
"""

CORRECTION_PROMPT = """
Carefully analyze the provided information about a programming problem and a previous code attempt that failed test cases.

Your task is to generate a corrected version of the code that addresses the errors and passes the test cases.

Follow these steps:
1. Review the problem statement and the required function signature (entry point).
2. Examine the previous code and the test errors to identify the specific mistakes.
3. Generate a corrected Python function that exactly matches the required signature and solves the problem.

Return only the corrected code without any additional text, comments, or explanations.
"""