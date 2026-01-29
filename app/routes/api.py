from flask import Blueprint, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from app.models import Vehicle, FuelLog, Expense

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/vehicles/<int:vehicle_id>/stats')
@login_required
def vehicle_stats(vehicle_id):
    """Get statistics for a specific vehicle (for charts)"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    # Check access
    if vehicle not in current_user.get_all_vehicles():
        return jsonify({'error': 'Access denied'}), 403

    # Get fuel consumption over time
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

    # Get expense breakdown by category
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

    # Check access
    if vehicle not in current_user.get_all_vehicles():
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({'odometer': vehicle.get_last_odometer()})


@bp.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
