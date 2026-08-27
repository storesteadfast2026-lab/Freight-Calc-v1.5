from __future__ import annotations

import csv
import hashlib
import io
from difflib import SequenceMatcher
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from apps.imports.models import ExternalDataFile
from apps.imports.services.audit import create_audit_event
from apps.locations.models import Suburb
from apps.rates.models import FreightZone


AUSTRALIAN_STATES = {'ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA'}
REQUIRED_COLUMNS = ('index', 'suburb', 'state', 'postcode')
CROSS_VALIDATION_VERSION = 2
ALIAS_SIMILARITY_THRESHOLD = 0.90


class PostcodesImportError(Exception):
    pass


def uploaded_data_root() -> Path:
    configured = getattr(settings, 'FTP_UPLOADED_DATA_DIR', '')
    if configured:
        return Path(configured).resolve()
    return (Path(settings.BASE_DIR) / 'uploaded_data').resolve()


def resolve_uploaded_postcodes_file(filename: str) -> Path:
    safe_name = Path(str(filename or '')).name
    if not safe_name or safe_name != str(filename or ''):
        raise PostcodesImportError('Postcodes filename must be a simple filename inside uploaded_data.')
    path = (uploaded_data_root() / safe_name).resolve()
    root = uploaded_data_root()
    if path.parent != root:
        raise PostcodesImportError('Postcodes source must be located directly inside uploaded_data.')
    if not path.exists() or not path.is_file():
        raise PostcodesImportError(f'Postcodes source file not found: {path}.')
    if path.suffix.lower() != '.csv':
        raise PostcodesImportError('Postcodes source must be a .csv file.')
    return path


def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def snapshot_ftp_postcodes_file(*, client, filename='postcodes.csv', actor=None):
    source_path = resolve_uploaded_postcodes_file(filename)
    content = source_path.read_bytes()
    if not content:
        raise PostcodesImportError('Postcodes source is empty.')

    digest = calculate_sha256(content)
    existing = (
        ExternalDataFile.objects.filter(
            client=client,
            file_type='SUBURBS',
            source_method='FTP_DROP',
            sha256=digest,
        )
        .order_by('-uploaded_at')
        .first()
    )
    if existing is not None:
        create_audit_event(
            event_type='FTP_POSTCODES_SNAPSHOT_SKIPPED',
            message=f'Identical FTP postcodes content already registered for {client.code}.',
            actor=actor,
            client=client,
            external_file=existing,
            metadata={
                'source_path': str(source_path),
                'sha256': digest,
                'existing_file_id': existing.pk,
                'database_updated': False,
            },
        )
        return existing, False

    external_file = ExternalDataFile(
        client=client,
        file_type='SUBURBS',
        source_method='FTP_DROP',
        original_filename=source_path.name,
        stored_path='',
        file_size_bytes=len(content),
        mime_type='text/csv',
        sha256=digest,
        notes=f'Snapshot created from FTP uploaded_data/{source_path.name}.',
        uploaded_by=actor if getattr(actor, 'is_authenticated', False) else None,
        status='UPLOADED',
    )
    external_file.uploaded_file.save(source_path.name, ContentFile(content), save=False)
    external_file.save()
    external_file.stored_path = external_file.uploaded_file.name
    external_file.save(update_fields=['stored_path'])

    create_audit_event(
        event_type='FTP_POSTCODES_SNAPSHOT_CREATED',
        message=f'FTP postcodes snapshot created for {client.code}.',
        actor=actor,
        client=client,
        external_file=external_file,
        metadata={
            'source_path': str(source_path),
            'source_method': 'FTP_DROP',
            'original_filename': source_path.name,
            'stored_filename': external_file.uploaded_file.name,
            'file_size_bytes': len(content),
            'sha256': digest,
            'database_updated': False,
        },
    )
    return external_file, True


def _decode(content: bytes) -> str:
    try:
        return content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise PostcodesImportError('Postcodes CSV must be UTF-8 encoded.') from exc


def parse_postcodes_rows(content: bytes):
    text = _decode(content)
    reader = csv.DictReader(io.StringIO(text))
    headers = tuple(reader.fieldnames or ())
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise PostcodesImportError(
            'Postcodes CSV is missing required column(s): ' + ', '.join(missing) + '.'
        )

    rows = []
    excluded = []
    seen_source_indexes = set()
    seen_triplets = set()

    for source_row, raw in enumerate(reader, start=2):
        source_index = str(raw.get('index') or '').strip()
        suburb = str(raw.get('suburb') or '').strip().upper()
        state = str(raw.get('state') or '').strip().upper()
        postcode = str(raw.get('postcode') or '').strip()

        blank_fields = [
            name
            for name, value in (
                ('index', source_index),
                ('suburb', suburb),
                ('state', state),
                ('postcode', postcode),
            )
            if not value
        ]
        if blank_fields:
            raise PostcodesImportError(
                f'Postcodes row {source_row} has blank required field(s): {", ".join(blank_fields)}.'
            )

        expected_index = f'{suburb}{state}{postcode}'
        if source_index.upper() != expected_index:
            raise PostcodesImportError(
                f'Postcodes row {source_row} index mismatch: expected {expected_index!r}, '
                f'found {source_index!r}.'
            )

        if source_index.upper() in seen_source_indexes:
            raise PostcodesImportError(
                f'Postcodes row {source_row} duplicates source index {source_index!r}.'
            )
        seen_source_indexes.add(source_index.upper())

        triplet = (suburb, state, postcode)
        if triplet in seen_triplets:
            raise PostcodesImportError(
                f'Postcodes row {source_row} duplicates suburb/state/postcode {triplet!r}.'
            )
        seen_triplets.add(triplet)

        reasons = []
        if state not in AUSTRALIAN_STATES:
            reasons.append(f'non-Australian state {state}')
        if len(postcode) != 4 or not postcode.isdigit() or postcode == '0000':
            reasons.append(f'invalid Australian postcode {postcode}')

        item = {
            'source_row': source_row,
            'source_index': source_index,
            'suburb': suburb,
            'state': state,
            'postcode': postcode,
            'normalized_key': f'{state}{suburb}',
        }
        if reasons:
            item['reason'] = '; '.join(reasons)
            excluded.append(item)
            continue
        rows.append(item)

    if not rows:
        raise PostcodesImportError('Postcodes CSV contains no usable Australian postcode rows.')
    return rows, excluded


def _compact_suburb_name(value: str) -> str:
    return ''.join(character for character in str(value or '').upper() if character.isalnum())


def _best_alias_candidate(target: str, candidates):
    target_name = str(target or '').strip().upper()
    target_compact = _compact_suburb_name(target_name)
    best = None
    for candidate in sorted({str(value or '').strip().upper() for value in candidates if value}):
        if candidate == target_name:
            continue
        candidate_compact = _compact_suburb_name(candidate)
        if target_compact and candidate_compact == target_compact:
            score = 1.0
        else:
            score = SequenceMatcher(None, target_name, candidate).ratio()
        if best is None or score > best[0]:
            best = (score, candidate)
    return best


def classify_postcode_additions(*, client, would_add, current_set):
    """Classify prospective Suburb additions without changing operational data.

    Exact FreightZone evidence makes a row an ADD_CANDIDATE. Missing exact zone
    evidence remains a manual-review item. Likely aliases and postcode conflicts
    are surfaced explicitly so they are never silently inserted.
    """
    targets = list(would_add)
    if not targets:
        return []

    zone_filter = Q()
    for suburb, state, postcode in targets:
        zone_filter |= Q(state__iexact=state, postcode=postcode)
        zone_filter |= Q(state__iexact=state, suburb__iexact=suburb)

    zone_rows = list(
        FreightZone.objects.filter(client=client)
        .filter(zone_filter)
        .values_list(
            'suburb',
            'state',
            'postcode',
            'carrier_service__carrier__code',
        )
    )

    normalized_zone_rows = [
        (
            str(suburb or '').strip().upper(),
            str(state or '').strip().upper(),
            str(postcode or '').strip(),
            str(carrier or '').strip().upper(),
        )
        for suburb, state, postcode, carrier in zone_rows
    ]

    results = []
    for suburb, state, postcode in targets:
        exact_zone = [
            row for row in normalized_zone_rows
            if row[0] == suburb and row[1] == state and row[2] == postcode
        ]
        same_zone_suburb = [
            row for row in normalized_zone_rows
            if row[0] == suburb and row[1] == state
        ]
        same_zone_postcode = [
            row for row in normalized_zone_rows
            if row[1] == state and row[2] == postcode
        ]

        current_same_suburb_postcodes = sorted({
            existing_postcode
            for existing_suburb, existing_state, existing_postcode in current_set
            if existing_suburb == suburb and existing_state == state and existing_postcode != postcode
        })
        current_same_postcode_names = {
            existing_suburb
            for existing_suburb, existing_state, existing_postcode in current_set
            if existing_state == state and existing_postcode == postcode and existing_suburb != suburb
        }
        zone_same_postcode_names = {row[0] for row in same_zone_postcode if row[0] != suburb}
        alias = _best_alias_candidate(
            suburb, current_same_postcode_names | zone_same_postcode_names
        )

        exact_carriers = sorted({row[3] for row in exact_zone if row[3]})
        alternate_zone_postcodes = sorted({row[2] for row in same_zone_suburb if row[2] != postcode})

        if exact_zone:
            decision = 'ADD_CANDIDATE'
            reason = 'Exact suburb/state/postcode is referenced by current Django FreightZone data.'
        elif current_same_suburb_postcodes or alternate_zone_postcodes:
            decision = 'REVIEW_POSTCODE_CONFLICT'
            reason = 'Same suburb/state already exists with a different postcode and no exact FreightZone match.'
        elif alias is not None and alias[0] >= ALIAS_SIMILARITY_THRESHOLD:
            decision = 'REVIEW_ALIAS_LIKELY'
            reason = f'Likely alias or spelling variant of {alias[1]!r} at the same state/postcode.'
        else:
            decision = 'REVIEW_NO_EXACT_ZONE'
            reason = 'No exact current FreightZone evidence was found for this suburb/state/postcode.'

        results.append({
            'suburb': suburb,
            'state': state,
            'postcode': postcode,
            'decision': decision,
            'reason': reason,
            'exact_zone_rows': len(exact_zone),
            'exact_zone_carriers': exact_carriers,
            'alternate_existing_postcodes': current_same_suburb_postcodes[:10],
            'alternate_zone_postcodes': alternate_zone_postcodes[:10],
            'likely_alias': alias[1] if alias and alias[0] >= ALIAS_SIMILARITY_THRESHOLD else '',
            'likely_alias_similarity': round(alias[0], 3) if alias and alias[0] >= ALIAS_SIMILARITY_THRESHOLD else None,
        })

    return results


def validate_postcodes_file(external_file: ExternalDataFile, actor=None) -> dict:
    if external_file.file_type != 'SUBURBS':
        raise PostcodesImportError('External file must have file_type SUBURBS.')
    path = external_file.local_path
    if not path:
        raise PostcodesImportError('External postcodes file has no local snapshot path.')

    content = Path(path).read_bytes()
    try:
        candidate_rows, excluded_rows = parse_postcodes_rows(content)

        candidate_set = {
            (row['suburb'], row['state'], row['postcode']) for row in candidate_rows
        }
        current_set = {
            (
                str(suburb or '').strip().upper(),
                str(state or '').strip().upper(),
                str(postcode or '').strip(),
            )
            for suburb, state, postcode in Suburb.objects.values_list(
                'suburb_name', 'state', 'postcode'
            )
        }

        existing_matches = candidate_set & current_set
        would_add = sorted(candidate_set - current_set)
        current_not_in_source = sorted(current_set - candidate_set)

        suburb_state_counts = {}
        for suburb, state, postcode in candidate_set:
            key = (suburb, state)
            suburb_state_counts[key] = suburb_state_counts.get(key, 0) + 1
        multi_postcode_groups = sum(1 for count in suburb_state_counts.values() if count > 1)

        cross_validation = classify_postcode_additions(
            client=external_file.client,
            would_add=would_add,
            current_set=current_set,
        )
        cross_counts = {
            decision: sum(1 for row in cross_validation if row['decision'] == decision)
            for decision in (
                'ADD_CANDIDATE',
                'REVIEW_ALIAS_LIKELY',
                'REVIEW_POSTCODE_CONFLICT',
                'REVIEW_NO_EXACT_ZONE',
            )
        }

        warnings = []
        if excluded_rows:
            warnings.append(
                f'{len(excluded_rows)} source row(s) are outside the Australian postcode candidate set '
                'and would be excluded from any future activation.'
            )
        if current_not_in_source:
            warnings.append(
                f'{len(current_not_in_source)} current Django suburb row(s) are not present in this source. '
                'They remain PRESERVE EXISTING.'
            )
        review_count = len(cross_validation) - cross_counts['ADD_CANDIDATE']
        if review_count:
            warnings.append(
                f'{review_count} prospective addition(s) require manual review and are not eligible for '
                'a future add-only activation until resolved.'
            )

        summary = {
            'source_format': 'FTP_POSTCODES',
            'cross_validation_version': CROSS_VALIDATION_VERSION,
            'rows_read': len(candidate_rows) + len(excluded_rows),
            'candidate_rows': len(candidate_rows),
            'excluded_rows_count': len(excluded_rows),
            'existing_matches': len(existing_matches),
            'would_add': len(would_add),
            'add_candidates': cross_counts['ADD_CANDIDATE'],
            'review_alias_likely': cross_counts['REVIEW_ALIAS_LIKELY'],
            'review_postcode_conflict': cross_counts['REVIEW_POSTCODE_CONFLICT'],
            'review_no_exact_zone': cross_counts['REVIEW_NO_EXACT_ZONE'],
            'cross_validation_preview': cross_validation[:50],
            'current_not_in_source': len(current_not_in_source),
            'multi_postcode_suburb_state_groups': multi_postcode_groups,
            'excluded_rows': excluded_rows[:50],
            'would_add_preview': [
                {'suburb': suburb, 'state': state, 'postcode': postcode}
                for suburb, state, postcode in would_add[:50]
            ],
            'current_not_in_source_preview': [
                {'suburb': suburb, 'state': state, 'postcode': postcode}
                for suburb, state, postcode in current_not_in_source[:50]
            ],
            'warnings': warnings,
            'database_updated': False,
            'activation_available': False,
            'activation_policy': 'ADD_ONLY_AFTER_REVIEW',
        }
    except PostcodesImportError as exc:
        external_file.status = 'VALIDATION_FAILED'
        external_file.error_message = str(exc)
        external_file.validated_by = actor if getattr(actor, 'is_authenticated', False) else None
        external_file.validated_at = timezone.now()
        external_file.save(
            update_fields=['status', 'error_message', 'validated_by', 'validated_at']
        )
        create_audit_event(
            event_type='FTP_POSTCODES_VALIDATION_FAILED',
            message=f'FTP postcodes validation failed for {external_file.client.code}.',
            actor=actor,
            client=external_file.client,
            external_file=external_file,
            severity='ERROR',
            metadata={'error': str(exc), 'database_updated': False},
        )
        raise

    external_file.status = 'VALIDATED'
    external_file.validation_summary = summary
    external_file.validated_by = actor if getattr(actor, 'is_authenticated', False) else None
    external_file.validated_at = timezone.now()
    external_file.error_message = ''
    external_file.save(
        update_fields=[
            'status',
            'validation_summary',
            'validated_by',
            'validated_at',
            'error_message',
        ]
    )
    create_audit_event(
        event_type='FTP_POSTCODES_VALIDATED',
        message=f'FTP postcodes snapshot validated for {external_file.client.code}.',
        actor=actor,
        client=external_file.client,
        external_file=external_file,
        metadata=summary,
    )
    return summary
