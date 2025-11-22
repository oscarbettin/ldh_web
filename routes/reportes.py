"""
Rutas para módulo de Reportes y Búsquedas
"""
from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('reportes', __name__, url_prefix='/reportes')


@bp.route('/')
@login_required
def index():
    """Página principal de reportes"""
    return render_template('reportes/index.html')

