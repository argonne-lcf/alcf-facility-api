"""
Test cases for test_job_inputs.py.

Each entry in CASES is a dict with:
    commands : bash commands to run inside the job
    expected : single string that must appear in the job's stdout

Cases are identified by their index in this list.
To add a new test case, just append a new dict to CASES.
"""


CASES: list[dict] = [
    {
        "commands": """
echo Start
echo Middle
echo End
""",
        "expected": "Start\nMiddle\nEnd",
    },
    {
        "commands": "echo Start; echo Middle; echo End",
        "expected": "Start\nMiddle\nEnd",
    },
    {
        "commands": """
echo Start
echo This is \
a continued line
echo End
""",
        "expected": "Start\nThis is a continued line\nEnd",
    },
    {
        "commands": "echo Start; echo This is a continued line; echo End",
        "expected": "Start\nThis is a continued line\nEnd",
    },
    {
        "commands": """
echo Start

(
    echo Inside subshell
    echo Finished subshell
)

echo End
""",
        "expected": "Start\nInside subshell\nFinished subshell\nEnd",
    },
    {
        "commands": "echo Start; ( echo Inside subshell; echo Finished subshell ); echo End",
        "expected": "Start\nInside subshell\nFinished subshell\nEnd",
    },
    {
        "commands": """
echo Start

{
    echo Inside group
    echo Still inside group
}

echo End
""",
        "expected": "Start\nInside group\nStill inside group\nEnd",
    },
    {
        "commands": "echo Start; { echo Inside group; echo Still inside group; }; echo End",
        "expected": "Start\nInside group\nStill inside group\nEnd",
    },
    {
        "commands": """
echo Start

if [ -n "$HOME" ]; then
    echo HOME exists
else
    echo HOME missing
fi

echo End
""",
        "expected": "Start\nHOME exists\nEnd",
    },
    {
        "commands": "echo Start; if [ -n \"$HOME\" ]; then echo HOME exists; else echo HOME missing; fi; echo End",
        "expected": "Start\nHOME exists\nEnd",
    },
    {
        "commands": """
echo Start

for i in 1 2 3 4 5; do
    echo "Iteration $i"
done

echo End
""",
        "expected": "Start\nIteration 1\nIteration 2\nIteration 3\nIteration 4\nIteration 5\nEnd",
    },
    {
        "commands": "echo Start; for i in 1 2 3 4 5; do echo \"Iteration $i\"; done; echo End",
        "expected": "Start\nIteration 1\nIteration 2\nIteration 3\nIteration 4\nIteration 5\nEnd",
    },
    {
        "commands": """
print_message() {
    echo "Hello from function"
}

echo Start
print_message
echo End
""",
        "expected": "Start\nHello from function\nEnd",
    },
    {
        "commands": "print_message() { echo \"Hello from function\"; }; echo Start; print_message; echo End",
        "expected": "Start\nHello from function\nEnd",
    },
    {
        "commands": """
echo Start

printf 'apple\nbanana\ncherry\n' |
    grep 'banana' |
    tr 'a-z' 'A-Z'

echo End
""",
        "expected": "Start\nBANANA\nEnd",
    },
    {
        "commands": "echo Start; printf 'apple\nbanana\ncherry\n' | grep 'banana' | tr 'a-z' 'A-Z'; echo End",
        "expected": "Start\nBANANA\nEnd",
    },
    {
        "commands": """
export MY_VARIABLE="Hello World"

echo Start
echo "$MY_VARIABLE"
echo End
""",
        "expected": "Start\nHello World\nEnd",
    },
    {
        "commands": "export MY_VARIABLE=\"Hello World\"; echo Start; echo \"$MY_VARIABLE\"; echo End",
        "expected": "Start\nHello World\nEnd",
    },
    {
        "commands": """
echo Start

cat <<EOF
This is line one.
This is line two.
This is line three.
EOF

echo End
""",
        "expected": "Start\nThis is line one.\nThis is line two.\nThis is line three.\nEnd",
    },
    {
        "commands": """
set -euo pipefail

log() {
    echo "[LOG] $1"
}

deploy() {
    (
        log "Pulling latest changes..."
        {
            log "Building application..."
            log "Deploying application..."
            log "Application started"
        }
    )
}

log "Starting deployment..."
if deploy; then
    log "Deployment successful"
else
    log "Deployment failed"
    exit 1
fi
""",
        "expected": "[LOG] Starting deployment...\n[LOG] Pulling latest changes...\n[LOG] Building application...\n[LOG] Deploying application...\n[LOG] Application started\n[LOG] Deployment successful",
    },
    {
        "commands": "\necho == dirs\nls -ld /eagle/iri_api 2>&1\necho == builds\ntimeout 120 find /eagle/iri_api/tests ~ -maxdepth 5 -type f \\( -name \"erf*\" -o -name \"*.testtxt\" \\) 2>/dev/null | head -40\necho == done\n",
        "expected": "== dirs\ndrwxrws--- 9 root iri_api 4096 Nov 17 19:32 /eagle/iri_api\n== builds\n/eagle/iri_api/tests/hello.testtxt\n== done"
    },
    {
        "commands": "\necho == dirs\nls -ld /eagle/iri_api 2>&1\necho == builds\ntimeout 120 find /eagle/iri_api/tests ~ -maxdepth 5 -type f \( -name \"erf*\" -o -name \"*.testtxt\" \) 2>/dev/null | head -40\necho == done\n",
        "expected": "== dirs\ndrwxrws--- 9 root iri_api 4096 Nov 17 19:32 /eagle/iri_api\n== builds\n/eagle/iri_api/tests/hello.testtxt\n== done"
    },
    {
        "commands": "cd /eagle/iri_api && echo '=== TOTAL ENERGY ===' && grep -i 'total energy' tests/test.out | tail -5 && cat /tmp/gnu_chunk_ac 2>/dev/null || echo 'no chunk c'",
        "expected": "=== TOTAL ENERGY ===\ntotal energy from file\nno chunk c"
    }
]
