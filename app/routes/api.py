from functools import wraps
from datetime import datetime
from flask import Blueprint, jsonify, request, send_from_directory, current_app, url_for, render_template
from flask_login import login_required, current_user
from app import db
from app.models import User, Vehicle, FuelLog, Expense, EXPENSE_CATEGORIES

bp = Blueprint('api', __name__, url_prefix='/api')


# =============================================================================
# API Documentation
# =============================================================================

@bp.route('/docs')
@login_required
def docs():
    """API Documentation page"""
    return render_template('api/docs.html')


# =============================================================================
# API Authentication
# =============================================================================

def api_auth_required(f):
    """Decorator for API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None

        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            api_key = auth_header[7:]

        # Check X-API-Key header
        if not api_key:
            api_key = request.headers.get('X-API-Key')

        if not api_key:
            return jsonify({'error': 'API key required', 'code': 'missing_api_key'}), 401

        user = User.get_by_api_key(api_key)
        if not user:
            return jsonify({'error': 'Invalid API key', 'code': 'invalid_api_key'}), 401

        # Attach user to request context
        request.api_user = user
        return f(*args, **kwargs)

    return decorated_function


def get_api_user():
    """Get the authenticated API user"""
    return getattr(request, 'api_user', None)


# =============================================================================
# API Key Management (Web UI routes)
# =============================================================================

@bp.route('/key/generate', methods=['POST'])
@login_required
def generate_api_key():
    """Generate a new API key for the current user"""
    api_key = current_user.generate_api_key()
    db.session.commit()
    return jsonify({
        'api_key': api_key,
        'created_at': current_user.api_key_created_at.isoformat()
    })


@bp.route('/key/revoke', methods=['POST'])
@login_required
def revoke_api_key():
    """Revoke the current user's API key"""
    current_user.revoke_api_key()
    db.session.commit()
    return jsonify({'success': True})


# =============================================================================
# File Serving
# =============================================================================

@bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# =============================================================================
# Internal API (for web UI, session-authenticated)
# =============================================================================

@bp.route('/vehicles/<int:vehicle_id>/stats')
@login_required
def vehicle_stats(vehicle_id):
    """Get statistics for a specific vehicle (for charts)"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle not in current_user.get_all_vehicles():
        return jsonify({'error': 'Access denied'}), 403

    logs = vehicle.fuel_logs.filter_by(is_full_tank=True).order_by(FuelLog.date).all()
    consumption_data = []
    for log in logs:
        consumption = log.get_consumption()
        if consumption:
            consumption_data.append({
                'date': log.date.isoformat(),
                'consumption': round(consumption, 2),
                'odometer': log.odometer
            })

    expenses = vehicle.expenses.all()
    category_totals = {}
    for exp in expenses:
        if exp.category in category_totals:
            category_totals[exp.category] += exp.cost
        else:
            category_totals[exp.category] = exp.cost

    return jsonify({
        'consumption': consumption_data,
        'expenses_by_category': category_totals,
        'total_fuel_cost': vehicle.get_total_fuel_cost(),
        'total_expense_cost': vehicle.get_total_expense_cost(),
        'total_distance': vehicle.get_total_distance(),
        'avg_consumption': vehicle.get_average_consumption()
    })


@bp.route('/vehicles/<int:vehicle_id>/last-odometer')
@login_required
def last_odometer(vehicle_id):
    """Get the last recorded odometer reading for a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle not in current_user.get_all_vehicles():
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({'odometer': vehicle.get_last_odometer()})


# =============================================================================
# Public API v1 - Vehicles
# =============================================================================

@bp.route('/v1/vehicles', methods=['GET'])
@api_auth_required
def api_list_vehicles():
    """
    List all vehicles

    Returns all vehicles the authenticated user has access to.
    """
    user = get_api_user()
    vehicles = user.get_all_vehicles()
    return jsonify({
        'vehicles': [v.to_dict() for v in vehicles],
        'count': len(vehicles)
    })


@bp.route('/v1/vehicles/<int:vehicle_id>', methods=['GET'])
@api_auth_required
def api_get_vehicle(vehicle_id):
    """
    Get a specific vehicle

    Returns detailed information about a single vehicle.
    """
    user = get_api_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Vehicle not found or access denied', 'code': 'not_found'}), 404

    return jsonify(vehicle.to_dict())


@bp.route('/v1/vehicles', methods=['POST'])
@api_auth_required
def api_create_vehicle():
    """
    Create a new vehicle

    Required fields: name, vehicle_type
    Optional fields: make, model, year, registration, vin, fuel_type, tank_capacity
    """
    user = get_api_user()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON body required', 'code': 'invalid_request'}), 400

    if not data.get('name'):
        return jsonify({'error': 'name is required', 'code': 'validation_error'}), 400

    if not data.get('vehicle_type'):
        return jsonify({'error': 'vehicle_type is required', 'code': 'validation_error'}), 400

    if data['vehicle_type'] not in ['car', 'van', 'motorbike', 'scooter']:
        return jsonify({'error': 'vehicle_type must be one of: car, van, motorbike, scooter', 'code': 'validation_error'}), 400

    vehicle = Vehicle(
        owner_id=user.id,
        name=data['name'],
        vehicle_type=data['vehicle_type'],
        make=data.get('make'),
        model=data.get('model'),
        year=data.get('year'),
        registration=data.get('registration'),
        vin=data.get('vin'),
        fuel_type=data.get('fuel_type', 'petrol'),
        tank_capacity=data.get('tank_capacity')
    )

    db.session.add(vehicle)
    db.session.commit()

    return jsonify(vehicle.to_dict()), 201


@bp.route('/v1/vehicles/<int:vehicle_id>', methods=['PUT', 'PATCH'])
@api_auth_required
def api_update_vehicle(vehicle_id):
    """
    Update a vehicle

    All fields are optional. Only provided fields will be updated.
    """
    user = get_api_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.owner_id != user.id:
        return jsonify({'error': 'Only the owner can update this vehicle', 'code': 'forbidden'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required', 'code': 'invalid_request'}), 400

    if 'name' in data:
        vehicle.name = data['name']
    if 'vehicle_type' in data:
        if data['vehicle_type'] not in ['car', 'van', 'motorbike', 'scooter']:
            return jsonify({'error': 'vehicle_type must be one of: car, van, motorbike, scooter', 'code': 'validation_error'}), 400
        vehicle.vehicle_type = data['vehicle_type']
    if 'make' in data:
        vehicle.make = data['make']
    if 'model' in data:
        vehicle.model = data['model']
    if 'year' in data:
        vehicle.year = data['year']
    if 'registration' in data:
        vehicle.registration = data['registration']
    if 'vin' in data:
        vehicle.vin = data['vin']
    if 'fuel_type' in data:
        vehicle.fuel_type = data['fuel_type']
    if 'tank_capacity' in data:
        vehicle.tank_capacity = data['tank_capacity']
    if 'is_active' in data:
        vehicle.is_active = data['is_active']

    db.session.commit()
    return jsonify(vehicle.to_dict())


@bp.route('/v1/vehicles/<int:vehicle_id>', methods=['DELETE'])
@api_auth_required
def api_delete_vehicle(vehicle_id):
    """
    Delete a vehicle

    This will also delete all associated fuel logs and expenses.
    """
    user = get_api_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.owner_id != user.id:
        return jsonify({'error': 'Only the owner can delete this vehicle', 'code': 'forbidden'}), 403

    db.session.delete(vehicle)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Vehicle deleted'})


# =============================================================================
# Public API v1 - Fuel Logs
# =============================================================================

@bp.route('/v1/vehicles/<int:vehicle_id>/fuel', methods=['GET'])
@api_auth_required
def api_list_fuel_logs(vehicle_id):
    """
    List fuel logs for a vehicle

    Query parameters:
    - limit: Maximum number of results (default: 100)
    - offset: Number of results to skip (default: 0)
    - sort: Sort order, 'asc' or 'desc' by date (default: desc)
    """
    user = get_api_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Vehicle not found or access denied', 'code': 'not_found'}), 404

    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)
    sort = request.args.get('sort', 'desc')

    query = vehicle.fuel_logs
    if sort == 'asc':
        query = query.order_by(FuelLog.date.asc())
    else:
        query = query.order_by(FuelLog.date.desc())

    total = query.count()
    logs = query.offset(offset).limit(limit).all()

    return jsonify({
        'fuel_logs': [log.to_dict() for log in logs],
        'count': len(logs),
        'total': total,
        'limit': limit,
        'offset': offset
    })


@bp.route('/v1/vehicles/<int:vehicle_id>/fuel', methods=['POST'])
@api_auth_required
def api_create_fuel_log(vehicle_id):
    """
    Create a fuel log

    Required fields: date, odometer
    Optional fields: volume, price_per_unit, total_cost, is_full_tank, is_missed, station, notes
    """
    user = get_api_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Vehicle not found or access denied', 'code': 'not_found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required', 'code': 'invalid_request'}), 400

    if not data.get('date'):
        return jsonify({'error': 'date is required (YYYY-MM-DD)', 'code': 'validation_error'}), 400

    if not data.get('odometer'):
        return jsonify({'error': 'odometer is required', 'code': 'validation_error'}), 400

    try:
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD', 'code': 'validation_error'}), 400

    log = FuelLog(
        vehicle_id=vehicle_id,
        user_id=user.id,
        date=date,
        odometer=float(data['odometer']),
        volume=float(data['volume']) if data.get('volume') else None,
        price_per_unit=float(data['price_per_unit']) if data.get('price_per_unit') else None,
        total_cost=float(data['total_cost']) if data.get('total_cost') else None,
        is_full_tank=data.get('is_full_tank', True),
        is_missed=data.get('is_missed', False),
        station=data.get('station'),
        notes=data.get('notes')
    )

    # Auto-calculate total cost if not provided
    if log.volume and log.price_per_unit and not log.total_cost:
        log.total_cost = round(log.volume * log.price_per_unit, 2)

    db.session.add(log)
    db.session.commit()

    return jsonify(log.to_dict()), 201


@bp.route('/v1/fuel/<int:log_id>', methods=['GET'])
@api_auth_required
def api_get_fuel_log(log_id):
    """Get a specific fuel log"""
    user = get_api_user()
    log = FuelLog.query.get_or_404(log_id)

    if log.vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Fuel log not found or access denied', 'code': 'not_found'}), 404

    return jsonify(log.to_dict())


@bp.route('/v1/fuel/<int:log_id>', methods=['PUT', 'PATCH'])
@api_auth_required
def api_update_fuel_log(log_id):
    """Update a fuel log"""
    user = get_api_user()
    log = FuelLog.query.get_or_404(log_id)

    if log.vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Fuel log not found or access denied', 'code': 'not_found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required', 'code': 'invalid_request'}), 400

    if 'date' in data:
        try:
            log.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD', 'code': 'validation_error'}), 400

    if 'odometer' in data:
        log.odometer = float(data['odometer'])
    if 'volume' in data:
        log.volume = float(data['volume']) if data['volume'] else None
    if 'price_per_unit' in data:
        log.price_per_unit = float(data['price_per_unit']) if data['price_per_unit'] else None
    if 'total_cost' in data:
        log.total_cost = float(data['total_cost']) if data['total_cost'] else None
    if 'is_full_tank' in data:
        log.is_full_tank = data['is_full_tank']
    if 'is_missed' in data:
        log.is_missed = data['is_missed']
    if 'station' in data:
        log.station = data['station']
    if 'notes' in data:
        log.notes = data['notes']

    db.session.commit()
    return jsonify(log.to_dict())


@bp.route('/v1/fuel/<int:log_id>', methods=['DELETE'])
@api_auth_required
def api_delete_fuel_log(log_id):
    """Delete a fuel log"""
    user = get_api_user()
    log = FuelLog.query.get_or_404(log_id)

    if log.vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Fuel log not found or access denied', 'code': 'not_found'}), 404

    db.session.delete(log)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Fuel log deleted'})


# =============================================================================
# Public API v1 - Expenses
# =============================================================================

@bp.route('/v1/vehicles/<int:vehicle_id>/expenses', methods=['GET'])
@api_auth_required
def api_list_expenses(vehicle_id):
    """
    List expenses for a vehicle

    Query parameters:
    - limit: Maximum number of results (default: 100)
    - offset: Number of results to skip (default: 0)
    - category: Filter by category
    - sort: Sort order, 'asc' or 'desc' by date (default: desc)
    """
    user = get_api_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Vehicle not found or access denied', 'code': 'not_found'}), 404

    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)
    category = request.args.get('category')
    sort = request.args.get('sort', 'desc')

    query = vehicle.expenses
    if category:
        query = query.filter_by(category=category)

    if sort == 'asc':
        query = query.order_by(Expense.date.asc())
    else:
        query = query.order_by(Expense.date.desc())

    total = query.count()
    expenses = query.offset(offset).limit(limit).all()

    return jsonify({
        'expenses': [exp.to_dict() for exp in expenses],
        'count': len(expenses),
        'total': total,
        'limit': limit,
        'offset': offset
    })


@bp.route('/v1/vehicles/<int:vehicle_id>/expenses', methods=['POST'])
@api_auth_required
def api_create_expense(vehicle_id):
    """
    Create an expense

    Required fields: date, category, description, cost
    Optional fields: odometer, vendor, notes
    """
    user = get_api_user()
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Vehicle not found or access denied', 'code': 'not_found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required', 'code': 'invalid_request'}), 400

    required = ['date', 'category', 'description', 'cost']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required', 'code': 'validation_error'}), 400

    valid_categories = [c[0] for c in EXPENSE_CATEGORIES]
    if data['category'] not in valid_categories:
        return jsonify({
            'error': f'category must be one of: {", ".join(valid_categories)}',
            'code': 'validation_error'
        }), 400

    try:
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD', 'code': 'validation_error'}), 400

    expense = Expense(
        vehicle_id=vehicle_id,
        user_id=user.id,
        date=date,
        category=data['category'],
        description=data['description'],
        cost=float(data['cost']),
        odometer=float(data['odometer']) if data.get('odometer') else None,
        vendor=data.get('vendor'),
        notes=data.get('notes')
    )

    db.session.add(expense)
    db.session.commit()

    return jsonify(expense.to_dict()), 201


@bp.route('/v1/expenses/<int:expense_id>', methods=['GET'])
@api_auth_required
def api_get_expense(expense_id):
    """Get a specific expense"""
    user = get_api_user()
    expense = Expense.query.get_or_404(expense_id)

    if expense.vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Expense not found or access denied', 'code': 'not_found'}), 404

    return jsonify(expense.to_dict())


@bp.route('/v1/expenses/<int:expense_id>', methods=['PUT', 'PATCH'])
@api_auth_required
def api_update_expense(expense_id):
    """Update an expense"""
    user = get_api_user()
    expense = Expense.query.get_or_404(expense_id)

    if expense.vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Expense not found or access denied', 'code': 'not_found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required', 'code': 'invalid_request'}), 400

    if 'date' in data:
        try:
            expense.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD', 'code': 'validation_error'}), 400

    if 'category' in data:
        valid_categories = [c[0] for c in EXPENSE_CATEGORIES]
        if data['category'] not in valid_categories:
            return jsonify({
                'error': f'category must be one of: {", ".join(valid_categories)}',
                'code': 'validation_error'
            }), 400
        expense.category = data['category']

    if 'description' in data:
        expense.description = data['description']
    if 'cost' in data:
        expense.cost = float(data['cost'])
    if 'odometer' in data:
        expense.odometer = float(data['odometer']) if data['odometer'] else None
    if 'vendor' in data:
        expense.vendor = data['vendor']
    if 'notes' in data:
        expense.notes = data['notes']

    db.session.commit()
    return jsonify(expense.to_dict())


@bp.route('/v1/expenses/<int:expense_id>', methods=['DELETE'])
@api_auth_required
def api_delete_expense(expense_id):
    """Delete an expense"""
    user = get_api_user()
    expense = Expense.query.get_or_404(expense_id)

    if expense.vehicle not in user.get_all_vehicles():
        return jsonify({'error': 'Expense not found or access denied', 'code': 'not_found'}), 404

    db.session.delete(expense)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Expense deleted'})


# =============================================================================
# Public API v1 - Metadata
# =============================================================================

@bp.route('/v1/categories', methods=['GET'])
@api_auth_required
def api_list_categories():
    """List all expense categories"""
    return jsonify({
        'categories': [{'id': c[0], 'name': c[1]} for c in EXPENSE_CATEGORIES]
    })
