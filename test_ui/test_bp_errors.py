"""
ARM UI Test - Blueprints

Blueprint:
    errors

Tests:
    test_errors_404 - test error 404 reports not found
    test_errors_500 - test error 500 reports server error
"""


def test_errors_404(test_client):
    response = test_client.get("/non-existent-url")

    # Check for a 404 page not found, and data on the 404.html page
    assert response.status_code == 404
    assert b"404" in response.data

    # Check that the page is displaying base_simple not base
    assert b"Home" in response.data
    assert b"Settings" not in response.data
    assert b"Notifications" not in response.data


def test_errors_500(test_client):
    response = test_client.get("/error")

    # Check for a 500 page not found, and data on the 500.html page
    assert response.status_code == 500
    assert b"500" in response.data

    # Check that the page is displaying base_simple not base
    assert b"Home" in response.data
    assert b"Settings" not in response.data
    assert b"Notifications" not in response.data
