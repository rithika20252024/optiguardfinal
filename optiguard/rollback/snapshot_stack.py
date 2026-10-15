"""Transactional Snapshot Stack for OptiGuard Rollback Engine.

Provides a push/pop interface to atomically commit or revert IR state
during the adaptive optimization loop.

Usage:
    stack = SnapshotStack()
    stack.push(current_ir)          # checkpoint before applying a pass
    new_ir = apply_pass(current_ir)
    if degraded(new_ir):
        current_ir = stack.pop()    # ROLLBACK to prior stable state
    else:
        stack.commit()              # accept new_ir, discard snapshot
"""

from typing import List, Optional
from optiguard.ir.tac import TACProgram


class SnapshotStack:
    """Atomic IR snapshot stack supporting transactional rollback.

    Each `push` creates a deep clone of the supplied TACProgram and
    stores it on a LIFO stack.  `pop` restores the most-recent snapshot.
    `commit` discards the topmost snapshot without restoring it.
    """

    def __init__(self) -> None:
        self._stack: List[TACProgram] = []

    def push(self, ir: TACProgram) -> None:
        """Checkpoint: save a deep-copy snapshot of *ir*."""
        self._stack.append(ir.clone())

    def pop(self) -> TACProgram:
        """ROLLBACK: restore and return the most-recent snapshot.

        Raises:
            IndexError: if the stack is empty (no checkpoint was made).
        """
        if not self._stack:
            raise IndexError("SnapshotStack is empty — no snapshot to restore.")
        return self._stack.pop()

    def commit(self) -> None:
        """COMMIT: discard the topmost snapshot (optimization accepted)."""
        if self._stack:
            self._stack.pop()

    def peek(self) -> Optional[TACProgram]:
        """Return the topmost snapshot without removing it (or None if empty)."""
        return self._stack[-1] if self._stack else None

    def depth(self) -> int:
        """Return the current number of saved snapshots."""
        return len(self._stack)

    def clear(self) -> None:
        """Discard all snapshots."""
        self._stack.clear()
