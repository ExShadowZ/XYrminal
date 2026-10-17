"""
Modem status lines for serial ports.

These are INPUT lines from the modem/device's point of view — the
DCE side drives them, the DTE (our app) reads them:

    CD  — Carrier Detect
    RI  — Ring Indicator
    DSR — Data Set Ready
    CTS — Clear To Send

Note: DTR and RTS go the other way (outputs from our side) and are
handled separately in ConnectingGroup as ToggleButton's.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModemLines:
    cd:  bool = False
    ri:  bool = False
    dsr: bool = False
    cts: bool = False

    def as_tuple(self) -> tuple[bool, bool, bool, bool]:
        return (self.cd, self.ri, self.dsr, self.cts)

    def __eq__(self, other) -> bool:
        if not isinstance(other, ModemLines):
            return NotImplemented
        return self.as_tuple() == other.as_tuple()