CODE_GENERATION_PROMPT = """
You are given a programming problem. Write a Python function that exactly matches the required function signature and solves the problem.
Pay special attention to the function name and the parameters. The function must be named exactly as specified in the problem.
Ensure the code is syntactically correct, efficient, and passes all typical test cases.
Return only the function code without any additional text, comments, or explanations.
"""

CORRECTION_PROMPT = """
Analyze the previous code that failed the test cases. Identify the specific errors or logical mistakes.
Check carefully if the function name matches the required signature exactly.
Generate a corrected version of the code that addresses these issues while maintaining the original function signature.
Return only the corrected code without any additional text.
"""