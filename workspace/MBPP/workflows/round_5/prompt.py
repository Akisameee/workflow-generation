CODE_GENERATION_PROMPT = """
You are given a programming problem. Write a Python function that exactly matches the required function signature and solves the problem.
Ensure the code is syntactically correct, efficient, and passes all typical test cases.
Return only the function code without any additional text, comments, or explanations.
"""

CORRECTION_PROMPT = """
Analyze the previous code that failed the test cases. Identify the specific errors or logical mistakes, including any discrepancies in function name or signature. The required function name is provided in the entry point.
Generate a corrected version of the code that addresses these issues. Ensure that the function name exactly matches the entry point and the signature is correct.
Return only the corrected code without any additional text.
"""