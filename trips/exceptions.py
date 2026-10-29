class RoutingError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


class NoFeasiblePlanError(Exception):
    def __init__(self, message, route_summary=None):
        super().__init__(message)
        self.route_summary = route_summary or {}
