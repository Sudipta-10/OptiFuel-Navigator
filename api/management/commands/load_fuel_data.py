import csv
import time
from django.core.management.base import BaseCommand
from django.core.cache import cache
from api.models import FuelStation
import pgeocode
import pandas as pd

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
        with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
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
        
        cache.set('upload_status', 'processing', timeout=3600)
        cache.set('upload_total', len(stations_dict), timeout=3600)
        cache.set('upload_progress', 0, timeout=3600)
        
        # Initialize offline geocoders
        nom_us = pgeocode.Nominatim('us')
        nom_ca = pgeocode.Nominatim('ca')
        nom_in = pgeocode.Nominatim('in')
        
        def local_geocode(city, state):
            res = nom_us.query_location(city)
            if not res.empty:
                if 'state_code' in res.columns:
                    match = res[res['state_code'] == state]
                    if not match.empty:
                        return float(match.iloc[0]['latitude']), float(match.iloc[0]['longitude'])
                
            res_ca = nom_ca.query_location(city)
            if not res_ca.empty:
                if 'state_code' in res_ca.columns:
                    match = res_ca[res_ca['state_code'] == state]
                    if not match.empty:
                        return float(match.iloc[0]['latitude']), float(match.iloc[0]['longitude'])
                        
            res_in = nom_in.query_location(city)
            if not res_in.empty:
                return float(res_in.iloc[0]['latitude']), float(res_in.iloc[0]['longitude'])

            # Fallbacks
            if not res.empty:
                return float(res.iloc[0]['latitude']), float(res.iloc[0]['longitude'])
            if not res_ca.empty:
                return float(res_ca.iloc[0]['latitude']), float(res_ca.iloc[0]['longitude'])
                
            raise ValueError("Location not found")
        
        bulk_list = []
        count = 0
        
        # Fetch existing IDs to prevent duplicates
        existing_ids = set(FuelStation.objects.values_list('opis_id', flat=True))
        
        for opis_id, data in stations_dict.items():
            if opis_id in existing_ids:
                continue
                
            loc_str = f"{data['city']}, {data['state']}"
            if loc_str not in location_cache:
                try:
                    lat, lon = local_geocode(data['city'], data['state'])
                    if pd.isna(lat) or pd.isna(lon):
                        raise ValueError("NaN returned")
                    location_cache[loc_str] = (lat, lon)
                except Exception as e:
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
            if count % 10 == 0:
                cache.set('upload_progress', count, timeout=3600)
            if count % 100 == 0:
                self.stdout.write(f"Processed {count} stations")
                
        if bulk_list:
            FuelStation.objects.bulk_create(bulk_list)
            self.stdout.write(self.style.SUCCESS(f'Successfully appended {len(bulk_list)} new stations'))
        else:
            self.stdout.write(self.style.SUCCESS('No new stations to add (all were duplicates).'))
            
        cache.set('upload_status', 'completed', timeout=3600)
        cache.set('upload_progress', len(stations_dict), timeout=3600)
