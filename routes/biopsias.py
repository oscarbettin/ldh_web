"""
Rutas para módulo de Biopsias
"""
from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('biopsias', __name__, url_prefix='/biopsias')


@bp.route('/')
@login_required
def index():
    """Listado de biopsias"""
    return render_template('biopsias/index.html')


@bp.route('/nuevo')
@login_required
def nuevo():
    """Nuevo protocolo de biopsia"""
    return render_template('biopsias/form.html')

