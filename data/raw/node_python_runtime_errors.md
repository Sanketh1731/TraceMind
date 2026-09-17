# Node.js & Python Backend Runtime Errors Runbook

## 1. Node.js ECONNREFUSED – Connection Refused

### Problem Description
```text
Error: connect ECONNREFUSED 127.0.0.1:5432
    at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1494:16)
    errno: -4078, code: 'ECONNREFUSED', syscall: 'connect', address: '127.0.0.1', port: 5432
```

### Root Cause Analysis
`ECONNREFUSED` is a socket-level network error generated when a client attempts to open a TCP connection to a host and port where no listening socket is active, or the operating system firewall actively rejected the SYN handshake.
Primary operational causes:
1. **Startup Race Condition & Container Timing**: When an application container starts before the database container is fully ready and accepting connections, the client attempts premature TCP connection handshakes. Docker Compose `depends_on` without health conditions only guarantees container spawn order, not database socket readiness.
2. **Container Localhost Isolation (Wrong Host)**: In containerized environments, `127.0.0.1` refers to the container's private loopback interface rather than the host or database container. Applications must connect via the Docker network service name (e.g. `postgres` or `db`).
3. **Database Service Stopped or Crashed**: The target database daemon is stopped, crashing on boot, or bound to `localhost` rather than `0.0.0.0` in `postgresql.conf`.

### Grounded Actionable Fix Steps
1. **Configure Container Service Name in Connection String**:
   In Docker Compose, change `DATABASE_URL="postgres://user:pass@127.0.0.1:5432/db"` to use the internal DNS service name:
   ```yaml
   DATABASE_URL: "postgres://postgres:password@db:5432/production_db"
   ```
2. **Add Container Readiness Dependency in docker-compose.yml**:
   Prevent startup race conditions by requiring the database to pass its health check before the application container launches:
   ```yaml
   services:
     web:
       depends_on:
         db:
           condition: service_healthy
     db:
       image: postgres:15
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U postgres"]
         interval: 2s
         timeout: 3s
         retries: 10
   ```
3. **Implement Connection Retry Loop & wait-for-db Script**:
   Add resilient retry logic with exponential backoff or prepend `wait-for-it.sh` in the entrypoint:
   ```bash
   ./wait-for-it.sh db:5432 --timeout=30 -- npm start
   ```
4. **Verify Target Service is Running and Listening**:
   On Linux/macOS:
   ```bash
   sudo systemctl status postgresql
   ss -tulpn | grep 5432
   ```
   On Windows PowerShell:
   ```powershell
   Get-Service -Name "*postgres*"
   Test-NetConnection -ComputerName 127.0.0.1 -Port 5432
   ```

---

## 2. Python RecursionError: maximum recursion depth exceeded

### Problem Description
```text
RecursionError: maximum recursion depth exceeded while calling a Python object
  File "engine/parser.py", line 84, in traverse_ast
    return traverse_ast(node.child)
  [Previous line repeated 996 more times]
```

### Root Cause Analysis
Python interpreters enforce a maximum call stack depth (default 1000 frames via `sys.getrecursionlimit()`) to prevent C stack overflow and segmentation faults. A `RecursionError` indicates an unbounded recursive call missing a terminating base condition, cyclic graph references without a visited set, or an unintended recursive `__getattr__` call in class methods.

### Grounded Actionable Fix Steps
1. **Add Base Case or Cycle Tracking**:
   Introduce a `visited: set()` tracker for cyclic graph structures:
   ```python
   def traverse_ast(node, visited=None):
       if visited is None:
           visited = set()
       if id(node) in visited or node is None:
           return None
       visited.add(id(node))
       return traverse_ast(node.child, visited)
   ```
2. **Refactor from Recursion to Iterative Loop with Explicit Stack**:
   ```python
   def traverse_iterative(root):
       stack = [root]
       while stack:
           curr = stack.pop()
           if curr and curr.child:
               stack.append(curr.child)
   ```
3. **Temporarily Increase Limit (Use with Caution)**:
   ```python
   import sys
   sys.setrecursionlimit(3000)
   ```
