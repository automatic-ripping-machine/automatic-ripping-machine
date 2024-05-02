"""
ARM UI Test - Blueprints

Blueprint:
    main

Tests:
    test_index - test the index page returns correctly
"""

def test_home_page_get_with_fixture(test_client):
    response = test_client.get('/')
    assert response.status_code == 200
    assert b"Hello World - the code is working - current time: " in response.data

def test_home_page_post_with_fixture(test_client):
    response = test_client.post('/')
    assert response.status_code == 405
    assert b"Hello World - the code is working - current time: " not in response.data