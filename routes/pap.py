"""
Rutas para módulo de PAP (Citología Cérvico Vaginal)
"""
from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('pap', __name__, url_prefix='/pap')


@bp.route('/')
@login_required
def index():
    """Listado de PAPs"""
    return render_template('pap/index.html')

