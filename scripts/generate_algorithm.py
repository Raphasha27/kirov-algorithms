import os
import requests
import json
import base64
import random
import subprocess
import tempfile
import sys
from openai import OpenAI
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO_NAME = os.getenv("GITHUB_REPOSITORY", "Raphasha27/kirov-algorithms")

ALGORITHMS = [
    "Dijkstra's Shortest Path", "A* Search Algorithm", "Merge Sort", "Quick Sort",
    "Knapsack Problem (Dynamic Programming)", "Binary Search Tree (Insert & Delete)",
    "Depth First Search (DFS)", "Breadth First Search (BFS)", "Kruskal's Minimum Spanning Tree",
    "Prim's Minimum Spanning Tree", "Bellman-Ford Algorithm", "Floyd-Warshall Algorithm",
    "Rabin-Karp String Matching", "KMP String Matching", "Trie Data Structure",
    "AVL Tree", "Red-Black Tree", "Heap Sort", "Counting Sort", "Radix Sort",
    "Longest Common Subsequence", "Longest Increasing Subsequence", "Matrix Chain Multiplication",
    "Sieve of Eratosthenes", "Euclidean Algorithm for GCD", "Fast Fourier Transform (FFT)",
    "RSA Cryptography basic implementation", "SHA-256 Hashing simulation"
]

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set. Cannot generate algorithm.")
    sys.exit(0)

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_algorithm_code(algo_name):
    prompt = f"""
    You are an expert computer scientist and algorithmic educator.
    Write a clean, highly documented Python 3 implementation of '{algo_name}'.
    
    Requirements:
    1. Provide the implementation.
    2. Include a detailed docstring explaining how it works, and its Time and Space Complexity (Big O).
    3. Below the implementation, write 3-5 comprehensive `pytest` test cases to verify its correctness.
    
    Output ONLY valid Python code. No markdown formatting (like ```python). 
    Do not explain outside of comments.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    code = response.choices[0].message.content.strip()
    if code.startswith("```python"):
        code = code[9:]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()

def run_tests_securely(code_str):
    """
    Uses standard subprocess with temp file to run pytest.
    In a full deployment, this would use Ironclad Sandbox (Monty) 
    for true isolation.
    """
    print("Running tests via temporary isolation...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code_str)
        tmp_path = f.name
        
    try:
        # Run pytest on the temporary file
        result = subprocess.run(["pytest", tmp_path, "-v"], capture_output=True, text=True, timeout=30)
        success = result.returncode == 0
        output = result.stdout
    except subprocess.TimeoutExpired:
        success = False
        output = "Test execution timed out."
    finally:
        os.unlink(tmp_path)
        
    return success, output

def push_to_github(algo_name, code_str):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Format filename safely
    filename = algo_name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("'", "")
    path = f"algorithms/{filename}.py"
    
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    
    # Check if exists
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    payload = {
        "message": f"feat(algo): Automated implementation of {algo_name}",
        "content": base64.b64encode(code_str.encode()).decode(),
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
        
    res = requests.put(url, headers=headers, json=payload)
    if res.status_code in [200, 201]:
        print(f"Successfully committed {path} to GitHub!")
        return True
    else:
        print(f"Failed to commit: {res.status_code} - {res.text}")
        return False

def main():
    print(f"[{datetime.utcnow().isoformat()}] Starting daily algorithm generation...")
    
    # Pick a random algorithm
    algo = random.choice(ALGORITHMS)
    print(f"Selected Algorithm: {algo}")
    
    code = generate_algorithm_code(algo)
    
    success, test_output = run_tests_securely(code)
    
    if success:
        print("Tests passed successfully!")
        push_to_github(algo, code)
    else:
        print("Tests failed or timed out. Code will not be committed.")
        print(test_output)
        sys.exit(1)

if __name__ == "__main__":
    main()
