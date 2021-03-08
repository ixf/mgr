from typing import Any

class Debouncer:
    """ receives Reads through put() and outputs next element.
        If last 2 objects
        are the same, then it outputs nothing, e.g.
        "123 4455 678 99" -> "123 45 678 9"
        per pid.
    """
    pasts: 'dict[int, Any]' = {}

    def put(self, pid: int, thing: Any) -> bool:
        past = self.pasts.get(pid)
        same = past == thing
        self.pasts[pid] = thing
        return same

