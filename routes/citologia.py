"""
Rutas para módulo de Citología
"""
from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('citologia', __name__, url_prefix='/citologia')


@bp.route('/')
@login_required
def index():
    """Listado de citologías"""
    return render_template('citologia/index.html')

