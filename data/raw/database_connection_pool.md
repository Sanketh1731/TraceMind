# Database Connection Pooling & Concurrency Troubleshooting Runbook

## 1. PostgreSQL Error 53300: sorry, too many clients already

### Problem Description
`psycopg2.OperationalError: FATAL: sorry, too many clients already (SQLSTATE 53300)`

### Root Cause Analysis
The PostgreSQL server has reached its configured `max_connections` ceiling. Every concurrent backend process in Postgres consumes ~10MB of RAM and dedicated lock table space. Unpooled microservices, worker processes leaking open sessions, or sudden traffic spikes without connection queueing cause rapid connection pool exhaustion.

### Grounded Actionable Fix Steps
1. **Identify Top Connection Consumers**:
   ```sql
   SELECT client_addr, usename, datname, state, count(*) 
   FROM pg_stat_activity 
   GROUP BY client_addr, usename, datname, state 
   ORDER BY count(*) DESC;
   ```
2. **Deploy PgBouncer Connection Pooler**:
   Deploy PgBouncer in transaction pooling mode (`pool_mode = transaction`) between client microservices and PostgreSQL.
3. **Configure Application-Side Pool Limits**:
   In SQLAlchemy or Prisma, bound max pool size and overflow:
   ```python
   create_engine(
       DATABASE_URL,
       pool_size=15,
       max_overflow=5,
       pool_timeout=30,
       pool_recycle=1800
   )
   ```

---

## 2. PostgreSQL Error 40P01: Deadlock Detected

### Problem Description
`ERROR: deadlock detected (SQLSTATE 40P01)`
`DETAIL: Process 14202 waits for ShareLock on transaction 8912; blocked by process 14205.`

### Root Cause Analysis
Two or more concurrent database transactions attempt to obtain conflicting row or table locks in reverse order (Transaction A locks Row 1 and attempts to lock Row 2; Transaction B locks Row 2 and attempts to lock Row 1). PostgreSQL's deadlock detector catches the cyclic wait after `deadlock_timeout` (default 1s) and aborts one transaction.

### Grounded Actionable Fix Steps
1. **Acquire Locks in Deterministic Order**:
   Sort entity IDs prior to bulk update operations:
   ```python
   # Always sort primary keys before locking in transaction
   sorted_ids = sorted(account_ids)
   for aid in sorted_ids:
       session.query(Account).filter_by(id=aid).with_for_update().first()
   ```
2. **Implement Exponential Backoff Retry on SQLSTATE 40P01**:
   Wrap transactions in an automated retry handler for transient deadlocks:
   ```python
   @retry(retry=retry_if_exception_type(DeadlockDetected), stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.1))
   def run_transaction():
       # database query execution
       pass
   ```
