from flask import Blueprint
from ckanext.data_requests.views import (
    data_requests_index,
    data_requests_create,
    data_requests_admin,
    data_requests_detail
)

data_requests = Blueprint(
    'data_requests', 
    __name__,
    url_prefix='/data-requests'
)

# Routes
data_requests.add_url_rule('/', 'index', data_requests_index, methods=['GET'])
data_requests.add_url_rule('/create', 'create', data_requests_create, methods=['GET', 'POST'])
data_requests.add_url_rule('/admin', 'admin', data_requests_admin, methods=['GET', 'POST'])
data_requests.add_url_rule('/<int:request_id>', 'detail', data_requests_detail, methods=['GET'])
