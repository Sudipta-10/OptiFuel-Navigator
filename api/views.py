from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.geocoder import geocode
from .services.router import get_route
from .services.fuel_optimizer import optimize_fuel_stops
from .models import FuelStation

class RouteView(APIView):
    def post(self, request):
        start = request.data.get('start')
        finish = request.data.get('finish')
        
        if not start or not finish:
            return Response({"error": "Start and finish are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            start_ll = geocode(start)
            finish_ll = geocode(finish)
        except Exception as e:
            return Response({"error": f"Geocoding error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            route_data = get_route(start_ll, finish_ll)
        except Exception as e:
            return Response({"error": f"Routing error: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        stations = FuelStation.objects.all()
        try:
            stops, summary = optimize_fuel_stops(route_data, stations)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
        response_data = {
            "route": {
                "total_distance_miles": round(route_data['distance_miles'], 2),
                "encoded_polyline": route_data['encoded_polyline'],
                "geojson": {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in route_data['waypoints']]
                }
            },
            "fuel_stops": stops,
            "summary": summary
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
