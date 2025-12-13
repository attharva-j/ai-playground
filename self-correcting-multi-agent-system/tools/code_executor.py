"""
Code Executor Tool - Provides safe code execution capabilities for agents.
"""

import subprocess
import tempfile
import os
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: str
    execution_time: float
    return_code: int

class CodeExecutor:
    """
    Safe code execution tool for agents.
    
    Provides sandboxed execution of Python code with security restrictions
    and resource limits.
    """
    
    def __init__(self, timeout: int = 30, max_output_size: int = 10000):
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.allowed_imports = {
            'math', 'statistics', 'json', 'datetime', 'time',
            'pandas', 'numpy', 'matplotlib', 'seaborn',
            'sqlite3', 'csv', 're', 'collections'
        }
    
    def execute_python(self, code: str, context: Dict[str, Any] = None) -> ExecutionResult:
        """
        Execute Python code safely in a restricted environment.
        
        Args:
            code: Python code to execute
            context: Optional context variables to make available
            
        Returns:
            ExecutionResult with execution details
        """
        import time
        start_time = time.time()
        
        try:
            # Validate code safety
            if not self._is_code_safe(code):
                return ExecutionResult(
                    success=False,
                    output="",
                    error="Code contains potentially unsafe operations",
                    execution_time=0.0,
                    return_code=-1
                )
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Add context setup if provided
                if context:
                    f.write("# Context variables\n")
                    for key, value in context.items():
                        if isinstance(value, str):
                            f.write(f"{key} = {repr(value)}\n")
                        else:
                            f.write(f"{key} = {value}\n")
                    f.write("\n")
                
                f.write(code)
                temp_file = f.name
            
            try:
                # Execute with subprocess for isolation
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                execution_time = time.time() - start_time
                
                # Truncate output if too large
                output = result.stdout
                error = result.stderr
                
                if len(output) > self.max_output_size:
                    output = output[:self.max_output_size] + "\n... (output truncated)"
                
                if len(error) > self.max_output_size:
                    error = error[:self.max_output_size] + "\n... (error truncated)"
                
                return ExecutionResult(
                    success=result.returncode == 0,
                    output=output,
                    error=error,
                    execution_time=execution_time,
                    return_code=result.returncode
                )
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Code execution timed out after {self.timeout} seconds",
                execution_time=self.timeout,
                return_code=-1
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time=time.time() - start_time,
                return_code=-1
            )
    
    def _is_code_safe(self, code: str) -> bool:
        """
        Check if code is safe to execute.
        
        This is a basic safety check - in production, you'd want more
        sophisticated sandboxing.
        """
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess',
            'import shutil', 'import glob', 'import socket',
            'open(', 'file(', 'exec(', 'eval(',
            '__import__', 'getattr', 'setattr', 'delattr',
            'globals()', 'locals()', 'vars()', 'dir()',
            'input(', 'raw_input('
        ]
        
        code_lower = code.lower()
        
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                return False
        
        return True
    
    def execute_calculation(self, expression: str, variables: Dict[str, float] = None) -> ExecutionResult:
        """
        Execute a mathematical calculation safely.
        
        Args:
            expression: Mathematical expression to evaluate
            variables: Optional variables to include in calculation
            
        Returns:
            ExecutionResult with calculation result
        """
        # Build safe calculation code
        code_lines = []
        
        if variables:
            for name, value in variables.items():
                if isinstance(value, (int, float)):
                    code_lines.append(f"{name} = {value}")
        
        code_lines.extend([
            "import math",
            "import statistics",
            f"result = {expression}",
            "print(f'Result: {result}')",
            "print(f'Type: {type(result).__name__}')"
        ])
        
        code = "\n".join(code_lines)
        
        return self.execute_python(code)
    
    def format_result_for_agent(self, result: ExecutionResult, code: str) -> str:
        """
        Format execution result for agent consumption.
        
        Args:
            result: Execution result to format
            code: Original code that was executed
            
        Returns:
            Formatted string representation
        """
        formatted = f"Code Execution Result:\n"
        formatted += f"Success: {'✅' if result.success else '❌'}\n"
        formatted += f"Execution Time: {result.execution_time:.3f}s\n\n"
        
        if result.success:
            formatted += f"Output:\n{result.output}\n"
        else:
            formatted += f"Error:\n{result.error}\n"
        
        if result.output and result.error:
            formatted += f"\nWarnings/Stderr:\n{result.error}\n"
        
        formatted += f"\nExecuted Code:\n```python\n{code}\n```"
        
        return formatted

# Example usage and testing
def test_code_executor():
    """Test function for code executor."""
    executor = CodeExecutor()
    
    # Test simple calculation
    calc_result = executor.execute_calculation("2 + 2 * 3")
    print("Calculation Test:")
    print(executor.format_result_for_agent(calc_result, "2 + 2 * 3"))
    
    # Test with variables
    var_result = executor.execute_calculation(
        "revenue * profit_margin", 
        {"revenue": 1000000, "profit_margin": 0.15}
    )
    print("\nVariable Calculation Test:")
    print(executor.format_result_for_agent(var_result, "revenue * profit_margin"))
    
    # Test Python code
    python_code = """
import math
import statistics

data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
mean = statistics.mean(data)
std_dev = statistics.stdev(data)

print(f"Data: {data}")
print(f"Mean: {mean}")
print(f"Standard Deviation: {std_dev:.2f}")
print(f"Sum: {sum(data)}")
"""
    
    python_result = executor.execute_python(python_code)
    print("\nPython Code Test:")
    print(executor.format_result_for_agent(python_result, python_code))

if __name__ == "__main__":
    test_code_executor()