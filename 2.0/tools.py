import io
import contextlib
import multiprocessing

def _exec_worker(code: str, queue):
    """
    Worker function to execute code in a separate process.
    Captures stdout and puts it in the queue.
    """
    buffer = io.StringIO()
    
    try:
        with contextlib.redirect_stdout(buffer):
            import math
            import random
            import datetime
            import re
            import statistics
            import itertools
            import collections
            import sympy
            
            safe_globals = {
                "math": math,
                "random": random,
                "datetime": datetime,
                "re": re,
                "statistics": statistics,
                "itertools": itertools,
                "collections": collections,
                "sympy": sympy,
                "print": print,
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "set": set,
                "sorted": sorted,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "bool": bool,
                "pow": pow,
                "divmod": divmod,
            }
            
            exec(code, safe_globals)
            
        result = buffer.getvalue().strip()
        queue.put({"success": True, "result": result})
        
    except Exception as e:
        queue.put({"success": False, "error": str(e)})

def execute_python(code: str, timeout: int = 5) -> str:
    """
    Executes Python code in a separate process with a timeout.
    Returns the captured stdout or an error message.
    """
    code = code.replace("```python", "").replace("```", "").strip()
    
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_exec_worker, args=(code, queue))
    p.start()
    
    p.join(timeout)
    
    if p.is_alive():
        p.terminate()
        p.join()
        return "Error: Execution timed out."
    
    if not queue.empty():
        output = queue.get()
        if output["success"]:
            return output["result"]
        else:
            return f"Error: {output['error']}"
    return "Error: No output captured."
