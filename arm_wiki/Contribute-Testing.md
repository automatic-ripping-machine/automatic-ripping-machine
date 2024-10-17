# ARM Contribution Testing Guide

## Introduction
Testing code is important, people make mistakes, errors or miss edge cases that make the user experience sub-optimal.
The idea of conducting testing against the code within ARM is to ensure the user experience is always good.

For more information have a look at some of these resources:
- [pytest](docs.pytest.org)
- [Wiki Unit Testing](en.wikipedia.org/wiki/Unit_testing)

## Test Ripper

### Overview

Test Ripper covers test within ARM, focused on ripping.
ARM has been separated out such that the ripping code operates independently of the UI code, any changes to the code should respect this and not call any UI functions.

`../test_ripper`

### Testing

The following test execution is conducted within a virtual environment, refer [Virtual Environment Setup](#virtual-environment-setup) below for assistance.
Whilst a virtual environment is not required, it makes testing easier without impacting the system installed packages.

1. Activate the virtual environment
```bash
source .venv/bin/activate
```
2. Run pytest
```bash
pytest test_ripper/
```
3. Assess the results, ensuring all tests passed, refer to [Example Test Results](#example-test-results).

## Test UI

### Overview

Test UI covers test code for the User Interface, which comprises the Flask web pages, API calls, and the database modules.
As with the ripper code, the UI has been separated from the ARM ripper. Changes to code within the UI should not make any calls into the ripper.

`../test_ui`

### Testing

The following test execution is conducted within a virtual environment, refer [Virtual Environment Setup](#virtual-environment-setup) below for assistance.
Whilst a virtual environment is not required, it makes testing easier without impacting the system installed packages.

1. Activate the virtual environment
```bash
source .venv/bin/activate
```
2. Run pytest
```bash
pytest test_ui/
```
3. Assess the results, ensuring all tests passed, refer to [Example Test Results](#example-test-results).


## Example Test Results

### Example Failed Test

```bash
============================= test session starts ==============================
collecting ... collected 19 items

../../../../../opt/arm/test_ui/test_bp_error_404.py::test_errors_404 [2024-05-09 22:49:16,984] DEBUG ARM: __init__.create_app Debugging pin: 12345
[2024-05-09 22:49:16,985] DEBUG ARM: __init__.create_app Mysql configuration: mysql+mysqlconnector://arm:*******@127.0.0.1/arm?charset=utf8mb4
PASSED [  5%]
../../../../../opt/arm/test_ui/test_bp_error_404.py::test_errors_500 FAILED [ 10%]
test_bp_error_404.py:25 (test_errors_500)
404 != 500

Expected :500
Actual   :404
<Click to see difference>

test_client = <FlaskClient <Flask 'ui'>>

    def test_errors_500(test_client):
        response = test_client.get('server_error_page')
    
        # Check for a 500 page not found, and data on the 500.html page
>       assert response.status_code == 500
E       assert 404 == 500
E        +  where 404 = <WrapperTestResponse streamed [404 NOT FOUND]>.status_code

/opt/arm/test_ui/test_bp_error_404.py:30: AssertionError

../../../../../opt/arm/test_ui/test_bp_error_404.py::test_errors_error PASSED [ 15%]
../../../../../opt/arm/test_ui/test_model_alembic_version.py::test_create_alembic_version PASSED [ 21%]
../../../../../opt/arm/test_ui/test_model_alembic_version.py::test_query_alembic_version PASSED [ 26%]
../../../../../opt/arm/test_ui/test_model_config.py::test_create_config PASSED [ 31%]
../../../../../opt/arm/test_ui/test_model_config.py::test_query_config PASSED [ 36%]
../../../../../opt/arm/test_ui/test_model_job.py::test_create_job PASSED [ 42%]
../../../../../opt/arm/test_ui/test_model_job.py::test_job_attributes PASSED [ 47%]
../../../../../opt/arm/test_ui/test_model_notifications.py::test_create_notifications PASSED [ 52%]
../../../../../opt/arm/test_ui/test_model_notifications.py::test_query_notifications PASSED [ 57%]
../../../../../opt/arm/test_ui/test_model_system_drives.py::test_create_system_drives PASSED [ 63%]
../../../../../opt/arm/test_ui/test_model_system_drives.py::test_query_system_drives PASSED [ 68%]
../../../../../opt/arm/test_ui/test_model_system_info.py::test_create_system_info PASSED [ 73%]
../../../../../opt/arm/test_ui/test_model_system_info.py::test_query_system_info PASSED [ 78%]
../../../../../opt/arm/test_ui/test_model_ui_settings.py::test_create_ui_settings PASSED [ 84%]
../../../../../opt/arm/test_ui/test_model_ui_settings.py::test_query_ui_settings PASSED [ 89%]
../../../../../opt/arm/test_ui/test_model_user.py::test_create_user PASSED [ 94%]
../../../../../opt/arm/test_ui/test_model_user.py::test_query_user PASSED [100%]

========================= 1 failed, 18 passed in 0.99s =========================

Process finished with exit code 1
```

### Example Passing Test

```bash
============================= test session starts ==============================
collecting ... collected 18 items

../../../../../opt/arm/test_ui/test_bp_errors.py::test_errors_404 [2024-05-09 22:50:45,023] DEBUG ARM: __init__.create_app Debugging pin: 12345
[2024-05-09 22:50:45,023] DEBUG ARM: __init__.create_app Mysql configuration: mysql+mysqlconnector://arm:*******@127.0.0.1/arm?charset=utf8mb4
PASSED [  5%]
../../../../../opt/arm/test_ui/test_bp_errors.py::test_errors_error PASSED [ 11%]
../../../../../opt/arm/test_ui/test_model_alembic_version.py::test_create_alembic_version PASSED [ 16%]
../../../../../opt/arm/test_ui/test_model_alembic_version.py::test_query_alembic_version PASSED [ 22%]
../../../../../opt/arm/test_ui/test_model_config.py::test_create_config PASSED [ 27%]
../../../../../opt/arm/test_ui/test_model_config.py::test_query_config PASSED [ 33%]
../../../../../opt/arm/test_ui/test_model_job.py::test_create_job PASSED [ 38%]
../../../../../opt/arm/test_ui/test_model_job.py::test_job_attributes PASSED [ 44%]
../../../../../opt/arm/test_ui/test_model_notifications.py::test_create_notifications PASSED [ 50%]
../../../../../opt/arm/test_ui/test_model_notifications.py::test_query_notifications PASSED [ 55%]
../../../../../opt/arm/test_ui/test_model_system_drives.py::test_create_system_drives PASSED [ 61%]
../../../../../opt/arm/test_ui/test_model_system_drives.py::test_query_system_drives PASSED [ 66%]
../../../../../opt/arm/test_ui/test_model_system_info.py::test_create_system_info PASSED [ 72%]
../../../../../opt/arm/test_ui/test_model_system_info.py::test_query_system_info PASSED [ 77%]
../../../../../opt/arm/test_ui/test_model_ui_settings.py::test_create_ui_settings PASSED [ 83%]
../../../../../opt/arm/test_ui/test_model_ui_settings.py::test_query_ui_settings PASSED [ 88%]
../../../../../opt/arm/test_ui/test_model_user.py::test_create_user PASSED [ 94%]
../../../../../opt/arm/test_ui/test_model_user.py::test_query_user PASSED [100%]

============================== 18 passed in 1.03s ==============================

Process finished with exit code 0
```

## Virtual Environment Setup

1. Open a terminal and change to the ARM code folder, normally `/opt/arm`
```bash
cd /opt/arm
```
2. Setup virtual environment
```bash
python -m venv .venv
```
3. Activate the virtual environment
```bash
source .venv/bin/activate
```
4. Install packages and dependancies
```bash
pip install requirements.txt
```
5. Once finished, deactivate the virtual environment
```bash
deactivate
```
