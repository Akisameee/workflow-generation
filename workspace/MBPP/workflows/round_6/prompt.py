CODE_GENERATION_PROMPT = """
You are given a programming problem. Write a Python function that exactly matches the required function signature and solves the problem.
Ensure the code is syntactically correct, efficient, and passes all typical test cases.
Return only the function code without any additional text, comments, or explanations.
"""

CORRECTION_PROMPT = """
Analyze the previous code and the test result code. The test failed, indicating errors. Compare both codes to identify logical or syntactic mistakes.
Generate a corrected version of the code that fixes these issues while maintaining the original function signature.
Return only the corrected code without any additional text.
"""