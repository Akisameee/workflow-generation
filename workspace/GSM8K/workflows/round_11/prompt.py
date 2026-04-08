SOLVE_STANDARD = """
Solve the following math problem step by step using clear mathematical reasoning.
Ensure your final answer is placed within a box using the format \boxed{final_answer}.
Provide explicit step-by-step calculations and label each step clearly.
"""

SOLVE_ALTERNATIVE = """
Solve the same math problem from a different perspective or using an alternative method.
Consider different approaches like unit analysis, working backwards, or visual reasoning.
Ensure your final answer is placed within a box using the format \boxed{final_answer}.
Clearly explain your alternative approach.
"""

SOLVE_ASSUMPTIONS = """
Solve the math problem while explicitly identifying and questioning all assumptions.
List any implicit assumptions in the problem statement and verify if they are reasonable.
Consider edge cases and alternative interpretations.
Ensure your final answer is placed within a box using the format \boxed{final_answer}.
"""

REVIEW_FINAL = """
You are an expert math solver reviewing a solution selected from multiple approaches.
First, re-interpret the original problem statement in your own words to ensure you understand the exact requirement.
Second, carefully examine the provided solution against the original wording. Check if any part of the solution misinterprets the problem (e.g., misreading "needed 2 more toys than he already had").
Third, verify the logical flow and mathematical correctness.
Fourth, check that all units, conversions, and calculations are accurate.
Fifth, ensure the final answer properly addresses the original question's requirements.
If you find any errors or improvements needed, provide a corrected solution.
Regardless of corrections, output the final answer in the format: \boxed{final_answer}.
Make absolutely certain the final answer is numerically correct and complete.
"""