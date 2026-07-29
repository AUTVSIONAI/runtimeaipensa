"""
Scheduler Runtime Module

Provides cron scheduling, recurring tasks, one-time jobs,
and task queue management with backpressure handling.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import logging
import uuid
from croniter import croniter
from sortedcontainers import SortedDict

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class JobType(Enum):
    """Job type."""
    ONCE = "once"           # Run once at specific time
    RECURRING = "recurring" # Cron-based recurring
    INTERVAL = "interval"   # Fixed interval
    DELAYED = "delayed"     # Run after delay


class ScheduleStatus(Enum):
    """Schedule status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    COMPLETED = "completed"  # For one-time jobs that ran


@dataclass
class Job:
    """Scheduled job definition."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    job_type: JobType = JobType.ONCE
    action: str = ""  # Tool/action to execute
    parameters: Dict[str, Any] = field(default_factory=dict)
    agent_type: str = "default"
    cron_expression: Optional[str] = None  # For recurring
    interval_seconds: Optional[float] = None  # For interval
    run_at: Optional[datetime] = None  # For one-time
    delay_seconds: Optional[float] = None  # For delayed
    timezone: str = "UTC"
    max_runs: Optional[int] = None  # None = infinite
    run_count: int = 0
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_result: Optional[Any] = None
    last_error: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.job_type == JobType.RECURRING and self.cron_expression:
            self._calculate_next_run()
        elif self.job_type == JobType.INTERVAL and self.interval_seconds:
            self.next_run = datetime.utcnow() + timedelta(seconds=self.interval_seconds)
        elif self.job_type == JobType.ONCE and self.run_at:
            self.next_run = self.run_at
        elif self.job_type == JobType.DELAYED and self.delay_seconds:
            self.next_run = datetime.utcnow() + timedelta(seconds=self.delay_seconds)

    def _calculate_next_run(self) -> None:
        """Calculate next run time from cron expression."""
        if self.cron_expression:
            try:
                cron = croniter(self.cron_expression, datetime.utcnow())
                self.next_run = cron.get_next(datetime)
            except Exception as e:
                logger.error(f"Invalid cron expression: {self.cron_expression} - {e}")


@dataclass
class JobExecution:
    """Job execution record."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    job_id: str = ""
    job_name: str = ""
    status: JobStatus = JobStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    attempt: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class SchedulerModule(RuntimeModule):
    """
    Scheduler module for job scheduling and execution.

    Supports:
    - One-time jobs (run_at)
    - Recurring jobs (cron expressions)
    - Interval jobs (fixed interval)
    - Delayed jobs (run after delay)
    - Job persistence and recovery
    - Backpressure handling
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="scheduler",
            version="1.0.0",
            description="Job scheduling with cron, interval, and one-time execution",
            author="AIPENSA",
            dependencies=["tool", "execution"],
            provides=["job_scheduling", "cron_execution", "interval_execution", "delayed_execution"],
            tags={"scheduler", "cron", "jobs", "automation"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._jobs: Dict[str, Job] = {}
        self._executions: Dict[str, JobExecution] = {}
        self._schedule_queue: SortedDict = SortedDict()  # next_run -> List[job_id]
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._execution_semaphore: Optional[asyncio.Semaphore] = None
        self._max_concurrent_jobs = config.get("max_concurrent_jobs", 10) if config else 10
        self._max_history = config.get("max_execution_history", 1000) if config else 1000
        self._default_timezone = config.get("timezone", "UTC") if config else "UTC"
        self._paused = False
        self._job_handlers: Dict[str, Callable] = {}

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize scheduler module."""
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._max_concurrent_jobs = self._config.get("max_concurrent_jobs", self._max_concurrent_jobs)
        self._max_history = self._config.get("max_execution_history", self._max_history)
        self._default_timezone = self._config.get("timezone", self._default_timezone)

        # Load persisted jobs
        persist_path = self._config.get("persist_path")
        if persist_path:
            await self._load_jobs(persist_path)

        # Initialize semaphore for concurrency control
        self._execution_semaphore = asyncio.Semaphore(self._max_concurrent_jobs)

        # Recalculate next runs for all jobs
        for job in self._jobs.values():
            if job.status == ScheduleStatus.ACTIVE:
                self._schedule_job(job)

        self.state = ModuleState.INITIALIZED
        logger.info(f"Scheduler module initialized with {len(self._jobs)} jobs")

    async def start(self) -> None:
        """Start scheduler."""
        self._running = True
        self._paused = False
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.state = ModuleState.RUNNING
        logger.info("Scheduler module started")

    async def stop(self) -> None:
        """Stop scheduler."""
        self._running = False
        self._paused = True

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        self.state = ModuleState.STOPPED
        logger.info("Scheduler module stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.stop()

        # Save jobs if persistence enabled
        persist_path = self._config.get("persist_path")
        if persist_path:
            await self._save_jobs(persist_path)

        self._jobs.clear()
        self._executions.clear()
        self._schedule_queue.clear()
        self._job_handlers.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("Scheduler module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        active_jobs = len([j for j in self._jobs.values() if j.status == ScheduleStatus.ACTIVE])
        running_executions = len([e for e in self._executions.values() if e.status == JobStatus.RUNNING])

        return {
            "module": "scheduler",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "total_jobs": len(self._jobs),
            "active_jobs": active_jobs,
            "paused_jobs": len([j for j in self._jobs.values() if j.status == ScheduleStatus.PAUSED]),
            "running_executions": running_executions,
            "total_executions": len(self._executions),
            "next_job": self._schedule_queue.iloc[0] if self._schedule_queue else None
        }

    # Job Management
    async def create_job(
        self,
        name: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        job_type: JobType = JobType.ONCE,
        run_at: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[float] = None,
        delay_seconds: Optional[float] = None,
        max_runs: Optional[int] = None,
        agent_type: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None
    ) -> Job:
        """Create a new scheduled job."""
        if len(self._jobs) >= 10000:  # Limit
            raise RuntimeError("Maximum jobs limit reached")

        job = Job(
            job_id=job_id or str(uuid.uuid4())[:8],
            name=name,
            action=action,
            parameters=parameters or {},
            job_type=job_type,
            run_at=run_at,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            delay_seconds=delay_seconds,
            max_runs=max_runs,
            agent_type=agent_type,
            tags=tags or [],
            metadata=metadata or {},
            timezone=self._default_timezone
        )

        self._jobs[job.job_id] = job

        if job.status == ScheduleStatus.ACTIVE:
            self._schedule_job(job)

        logger.info(f"Created job: {job.job_id} - {job.name} ({job.job_type.value})")
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    async def update_job(self, job: Job) -> Job:
        """Update a job."""
        if job.job_id not in self._jobs:
            raise ValueError(f"Job not found: {job.job_id}")

        old_job = self._jobs[job.job_id]
        # Unschedule old
        if old_job.status == ScheduleStatus.ACTIVE:
            self._unschedule_job(old_job)

        job.updated_at = datetime.utcnow()
        self._jobs[job.job_id] = job

        # Reschedule if active
        if job.status == ScheduleStatus.ACTIVE:
            self._schedule_job(job)

        logger.info(f"Updated job: {job.job_id}")
        return job

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        job = self._jobs.pop(job_id, None)
        if job:
            if job.status == ScheduleStatus.ACTIVE:
                self._unschedule_job(job)
            # Remove executions
            self._executions = {k: v for k, v in self._executions.items() if v.job_id != job_id}
            logger.info(f"Deleted job: {job_id}")
            return True
        return False

    async def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        job = self._jobs.get(job_id)
        if job and job.status == ScheduleStatus.ACTIVE:
            job.status = ScheduleStatus.PAUSED
            job.updated_at = datetime.utcnow()
            self._unschedule_job(job)
            logger.info(f"Paused job: {job_id}")
            return True
        return False

    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self._jobs.get(job_id)
        if job and job.status == ScheduleStatus.PAUSED:
            job.status = ScheduleStatus.ACTIVE
            job.updated_at = datetime.utcnow()
            self._schedule_job(job)
            logger.info(f"Resumed job: {job_id}")
            return True
        return False

    async def list_jobs(
        self,
        status: Optional[ScheduleStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """List jobs with filtering."""
        jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]

        if tags:
            jobs = [j for j in jobs if any(t in j.tags for t in tags)]

        # Sort by next_run, then created_at
        jobs.sort(key=lambda j: (j.next_run or datetime.max, j.created_at))

        return jobs[offset:offset + limit]

    async def trigger_job(self, job_id: str) -> JobExecution:
        """Manually trigger a job execution."""
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        return await self._execute_job(job)

    # Execution History
    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Get execution by ID."""
        return self._executions.get(execution_id)

    async def get_job_executions(
        self,
        job_id: str,
        limit: int = 50,
        status: Optional[JobStatus] = None
    ) -> List[JobExecution]:
        """Get executions for a job."""
        executions = [e for e in self._executions.values() if e.job_id == job_id]

        if status:
            executions = [e for e in executions if e.status == status]

        executions.sort(key=lambda e: e.started_at or datetime.min, reverse=True)
        return executions[:limit]

    async def get_recent_executions(
        self,
        limit: int = 100,
        status: Optional[JobStatus] = None,
        since: Optional[datetime] = None
    ) -> List[JobExecution]:
        """Get recent executions."""
        executions = list(self._executions.values())

        if status:
            executions = [e for e in executions if e.status == status]

        if since:
            executions = [e for e in executions if e.started_at and e.started_at >= since]

        executions.sort(key=lambda e: e.started_at or datetime.min, reverse=True)
        return executions[:limit]

    # Scheduler Control
    def pause_scheduler(self) -> None:
        """Pause all scheduling."""
        self._paused = True
        logger.info("Scheduler paused")

    def resume_scheduler(self) -> None:
        """Resume scheduling."""
        self._paused = False
        logger.info("Scheduler resumed")

    @property
    def is_paused(self) -> bool:
        return self._paused

    # Internal Scheduling
    def _schedule_job(self, job: Job) -> None:
        """Add job to schedule queue."""
        if job.next_run:
            if job.next_run not in self._schedule_queue:
                self._schedule_queue[job.next_run] = []
            self._schedule_queue[job.next_run].append(job.job_id)

    def _unschedule_job(self, job: Job) -> None:
        """Remove job from schedule queue."""
        if job.next_run and job.next_run in self._schedule_queue:
            if job.job_id in self._schedule_queue[job.next_run]:
                self._schedule_queue[job.next_run].remove(job.job_id)
                if not self._schedule_queue[job.next_run]:
                    del self._schedule_queue[job.next_run]

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                if self._paused:
                    await asyncio.sleep(1)
                    continue

                now = datetime.utcnow()

                # Get jobs due to run
                due_jobs = []
                while self._schedule_queue:
                    next_run_time = self._schedule_queue.iloc[0]
                    if next_run_time <= now:
                        job_ids = self._schedule_queue.pop(next_run_time)
                        for job_id in job_ids:
                            job = self._jobs.get(job_id)
                            if job and job.status == ScheduleStatus.ACTIVE:
                                due_jobs.append(job)
                    else:
                        break

                # Execute due jobs
                for job in due_jobs:
                    # Check max runs
                    if job.max_runs and job.run_count >= job.max_runs:
                        job.status = ScheduleStatus.COMPLETED
                        logger.info(f"Job completed max runs: {job.job_id}")
                        continue

                    # Execute job (with concurrency control)
                    asyncio.create_task(self._execute_job(job))

                # Calculate sleep time
                if self._schedule_queue:
                    next_run = self._schedule_queue.iloc[0]
                    sleep_seconds = (next_run - datetime.utcnow()).total_seconds()
                    sleep_seconds = max(0.1, min(sleep_seconds, 60))
                else:
                    sleep_seconds = 60

                await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5)

    async def _execute_job(self, job: Job) -> JobExecution:
        """Execute a job."""
        async with self._execution_semaphore:
            execution = JobExecution(
                job_id=job.job_id,
                job_name=job.name,
                status=JobStatus.RUNNING,
                started_at=datetime.utcnow(),
                attempt=job.run_count + 1
            )

            self._executions[execution.execution_id] = execution

            # Update job
            job.run_count += 1
            job.last_run = datetime.utcnow()

            try:
                logger.info(f"Executing job: {job.job_id} - {job.name}")

                # Execute action via tool module or handler
                result = await self._execute_action(job)

                execution.status = JobStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                execution.result = result

                job.last_result = result
                job.last_error = None

                # Schedule next run for recurring/interval jobs
                if job.job_type == JobType.RECURRING and job.cron_expression:
                    cron = croniter(job.cron_expression, datetime.utcnow())
                    job.next_run = cron.get_next(datetime)
                    self._schedule_job(job)
                elif job.job_type == JobType.INTERVAL and job.interval_seconds:
                    job.next_run = datetime.utcnow() + timedelta(seconds=job.interval_seconds)
                    self._schedule_job(job)
                elif job.job_type in (JobType.ONCE, JobType.DELAYED):
                    job.status = ScheduleStatus.COMPLETED
                    job.next_run = None

            except Exception as e:
                execution.status = JobStatus.FAILED
                execution.completed_at = datetime.utcnow()
                execution.error = str(e)

                job.last_error = str(e)

                # Retry logic could be added here
                if job.job_type in (JobType.RECURRING, JobType.INTERVAL):
                    # Schedule next run anyway
                    if job.job_type == JobType.RECURRING and job.cron_expression:
                        cron = croniter(job.cron_expression, datetime.utcnow())
                        job.next_run = cron.get_next(datetime)
                    elif job.job_type == JobType.INTERVAL and job.interval_seconds:
                        job.next_run = datetime.utcnow() + timedelta(seconds=job.interval_seconds)
                    self._schedule_job(job)
                else:
                    job.status = ScheduleStatus.DISABLED

                logger.error(f"Job execution failed: {job.job_id} - {e}")

            job.updated_at = datetime.utcnow()

            # Trim execution history
            if len(self._executions) > self._max_history:
                # Remove oldest completed executions
                completed = sorted(
                    [(k, v) for k, v in self._executions.items() if v.status in (JobStatus.COMPLETED, JobStatus.FAILED)],
                    key=lambda x: x[1].completed_at or datetime.min
                )
                for k, _ in completed[:len(completed)//10]:
                    del self._executions[k]

            return execution

    async def _execute_action(self, job: Job) -> Any:
        """Execute job action."""
        # Try custom handler first
        if job.action in self._job_handlers:
            handler = self._job_handlers[job.action]
            if asyncio.iscoroutinefunction(handler):
                return await handler(job.parameters)
            else:
                return handler(job.parameters)

        # Try tool module
        tool_module = self._runtime.modules.get("tool")
        if tool_module:
            return await tool_module.execute("execute_tool", tool_name=job.action, arguments=job.parameters)

        # Try execution module
        execution_module = self._runtime.modules.get("execution")
        if execution_module:
            if job.action.startswith("python:"):
                code = job.parameters.get("code", job.action[7:])
                return await execution_module.execute("execute_python", code=code)
            elif job.action.startswith("shell:"):
                command = job.parameters.get("command", job.action[6:])
                return await execution_module.execute("execute_shell", command=command)

        raise ValueError(f"No handler for action: {job.action}")

    def register_job_handler(self, action: str, handler: Callable) -> None:
        """Register a custom job handler."""
        self._job_handlers[action] = handler

    def unregister_job_handler(self, action: str) -> bool:
        """Unregister a job handler."""
        if action in self._job_handlers:
            del self._job_handlers[action]
            return True
        return False

    # Persistence
    async def _load_jobs(self, path: str) -> None:
        """Load jobs from disk."""
        import os
        import aiofiles
        import json

        if not os.path.exists(path):
            return

        try:
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    filepath = os.path.join(path, filename)
                    async with aiofiles.open(filepath, 'r') as f:
                        content = await f.read()
                        data = json.loads(content)

                        job = Job(
                            job_id=data.get("job_id", str(uuid.uuid4())[:8]),
                            name=data.get("name", ""),
                            description=data.get("description", ""),
                            job_type=JobType(data.get("job_type", "once")),
                            action=data.get("action", ""),
                            parameters=data.get("parameters", {}),
                            agent_type=data.get("agent_type", "default"),
                            cron_expression=data.get("cron_expression"),
                            interval_seconds=data.get("interval_seconds"),
                            run_at=datetime.fromisoformat(data["run_at"]) if data.get("run_at") else None,
                            delay_seconds=data.get("delay_seconds"),
                            timezone=data.get("timezone", "UTC"),
                            max_runs=data.get("max_runs"),
                            run_count=data.get("run_count", 0),
                            status=ScheduleStatus(data.get("status", "active")),
                            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
                            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
                            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None,
                            last_run=datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None,
                            last_result=data.get("last_result"),
                            last_error=data.get("last_error"),
                            tags=data.get("tags", []),
                            metadata=data.get("metadata", {})
                        )

                        self._jobs[job.job_id] = job

            logger.info(f"Loaded {len(self._jobs)} jobs from {path}")
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")

    async def _save_jobs(self, path: str) -> None:
        """Save jobs to disk."""
        import os
        import aiofiles
        import json

        os.makedirs(path, exist_ok=True)

        try:
            for job in self._jobs.values():
                data = {
                    "job_id": job.job_id,
                    "name": job.name,
                    "description": job.description,
                    "job_type": job.job_type.value,
                    "action": job.action,
                    "parameters": job.parameters,
                    "agent_type": job.agent_type,
                    "cron_expression": job.cron_expression,
                    "interval_seconds": job.interval_seconds,
                    "run_at": job.run_at.isoformat() if job.run_at else None,
                    "delay_seconds": job.delay_seconds,
                    "timezone": job.timezone,
                    "max_runs": job.max_runs,
                    "run_count": job.run_count,
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                    "next_run": job.next_run.isoformat() if job.next_run else None,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "last_result": job.last_result,
                    "last_error": job.last_error,
                    "tags": job.tags,
                    "metadata": job.metadata
                }

                filepath = os.path.join(path, f"{job.job_id}.json")
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(json.dumps(data, indent=2, default=str))

            logger.info(f"Saved {len(self._jobs)} jobs to {path}")
        except Exception as e:
            logger.error(f"Failed to save jobs: {e}")

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "create_job":
            return await self.create_job(**kwargs)
        elif operation == "get_job":
            return await self.get_job(kwargs.get("job_id"))
        elif operation == "update_job":
            return await self.update_job(kwargs.get("job"))
        elif operation == "delete_job":
            return await self.delete_job(kwargs.get("job_id"))
        elif operation == "pause_job":
            return await self.pause_job(kwargs.get("job_id"))
        elif operation == "resume_job":
            return await self.resume_job(kwargs.get("job_id"))
        elif operation == "list_jobs":
            return await self.list_jobs(**kwargs)
        elif operation == "trigger_job":
            return await self.trigger_job(kwargs.get("job_id"))
        elif operation == "get_execution":
            return await self.get_execution(kwargs.get("execution_id"))
        elif operation == "get_job_executions":
            return await self.get_job_executions(**kwargs)
        elif operation == "get_recent_executions":
            return await self.get_recent_executions(**kwargs)
        elif operation == "pause_scheduler":
            self.pause_scheduler()
            return True
        elif operation == "resume_scheduler":
            self.resume_scheduler()
            return True
        elif operation == "register_handler":
            self.register_job_handler(kwargs.get("action"), kwargs.get("handler"))
            return True
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "SchedulerModule",
    "Job",
    "JobExecution",
    "JobStatus",
    "JobType",
    "ScheduleStatus",
]