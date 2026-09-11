#!/usr/bin/env python3
"""Run the FairSense AgentiX backend (thin wrapper kept for backwards compatibility).

Equivalent to ``python -m fairsense_agentix.service_api``.
"""

import sys

from fairsense_agentix.service_api.__main__ import main


if __name__ == "__main__":
    sys.exit(main())
