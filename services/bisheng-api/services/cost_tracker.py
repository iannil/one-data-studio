"""
ONE-DATA-STUDIO Token Cost Tracker
Sprint 32: Developer Experience Optimization

Tracks token usage and costs for LLM/Agent executions.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
from collections import defaultdict
import threading
import json

logger = logging.getLogger(__name__)

# Try importing tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, using approximate token counting")


class ModelProvider(Enum):
    """Supported model providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"  # vLLM, TGI, etc.
    AZURE = "azure"
    CUSTOM = "custom"


@dataclass
class ModelPricing:
    """Pricing per 1M tokens"""
    input_price: float  # per 1M input tokens
    output_price: float  # per 1M output tokens
    currency: str = "USD"

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given token counts"""
        input_cost = (input_tokens / 1_000_000) * self.input_price
        output_cost = (output_tokens / 1_000_000) * self.output_price
        return round(input_cost + output_cost, 6)


# Default pricing (as of 2024)
DEFAULT_PRICING: Dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4o": ModelPricing(input_price=5.0, output_price=15.0),
    "gpt-4o-mini": ModelPricing(input_price=0.15, output_price=0.6),
    "gpt-4-turbo": ModelPricing(input_price=10.0, output_price=30.0),
    "gpt-4": ModelPricing(input_price=30.0, output_price=60.0),
    "gpt-3.5-turbo": ModelPricing(input_price=0.5, output_price=1.5),
    # Anthropic
    "claude-3-opus": ModelPricing(input_price=15.0, output_price=75.0),
    "claude-3-sonnet": ModelPricing(input_price=3.0, output_price=15.0),
    "claude-3-haiku": ModelPricing(input_price=0.25, output_price=1.25),
    "claude-3.5-sonnet": ModelPricing(input_price=3.0, output_price=15.0),
    # Local models (free but track for resource usage)
    "local": ModelPricing(input_price=0.0, output_price=0.0),
    "vllm": ModelPricing(input_price=0.0, output_price=0.0),
}


@dataclass
class TokenUsage:
    """Token usage for a single call"""
    input_tokens: int
    output_tokens: int
    total_tokens: int

    @classmethod
    def from_response(cls, response: Dict[str, Any]) -> "TokenUsage":
        """Extract token usage from API response"""
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )


@dataclass
class CostRecord:
    """Record of a single cost event"""
    id: str
    timestamp: datetime
    user_id: str
    tenant_id: str
    workflow_id: Optional[str]
    agent_id: Optional[str]
    model: str
    provider: ModelProvider
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    currency: str
    execution_time_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider.value,
        }


@dataclass
class CostSummary:
    """Aggregated cost summary"""
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    call_count: int
    avg_cost_per_call: float
    avg_tokens_per_call: float
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_user: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_workflow: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    currency: str = "USD"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


class TokenCounter:
    """Token counting utilities"""

    _encoders: Dict[str, Any] = {}
    _lock = threading.Lock()

    @classmethod
    def count_tokens(cls, text: str, model: str = "gpt-4") -> int:
        """
        Count tokens in text for a given model

        Args:
            text: Text to count tokens for
            model: Model name (affects encoding)

        Returns:
            Number of tokens
        """
        if not TIKTOKEN_AVAILABLE:
            # Approximate: ~4 chars per token for English
            return len(text) // 4

        try:
            encoder = cls._get_encoder(model)
            return len(encoder.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            return len(text) // 4

    @classmethod
    def count_messages(
        cls,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
    ) -> int:
        """Count tokens in a list of messages"""
        total = 0
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")
            # Add overhead for message structure
            total += cls.count_tokens(content, model) + 4
            total += cls.count_tokens(role, model)
        return total + 2  # Add priming tokens

    @classmethod
    def _get_encoder(cls, model: str):
        """Get or create encoder for model"""
        if not TIKTOKEN_AVAILABLE:
            return None

        with cls._lock:
            if model not in cls._encoders:
                try:
                    cls._encoders[model] = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Fall back to cl100k_base for unknown models
                    cls._encoders[model] = tiktoken.get_encoding("cl100k_base")
            return cls._encoders[model]


class CostTracker:
    """
    Tracks and manages token costs across the system

    Usage:
        tracker = CostTracker()

        # Record usage
        tracker.record_usage(
            user_id="user-123",
            tenant_id="tenant-456",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            workflow_id="wf-789",
        )

        # Get summary
        summary = tracker.get_summary(
            tenant_id="tenant-456",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Check budget
        if tracker.check_budget("tenant-456", limit=100.0):
            # Proceed with execution
            pass
    """

    def __init__(
        self,
        db_session=None,
        pricing: Optional[Dict[str, ModelPricing]] = None,
    ):
        self.session = db_session
        self.pricing = pricing or DEFAULT_PRICING
        self._records: List[CostRecord] = []
        self._lock = threading.Lock()
        self._batch_queue: List[CostRecord] = []
        self._batch_size = 100
        self._record_counter = 0

    def record_usage(
        self,
        user_id: str,
        tenant_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: ModelProvider = ModelProvider.OPENAI,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        execution_time_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CostRecord:
        """
        Record token usage and calculate cost

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            provider: Model provider
            workflow_id: Optional workflow identifier
            agent_id: Optional agent identifier
            execution_time_ms: Execution time in milliseconds
            metadata: Additional metadata

        Returns:
            Created CostRecord
        """
        # Calculate cost
        pricing = self.pricing.get(model, ModelPricing(0, 0))
        cost = pricing.calculate_cost(input_tokens, output_tokens)

        # Create record
        with self._lock:
            self._record_counter += 1
            record_id = f"cost-{int(time.time() * 1000)}-{self._record_counter}"

        record = CostRecord(
            id=record_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            currency=pricing.currency,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )

        # Store record
        self._store_record(record)

        logger.debug(
            f"Recorded usage: model={model}, tokens={record.total_tokens}, cost=${cost:.6f}"
        )
        return record

    def get_summary(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """
        Get aggregated cost summary

        Args:
            tenant_id: Filter by tenant
            user_id: Filter by user
            workflow_id: Filter by workflow
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            CostSummary with aggregated data
        """
        records = self._query_records(
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_id=workflow_id,
            start_date=start_date,
            end_date=end_date,
        )

        if not records:
            return CostSummary(
                total_cost=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_tokens=0,
                call_count=0,
                avg_cost_per_call=0,
                avg_tokens_per_call=0,
                period_start=start_date,
                period_end=end_date,
            )

        # Aggregate
        total_cost = sum(r.cost for r in records)
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_tokens = sum(r.total_tokens for r in records)
        call_count = len(records)

        # Group by model
        by_model: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"cost": 0, "tokens": 0, "calls": 0}
        )
        for r in records:
            by_model[r.model]["cost"] += r.cost
            by_model[r.model]["tokens"] += r.total_tokens
            by_model[r.model]["calls"] += 1

        # Group by user
        by_user: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"cost": 0, "tokens": 0, "calls": 0}
        )
        for r in records:
            by_user[r.user_id]["cost"] += r.cost
            by_user[r.user_id]["tokens"] += r.total_tokens
            by_user[r.user_id]["calls"] += 1

        # Group by workflow
        by_workflow: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"cost": 0, "tokens": 0, "calls": 0}
        )
        for r in records:
            if r.workflow_id:
                by_workflow[r.workflow_id]["cost"] += r.cost
                by_workflow[r.workflow_id]["tokens"] += r.total_tokens
                by_workflow[r.workflow_id]["calls"] += 1

        return CostSummary(
            total_cost=round(total_cost, 6),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            call_count=call_count,
            avg_cost_per_call=round(total_cost / call_count, 6) if call_count else 0,
            avg_tokens_per_call=round(total_tokens / call_count, 2) if call_count else 0,
            by_model=dict(by_model),
            by_user=dict(by_user),
            by_workflow=dict(by_workflow),
            period_start=start_date or min(r.timestamp for r in records),
            period_end=end_date or max(r.timestamp for r in records),
        )

    def check_budget(
        self,
        tenant_id: str,
        limit: float,
        period_days: int = 30,
    ) -> bool:
        """
        Check if tenant is within budget

        Args:
            tenant_id: Tenant identifier
            limit: Budget limit in USD
            period_days: Period to check (default 30 days)

        Returns:
            True if within budget, False if exceeded
        """
        start_date = datetime.utcnow() - timedelta(days=period_days)
        summary = self.get_summary(tenant_id=tenant_id, start_date=start_date)
        return summary.total_cost < limit

    def get_remaining_budget(
        self,
        tenant_id: str,
        limit: float,
        period_days: int = 30,
    ) -> float:
        """Get remaining budget for tenant"""
        start_date = datetime.utcnow() - timedelta(days=period_days)
        summary = self.get_summary(tenant_id=tenant_id, start_date=start_date)
        return max(0, limit - summary.total_cost)

    def get_daily_breakdown(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get daily cost breakdown"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        records = self._query_records(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Group by date
        by_date: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"cost": 0, "tokens": 0, "calls": 0}
        )
        for r in records:
            date_str = r.timestamp.strftime("%Y-%m-%d")
            by_date[date_str]["cost"] += r.cost
            by_date[date_str]["tokens"] += r.total_tokens
            by_date[date_str]["calls"] += 1

        # Fill in missing dates
        result = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            data = by_date.get(date_str, {"cost": 0, "tokens": 0, "calls": 0})
            result.append({
                "date": date_str,
                **data,
            })
            current += timedelta(days=1)

        return result

    def _store_record(self, record: CostRecord):
        """Store record (batch for database)"""
        with self._lock:
            self._records.append(record)
            self._batch_queue.append(record)

            if len(self._batch_queue) >= self._batch_size:
                self._flush_batch()

    def _flush_batch(self):
        """Flush batch to database"""
        if not self._batch_queue:
            return

        if self.session:
            try:
                self._persist_batch(self._batch_queue)
            except Exception as e:
                logger.error(f"Failed to persist cost records: {e}")

        self._batch_queue = []

    def _persist_batch(self, records: List[CostRecord]):
        """Persist batch to database"""
        try:
            from sqlalchemy import text

            for record in records:
                self.session.execute(
                    text("""
                        INSERT INTO cost_records
                        (id, timestamp, user_id, tenant_id, workflow_id, agent_id,
                         model, provider, input_tokens, output_tokens, total_tokens,
                         cost, currency, execution_time_ms, metadata)
                        VALUES
                        (:id, :timestamp, :user_id, :tenant_id, :workflow_id, :agent_id,
                         :model, :provider, :input_tokens, :output_tokens, :total_tokens,
                         :cost, :currency, :execution_time_ms, :metadata)
                    """),
                    {
                        "id": record.id,
                        "timestamp": record.timestamp,
                        "user_id": record.user_id,
                        "tenant_id": record.tenant_id,
                        "workflow_id": record.workflow_id,
                        "agent_id": record.agent_id,
                        "model": record.model,
                        "provider": record.provider.value,
                        "input_tokens": record.input_tokens,
                        "output_tokens": record.output_tokens,
                        "total_tokens": record.total_tokens,
                        "cost": record.cost,
                        "currency": record.currency,
                        "execution_time_ms": record.execution_time_ms,
                        "metadata": json.dumps(record.metadata),
                    }
                )
            self.session.commit()
        except Exception as e:
            logger.error(f"Database persist failed: {e}")
            self.session.rollback()
            raise

    def _query_records(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CostRecord]:
        """Query records with filters"""
        # Try database first
        if self.session:
            try:
                return self._query_database(
                    tenant_id, user_id, workflow_id, start_date, end_date
                )
            except Exception as e:
                logger.warning(f"Database query failed: {e}")

        # Fall back to in-memory
        with self._lock:
            records = self._records.copy()

        # Apply filters
        if tenant_id:
            records = [r for r in records if r.tenant_id == tenant_id]
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        if workflow_id:
            records = [r for r in records if r.workflow_id == workflow_id]
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]

        return records

    def _query_database(
        self,
        tenant_id: Optional[str],
        user_id: Optional[str],
        workflow_id: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[CostRecord]:
        """Query records from database"""
        from sqlalchemy import text

        conditions = []
        params = {}

        if tenant_id:
            conditions.append("tenant_id = :tenant_id")
            params["tenant_id"] = tenant_id
        if user_id:
            conditions.append("user_id = :user_id")
            params["user_id"] = user_id
        if workflow_id:
            conditions.append("workflow_id = :workflow_id")
            params["workflow_id"] = workflow_id
        if start_date:
            conditions.append("timestamp >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("timestamp <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        result = self.session.execute(
            text(f"""
                SELECT id, timestamp, user_id, tenant_id, workflow_id, agent_id,
                       model, provider, input_tokens, output_tokens, total_tokens,
                       cost, currency, execution_time_ms, metadata
                FROM cost_records
                WHERE {where_clause}
                ORDER BY timestamp DESC
            """),
            params
        )

        records = []
        for row in result:
            records.append(CostRecord(
                id=row.id,
                timestamp=row.timestamp,
                user_id=row.user_id,
                tenant_id=row.tenant_id,
                workflow_id=row.workflow_id,
                agent_id=row.agent_id,
                model=row.model,
                provider=ModelProvider(row.provider),
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                total_tokens=row.total_tokens,
                cost=row.cost,
                currency=row.currency,
                execution_time_ms=row.execution_time_ms,
                metadata=json.loads(row.metadata) if row.metadata else {},
            ))
        return records


def track_cost(
    model: str,
    user_id_param: str = "user_id",
    tenant_id_param: str = "tenant_id",
    workflow_id_param: str = "workflow_id",
):
    """
    Decorator to track costs of LLM calls

    Usage:
        @track_cost(model="gpt-4o", user_id_param="user_id")
        async def generate_response(user_id: str, tenant_id: str, prompt: str):
            response = await llm.generate(prompt)
            return response
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            # Extract IDs from kwargs
            user_id = kwargs.get(user_id_param, "unknown")
            tenant_id = kwargs.get(tenant_id_param, "unknown")
            workflow_id = kwargs.get(workflow_id_param)

            # Execute function
            result = await func(*args, **kwargs)

            # Extract token usage from result
            execution_time_ms = int((time.time() - start_time) * 1000)

            if isinstance(result, dict) and "usage" in result:
                usage = TokenUsage.from_response(result)

                # Get global tracker
                tracker = get_cost_tracker()
                tracker.record_usage(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    model=model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    workflow_id=workflow_id,
                    execution_time_ms=execution_time_ms,
                )

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            user_id = kwargs.get(user_id_param, "unknown")
            tenant_id = kwargs.get(tenant_id_param, "unknown")
            workflow_id = kwargs.get(workflow_id_param)

            result = func(*args, **kwargs)

            execution_time_ms = int((time.time() - start_time) * 1000)

            if isinstance(result, dict) and "usage" in result:
                usage = TokenUsage.from_response(result)

                tracker = get_cost_tracker()
                tracker.record_usage(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    model=model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    workflow_id=workflow_id,
                    execution_time_ms=execution_time_ms,
                )

            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Global tracker instance
_cost_tracker: Optional[CostTracker] = None
_tracker_lock = threading.Lock()


def get_cost_tracker(session=None) -> CostTracker:
    """Get global CostTracker instance"""
    global _cost_tracker
    with _tracker_lock:
        if _cost_tracker is None:
            _cost_tracker = CostTracker(db_session=session)
    return _cost_tracker


def set_cost_tracker(tracker: CostTracker):
    """Set global CostTracker instance"""
    global _cost_tracker
    with _tracker_lock:
        _cost_tracker = tracker
