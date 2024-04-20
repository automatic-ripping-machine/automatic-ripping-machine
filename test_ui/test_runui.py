# import pytest
# from unittest.mock import patch, MagicMock
# from ui import create_app
#
#
# @pytest.fixture
# def app():
#     with patch('ui.create_app') as mock_create_app:
#         mock_app = MagicMock()
#         mock_create_app.return_value = mock_app
#         yield mock_app
#
#
# @pytest.fixture
# def client(app):
#     return app.test_client()
#
#
# def test_index(client, app):
#     # Define your test for the index route here
#     response = client.get('/')
#     assert response.status_code == 200
#
#
# @patch('waitress.serve')
# @patch('runui.create_app')
# def test_app_start(mock_serve, app):
#     with patch('ui.UIConfig') as mock_config:
#         mock_config.return_value.server_host = '127.0.0.1'
#         mock_config.return_value.server_port = 5000
#
#         import arm.runui  # Import the script containing the provided code
#
#         mock_app = app.return_value
#
#         # Assert create_app is called
#         mock_app.assert_called_once()
#
#         # Assert logger is called with the correct information
#         mock_app.logger.info.assert_called_with("Starting ARM UI on interface address - 127.0.0.1:5000")
#
#         # Assert serve function is called with the correct arguments
#         mock_serve.assert_called_once_with(mock_app, host='127.0.0.1', port=5000)