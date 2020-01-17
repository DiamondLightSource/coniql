class GenericScannable:
    """A beamline implementing this feature can run a scan using a
    ScanPointGenerator"""
    async def scan(self, scan_model) -> None:
        return NotImplemented


class GridScannable:
    """A beamline implementing this feature can run an optimized grid scan at
    >10kHz"""
    async def grid_scan(self, scan_model) -> None:
        return NotImplemented
