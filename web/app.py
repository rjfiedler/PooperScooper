"""
Flask Web Application - Control interface and monitoring dashboard
Provides web-based control and real-time status monitoring
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
from loguru import logger

# System reference (set by main.py)
_system = None

def set_system_reference(system):
    """Set reference to main PooperScooperSystem"""
    global _system
    _system = system
    logger.info("System reference set for web interface")

# Global state
app_state = {
    'patrol_status': 'idle',  # idle, patrolling, returning_home
    'current_position': {'x': 0.0, 'y': 0.0},
    'coverage_percent': 0.0,
    'pickups_today': 0,
    'success_rate': 0.0,
    'last_update': time.time(),
}

# Control flags
control_flags = {
    'start_patrol': False,
    'stop_patrol': False,
    'return_home': False,
}

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# ===== Routes =====

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')


@app.route('/analytics')
def analytics():
    """Analytics page"""
    return render_template('analytics.html')


# ===== API Endpoints =====

@app.route('/api/status')
def get_status():
    """Get current system status"""
    if _system:
        # Get live status from system
        status = _system.get_status()
        app_state.update(status)
    return jsonify(app_state)


@app.route('/api/start_patrol', methods=['POST'])
def start_patrol():
    """Start patrol command"""
    if _system:
        _system.start_patrol_from_web()
    else:
        control_flags['start_patrol'] = True
        control_flags['stop_patrol'] = False

    logger.info("Web: Start patrol command received")

    return jsonify({'success': True, 'message': 'Patrol started'})


@app.route('/api/stop_patrol', methods=['POST'])
def stop_patrol():
    """Stop patrol command"""
    if _system:
        _system.stop_patrol_from_web()
    else:
        control_flags['stop_patrol'] = True
        control_flags['start_patrol'] = False

    logger.info("Web: Stop patrol command received")

    return jsonify({'success': True, 'message': 'Patrol stopped'})


@app.route('/api/return_home', methods=['POST'])
def return_home():
    """Return to home command"""
    if _system:
        _system.return_home_from_web()
    else:
        control_flags['return_home'] = True

    logger.info("Web: Return home command received")

    return jsonify({'success': True, 'message': 'Returning to home'})


@app.route('/api/metrics')
def get_metrics():
    """Get performance metrics (placeholder for database queries)"""
    # This will be populated by main.py with actual database data
    return jsonify({
        'total_attempts': 0,
        'success_rate': 0.0,
        'pickups_today': 0,
        'coverage_percent': 0.0,
    })


# ===== WebSocket Events =====

@socketio.on('connect')
def handle_connect():
    """Client connected"""
    logger.info("Web: Client connected")
    emit('status_update', app_state)


@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected"""
    logger.info("Web: Client disconnected")


# ===== Helper Functions =====

def update_status(status_dict: dict):
    """
    Update app state and broadcast to clients

    Args:
        status_dict: Dictionary with status updates
    """
    app_state.update(status_dict)
    app_state['last_update'] = time.time()

    # Broadcast to all connected clients
    socketio.emit('status_update', app_state)


def get_control_flag(flag_name: str) -> bool:
    """
    Get and reset control flag

    Args:
        flag_name: Name of flag

    Returns:
        Flag value (resets to False after reading)
    """
    value = control_flags.get(flag_name, False)
    if value:
        control_flags[flag_name] = False
    return value


def run_app(host: str = '0.0.0.0', port: int = 5000):
    """
    Run Flask app

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    logger.info(f"Starting web server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    run_app()
