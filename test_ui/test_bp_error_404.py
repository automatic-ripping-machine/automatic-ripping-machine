"""
ARM UI Test - Blueprints

Blueprint:
    errors

Tests:
    test_errors_404 - test error 404 reports not found
    test_errors_500 - test error 500 reports server error
"""


def test_errors_404(test_client):
    response = test_client.get('not_a_webpage')

    # Check for a 404 page not found, and data on the 404.html page
    assert response.status_code == 404
    assert b"Page not Found" in response.data
    
    # Check that the page is displaying base_simple not base
    assert b"Home" in response.data
    assert b"Settings" not in response.data
    assert b"Notifications" not in response.data


def test_errors_500(test_client):
    response = test_client.get('server_error_page')

    # Check for a 500 page not found, and data on the 500.html page
    assert response.status_code == 500
    assert b"ARM has encountered an error in processing your request, please try again" in response.data

    # Check that the page is displaying base_simple not base
    assert b"Home" in response.data
    assert b"Settings" not in response.data
    assert b"Notifications" not in response.data


def test_errors_error(test_client):
    response = test_client.get('/error')

    # Check for a 500 page not found, and data on the 500.html page
    assert response.status_code == 500
    assert b"<h3> ARM has encountered an Error </h3>" in response.data

    # Check that the page is displaying base_simple not base
    assert b"Home" in response.data
    assert b"Settings" not in response.data
    assert b"Notifications" not in response.data
