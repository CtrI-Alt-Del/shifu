from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class BetterAuthRateLimitModel(Model):
    __tablename__ = 'better_auth_rate_limits'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='pk_better_auth_rate_limits'),
        UniqueConstraint('key', name='uq_better_auth_rate_limits_key'),
        CheckConstraint('count >= 0', name='ck_better_auth_rate_limits_count'),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_request: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text('(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) * 1000)::bigint'),
    )
