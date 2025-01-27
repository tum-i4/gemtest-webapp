import os
import shutil
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from app import create_app
from app.run import default_dir

tests_end2end_path = Path(__file__).parent.parent
project_root_path = tests_end2end_path.parent.parent

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


def test_empty_landing_page(client):
    """
    Try running the app before any data is in the test_result folder.
    Verifies that the empty landing page is loaded and a hint message is displayed.
    """
    # Ensure no test results exist
    test_results_dir = project_root_path / "gemtest_results"

    if test_results_dir.exists():
        shutil.rmtree(test_results_dir)
    os.makedirs(test_results_dir, exist_ok=True)

    response = client.get("/")

    # Ensure the response is successful
    assert response.status_code == 200

    hint_message = 'Please run a test using <span style="color: blue; font-weight: bold;">poetry run pytest --html-report &lt;test-file path&gt;</span>.'
    # Check if the hint message is present in the response data
    assert hint_message in response.text


@pytest.fixture(scope="module")
def mock_test_run_file():
    """Fixture to copy test run files from test_data to the test_results directory."""

    local_test_run_path_01 = (
            tests_end2end_path
            / "test_data"
            / "metamorphic_test_run_2024-09-24_00-00-01.db"
    )
    local_test_run_path_02 = (
            tests_end2end_path
            / "test_data"
            / "metamorphic_test_run_2024-09-24_00-00-02.db"
    )
    test_results_dir = project_root_path / "gemtest_results"

    # Ensure the test_results directory is empty
    if test_results_dir.exists():
        shutil.rmtree(test_results_dir)  # Removes the directory and all its contents
    os.makedirs(test_results_dir, exist_ok=True)  # Recreate the empty directory

    # Copy mock test run files
    shutil.copy(
        local_test_run_path_01,
        test_results_dir / "metamorphic_test_run_2024-09-24_00-00-01.db",
    )
    shutil.copy(
        local_test_run_path_02,
        test_results_dir / "metamorphic_test_run_2024-09-24_00-00-02.db",
    )

    yield

    # Cleanup after tests
    shutil.rmtree(test_results_dir)  # Completely remove the test_results directory


def test_landing_page(mock_test_run_file, client):
    """
    Landing page should correctly display data of the most recent run.
    In our case, the most recent run is the test_add.py test result data.
    Verify the selection options, the number of test cases, passed tests
    and more test run specific data.
    """

    response = client.get("/")
    # Ensure the response is successful
    assert response.status_code == 200

    # Parse the response content with Beautiful Soup
    soup = BeautifulSoup(response.data, "html.parser")

    # Check that the mocked database files appear in the form options
    db_file_option_02 = "metamorphic_test_run_2024-09-24_00-00-02.db"
    db_file_option_01 = "metamorphic_test_run_2024-09-24_00-00-01.db"
    assert soup.find(string=db_file_option_02) is not None
    assert soup.find(string=db_file_option_01) is not None

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
    b_count = len(soup.find_all("td", string="A"))
    test_add_count = len(soup.find_all("td", string="test_sin"))
    assert b_count == 20
    assert test_add_count == 20


def test_switch_selection_apply_filters(client, mock_test_run_file):
    """
    We switch to the test_sin file, select various filters and verify pagination and the results
    """
    # Select the test_sin
    client.get(
        "/select",
        query_string={"test_run": "metamorphic_test_run_2024-09-24_00-00-01.db"},
    )

    # Define the filters to be applied
    filters = {
        "mr_name": "A_parameters",
        "sut_name": "test_sin",
        "test_result": "passed",
        "substring": "",
    }

    # Construct the URL with the filters
    filter_url = f"/filter?mr_name={filters['mr_name']}&sut_name={filters['sut_name']}&test_result={filters['test_result']}&substring={filters['substring']}"

    response = client.get(filter_url)

    soup = BeautifulSoup(response.data, "html.parser")

    # Verify that the filter options are present for MR Name
    mr_name_options = soup.select("select#mr_name option")
    expected_mr_options = ["all", "A_parameters", "B", "A"]
    actual_mr_options = [option["value"] for option in mr_name_options]

    assert all(
        option in actual_mr_options for option in expected_mr_options
    ), f"At least one of the options not visible: {expected_mr_options}"

    # Find all pagination links
    pagination_links = soup.select(".pagination a")

    page_numbers = [
        link.get_text() for link in pagination_links if link.get_text().isdigit()
    ]

    expected_pages = ["1", "2", "3", "4"]
    assert all(page in page_numbers for page in expected_pages)

    # Verify all pagination links have correct filters set
    for link in pagination_links:
        pagination_url = link["href"]
        assert f"mr_name={filters['mr_name']}" in pagination_url
        assert f"sut_name={filters['sut_name']}" in pagination_url
        assert f"test_result={filters['test_result']}" in pagination_url

    pages_to_test = [1, 2, 3, 4]

    for page in pages_to_test:
        # Construct the URL with the filters and current page
        filter_url = f"/filter?page={page}&mr_name={filters['mr_name']}&sut_name={filters['sut_name']}&test_result={filters['test_result']}&substring={filters['substring']}"

        # Simulating switching the pages
        response = client.get(filter_url)

        soup = BeautifulSoup(response.data, "html.parser")

        # Assert the number of mtc_detail_view links, expected to have 80 tests total, 20 per page
        mtc_links = soup.find_all(
            "a", href=lambda href: href and "mtc_detail_view/" in href
        )
        assert len(mtc_links) == 20

        # Verify all mtc_detail_view rows have correct filters set
        for link in mtc_links:
            # Get the parent <tr> of the link
            row = link.find_parent("tr")
            columns = row.find_all("td")

            # Check that the correct filters are set in the corresponding columns
            assert columns[1].text == filters["test_result"]
            assert columns[2].text == filters["mr_name"]
            assert columns[3].text == filters["sut_name"]


def test_switch_selection_with_set_filters(client, mock_test_run_file):
    """
    Simulate the selection of another test case by setting the url test_run parameter.
    The second test file contains test_sin.py test data. Previously the filters for test_sin were set.
    Verify that selection resets the filters.
    """
    # Switch to test_add file
    response = client.get(
        "/select",
        query_string={"test_run": "metamorphic_test_run_2024-09-24_00-00-02.db"},
    )

    assert response.status_code == 200

    # Verify the number of executed test cases
    executed_cases_text = "Number of executed test cases: 4"
    assert executed_cases_text in response.get_data(as_text=True)

    soup = BeautifulSoup(response.data, "html.parser")

    # Verify that the filter for SUT includes 'test_add'
    sut_select = soup.find("select", id="sut_name")
    assert "test_add" in sut_select.text

    # Click the page link
    response = client.get("/?page=1")

    soup = BeautifulSoup(response.data, "html.parser")

    # Verify that the table has the correct MTC links, should be exactly 4 for test_add
    mtc_links = soup.find_all(
        "a", href=lambda href: href and "/mtc_detail_view/" in href
    )
    assert (
        len(mtc_links) == 4
    ), f"There should be 4 MTC links, but found {len(mtc_links)}"

    # Find all <td> elements containing 'test_add'
    sut_name_cells = soup.find_all("td", string="test_add")
    assert len(sut_name_cells) == 4

    # Switch back to the test_sin file for further tests
    client.get(
        "/select",
        query_string={"test_run": "metamorphic_test_run_2024-09-24_00-00-01.db"},
    )


def test_detail_view(client):
    """
    Test the detail view for multiple metamorphic test cases.
    The test data file test_sin contains 120 Test Cases. We verify the Test Case ID, the SUT and the Test Result
    in each mtc detail view.
    """
    for case_id in range(1, 121):
        # Simulate a request to the detail view for the current test case
        response = client.get(f"/mtc_detail_view/{case_id}")

        assert response.status_code == 200

        soup = BeautifulSoup(response.data, "html.parser")

        # Verify the title
        title = soup.find("h1")
        assert title.text.strip() == "MTC Detail View"

        # Verify the Test Case ID
        test_case_id = soup.find("p", string=lambda x: x and "Test Case ID:" in x)
        assert test_case_id.text.strip() == f"Test Case ID: {case_id}"

        # Verify the System Under Test
        sut = soup.find("p", string=lambda x: x and "System Under Test:" in x)
        assert sut.text.strip() == "System Under Test: test_sin"

        # Find the span with the content "passed"
        result_span = soup.find("span", string=lambda x: "passed" in x if x else False)
        assert "passed" in result_span.text
