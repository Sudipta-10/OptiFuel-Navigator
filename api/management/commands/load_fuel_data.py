import csv
import time
from django.core.management.base import BaseCommand
from api.models import FuelStation
from api.services.geocoder import geocode

class Command(BaseCommand):
    help = 'Load fuel stations from CSV and geocode'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to CSV file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file']
        
        # To avoid geocoding the same city/state repeatedly
        location_cache = {}
        
        # Read the CSV to get the cheapest price per OPIS ID
        stations_dict = {}
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                opis_id = int(row['OPIS Truckstop ID'])
                price = float(row['Retail Price'])
                if opis_id not in stations_dict or price < stations_dict[opis_id]['price']:
                    stations_dict[opis_id] = {
                        'name': row['Truckstop Name'],
                        'address': row['Address'],
                        'city': row['City'],
                        'state': row['State'],
                        'rack_id': int(row['Rack ID']),
                        'price': price
                    }
        
        self.stdout.write(f'Parsed {len(stations_dict)} unique stations')
        
        bulk_list = []
        count = 0
        for opis_id, data in stations_dict.items():
            loc_str = f"{data['city']}, {data['state']}, USA"
            if loc_str not in location_cache:
                try:
                    lat, lon = geocode(loc_str)
                    location_cache[loc_str] = (lat, lon)
                    time.sleep(1.1)  # respect Nominatim 1 req/sec rate limit
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed to geocode {loc_str}: {e}"))
                    continue
                    
            lat, lon = location_cache[loc_str]
            bulk_list.append(FuelStation(
                opis_id=opis_id,
                name=data['name'],
                address=data['address'],
                city=data['city'],
                state=data['state'],
                rack_id=data['rack_id'],
                retail_price=data['price'],
                latitude=lat,
                longitude=lon
            ))
            
            count += 1
            if count % 100 == 0:
                self.stdout.write(f"Processed {count} stations")
                
        FuelStation.objects.all().delete()
        FuelStation.objects.bulk_create(bulk_list)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(bulk_list)} stations'))
