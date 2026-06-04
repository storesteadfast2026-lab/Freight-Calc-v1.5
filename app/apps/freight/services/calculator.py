from decimal import Decimal, ROUND_UP
from apps.carriers.models import ClientCarrierConfig
from .dtos import FreightRequest, FreightLine, FreightResult
from .consolidator import consolidate_lines
from .validators import validate_location, validate_consolidated
from .resolvers import resolve_client, resolve_postcode, resolve_zone, resolve_rate
from .tailgate_calculator import calculate_tailgate, calculate_hand_unload


def roundup(value: Decimal, places: str = '0.01') -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_UP)


class FreightCalculatorService:
    """Main freight engine / Motor principal de flete.

    This service intentionally mirrors the Excel flow:
    Calculator -> CalcLines -> FuelSurcharge -> ZONES -> RATES -> BrokerTotals.
    Este servicio replica el flujo lógico del Excel.
    """

    def calculate(self, request: FreightRequest) -> list[FreightResult]:
        client = resolve_client(request.client_code)
        if not request.postcode:
            request.postcode = resolve_postcode(request.suburb, request.state)
        validate_location(request)
        consolidated = consolidate_lines(request.lines, request.tailgate)
        validate_consolidated(consolidated)

        results: list[FreightResult] = []
        configs = ClientCarrierConfig.objects.select_related('carrier_service__carrier').filter(client=client, active=True)
        for cfg in configs:
            carrier = cfg.carrier_service.carrier
            carrier_service = cfg.carrier_service
            zone = resolve_zone(client, carrier_service, request.suburb, request.state, request.postcode)
            if not zone:
                continue
            rate = resolve_rate(client, carrier_service, zone, cfg.customer_code, consolidated.freight_type_for_rate)
            if not rate:
                continue

            # Excel: chargeable weight = ROUNDUP(MAX(cubic * cubic_conv, actual_weight), 0)
            volumetric_weight = consolidated.cubic_total_m3 * cfg.cubic_conversion
            chargeable_weight = max(volumetric_weight, consolidated.weight_total_kg).quantize(Decimal('1'), rounding=ROUND_UP)

            # Conservative migration of the base structure. Exact carrier-specific branches should be locked with Excel regression tests.
            variable_by_kg = rate.per_kg * chargeable_weight if rate.per_kg else Decimal('0')
            subsequent = rate.per_subsequent_basic * max(consolidated.pallet_count - Decimal('1'), Decimal('0'))
            base_candidate = rate.basic_charge + subsequent + variable_by_kg
            freight_base = roundup(max(rate.minimum_charge, base_candidate))

            tailgate_fee = calculate_tailgate(client, carrier, consolidated.pallet_count, consolidated.tailgate) if cfg.tailgate_enabled else Decimal('0')
            hand_unload = calculate_hand_unload(client, carrier, consolidated.pallet_count, consolidated.tailgate, cfg.hand_unload_enabled)
            fuel = freight_base * (cfg.fuel_levy + cfg.extra_surcharge)
            subtotal = freight_base + tailgate_fee + hand_unload + rate.remote_charge + rate.offshore_charge + rate.overlength_charge + fuel
            uprate_amount = subtotal * cfg.uprate
            estimate = roundup(subtotal + uprate_amount)

            results.append(FreightResult(
                carrier=carrier.code,
                service=carrier_service.service_code,
                estimate_ex_gst=estimate,
                status='L',
                details={
                    'zone': zone.zone,
                    'subzone': zone.subzone,
                    'area': zone.area,
                    'chargeable_weight': str(chargeable_weight),
                    'actual_weight': str(consolidated.weight_total_kg),
                    'cubic_total': str(consolidated.cubic_total_m3),
                    'pallets': str(consolidated.pallet_count),
                    'cartons': str(consolidated.carton_count),
                    'freight_base': str(freight_base),
                    'fuel': str(roundup(fuel)),
                    'tailgate_fee': str(tailgate_fee),
                    'hand_unload': str(hand_unload),
                    'excel_mapping_warning': 'BrokerTotals contains carrier-specific branches; verify this result against Excel regression cases.',
                }
            ))
        return sorted(results, key=lambda r: r.estimate_ex_gst)
