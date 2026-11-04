from functools import cache

from app.reports.headers import build_header_lookup
from app.reports.report_types import ReportType
from app.reports.schemas import ReportDefinition


REPORT_REGISTRY: dict[ReportType, ReportDefinition] = {
    ReportType.APR: ReportDefinition(
        report_type=ReportType.APR,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Date Time",
            "Campaigns",
            "User Group",
            "Attendance",
            "Staff time",
            "Total Talk Time",
            "Total Break Time",
            "Total Idle Time",
        ],
        optional_columns=[
            "Productivity %",
            "Total Calls",
            "Total calls",
            "Connected",
            "Not Connected",
            "Positive",
            "TL Remark",
        ],
        description="Agent performance report definition.",
    ),
    ReportType.CALL_COUNT: ReportDefinition(
        report_type=ReportType.CALL_COUNT,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Call Count",
        ],
        optional_columns=[],
        description="Call count report definition.",
    ),
    ReportType.CONVERTER: ReportDefinition(
        report_type=ReportType.CONVERTER,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Converted Count",
        ],
        optional_columns=[],
        description="Converter report definition.",
    ),
    ReportType.SHIFT_ADHERENCE: ReportDefinition(
        report_type=ReportType.SHIFT_ADHERENCE,
        required_columns=[
            "Emp ID",
            "Emp Name",
            "Date",
            "Status",
            "Process",
            "Designation",
            "Manager",
            "Attendance",
            "Shift in",
            "Shift out",
            "Log In",
            "log out",
            "Login hours",
            "Downtime",
            "Login + downtime",
            "Adhere",
        ],
        optional_columns=[
            "Shift adherence Log IN",
            "Late login",
            "early logout",
            "Adherence",
            "Non Adherence",
            "Non Adherence %",
        ],
        description="Shift adherence report definition.",
    ),
    ReportType.SHRINKAGE: ReportDefinition(
        report_type=ReportType.SHRINKAGE,
        required_columns=[
            "Date",
            "Emp ID",
            "Emp Name",
            "Status",
            "Process",
            "Designation",
            "Manager",
            "DOS",
            "Login hours",
            "Attendance",
            "Age",
            "Bucket",
        ],
        optional_columns=[
            "Agent count",
            "P",
            "A",
            "LWP",
            "CL",
            "HD",
            "TP",
            "Planned Shrinkage",
            "Unplanned Shrinkage",
            "Opening",
            "Closing",
            "Attrition",
        ],
        description="Shrinkage report definition.",
    ),
    ReportType.SUPPORT_ATTENDANCE: ReportDefinition(
        report_type=ReportType.SUPPORT_ATTENDANCE,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Attendance Date",
            "Status",
        ],
        optional_columns=[],
        description="Support attendance report definition.",
    ),
    ReportType.SUPPORT_BREAK: ReportDefinition(
        report_type=ReportType.SUPPORT_BREAK,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Break Start",
            "Break End",
        ],
        optional_columns=[],
        description="Support break report definition.",
    ),
    ReportType.SUPPORT_ADHERENCE: ReportDefinition(
        report_type=ReportType.SUPPORT_ADHERENCE,
        required_columns=[
            "Agent ID",
            "Agent Name",
            "Support Date",
            "Adherence %",
        ],
        optional_columns=[],
        description="Support adherence report definition.",
    ),
    ReportType.MASTER_DATABASE: ReportDefinition(
        report_type=ReportType.MASTER_DATABASE,
        # Every employees column is NOT NULL, and the importer needs all of them,
        # so every one is required here too. Keep this in step with
        # EMPLOYEE_COLUMN_ALIASES in app/imports/master_database.py.
        required_columns=[
            "Employee ID",
            "Employee Name",
            "Email",
            "Mobile",
            "Department",
            "Process",
            "Designation",
            "Manager Name",
            "TL Name",
            "Date Of Joining",
            "Employment Status",
            "Location",
        ],
        optional_columns=[],
        # Keep these in step with EMPLOYEE_COLUMN_ALIASES in
        # app/imports/master_database.py: a header accepted here must also be
        # understood by the importer.
        column_aliases={
            "Employee ID": ["Emp ID"],
            "Mobile": ["Mobile Number"],
            "TL Name": ["Team Lead"],
            "Date Of Joining": ["DOJ"],
            "Employment Status": ["Status"],
        },
        description="Master database report definition.",
    ),
    ReportType.TRAINING_DATA: ReportDefinition(
        report_type=ReportType.TRAINING_DATA,
        required_columns=[
            "Employee ID",
            "Employee Name",
            "Training Name",
            "Training Date",
        ],
        optional_columns=[],
        description="Training data report definition.",
    ),
    ReportType.EMPLOYEE_ROSTER: ReportDefinition(
        report_type=ReportType.EMPLOYEE_ROSTER,
        required_columns=[
            "Employee ID",
            "Employee Name",
            "Team",
            "Designation",
            "Date Of Joining",
            "Employment Status",
        ],
        optional_columns=[
            "Shift Name",
            "Shift Start",
            "Shift End",
            "Date Of Exit",
        ],
        column_aliases={
            "Employee ID": ["Emp ID", "Employee Code", "Emp Code"],
            "Employee Name": ["Emp Name"],
            "Date Of Joining": ["DOJ"],
            "Date Of Exit": ["DOE", "Exit Date"],
        },
        description="Employee roster with team and shift (test data format).",
    ),
    ReportType.DAILY_ACTIVITY: ReportDefinition(
        report_type=ReportType.DAILY_ACTIVITY,
        required_columns=[
            "Work Date",
            "Employee ID",
            "Employee Name",
            "Attendance Status",
        ],
        optional_columns=[
            "Team",
            "Shift Name",
            "Shift Start",
            "Shift End",
            "Login Time",
            "Logout Time",
            "First Login Time",
            "Last Logout Time",
            "Login Hours",
            "Total Login Hours",
            "Staff Time Hours",
            "Talk Time Hours",
            "Downtime Hours",
            "Idle Time Hours",
            "Break Time Hours",
            "Shift Adherence",
        ],
        # Aliases are kept to names that no older report layout shares as a *set*,
        # so a short or damaged shift adherence / shrinkage file is not mistaken for this.
        column_aliases={
            "Work Date": ["Report Date", "Activity Date"],
            "Employee ID": ["Employee Code", "Emp Code", "Emp ID", "Agent ID"],
            "Employee Name": ["Emp Name", "Agent Name"],
            "Attendance Status": ["Attendance"],
            "Shift Start": ["Shift In"],
            "Shift End": ["Shift Out"],
            "Login Time": ["Log In"],
            "Logout Time": ["Log Out"],
        },
        description="Daily agent activity: attendance, login and talk time (test data format).",
    ),
    ReportType.SHRINKAGE_HOURS: ReportDefinition(
        report_type=ReportType.SHRINKAGE_HOURS,
        required_columns=[
            "Work Date",
            "Employee ID",
            "Employee Name",
            "Planned Shrinkage Hours",
            "Unplanned Shrinkage Hours",
        ],
        optional_columns=[],
        column_aliases={
            "Work Date": ["Report Date", "Activity Date"],
            "Employee ID": ["Employee Code", "Emp Code", "Emp ID", "Agent ID"],
            "Employee Name": ["Emp Name", "Agent Name"],
        },
        description="Planned and unplanned shrinkage hours per agent per day.",
    ),
}


def get_report_definition(report_type: ReportType | str) -> ReportDefinition:
    normalized_report_type = ReportType(report_type)
    return REPORT_REGISTRY[normalized_report_type]


@cache
def get_header_lookup(report_type: ReportType | str) -> dict[str, str]:
    """Accepted header spellings (normalized) -> canonical column name."""
    definition = get_report_definition(report_type)
    return build_header_lookup(
        definition.required_columns,
        definition.optional_columns,
        definition.column_aliases,
    )


def get_all_report_types() -> list[ReportType]:
    return list(REPORT_REGISTRY.keys())

