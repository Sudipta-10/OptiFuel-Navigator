from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.geocoder import geocode
from .services.router import get_route
from .services.fuel_optimizer import optimize_fuel_stops
from .models import FuelStation
from rest_framework.parsers import MultiPartParser, FormParser
import threading
import os
from django.core.management import call_command
from django.conf import settings

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

class UploadCSVView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Save the file to the project root
        file_path = os.path.join(settings.BASE_DIR, 'uploaded_fuel_prices.csv')
        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
                
        # Run the management command in a background thread so we don't block the UI
        def run_loader():
            try:
                call_command('load_fuel_data', file=file_path)
            except Exception as e:
                print(f"Error loading CSV in background: {e}")
                
        thread = threading.Thread(target=run_loader)
        thread.daemon = True
        thread.start()

        return Response({"message": "File uploaded successfully! Data is now being processed in the background."}, status=status.HTTP_200_OK)
