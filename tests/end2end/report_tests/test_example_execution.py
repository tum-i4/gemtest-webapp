import os
import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from app import create_app
from app.run import default_dir

@pytest.fixture(scope="module")
def app():
    """Fixture to create a Flask app instance."""
    flask_app = create_app(default_dir)

    # Configure the app for testing
    flask_app.config["TESTING"] = True

    yield flask_app


@pytest.fixture(scope="module")
def client(app):
    """Fixture to create a Flask test client."""
    with app.test_client() as test_client:
        yield test_client

@pytest.fixture(scope="module")
def generate_test_data():
    """Fixture to run a pytest test file and generate test results dynamically."""
    current_dir = Path(os.getcwd())
    test_results_dir = current_dir.joinpath('gemtest_results')
    # Define the command to run the specific test file with an HTML report
    test_command = [
        "poetry",
        "run",
        "pytest",
        "tests/end2end/test_data/test_sin_example.py",
        "--html-report"
    ]

    # Run the test file as a subprocess
    process = subprocess.run(test_command, check=True)

    yield process

    # Remove all .db files after the test
    for db_file in test_results_dir.glob("*.db"):
        db_file.unlink()


def test_landing_page(generate_test_data, client):
    """
    Landing page should correctly display data of the most recent run.
    In our case, the most recent run is the test_add.py test result data.
    Verify the selection options, the number of test cases, passed tests
    and more test run specific data.
    """
    # Simulate a request to the application
    response = client.get("/")
    # Ensure the response is successful
    assert response.status_code == 200

    # Parse the response content with Beautiful Soup
    soup = BeautifulSoup(response.data, "html.parser")

    executed_cases_text = "Number of executed test cases: 20"
    assert soup.find(string=executed_cases_text) is not None

    # Verify the number of passed test cases
    passed_cases_text = "Number of passed test cases: 20"
    assert soup.find(string=passed_cases_text) is not None

    # Verify the number of failed test cases
    failed_cases_text = "Number of failed test cases: 0"
    assert soup.find(string=failed_cases_text) is not None

    # Verify the number of skipped test cases
    skipped_cases_text = "Number of skipped test cases: 0"
    assert soup.find(string=skipped_cases_text) is not None

    # Verify the number of individual metamorphic test case details
    mtc_detail_count = len(
        soup.find_all("a", href=lambda href: href and "mtc_detail_view/" in href)
    )
    assert mtc_detail_count == 20

    # Verify that the MR "A" and SUT "test_sin" occurs 20 times in <td> elements
    a_count = len(soup.find_all("td", string="A"))
    test_sin_count = len(soup.find_all("td", string="test_sin"))
    assert a_count == 20
    assert test_sin_count == 20
