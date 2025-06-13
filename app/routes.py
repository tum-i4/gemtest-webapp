import math
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Blueprint, current_app, render_template, request

bp = Blueprint('main', __name__)

# Define a global variable to store the df loaded from the database
global_df = None
global_df_filtered = None
current_test_runs = []


def get_most_recent_run_name(folder_path):
    # Get the most recent test_run database name
    test_runs = [f for f in os.listdir(folder_path) if
                 os.path.isfile(os.path.join(folder_path, f))]
    return max(test_runs, key=extract_datetime_from_filename)


def extract_datetime_from_filename(file_name):
    # function to extract the datetime of the test execution from the database filename
    file_name = file_name.replace("metamorphic_test_run_", "").replace(".db", "")
    return datetime.strptime(file_name, "%Y-%m-%d_%H-%M-%S")


def get_df_from_db(selected_test_runs):
    folder_path = current_app.config['DIR']

    if not selected_test_runs:
        selected_test_runs = [get_most_recent_run_name(folder_path)]

    global current_test_runs
    current_test_runs = selected_test_runs

    # create a dataframe from all selected test runs
    df_list = []
    for test_run in selected_test_runs:
        db_path = os.path.join(os.getcwd(), folder_path, test_run)
        conn = sqlite3.connect(db_path)
        df_test_run = get_test_results_df(conn)
        df_list.append(df_test_run)
        conn.close()

    # update global df variable
    global global_df
    global_df = pd.concat(df_list)
    return global_df


def get_test_results_df(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mtc_results")
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
    df['relation_result'] = df['relation_result'].map({'True': True, 'False': False})
    return df


def compile_metadata(df):
    total = df.shape[0]
    passed = df[df["test_result"] == "passed"].shape[0]
    failed = df[df["test_result"] == "failed"].shape[0]
    skipped = df[df["test_result"] == "skipped"].shape[0]
    duration = round(df["duration"].sum(), 2)
    return total, passed, failed, skipped, duration


def process_df(df):
    # do not consider skipped test cases in the calculation of the failure rate
    df = df.loc[df['test_result'] != 'skipped']

    # Group the DataFrame by "mr_name" and "sut_name" and count the occurrences of
    # "True" in "relation_result"
    grouped = df.groupby(["mr_name", "sut_name"], group_keys=True)["test_result"].apply(
        lambda x: (x == "failed").sum())

    # Calculate the total count for each group
    total_count = df.groupby(["mr_name", "sut_name"], group_keys=True).size()

    # Calculate the failure rate per group
    failure_rate = grouped / total_count

    # Convert the failure rate Series to a DataFrame with proper column names
    df_fr = failure_rate.unstack()

    # add average row
    df_fr.loc['average'] = df_fr.mean()

    # beauty updates
    df_fr.columns = [col.replace('test_', '') for col in df_fr.columns]
    df_fr.columns = [col.replace('_', ' ') for col in df_fr.columns]
    df_fr.index = [idx.replace('_', ' ') for idx in df_fr.index]
    df_fr = (df_fr * 100).round(2).astype(str) + '%'
    df_fr = df_fr.replace('nan%', '-')

    styler = df_fr.style

    print(styler.to_latex(hrules=True))

    return df_fr


def paginate_df(df):
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Calculate the start and end indices for the current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Slice the DataFrame based on the indices
    sliced_df = df[start_idx:end_idx][["_id", "mtc_name", "mr_name", "sut_name",
                                       "parameters", "test_result"]]

    # Calculate the total number of pages for the pagination links
    total_pages = int(math.ceil(len(df) / per_page))
    return page, total_pages, sliced_df


def get_sorted_files(folder_path):
    files = [f for f in os.listdir(folder_path) if
             os.path.isfile(os.path.join(folder_path, f))]

    return sorted(files, key=extract_datetime_from_filename, reverse=True)


@bp.route('/')
def landing_page():
    # Get the list of all db files
    folder_path = current_app.config['DIR']

    # check if test_results is empty: No tests have been executed with --html-report
    if not os.path.exists(folder_path) or not os.listdir(folder_path):
        # if no results have been found, display the following hint message
        hint_message = ('Please run a test using <span style="color: blue; font-weight: bold'
                        ';">poetry run pytest --html-report &lt;test-file path&gt;</span>.')
        return render_template("empty_landing_page.html", hint_message=hint_message)

    files = get_sorted_files(folder_path)

    if global_df is None:
        df = get_df_from_db(selected_test_runs=current_test_runs)
    else:
        df = global_df

    df_fr = process_df(df)
    total, passed, failed, skipped, duration = compile_metadata(df)

    landing_page_data = {
        'num_executed': total,
        'num_passed': passed,
        'num_failed': failed,
        'num_skipped': skipped,
        'execution_time': duration,
        'table_data': df_fr
    }

    if global_df_filtered is not None:
        df_filtered = global_df_filtered
    else:
        df_filtered = df

    # Sort the DataFrame by the "relation_result" column
    df_filtered = df_filtered.sort_values(by='relation_result', ascending=True)

    # paginate the df
    page, total_pages, df_sliced = paginate_df(df_filtered)

    return render_template(
        template_name_or_list='landing_page.html',
        files=files,
        current_test_run=current_test_runs,
        data=landing_page_data,
        individual_test_results=df_sliced,
        total_pages=total_pages,
        current_page=page,
        unique_mr_names=df["mr_name"].unique(),
        unique_sut_names=df["sut_name"].unique(),
        unique_test_results=df["test_result"].unique()
    )


@bp.route('/select', methods=['GET'])
def select_test_run():
    # Reset filtered df when a new test run is selected, there should be no filters applied.
    global global_df_filtered
    global_df_filtered = None

    # Get the list of all db files
    folder_path = current_app.config['DIR']

    files = get_sorted_files(folder_path)

    # connect to selected test run databases and fetch stored results
    selected_test_runs = request.args.getlist('test_run')
    df = get_df_from_db(selected_test_runs=selected_test_runs)

    df_fr = process_df(df)
    total, passed, failed, skipped, duration = compile_metadata(df)

    landing_page_data = {
        'num_executed': total,
        'num_passed': passed,
        'num_failed': failed,
        'num_skipped': skipped,
        'execution_time': duration,
        'table_data': df_fr
    }

    # Sort the DataFrame by the "relation_result" column
    df = df.sort_values(by='relation_result', ascending=True)

    # paginate the df
    page, total_pages, df_sliced = paginate_df(df)

    return render_template(
        'landing_page.html',
        individual_test_results=df_sliced,
        current_test_run=current_test_runs,
        files=files,
        data=landing_page_data,
        total_pages=total_pages,
        current_page=page,
        unique_mr_names=df['mr_name'].unique(),
        unique_sut_names=df["sut_name"].unique(),
        unique_test_results=df["test_result"].unique()
    )


@bp.route('/filter', methods=['GET'])
def filter_test_cases():  # pylint: disable=too-many-locals
    # Get the list of all db files
    folder_path = current_app.config['DIR']

    files = get_sorted_files(folder_path)

    if global_df is None:
        raise TypeError("No test run selected as global_df is None")

    df = global_df

    # Retain original unfiltered options for dropdowns
    all_mr_names = df['mr_name'].unique()
    all_sut_names = df['sut_name'].unique()
    all_test_results = df['test_result'].unique()

    df_fr = process_df(df)
    total, passed, failed, skipped, duration = compile_metadata(df)

    landing_page_data = {
        'num_executed': total,
        'num_passed': passed,
        'num_failed': failed,
        'num_skipped': skipped,
        'execution_time': duration,
        'table_data': df_fr
    }

    selected_mr = request.args.getlist('mr_name')
    selected_sut = request.args.getlist('sut_name')
    selected_test_result = request.args.getlist('test_result')
    substring = request.args.get('substring')

    # Filter by Metamorphic Relation
    if selected_mr and selected_mr != ["all"]:
        df = df[df['mr_name'].isin(selected_mr)]

    # Filter by System Under Test
    if selected_sut and selected_sut != ["all"]:
        df = df[df['sut_name'].isin(selected_sut)]

    # Filter by Test Result
    if selected_test_result and selected_test_result != ["all"]:
        df = df[df['test_result'].isin(selected_test_result)]

    # Apply substring filter
    if substring:
        df = df[df.applymap(lambda cell: substring.lower() in str(cell).lower()).any(axis=1)]

    # Sort the DataFrame by the "relation_result" column
    df = df.sort_values(by='relation_result', ascending=True)

    # update the global df variable
    global global_df_filtered
    global_df_filtered = df

    # Paginate the df
    page, total_pages, df_sliced = paginate_df(df)

    return render_template(
        'landing_page.html',
        files=files,
        individual_test_results=df_sliced,
        current_test_run=current_test_runs,
        data=landing_page_data,
        total_pages=total_pages,
        current_page=page,
        unique_mr_names=all_mr_names,
        unique_sut_names=all_sut_names,
        unique_test_results=all_test_results
    )


def _get_values_valid_path(row, value_type):
    separator = "__\n\r__"
    values = row[value_type].split(separator)
    paths_to_posix(values)
    is_valid_path = [os.path.exists(os.path.join("app/static/" + value)) for value in values]
    return {'values': values, 'is_valid_path': is_valid_path}


def paths_to_posix(values):
    for i, _ in enumerate(values):
        values[i] = Path(values[i]).as_posix()


@bp.route('/mtc_detail_view/<test_case_id>')
def mtc_detail_view(test_case_id):
    # Load the row from the DataFrame based on the test_case_id
    test_case_id = int(test_case_id)
    row = global_df[global_df['_id'] == test_case_id].iloc[0]

    # string representation of inputs and outputs
    source_inputs = _get_values_valid_path(row, 'source_inputs')
    followup_inputs = _get_values_valid_path(row, 'followup_inputs')
    source_outputs = _get_values_valid_path(row, 'source_outputs')
    followup_outputs = _get_values_valid_path(row, 'followup_outputs')

    sut = f"⇨ {row['sut_name']} ⇨"
    transformation = f"⇩ {row['transformation_name']} ⇩"
    relation = f"⇧⇩ {row['relation_name']}: {row['test_result']} ⇩⇧"

    # Specify the color for the 'skipped' option
    dark_yellow = 'rgb(185, 165, 49)'

    return render_template(
        'mtc_detail_view.html',
        test_case_id=test_case_id,
        source_inputs=source_inputs,
        followup_inputs=followup_inputs,
        source_outputs=source_outputs,
        followup_outputs=followup_outputs,
        sut=sut,
        transformation=transformation,
        relation=relation,
        stdout=row['stdout'],
        stderr=row['stderr'],
        sut_name=row['sut_name'],
        mr_name=row['mr_name'],
        mtc_name=row['mtc_name'],
        test_result=row['test_result'],
        skipped_color=dark_yellow
    )
