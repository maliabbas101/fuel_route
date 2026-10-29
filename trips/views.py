from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import planner
from .constants import CONTIGUOUS_USA_BOUNDS
from .exceptions import NoFeasiblePlanError, RoutingError
from .serializers import TripRequestSerializer


def trip_map(request):
    return render(request, "trips/map.html", {"bounds": CONTIGUOUS_USA_BOUNDS})


class TripPlanView(APIView):
    def post(self, request):
        serializer = TripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.validated_data

        try:
            plan = planner.plan_trip(
                trip["start"], trip["finish"], trip["initial_fuel_gallons"]
            )
        except RoutingError as exc:
            return Response({"detail": str(exc)}, status=exc.status)
        except NoFeasiblePlanError as exc:
            return Response(
                {
                    **exc.route_summary,
                    "error": "NO_FEASIBLE_FUEL_PLAN",
                    "detail": str(exc),
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(plan)
