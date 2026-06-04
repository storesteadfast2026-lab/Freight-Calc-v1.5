from decimal import Decimal, InvalidOperation
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from openpyxl import load_workbook
from apps.clients.models import Client, FreightCalculator
from apps.locations.models import Suburb, FromAddress
from apps.products.models import Product
from apps.carriers.models import Carrier, CarrierService, ClientCarrierConfig
from apps.rates.models import FreightZone, FreightRate, CarrierTailgateCharge
from apps.imports.models import ExternalDataFile


def d(value, default='0'):
    if value in (None, ''):
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def s(value):
    return str(value or '').strip()


class Command(BaseCommand):
    help = 'Import main STH workbook sheets into PostgreSQL staging tables.'

    def add_arguments(self, parser):
        parser.add_argument('workbook_path')
        parser.add_argument('--client', default='STH')

    def handle(self, *args, **options):
        path = Path(options['workbook_path'])
        if not path.exists():
            raise CommandError(f'Workbook not found: {path}')

        client, _ = Client.objects.get_or_create(code=options['client'], defaults={'name': 'Stenhoj Australia'})
        FreightCalculator.objects.get_or_create(client=client, name='STH Freight Calculator', version='V2026.R2')
        FromAddress.objects.get_or_create(client=client, name='Default STH FROM', defaults={'suburb': '', 'state': '', 'postcode': '', 'is_default': True})

        wb = load_workbook(path, data_only=False, read_only=True)
        summary = {}
        summary['suburbs'] = self.import_suburbs(wb, client)
        summary['products'] = self.import_products(wb, client)
        summary['carriers'] = self.import_carriers(wb, client)
        summary['zones'] = self.import_zones(wb, client)
        summary['rates'] = self.import_rates(wb, client)
        summary['tailgate'] = self.import_tailgate(wb, client)

        ExternalDataFile.objects.create(
            client=client,
            file_type='WORKBOOK',
            original_filename=path.name,
            stored_path=str(path),
            status='IMPORTED',
            last_imported_at=timezone.now(),
            import_summary=summary,
        )
        self.stdout.write(self.style.SUCCESS(f'Imported workbook for {client.code}: {summary}'))

    def import_suburbs(self, wb, client):
        if 'SUBURBS' not in wb.sheetnames:
            return 0
        ws = wb['SUBURBS']
        count = 0
        # Evidence: SUBURBS columns D/E/F contain state/suburb/postcode in prior analysis.
        for row in ws.iter_rows(min_row=2, values_only=True):
            state, suburb, postcode = s(row[3] if len(row) > 3 else ''), s(row[4] if len(row) > 4 else ''), s(row[5] if len(row) > 5 else '')
            if not state or not suburb or not postcode:
                continue
            Suburb.objects.update_or_create(suburb_name=suburb, state=state, postcode=postcode, defaults={'normalized_key': f'{state}{suburb}'.upper().strip()})
            count += 1
        return count

    def import_products(self, wb, client):
        if 'SKUs' not in wb.sheetnames:
            return 0
        ws = wb['SKUs']
        count = 0
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            sku = s(row[0] if len(row) > 0 else '')
            if not sku:
                continue
            name = s(row[1] if len(row) > 1 else '') or s(row[2] if len(row) > 2 else '')
            # From Excel analysis: SKULISTFULL col 5:9 are dimensions/weight/cubic, col 10 type.
            Product.objects.update_or_create(
                client=client,
                sku=sku,
                defaults={
                    'name': name,
                    'length_m': d(row[4] if len(row) > 4 else 0),
                    'width_m': d(row[5] if len(row) > 5 else 0),
                    'height_m': d(row[6] if len(row) > 6 else 0),
                    'weight_kg': d(row[7] if len(row) > 7 else 0),
                    'cubic_m3': d(row[8] if len(row) > 8 else 0),
                    'freight_type': (s(row[9] if len(row) > 9 else 'P') or 'P')[:1],
                    'source_row': idx,
                    'active': True,
                }
            )
            count += 1
        return count

    def _carrier_service(self, carrier_code, service_code):
        carrier, _ = Carrier.objects.get_or_create(code=carrier_code, defaults={'name': carrier_code})
        service, _ = CarrierService.objects.get_or_create(carrier=carrier, service_code=service_code, defaults={'service_name': service_code})
        return carrier, service

    def import_carriers(self, wb, client):
        if 'FuelSurcharge' not in wb.sheetnames:
            return 0
        ws = wb['FuelSurcharge']
        count = 0
        for row in ws.iter_rows(min_row=6, max_row=135, values_only=True):
            carrier_code = s(row[6] if len(row) > 6 else '')
            service_code = s(row[7] if len(row) > 7 else '')
            if not carrier_code or not service_code:
                continue
            carrier, service = self._carrier_service(carrier_code, service_code)
            ClientCarrierConfig.objects.update_or_create(
                client=client,
                carrier_service=service,
                defaults={
                    'customer_code': 'STH',
                    'fuel_levy': d(row[10] if len(row) > 10 else 0),
                    'extra_surcharge': d(row[11] if len(row) > 11 else 0),
                    'cubic_conversion': d(row[12] if len(row) > 12 else 0),
                    'tailgate_enabled': str(row[13]).upper() == 'YES' if len(row) > 13 else False,
                    'active': True,
                }
            )
            count += 1
        return count

    def import_zones(self, wb, client):
        if 'ZONES' not in wb.sheetnames:
            return 0
        ws = wb['ZONES']
        count = 0
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            carrier_code = s(row[2] if len(row) > 2 else '')
            service_code = s(row[3] if len(row) > 3 else '')
            suburb = s(row[4] if len(row) > 4 else '')
            state = s(row[5] if len(row) > 5 else '')
            postcode = s(row[6] if len(row) > 6 else '')
            zone = s(row[7] if len(row) > 7 else '')
            subzone = s(row[8] if len(row) > 8 else '')
            area = s(row[9] if len(row) > 9 else '')
            if not carrier_code or not service_code or not suburb or not state:
                continue
            _, service = self._carrier_service(carrier_code, service_code)
            FreightZone.objects.update_or_create(
                client=client, carrier_service=service, suburb=suburb, state=state, postcode=postcode, zone=zone, subzone=subzone, area=area,
                defaults={'source_row': idx}
            )
            count += 1
        return count

    def import_rates(self, wb, client):
        if 'RATES' not in wb.sheetnames:
            return 0
        ws = wb['RATES']
        count = 0
        for idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
            carrier_code = s(row[2] if len(row) > 2 else '')
            service_code = s(row[3] if len(row) > 3 else '')
            zone = s(row[4] if len(row) > 4 else '')
            if not carrier_code or not service_code or not zone:
                continue
            _, service = self._carrier_service(carrier_code, service_code)
            FreightRate.objects.create(
                client=client, carrier_service=service,
                zone=zone, subzone=s(row[5] if len(row)>5 else ''), area=s(row[6] if len(row)>6 else ''),
                weight_break=s(row[7] if len(row)>7 else ''), freight_type=s(row[8] if len(row)>8 else ''),
                minimum_charge=d(row[9] if len(row)>9 else 0), basic_charge=d(row[10] if len(row)>10 else 0),
                per_subsequent_basic=d(row[11] if len(row)>11 else 0), per_kg=d(row[12] if len(row)>12 else 0),
                overweight_charge=d(row[13] if len(row)>13 else 0), remote_charge=d(row[14] if len(row)>14 else 0),
                offshore_charge=d(row[15] if len(row)>15 else 0), overlength_charge=d(row[16] if len(row)>16 else 0),
                customer_code=s(row[17] if len(row)>17 else 'STH') or 'STH', margin=d(row[18] if len(row)>18 else 0),
                source_row=idx
            )
            count += 1
        return count

    def import_tailgate(self, wb, client):
        if 'SettingFlags' not in wb.sheetnames:
            return 0
        ws = wb['SettingFlags']
        count = 0
        for row in ws.iter_rows(min_row=34, max_row=52, values_only=True):
            carrier_code = s(row[2] if len(row) > 2 else '')
            if not carrier_code:
                continue
            carrier, _ = Carrier.objects.get_or_create(code=carrier_code, defaults={'name': carrier_code})
            CarrierTailgateCharge.objects.update_or_create(
                client=client, carrier=carrier,
                defaults={'minimum_charge': d(row[4] if len(row)>4 else 0), 'per_subsequent_charge': d(row[5] if len(row)>5 else 0), 'hand_unload_charge': d(row[6] if len(row)>6 else 0)}
            )
            count += 1
        return count
