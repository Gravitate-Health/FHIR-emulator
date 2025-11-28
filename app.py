import traceback
from flask import Flask, request, jsonify, make_response
import os
import json
from urllib.parse import urlencode, urlunparse

app = Flask(__name__, template_folder='templates')

# Base directory used if FILES_DIR env var is not set
BASE_DIR = os.path.dirname(__file__)



@app.route('/')
def index():
    # Minimal HTML response; templates removed per cleanup request
    message = request.args.get('message', 'Welcome to the simple server')
    html = f"""
    <html><head><title>FHIR Emulator</title></head>
    <body>
    <h1>FHIR Emulator</h1>
    <p>{message}</p>
    <p>See README for endpoints and usage.</p>
    </body></html>
    """
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp


def load_json_files(folder):
    """Yield parsed JSON objects from files in folder (sorted by filename)."""
    if not os.path.isdir(folder):
        return []
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.json') and not f.lower().endswith('_summary.json'))
    results = []
    for fn in files:
        path = os.path.join(folder, fn)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                results.append(json.load(fh))
        except Exception:
            # skip invalid files
            continue
    print(f"Loaded {len(results)} resources from {folder}")
    return results


def matches_search_params(resource, search_params):
    """Check if a resource matches all provided search parameters.
    Supports searching on _id and nested fields like name, gender, birthdate, etc.
    Search is case-insensitive substring/prefix matching.
    """
    if not search_params:
        return True
    
    for param, value in search_params.items():
        if param == '_id':
            # Direct field match, exact case-insensitive
            if str(resource.get('id', '')).lower() != value.lower():
                return False
        elif param == 'identifier':
            # Special handling for identifier (can be array of objects)
            identifiers = resource.get('identifier', [])
            if not isinstance(identifiers, list):
                identifiers = [identifiers]
            #match if any identifier.value matches value
            found = False
            for ident in identifiers:
                ident_value = ident.get('value', '')
                if value.lower() == str(ident_value).lower():
                    found = True
                    break
            if not found:
                return False
        elif param == 'name':
            # Special handling for name (can be array of objects or string)
            names = resource.get('name', [])
            if not isinstance(names, list):
                names = [names]
            found = False
            for name_obj in names:
                if isinstance(name_obj, dict):
                    # Check given and family fields
                    given = name_obj.get('given', [])
                    family = name_obj.get('family', '')
                    if not isinstance(given, list):
                        given = [given]
                    full_name = ' '.join(given) + ' ' + family
                    if value.lower() in full_name.lower():
                        found = True
                        break
                elif isinstance(name_obj, str):
                    if value.lower() in name_obj.lower():
                        found = True
                        break
            if not found:
                return False
        elif param == 'gender':
            # Direct field match, case-insensitive
            if str(resource.get('gender', '')).lower() != value.lower():
                return False
        elif param == 'birthdate':
            # Prefix match for date (e.g., 1980 matches 1980-01-01)
            if not str(resource.get('birthDate', '')).startswith(value):
                return False
        elif param == '_format' and value.lower() in ('json', 'fhir+json'):
            # Ignore _format parameter for matching
            continue
        else:
            # Generic field matching: case-insensitive substring
            if value.lower() not in str(resource.get(param, '')).lower():
                return False
    
    return True


def make_bundle(total, entries=None, base_url=None):
    """Construct a FHIR Bundle dict. entries is a list of resource dicts.
    If entries is empty or None, don't include link/search related fields.
    """
    bundle = {'resourceType': 'Bundle', 'type': 'searchset', 'total': total}
    if entries is not None:
        bundle['entry'] = []
        for res in entries:
            bundle['entry'].append({'resource': res})
    else:
        # per requirement, no entries key when entries is None
        pass
    return bundle


def render_bundle_response(bundle):
    resp = make_response(json.dumps(bundle, ensure_ascii=False))
    resp.headers['Content-Type'] = 'application/fhir+json; charset=utf-8'
    return resp


def create_fhir_endpoint(resource_type):
    """Factory function to create FHIR endpoint handlers for different resource types."""
    def handler(resource_id=None, extra=None):
        return fhir_endpoint_impl(resource_type, resource_id, extra)
    handler.__name__ = f'fhir_{resource_type.lower()}_endpoint'
    return handler



def fhir_endpoint_impl(resource_type, resource_id=None, extra=None):
    # resource_type is either 'Bundle' or 'Patient'
    files_dir = os.environ.get('FILES_DIR', os.path.join(BASE_DIR, 'files'))
    resource_folder = os.path.join(files_dir, resource_type)
    
    # Track if this is a $summary operation (always return bundle, never single resource)
    is_summary_operation = resource_id == '$summary' or (extra == '$summary')
    
    # Handle $summary special case: extract parameters from POST body
    summary_identifier = None
    if resource_id == '$summary' and request.method == 'POST':
        try:
            body = request.get_json()
            if body and body.get('resourceType') == 'Parameters':
                # Extract parameters from the Parameters resource
                parameters = body.get('parameter', [])
                for param in parameters:
                    param_name = param.get('name')
                    if param_name == 'identifier':
                        # Extract the identifier value
                        identifier_val = param.get('valueIdentifier', {}).get('value')
                        if identifier_val:
                            summary_identifier = identifier_val
                            break
        except Exception:
            # If JSON parsing fails or structure is unexpected, continue normally
            print("Failed to parse $summary Parameters body")
            traceback.print_exc()
            pass
    
    # Determine if explicit paging parameters were supplied
    has_count = '_count' in request.args
    has_page = '_page' in request.args
    has_offset = '_offset' in request.args
    
    # Default page size when no paging params supplied
    DEFAULT_PAGE_SIZE = 10
    
    if not (has_count or has_page or has_offset):
        # No paging params supplied: return first DEFAULT_PAGE_SIZE resources
        count = str(DEFAULT_PAGE_SIZE)
    else:
        # At least one paging param supplied: use _count (default to 0 for totals-only)
        count = request.args.get('_count', '0')
    
    try:
        count_i = int(count)
    except ValueError:
        return jsonify({'error': '_count must be an integer'}), 400

    # Support _page (1-based) as a convenience; if provided, translate to offset
    page = request.args.get('_page')
    if page is not None:
        try:
            page_i = int(page)
            if page_i < 1:
                raise ValueError()
            offset_i = (page_i - 1) * count_i
        except ValueError:
            return jsonify({'error': '_page must be a positive integer'}), 400
    else:
        # _offset controls paging start index; default 0
        offset = request.args.get('_offset', '0')
        try:
            offset_i = int(offset)
        except ValueError:
            return jsonify({'error': '_offset must be an integer'}), 400

    # Load all resources from the appropriate folder
    all_resources = load_json_files(resource_folder)
    
    # Extract search parameters (exclude pagination params)
    search_params = {}
    # Extract search parameters (exclude pagination params)
    search_params = {}
    pagination_params = {'_count', '_offset', '_page'}
    for param, value in request.args.items():
        if param not in pagination_params:
            search_params[param] = value
    
    # Add extracted identifier from POST body if present
    if summary_identifier:
        search_params['identifier'] = summary_identifier
    if resource_id is not None and not resource_id.startswith('$'):
        search_params['_id'] = resource_id
    
    # Filter resources by search parameters
    resources = [r for r in all_resources if matches_search_params(r, search_params)]
    total = len(resources)

    print(f"Found {total} matching resources for type {resource_type} with search params {search_params}")
    print(f"listing resource IDs: {[r.get('id') for r in resources]}")
    # handle summary operation: return the json file that is named <resource_id>_summary.json
    if is_summary_operation and total == 1:
        resource_id = resources[0].get('id')
        summary_filename = f"{resource_id}_summary.json"
        summary_path = os.path.join(resource_folder, summary_filename)
        if os.path.isfile(summary_path):
            try:
                with open(summary_path, 'r', encoding='utf-8') as fh:
                    summary_resource = json.load(fh)
                print(f"Returning summary resource from {summary_path}")
                resp = make_response(json.dumps(summary_resource, ensure_ascii=False))
                resp.headers['Content-Type'] = 'application/fhir+json; charset=utf-8'
                return resp
            except Exception:
                return jsonify({'error': 'Failed to load summary resource'}), 500
        else:
            return jsonify({'error': 'Summary resource not found'}), 404

    # Return single resource directly only if: ID lookup AND no explicit paging params AND not a special operation
    if total == 1 and resource_id is not None and not (has_count or has_page or has_offset) and not resource_id.startswith('$') and not is_summary_operation:
        # Return the single matching resource directly (only for simple ID lookups without paging or special operations)
        return resources[0]

    if count_i == 0:
        # Return bundle with total set and no entries/links
        bundle = make_bundle(total, entries=None)
        bundle['total'] = total
        return render_bundle_response(bundle)

    # count_i > 0: get slice [offset_i: offset_i+count_i]
    start = max(0, offset_i)
    end = start + max(0, count_i)
    page_entries = resources[start:end]
    bundle = make_bundle(total, entries=page_entries)

    # Build paging links (self/next/prev/last) when appropriate
    # build URLs using urllib, preserving other query params; replace _offset accordingly
    def make_link(new_offset, use_page=False):
        # build querydict preserving other params
        query = {}
        for k, v in request.args.items():
            if k in ('_offset', '_page'):
                continue
            query[k] = v
        if use_page and request.args.get('_page') is not None:
            # compute page number from offset
            page_num = (new_offset // count_i) + 1
            query['_page'] = str(page_num)
        else:
            query['_offset'] = str(new_offset)
        url = request.base_url
        return url + ('?' + urlencode(query) if query else '')

    links = []
    # self
    links.append({'relation': 'self', 'url': make_link(start, use_page=(request.args.get('_page') is not None))})
    # next
    if end < total:
        links.append({'relation': 'next', 'url': make_link(end, use_page=(request.args.get('_page') is not None))})
    # prev
    if start > 0:
        prev_offset = max(0, start - count_i)
        links.append({'relation': 'prev', 'url': make_link(prev_offset, use_page=(request.args.get('_page') is not None))})
    # last
    if total > 0:
        last_offset = ((total - 1) // count_i) * count_i
        links.append({'relation': 'last', 'url': make_link(last_offset, use_page=(request.args.get('_page') is not None))})

    if links:
        bundle['link'] = links

    return render_bundle_response(bundle)


# Register dynamic routes under a single simplified prefix `/fhir/`.
# This maps any resource type folder under `FILES_DIR` to `/fhir/<resource_type>`.
# Support both GET and POST methods (POST needed for $summary with Parameters body)
app.add_url_rule(
    '/fhir/<resource_type>',
    endpoint='fhir_base',
    view_func=fhir_endpoint_impl,
    defaults={'resource_id': None, 'extra': None},
    strict_slashes=False,
    methods=['GET', 'POST']
)
app.add_url_rule(
    '/fhir/<resource_type>/<resource_id>',
    endpoint='fhir_id',
    view_func=fhir_endpoint_impl,
    defaults={'extra': None},
    strict_slashes=False,
    methods=['GET', 'POST']
)
app.add_url_rule(
    '/fhir/<resource_type>/<resource_id>/<extra>',
    endpoint='fhir_id_extra',
    view_func=fhir_endpoint_impl,
    strict_slashes=False,
    methods=['GET', 'POST']
)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
