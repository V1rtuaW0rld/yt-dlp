.timeout 2000
UPDATE tasks SET status = '0' WHERE task_id = :TASK_ID;
