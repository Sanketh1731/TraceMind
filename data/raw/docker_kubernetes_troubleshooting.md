# Docker & Kubernetes Production Troubleshooting Guide

## 1. Kubernetes CrashLoopBackOff

### Problem Description
Pods transition into `CrashLoopBackOff` state. Status reveals restarts rapidly incrementing:
```text
NAME                     READY   STATUS             RESTARTS   AGE
api-gateway-7f8d6-x9b12  0/1     CrashLoopBackOff   6          3m15s
```

### Root Cause Analysis
`CrashLoopBackOff` is not an error in itself, but a Kubernetes controller status indicating that the pod's main container continuously crashes (exits with non-zero code) immediately after starting, causing kubelet to apply an exponential backoff delay (10s, 20s, 40s, up to 5m).
Common root causes include:
1. Missing or invalid environment variables (e.g., `DATABASE_URL` missing or unresolvable).
2. Liveness probe failing immediately because `initialDelaySeconds` is shorter than application bootstrap time.
3. Entrypoint command syntax error or missing execution permissions on binary (`exec format error`).
4. Out of Memory (OOMKilled) by the Linux kernel cgroup enforcer.

### Grounded Actionable Fix Steps
1. **Inspect Previous Container Crash Logs**:
   Retrieve stderr from the terminated container instance:
   ```bash
   kubectl logs api-gateway-7f8d6-x9b12 --previous
   ```
2. **Describe Pod Termination Reason**:
   Inspect the termination state and exit code:
   ```bash
   kubectl describe pod api-gateway-7f8d6-x9b12
   ```
   Look for `Last State: Terminated`, `Reason: Error`, `Exit Code: 1` or `Exit Code: 137`.
3. **Adjust Liveness and Readiness Probe Delays**:
   Increase `initialDelaySeconds` in the deployment manifest if the app takes 15-30s to boot:
   ```yaml
   livenessProbe:
     httpGet:
       path: /healthz
       port: 8080
     initialDelaySeconds: 30
     periodSeconds: 10
   ```

---

## 2. Container Exit Code 137 – OOMKilled (Out of Memory)

### Problem Description
Container terminates abruptly with:
`Error: container was killed (exit code 137): OOMKilled`

### Root Cause Analysis
Exit code 137 signifies process termination by `SIGKILL` (signal 9 + 128 = 137). In Docker/Kubernetes, this occurs when the container's resident set size (RSS) memory consumption surpasses the configured cgroup memory limit (`resources.limits.memory`). The Linux Kernel Out-Of-Memory Killer immediately invokes SIGKILL to protect the node host.

### Grounded Actionable Fix Steps
1. **Verify OOM State in Pod Manifest**:
   ```bash
   kubectl get pod <pod-name> -o jsonpath='{.status.containerStatuses[*].lastState.terminated.reason}'
   ```
2. **Increase Memory Limit**:
   Update `resources.limits.memory` in your deployment YAML:
   ```yaml
   resources:
     requests:
       memory: "512Mi"
       cpu: "250m"
     limits:
       memory: "2Gi"
       cpu: "1000m"
   ```
3. **Tune Runtime Garbage Collector & Heap Limits**:
   For Node.js: `--max-old-space-size=1536`
   For Java/JVM: `-XX:MaxRAMPercentage=75.0`
