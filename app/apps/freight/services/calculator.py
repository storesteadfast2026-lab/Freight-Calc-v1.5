from decimal import Decimal, ROUND_UP
from apps.carriers.models import ClientCarrierConfig
from apps.rates.models import FreightZone, FreightRate
from .dtos import FreightRequest, FreightResult
from .consolidator import consolidate_lines
from .validators import validate_location, validate_consolidated
from .resolvers import resolve_client, resolve_postcode
from .tailgate_calculator import calculate_tailgate, calculate_hand_unload


def roundup(value: Decimal, places: str = '0.01') -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_UP)


def excel_bool(value: bool) -> str:
    return 'YES' if value else 'NO'


def chargeable_weight(cubic_total: Decimal, cubic_conversion: Decimal, actual_weight: Decimal) -> Decimal:
    """BrokerTotals!AF: ROUNDUP(MAX(Cubic*CubicConv, Kg), 0)."""
    volumetric = cubic_total * (cubic_conversion or Decimal('0'))
    return max(volumetric, actual_weight).quantize(Decimal('1'), rounding=ROUND_UP)


def excel_weight_break(weight: Decimal) -> str:
    """Approximate BrokerTotals AI:AO break buckets used by rows with WeightBrk.

    English: RATES only uses break numbers 1-5 in the workbook.
    Español: RATES usa números de break 1-5 en la planilla.
    """
    if weight <= Decimal('251'):
        return '1'
    if weight <= Decimal('751'):
        return '2'
    if weight <= Decimal('1501'):
        return '3'
    if weight <= Decimal('3000'):
        return '4'
    return '5'


def overlength_fee(max_length_m: Decimal) -> Decimal:
    """SettingFlags TEAMEXWGTBKTAB approximation.

    English: Excel uses bracket numbers and a lookup table for overlength.
    Español: Excel usa números de tramo y una tabla para sobrelargo.
    """
    if max_length_m < Decimal('2.5'):
        return Decimal('0')
    if max_length_m < Decimal('3.7'):
        return Decimal('60')
    if max_length_m < Decimal('6.0'):
        return Decimal('170')
    if max_length_m <= Decimal('7.2'):
        return Decimal('240')
    return Decimal('850')


class FreightCalculatorService:
    """Main freight engine / Motor principal de flete.

    English: This version maps the Excel flow more closely:
    Calculator -> CalcLines -> FuelSurcharge -> ZONES -> RATES -> BrokerTotals.
    Español: Esta versión replica más de cerca el flujo del Excel.
    """

    def calculate(self, request: FreightRequest) -> list[FreightResult]:
        client = resolve_client(request.client_code)
        if not request.postcode:
            request.postcode = resolve_postcode(request.suburb, request.state)
        validate_location(request)
        consolidated = consolidate_lines(request.lines, request.tailgate)
        validate_consolidated(consolidated)

        results: list[FreightResult] = []
        configs = (
            ClientCarrierConfig.objects
            .select_related('carrier_service__carrier')
            .filter(client=client)
            .order_by('id')
        )

        for cfg in configs:
            diagnostic = self._carrier_status(cfg, request, consolidated)
            if diagnostic != 'L':
                continue

            carrier = cfg.carrier_service.carrier
            carrier_service = cfg.carrier_service
            zone_data = self._resolve_zone_for_config(client, cfg, request)
            if zone_data is None:
                continue

            weight = chargeable_weight(consolidated.cubic_total_m3, cfg.cubic_conversion, consolidated.weight_total_kg)
            rate = self._resolve_rate_for_config(client, cfg, zone_data, consolidated.freight_type_for_rate, weight)
            if rate is None:
                continue

            freight_base = self._calculate_base_freight(rate, weight, consolidated.pallet_count + consolidated.carton_count)
            tailgate_fee = calculate_tailgate(client, carrier, consolidated.pallet_count, consolidated.tailgate) if cfg.tailgate_enabled else Decimal('0')
            hand_unload = calculate_hand_unload(client, carrier, consolidated.pallet_count, consolidated.tailgate, cfg.hand_unload_enabled)
            overlength = overlength_fee(consolidated.max_length_m) if cfg.overlength_enabled else Decimal('0')
            handling = cfg.fixed_handling_charge if cfg.warehouse_handling_enabled else Decimal('0')
            fuel = freight_base * (cfg.fuel_levy + cfg.extra_surcharge)

            subtotal_before_uprate = (
                freight_base
                + rate.overweight_charge
                + overlength
                + tailgate_fee
                + hand_unload
                + rate.remote_charge
                + rate.offshore_charge
                + fuel
            )
            uprate_amount = subtotal_before_uprate * cfg.uprate
            estimate = roundup(subtotal_before_uprate + uprate_amount + handling)

            results.append(FreightResult(
                carrier=carrier.code,
                service=carrier_service.service_code,
                estimate_ex_gst=estimate,
                status='L',
                details={
                    'zone': zone_data['zone'],
                    'subzone': zone_data['subzone'],
                    'area': zone_data['area'],
                    'rate_lookup_key': rate.lookup_key,
                    'rate_source_row': rate.source_row,
                    'chargeable_weight': str(weight),
                    'actual_weight': str(consolidated.weight_total_kg),
                    'cubic_total': str(consolidated.cubic_total_m3),
                    'pallets': str(consolidated.pallet_count),
                    'cartons': str(consolidated.carton_count),
                    'freight_type': consolidated.freight_type_for_rate,
                    'freight_base': str(freight_base),
                    'fuel': str(roundup(fuel)),
                    'tailgate_fee': str(roundup(tailgate_fee)),
                    'hand_unload': str(roundup(hand_unload)),
                    'overlength': str(roundup(overlength)),
                    'remote': str(rate.remote_charge),
                    'offshore': str(rate.offshore_charge),
                    'handling': str(handling),
                    'mapping': 'Excel-like BrokerTotals calculation from imported FuelSurcharge/ZONES/RATES rows.',
                }
            ))
        return sorted(results, key=lambda r: r.estimate_ex_gst)

    def _carrier_status(self, cfg: ClientCarrierConfig, request: FreightRequest, consolidated) -> str:
        """Replicate FuelSurcharge!AA status behavior.

        English: L is contextual, not a fixed carrier flag.
        Español: L es contextual, no una bandera fija del carrier.
        """
        if cfg.base_status != 'L' or not cfg.active:
            return 'X'
        if consolidated.tailgate and not cfg.tailgate_enabled:
            return 'X'
        if cfg.order_ready_rule == 'WOODVILLE_NORTH_ONLY' and request.suburb.strip().upper() != 'WOODVILLE NORTH':
            return 'X'
        if consolidated.pallet_count > Decimal('0.99') and cfg.pallet_enabled:
            return 'L'
        if consolidated.carton_count > Decimal('0.99') and cfg.carton_enabled:
            return 'L'
        return 'X'

    def _resolve_zone_for_config(self, client, cfg: ClientCarrierConfig, request: FreightRequest) -> dict | None:
        """Replicate BrokerTotals zone/subzone/area lookup intent."""
        zone = ''
        subzone = ''
        area = ''

        if cfg.zone_enabled:
            qs = FreightZone.objects.filter(client=client, carrier_service=cfg.carrier_service)
            match = None
            if cfg.postcode_zones_enabled and request.postcode:
                match = qs.filter(postcode=str(request.postcode)).first()
            if match is None:
                match = qs.filter(suburb__iexact=request.suburb, state__iexact=request.state).first()
            if match is None:
                return None
            zone = match.zone or ''
            subzone = match.subzone or '' if cfg.subzone_enabled else ''
            area = match.area or '' if cfg.area_enabled else ''

        return {'zone': zone, 'subzone': subzone, 'area': area}

    def _resolve_rate_for_config(self, client, cfg: ClientCarrierConfig, zone_data: dict, freight_type: str, weight: Decimal) -> FreightRate | None:
        wb = excel_weight_break(weight)
        base_qs = FreightRate.objects.filter(
            client=client,
            carrier_service=cfg.carrier_service,
            zone=zone_data['zone'],
            subzone=zone_data['subzone'],
            area=zone_data['area'],
            customer_code=cfg.customer_code,
            freight_type=freight_type,
        )
        # Excel key includes AO WeightBreak; blank is valid for most carriers.
        rate = base_qs.filter(weight_break=wb).first()
        if rate:
            return rate
        rate = base_qs.filter(weight_break='').first()
        if rate:
            return rate
        # Safety fallback for tables where subzone/area data exists but config suppresses it.
        return FreightRate.objects.filter(
            client=client,
            carrier_service=cfg.carrier_service,
            zone=zone_data['zone'],
            customer_code=cfg.customer_code,
            freight_type=freight_type,
        ).filter(weight_break__in=[wb, '']).order_by('-weight_break').first()

    def _calculate_base_freight(self, rate: FreightRate, weight: Decimal, unit_count: Decimal) -> Decimal:
        """Replicate BrokerTotals!L main formula.

        English: Total = ROUNDUP(MAX(Minimum, Basic + Subsequent + Rate*ChargeableWeight), 2).
        Español: Total = redondeo hacia arriba del mayor entre mínimo y cálculo base.
        """
        subsequent = Decimal('0')
        if unit_count > Decimal('1.99'):
            subsequent = (unit_count - Decimal('1')) * rate.per_subsequent_basic
        candidate = rate.basic_charge + subsequent + (rate.per_kg * weight)
        base = max(rate.minimum_charge, candidate)
        return roundup(base)
