import pytest
from app import db
from app.models import Trip
from datetime import date, datetime


@pytest.fixture
def sample_trip(app, test_user, sample_vehicle):
    trip = Trip(
        vehicle_id=sample_vehicle.id,
        user_id=test_user.id,
        date=date(2024, 2, 1),
        start_odometer=10000.0,
        end_odometer=10150.0,
        purpose='business',
        description='Client meeting',
        status='completed',
    )
    db.session.add(trip)
    db.session.commit()
    return trip


@pytest.fixture
def running_trip(app, test_user, sample_vehicle):
    trip = Trip(
        vehicle_id=sample_vehicle.id,
        user_id=test_user.id,
        date=date.today(),
        status='running',
        driver_id=test_user.id,
        started_at=datetime.utcnow(),
    )
    db.session.add(trip)
    db.session.commit()
    return trip


class TestTripIndex:
    def test_index_requires_auth(self, client):
        resp = client.get('/trips/', follow_redirects=False)
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_index_returns_200(self, auth_client):
        resp = auth_client.get('/trips/')
        assert resp.status_code == 200

    def test_index_shows_trips(self, auth_client, sample_trip):
        resp = auth_client.get('/trips/')
        assert resp.status_code == 200
        assert b'Test Car' in resp.data

    def test_index_shows_running_trips(self, auth_client, running_trip):
        resp = auth_client.get('/trips/')
        assert resp.status_code == 200
        assert b'Running Trips' in resp.data


class TestTripNew:
    def test_new_requires_auth(self, client):
        resp = client.get('/trips/new', follow_redirects=False)
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_get_new_form_returns_200(self, auth_client, sample_vehicle):
        resp = auth_client.get('/trips/new')
        assert resp.status_code == 200

    def test_create_trip(self, auth_client, sample_vehicle, test_user):
        resp = auth_client.post('/trips/new', data={
            'vehicle_id': str(sample_vehicle.id),
            'date': '2024-03-01',
            'start_odometer': '12000',
            'end_odometer': '12200',
            'purpose': 'business',
            'description': 'Business trip',
            'start_location': 'Office',
            'end_location': 'Client',
        }, follow_redirects=True)
        assert resp.status_code == 200
        trip = Trip.query.filter_by(description='Business trip').first()
        assert trip is not None
        assert trip.start_odometer == 12000.0
        assert trip.end_odometer == 12200.0
        assert trip.user_id == test_user.id
        assert trip.status == 'completed'


class TestTripStart:
    def test_start_requires_auth(self, client):
        resp = client.get('/trips/start', follow_redirects=False)
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_get_start_form_returns_200(self, auth_client, sample_vehicle):
        resp = auth_client.get('/trips/start')
        assert resp.status_code == 200

    def test_start_trip(self, auth_client, sample_vehicle, test_user):
        resp = auth_client.post('/trips/start', data={
            'vehicle_id': str(sample_vehicle.id),
            'driver_id': str(test_user.id),
        }, follow_redirects=True)
        assert resp.status_code == 200
        trip = Trip.query.filter_by(status='running').first()
        assert trip is not None
        assert trip.vehicle_id == sample_vehicle.id
        assert trip.driver_id == test_user.id
        assert trip.started_at is not None

    def test_start_trip_with_notes(self, auth_client, sample_vehicle, test_user):
        resp = auth_client.post('/trips/start', data={
            'vehicle_id': str(sample_vehicle.id),
            'driver_id': str(test_user.id),
            'notes': 'Quick errand',
        }, follow_redirects=True)
        assert resp.status_code == 200
        trip = Trip.query.filter_by(status='running').first()
        assert trip is not None
        assert trip.notes == 'Quick errand'


class TestTripStop:
    def test_stop_requires_auth(self, client, running_trip):
        resp = client.post(f'/trips/{running_trip.id}/stop', follow_redirects=False)
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_stop_trip(self, auth_client, running_trip):
        trip_id = running_trip.id
        resp = auth_client.post(f'/trips/{trip_id}/stop', follow_redirects=True)
        assert resp.status_code == 200
        db.session.refresh(running_trip)
        assert running_trip.status == 'completed'
        assert running_trip.stopped_at is not None

    def test_stop_trip_flashes_key_reminder(self, auth_client, running_trip):
        resp = auth_client.post(f'/trips/{running_trip.id}/stop', follow_redirects=True)
        assert resp.status_code == 200
        assert 'forget to return the key' in resp.data.decode('utf-8')

    def test_stop_non_running_trip_fails(self, auth_client, sample_trip):
        resp = auth_client.post(f'/trips/{sample_trip.id}/stop', follow_redirects=True)
        assert resp.status_code == 200
        db.session.refresh(sample_trip)
        # Should still be completed (unchanged), not re-stopped
        assert sample_trip.status == 'completed'


class TestTripDelete:
    def test_delete_requires_auth(self, client, sample_trip):
        resp = client.post(f'/trips/{sample_trip.id}/delete', follow_redirects=False)
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_delete_trip(self, auth_client, sample_trip):
        trip_id = sample_trip.id
        resp = auth_client.post(f'/trips/{trip_id}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert Trip.query.get(trip_id) is None


class TestTripReport:
    def test_report_requires_auth(self, client):
        resp = client.get('/trips/report', follow_redirects=False)
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_report_returns_200(self, auth_client):
        resp = auth_client.get('/trips/report')
        assert resp.status_code == 200

    def test_report_with_trips(self, auth_client, sample_trip):
        resp = auth_client.get('/trips/report')
        assert resp.status_code == 200
