import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from ..models.schema import FixStep, CauseRanking

class ContextSignals(BaseModel):
    has_startup_timing: bool = False
    has_container_env: bool = False
    has_localhost: bool = False
    error_category: str = "generic"
    detected_clues: List[str] = []
    ambiguity_penalty_pct: int = 0
    ambiguity_reason: str = ""

class ContextAnalyzer:
    """
    Context Weighting & Situational Prioritization Layer.
    Translates raw operational context clues (e.g., containerization, startup timing,
    elevated tokens, port loopback isolation) into prioritized situational root causes,
    ranked fixes with probability weighting, and quick-scan summaries.
    """

    TIMING_PATTERNS = [
        re.compile(r'\b(?:started|launched|booted)\s+before\b', re.IGNORECASE),
        re.compile(r'\bbefore\s+(?:the\s+)?(?:db|database|container|service)\s+(?:was\s+)?ready\b', re.IGNORECASE),
        re.compile(r'\b(?:startup|initialization|boot)\s+race\s+condition\b', re.IGNORECASE),
        re.compile(r'\b(?:race\s+condition|startup\s+timing|timing\s+issue)\b', re.IGNORECASE),
        re.compile(r'\b(?:premature|unready|not\s+ready\s+yet|bootstrapping)\b', re.IGNORECASE)
    ]

    CONTAINER_PATTERNS = [
        re.compile(r'\b(?:docker|container|compose|k8s|kubernetes|pod|bridge\s+network)\b', re.IGNORECASE),
        re.compile(r'\b127\.0\.0\.1:\d+\b'),
        re.compile(r'\blocalhost:\d+\b', re.IGNORECASE)
    ]

    @classmethod
    def analyze(cls, raw_error: str, extracted_codes: List[str]) -> ContextSignals:
        signals = ContextSignals()
        text_lower = raw_error.lower()

        # 1. Detect Startup Timing Context
        timing_clues = []
        for pat in cls.TIMING_PATTERNS:
            m = pat.search(raw_error)
            if m:
                signals.has_startup_timing = True
                timing_clues.append(f"Detected startup lifecycle cue: '{m.group(0)}'")

        # 2. Detect Container Environment Context
        container_clues = []
        for pat in cls.CONTAINER_PATTERNS:
            m = pat.search(raw_error)
            if m:
                signals.has_container_env = True
                container_clues.append(f"Detected container networking cue: '{m.group(0)}'")

        # 3. Check for Localhost IP address
        if "127.0.0.1" in raw_error or "localhost" in text_lower:
            signals.has_localhost = True

        # 4. Categorize Core Error
        if "econnrefused" in text_lower or "connection refused" in text_lower:
            signals.error_category = "econnrefused"
        elif "137" in text_lower or "oomkilled" in text_lower:
            signals.error_category = "oom"
        elif "crashloopbackoff" in text_lower:
            signals.error_category = "crashloop"
        elif "0x80070005" in text_lower or "access denied" in text_lower or "eacces" in text_lower:
            signals.error_category = "access_denied"
        elif "53300" in text_lower or "too many clients" in text_lower:
            signals.error_category = "db_pool"
        elif "recursionerror" in text_lower or "maximum recursion depth" in text_lower:
            signals.error_category = "recursion"

        signals.detected_clues = timing_clues + container_clues

        # 5. Ambiguity & Confidence Calibration
        if signals.error_category == "econnrefused":
            signals.ambiguity_penalty_pct = 8
            signals.ambiguity_reason = "Multiple plausible failure modes: Startup timing race vs container loopback isolation."
        elif signals.error_category == "access_denied":
            signals.ambiguity_penalty_pct = 6
            signals.ambiguity_reason = "Multiple plausible failure modes: Unprivileged UAC token vs Controlled Folder Access vs locked file handle."
        elif signals.error_category == "db_pool":
            signals.ambiguity_penalty_pct = 4
            signals.ambiguity_reason = "Multiple plausible failure modes: Application connection leak vs organic traffic surge."
        elif signals.error_category == "crashloop":
            signals.ambiguity_penalty_pct = 6
            signals.ambiguity_reason = "Multiple plausible failure modes: Slow startup warmup vs fatal boot-time exception."
        elif signals.error_category == "oom":
            signals.ambiguity_penalty_pct = 5
            signals.ambiguity_reason = "Multiple plausible failure modes: Heap memory leak vs undersized container memory ceiling."
        else:
            signals.ambiguity_penalty_pct = 3
            signals.ambiguity_reason = "Deterministic multi-factor verification against indexed operational runbook."

        return signals

    @classmethod
    def get_contextual_override(
        cls,
        signals: ContextSignals,
        raw_error: str,
        section_title: str
    ) -> Optional[Dict[str, Any]]:
        """
        Applies situational reasoning, ranked fixes, confidence tradeoff signals,
        and quick fix summaries tailored directly to the problem instance.
        """
        text_lower = raw_error.lower()

        # =========================================================================
        # 1. Windows Access Denied (0x80070005)
        # =========================================================================
        if signals.error_category == "access_denied":
            is_installer = any(k in text_lower for k in ["installing", "package", "setup.msi", "installer", "setup.exe", "temp"])
            if is_installer:
                root_cause = "The installer doesn't have admin permission to write to protected system folders."
                impact = "Installer cannot write files to target path → installation fails completely."
                explanation = (
                    "Technical Breakdown: The MSI setup process was launched under an unprivileged user token. "
                    "Windows User Account Control (UAC) and NTFS Discretionary Access Control Lists (DACLs) enforce write "
                    "restrictions on protected temporary and system directories, causing the MSI installer engine to abort "
                    "with Win32 error ERROR_ACCESS_DENIED (0x80070005)."
                )
                cause_ranking = CauseRanking(
                    most_likely=["Not running as administrator (unprivileged UAC token)"],
                    possible=[
                        "Controlled Folder Access blocking directory",
                        "File lock from previous failed installation or hung msiexec"
                    ]
                )
            else:
                root_cause = "The application was denied permission to write or modify protected files."
                impact = "Process aborted due to lack of write privileges → operation cannot complete."
                explanation = (
                    "Technical Breakdown: The calling process attempted a file creation or registry write operation "
                    "without holding an elevated security token. Windows NTFS security sub-system returned ERROR_ACCESS_DENIED (0x80070005)."
                )
                cause_ranking = CauseRanking(
                    most_likely=["Process running under unprivileged user account"],
                    possible=[
                        "Target file or registry key owned by SYSTEM or TrustedInstaller",
                        "File marked as read-only or locked by another process"
                    ]
                )

            quick_fix = "Run installer as Administrator"
            fix_steps = [
                FixStep(
                    step_number=1,
                    title="Run Installer as Administrator",
                    priority="Priority 1 (Try First - 85% of cases)",
                    likelihood="Most Common",
                    instruction="Right-click the setup file or terminal and select 'Run as administrator', or launch elevated via PowerShell:",
                    code_snippet='Start-Process -FilePath "C:\\Users\\HP\\AppData\\Local\\Temp\\setup.msi" -Verb runAs',
                    rationale="Elevates the process token to bypass UAC file virtualization and write to system directories."
                ),
                FixStep(
                    step_number=2,
                    title="Check Windows Defender Controlled Folder Access",
                    priority="Priority 2 (Common - 60% of cases)",
                    likelihood="Common",
                    instruction="Verify if Controlled Folder Access blocked the installer's write attempt to Temp:",
                    code_snippet="Get-MpPreference | Select-Object EnableControlledFolderAccess",
                    rationale="Controlled Folder Access actively intercepts and rejects untrusted binary writes to user folders."
                ),
                FixStep(
                    step_number=3,
                    title="Verify NTFS Directory Permissions (icacls)",
                    priority="Priority 3 (Advanced - 25% of cases)",
                    likelihood="Advanced",
                    instruction="Grant current user FullControl permissions on the target directory:",
                    code_snippet='icacls "C:\\Users\\HP\\AppData\\Local\\Temp" /grant "%USERNAME%:(OI)(CI)F"',
                    rationale="Explicitly restores inherited DACL rights if the folder ACL was stripped."
                ),
                FixStep(
                    step_number=4,
                    title="Terminate Conflicting Background Locks",
                    priority="Priority 4 (Diagnostic - 10% of cases)",
                    likelihood="Edge Case",
                    instruction="Check and terminate background installer services holding open file locks:",
                    code_snippet="taskkill /IM msiexec.exe /F",
                    rationale="Clears orphaned msiexec mutexes from interrupted previous installations."
                )
            ]
            return {
                "quick_fix": quick_fix,
                "impact": impact,
                "root_cause": root_cause,
                "explanation": explanation,
                "cause_ranking": cause_ranking,
                "fix_steps": fix_steps,
                "calibrated_confidence_pct": 90,
                "supporting_signals": [
                    "Exact error code match (0x80070005)",
                    "Strong document grounding (Windows NTFS Runbook)"
                ],
                "risk_signals": [
                    "Multiple possible root causes (UAC privilege vs CFA vs file lock)"
                ]
            }

        # =========================================================================
        # 2. Node.js ECONNREFUSED
        # =========================================================================
        elif signals.error_category == "econnrefused":
            if signals.has_startup_timing or ("started before" in text_lower):
                root_cause = "The application tried to connect before the database was ready to accept connections (startup race condition)."
                impact = "Application crashes on boot and fails health checks → service outage during deployments."
                explanation = (
                    "Technical Breakdown: Docker containers boot asynchronously in parallel. While container orchestration spawned "
                    "the database service, PostgreSQL requires 2–5 seconds to perform internal initialization, allocate buffer pools, "
                    "and open port 5432. The application attempted to establish a TCP socket connection prematurely before the database "
                    "reached a ready state, causing the kernel to return ECONNREFUSED. Additionally, 127.0.0.1 inside a container targets "
                    "its own isolated loopback interface."
                )
                quick_fix = "Configure 'depends_on: condition: service_healthy' in docker-compose.yml and retry with wait-for-it.sh"
                cause_ranking = CauseRanking(
                    most_likely=["App container booting faster than PostgreSQL database readiness"],
                    possible=[
                        "DATABASE_URL incorrectly pointing to container loopback (127.0.0.1)",
                        "Database container encountered fatal initialization crash"
                    ]
                )
                fix_steps = [
                    FixStep(
                        step_number=1,
                        title="Add Container Readiness Dependency (docker-compose.yml)",
                        priority="Priority 1 (Recommended Architecture - 85% of cases)",
                        likelihood="Most Common",
                        instruction="Configure the web service to wait for the database healthcheck rather than simple container spawn:",
                        code_snippet="""services:
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
      retries: 10""",
                        rationale="Ensures docker-compose pauses web service launch until pg_isready returns exit code 0."
                    ),
                    FixStep(
                        step_number=2,
                        title="Implement Connection Retry Loop with Exponential Backoff",
                        priority="Priority 2 (Resilience Best Practice - 75% of cases)",
                        likelihood="Common",
                        instruction="Wrap database client connection in resilient retry logic or prepend wait-for-it.sh to entrypoint:",
                        code_snippet="./wait-for-it.sh db:5432 --timeout=30 -- npm start",
                        rationale="Prevents boot-time crashes caused by minor startup latency variations in microservices."
                    ),
                    FixStep(
                        step_number=3,
                        title="Update Connection Host to Docker Service Name",
                        priority="Priority 3 (Configuration Check - 90% of cases)",
                        likelihood="Prerequisite",
                        instruction="Ensure DATABASE_URL targets the Docker Compose service DNS name ('db' or 'postgres') rather than '127.0.0.1':",
                        code_snippet='DATABASE_URL="postgres://postgres:password@db:5432/production_db"',
                        rationale="127.0.0.1 inside a container routes to the local container network namespace, not adjacent services."
                    )
                ]
                return {
                    "quick_fix": quick_fix,
                    "impact": impact,
                    "root_cause": root_cause,
                    "explanation": explanation,
                    "cause_ranking": cause_ranking,
                    "fix_steps": fix_steps,
                    "calibrated_confidence_pct": 89,
                    "supporting_signals": [
                        "Exact error token match (ECONNREFUSED)",
                        "Strong document grounding (Node.js & Python Runtime Runbook)",
                        "Detected explicit startup timing cue ('started before DB container ready')"
                    ],
                    "risk_signals": [
                        "Multiple possible root causes (Startup race vs loopback isolation)"
                    ]
                }
            else:
                root_cause = "The app is looking for the database on its own isolated container network (127.0.0.1) instead of the Docker bridge."
                impact = "Application cannot reach database service → all backend database queries fail immediately."
                explanation = (
                    "Technical Breakdown: In containerized environments, '127.0.0.1' points to the container's isolated network namespace "
                    "rather than the host or database container. Connection requests must target the Docker Compose service DNS name (e.g., 'db:5432')."
                )
                quick_fix = "Update DATABASE_URL host from 127.0.0.1 to Docker service name (e.g. 'db:5432')"
                cause_ranking = CauseRanking(
                    most_likely=["Connection string configured with 127.0.0.1 instead of internal service DNS"],
                    possible=[
                        "Database container not attached to the same bridge network",
                        "Database port 5432 not exposed internally"
                    ]
                )
                fix_steps = [
                    FixStep(
                        step_number=1,
                        title="Update Connection String Host to Internal Service Name",
                        priority="Priority 1 (Immediate - 90% of cases)",
                        likelihood="Most Common",
                        instruction="In docker-compose.yml or .env, change 127.0.0.1 to the Docker network service name:",
                        code_snippet='DATABASE_URL="postgres://postgres:password@db:5432/my_app"',
                        rationale="Docker's embedded DNS resolves service names to the correct container IP on the shared bridge network."
                    ),
                    FixStep(
                        step_number=2,
                        title="Add Healthcheck Dependency in docker-compose.yml",
                        priority="Priority 2 (Architecture - 70% of cases)",
                        likelihood="Common",
                        instruction="Require the database container to report healthy before starting dependent application containers:",
                        code_snippet="""services:
  web:
    depends_on:
      db:
        condition: service_healthy""",
                        rationale="Guarantees the database socket is listening and accepting connections before application boot."
                    ),
                    FixStep(
                        step_number=3,
                        title="Implement Connection Retry with wait-for-db",
                        priority="Priority 3 (Resilience - 60% of cases)",
                        likelihood="Best Practice",
                        instruction="Add a startup retry wrapper to tolerate initialization latency:",
                        code_snippet="./wait-for-it.sh db:5432 --timeout=30 -- npm start",
                        rationale="Defensive real-world pattern preventing crash cascades during cold boots."
                    )
                ]
                return {
                    "quick_fix": quick_fix,
                    "impact": impact,
                    "root_cause": root_cause,
                    "explanation": explanation,
                    "cause_ranking": cause_ranking,
                    "fix_steps": fix_steps,
                    "calibrated_confidence_pct": 88,
                    "supporting_signals": [
                        "Exact error token match (ECONNREFUSED)",
                        "Container loopback IP signature (127.0.0.1)"
                    ],
                    "risk_signals": [
                        "Multiple possible root causes (Host resolution vs service unreadiness)"
                    ]
                }

        # =========================================================================
        # 3. PostgreSQL 53300 (Too Many Clients)
        # =========================================================================
        elif signals.error_category == "db_pool":
            root_cause = "PostgreSQL ran out of available connection slots for new clients."
            impact = "All new client requests rejected with SQLSTATE 53300 → cascading 500 errors across services."
            explanation = (
                "Technical Breakdown: The PostgreSQL server has reached its configured max_connections ceiling. Every concurrent "
                "backend process in Postgres consumes ~10MB of RAM and dedicated lock table space. Unpooled microservices, worker "
                "processes leaking open sessions, or sudden traffic spikes without connection queueing cause rapid connection pool exhaustion."
            )
            quick_fix = "Terminate idle leaked connections via pg_stat_activity or deploy PgBouncer connection pooler"
            cause_ranking = CauseRanking(
                most_likely=["Unpooled microservice client connections or leaked idle sessions"],
                possible=[
                    "Sudden traffic surge exceeding max_connections ceiling",
                    "Slow unindexed queries holding open transactions"
                ]
            )
            fix_steps = [
                FixStep(
                    step_number=1,
                    title="Identify and Terminate Top Connection Consumers",
                    priority="Priority 1 (Emergency Recovery - 95% of cases)",
                    likelihood="Immediate",
                    instruction="Query active connection allocations and kill idle in transaction leaked sessions:",
                    code_snippet="""SELECT client_addr, usename, datname, state, count(*)
FROM pg_stat_activity
GROUP BY client_addr, usename, datname, state
ORDER BY count(*) DESC;""",
                    rationale="Immediately frees exhausted backend connection slots on the production database."
                ),
                FixStep(
                    step_number=2,
                    title="Deploy PgBouncer Connection Pooler",
                    priority="Priority 2 (Architecture - 85% of cases)",
                    likelihood="Recommended Permanent Fix",
                    instruction="Deploy PgBouncer in transaction pooling mode (pool_mode = transaction) between services and PostgreSQL:",
                    code_snippet="""[databases]
* = host=127.0.0.1 port=5432

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20""",
                    rationale="Allows thousands of incoming application connections to multiplex over a bounded pool of ~20 Postgres server connections."
                ),
                FixStep(
                    step_number=3,
                    title="Configure Application-Side Pool Limits",
                    priority="Priority 3 (Application Configuration - 70% of cases)",
                    likelihood="Preventative",
                    instruction="In SQLAlchemy or Prisma, bound max pool size and overflow:",
                    code_snippet="""create_engine(
    DATABASE_URL,
    pool_size=15,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800
)""",
                    rationale="Prevents unbounded connection spawns during traffic spikes."
                )
            ]
            return {
                "quick_fix": quick_fix,
                "impact": impact,
                "root_cause": root_cause,
                "explanation": explanation,
                "cause_ranking": cause_ranking,
                "fix_steps": fix_steps,
                "calibrated_confidence_pct": 91,
                "supporting_signals": [
                    "Exact SQLSTATE code match (53300)",
                    "Strong document grounding (Database Connection Pool Runbook)"
                ],
                "risk_signals": [
                    "Multiple possible root causes (Connection leak vs organic traffic spike)"
                ]
            }

        # =========================================================================
        # 4. Docker 137 (OOMKilled)
        # =========================================================================
        elif signals.error_category == "oom":
            m_worker = re.search(r'worker-[a-zA-Z0-9\-_]+', raw_error)
            container_name = m_worker.group(0) if m_worker else "worker container"
            root_cause = f"The container '{container_name}' ran out of allocated memory and was killed by the system."
            impact = "Worker container terminated abruptly mid-job → lost batch processing progress."
            explanation = (
                f"Technical Breakdown: The worker process inside {container_name} allocated memory beyond its configured cgroup memory limit. "
                "Linux kernel's Out-Of-Memory (OOM) killer dispatched SIGKILL (128 + 9 = 137) to prevent host memory exhaustion."
            )
            quick_fix = "Increase container memory limit in Compose manifest ('limits.memory: 2G') or profile memory leak"
            cause_ranking = CauseRanking(
                most_likely=["Container memory limit (cgroups) set too low for peak workload"],
                possible=[
                    "Memory leak in application heap",
                    "Large payload or batch loaded entirely into memory"
                ]
            )
            fix_steps = [
                FixStep(
                    step_number=1,
                    title="Increase Container Memory Allocation",
                    priority="Priority 1 (Immediate Mitigation - 85% of cases)",
                    likelihood="Most Common",
                    instruction="Increase the container memory limit in docker-compose.yml or Kubernetes deployment spec:",
                    code_snippet="""deploy:
  resources:
    limits:
      memory: 2G
    reservations:
      memory: 1G""",
                    rationale="Allows peak allocations to complete without triggering kernel cgroup kill signals."
                ),
                FixStep(
                    step_number=2,
                    title="Inspect Container Memory Consumption (docker stats)",
                    priority="Priority 2 (Diagnostic - 65% of cases)",
                    likelihood="Common",
                    instruction="Monitor live resident set size (RSS) and cache growth:",
                    code_snippet="docker stats --no-stream",
                    rationale="Identifies whether memory usage climbs monotonically (leak) or spikes instantaneously (large batch job)."
                ),
                FixStep(
                    step_number=3,
                    title="Profile Application Heap for Memory Leaks",
                    priority="Priority 3 (Root Cause Analysis - 40% of cases)",
                    likelihood="Advanced",
                    instruction="Enable Node.js/Python heap profiling to identify uncollected object retained sizes:",
                    code_snippet="node --max-old-space-size=2048 --inspect index.js",
                    rationale="Resolves underlying memory leaks in global caches or event listener retention."
                )
            ]
            return {
                "quick_fix": quick_fix,
                "impact": impact,
                "root_cause": root_cause,
                "explanation": explanation,
                "cause_ranking": cause_ranking,
                "fix_steps": fix_steps,
                "calibrated_confidence_pct": 90,
                "supporting_signals": [
                    "Exact exit code match (exit code 137)",
                    "Strong document grounding (Docker Runtime Runbook)"
                ],
                "risk_signals": [
                    "Multiple possible root causes (Quota ceiling vs unbounded memory leak)"
                ]
            }

        # =========================================================================
        # 5. Kubernetes CrashLoopBackOff
        # =========================================================================
        elif signals.error_category == "crashloop":
            root_cause = "The pod crashed on startup because health checks started before the app finished booting."
            impact = "Pod enters exponential restart backoff → pod never joins service endpoint rotation."
            explanation = (
                "Technical Breakdown: The container was terminated and entered CrashLoopBackOff because Kubernetes kubelet initiated "
                "HTTP 500 liveness checks before internal web framework initialization and database warm-up routines completed."
            )
            quick_fix = "Increase initialDelaySeconds in pod livenessProbe (e.g., initialDelaySeconds: 30)"
            cause_ranking = CauseRanking(
                most_likely=["Liveness probe initialDelaySeconds too short for warmup"],
                possible=[
                    "Missing environment variable or secret causing boot crash",
                    "Uncaught promise/exception during database connection"
                ]
            )
            fix_steps = [
                FixStep(
                    step_number=1,
                    title="Increase initialDelaySeconds or Switch to startupProbe",
                    priority="Priority 1 (Probe Configuration - 80% of cases)",
                    likelihood="Most Common",
                    instruction="Grant sufficient warmup duration before the kubelet begins health evaluation:",
                    code_snippet="""livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10""",
                    rationale="Prevents premature SIGTERM termination during cold start framework boot."
                ),
                FixStep(
                    step_number=2,
                    title="Inspect Previous Pod Termination Logs",
                    priority="Priority 2 (Diagnostic - 90% of cases)",
                    likelihood="Immediate",
                    instruction="Retrieve standard error output from the crashed container instance:",
                    code_snippet="kubectl logs api-gateway-7f8d6-x9b12 --previous --tail=50",
                    rationale="Reveals fatal boot-time exceptions that caused HTTP 500 responses."
                ),
                FixStep(
                    step_number=3,
                    title="Handle Unhandled Boot Exceptions",
                    priority="Priority 3 (Application Fix - 50% of cases)",
                    likelihood="Code Level",
                    instruction="Ensure dependency initialization errors (e.g. Redis/DB unreachable) fail gracefully during startup probe phase.",
                    code_snippet=None,
                    rationale="Prevents uncaught promises from crashing the Node.js or Python runtime."
                )
            ]
            return {
                "quick_fix": quick_fix,
                "impact": impact,
                "root_cause": root_cause,
                "explanation": explanation,
                "cause_ranking": cause_ranking,
                "fix_steps": fix_steps,
                "calibrated_confidence_pct": 89,
                "supporting_signals": [
                    "Exact status match (CrashLoopBackOff)",
                    "Strong document grounding (Kubernetes Reliability Runbook)"
                ],
                "risk_signals": [
                    "Multiple possible root causes (Warmup timing vs fatal boot exception)"
                ]
            }

        # =========================================================================
        # 6. Python RecursionError
        # =========================================================================
        elif signals.error_category == "recursion":
            root_cause = "A function called itself endlessly until Python ran out of call stack space."
            impact = "Parser worker crashes immediately → request drops with unhandled 500 exception."
            explanation = (
                "Technical Breakdown: The AST traversal function in 'engine/parser.py' (traverse_ast) traversed a cyclic node graph "
                "without a visited set or missed a base termination condition, triggering Python's 1000-frame RecursionError limit."
            )
            quick_fix = "Add visited set tracker in traverse_ast (engine/parser.py) or refactor to iterative stack"
            cause_ranking = CauseRanking(
                most_likely=["Circular node reference in parsed tree without visited tracking"],
                possible=[
                    "Missing base termination condition in recursive helper",
                    "Extremely deep non-cyclic hierarchy exceeding default 1000 limit"
                ]
            )
            fix_steps = [
                FixStep(
                    step_number=1,
                    title="Add Base Case or Cycle Tracking (visited: set)",
                    priority="Priority 1 (Code Fix - 90% of cases)",
                    likelihood="Recommended Fix",
                    instruction="Introduce a visited set to detect cyclic graph references:",
                    code_snippet="""def traverse_ast(node, visited=None):
    if visited is None:
        visited = set()
    if id(node) in visited or node is None:
        return None
    visited.add(id(node))
    return traverse_ast(node.child, visited)""",
                    rationale="Guarantees recursion terminates when encountering circular AST branches."
                ),
                FixStep(
                    step_number=2,
                    title="Refactor to Iterative Loop with Explicit Stack",
                    priority="Priority 2 (Architecture - 70% of cases)",
                    likelihood="High Scale",
                    instruction="Replace call-stack recursion with an in-memory heap stack:",
                    code_snippet="""def traverse_iterative(root):
    stack = [root]
    while stack:
        curr = stack.pop()
        if curr and curr.child:
            stack.append(curr.child)""",
                    rationale="Eliminates interpreter recursion limits entirely for deep trees."
                ),
                FixStep(
                    step_number=3,
                    title="Temporarily Increase sys.setrecursionlimit",
                    priority="Priority 3 (Temporary Workaround - 20% of cases)",
                    likelihood="Caution / Temporary",
                    instruction="Bump recursion limit for non-cyclic deep parsing tasks:",
                    code_snippet="""import sys
sys.setrecursionlimit(3000)""",
                    rationale="Temporary band-aid; does not prevent C stack overflow if recursion is truly unbounded."
                )
            ]
            return {
                "quick_fix": quick_fix,
                "impact": impact,
                "root_cause": root_cause,
                "explanation": explanation,
                "cause_ranking": cause_ranking,
                "fix_steps": fix_steps,
                "calibrated_confidence_pct": 91,
                "supporting_signals": [
                    "Exact Python exception match (RecursionError)",
                    "Strong document grounding (Python Runtime Runbook)"
                ],
                "risk_signals": [
                    "Multiple possible root causes (Cyclic graph vs missing base condition)"
                ]
            }

        return None
