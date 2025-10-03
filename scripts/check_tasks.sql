.timeout 2000
.headers off
.mode csv
SELECT task_id, status FROM tasks
WHERE status NOT IN ('0', '1')
  AND timestamp < datetime('now', '-' || :TIMEOUT || ' seconds');
