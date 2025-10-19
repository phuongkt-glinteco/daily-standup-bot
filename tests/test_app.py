import datetime


from app import _collect_project_reports, _build_project_summary_lines


def _build_state(value_map):
    """Return Slack-style state values for the provided nested dictionary."""

    state = {}
    for block_id, data in value_map.items():
        state[block_id] = {next(iter(data)): next(iter(data.values()))}
    return state


def test_collect_project_reports_single_project():
    state = _build_state(
        {
            "project": {"project_input": {"value": "Apollo"}},
            "did": {"did_input": {"value": "Fix bug"}},
            "plan": {"plan_input": {"value": "Ship"}},
            "blockers": {"blockers_input": {"value": ""}},
            "hours": {"hours_input": {"value": "7.5"}},
        }
    )

    reports = _collect_project_reports(state)

    assert reports == [
        {
            "project": "Apollo",
            "did": "Fix bug",
            "plan": "Ship",
            "blockers": "",
            "hours": "7.5",
        }
    ]


def test_collect_project_reports_multiple_projects_order_preserved():
    state = _build_state(
        {
            "project": {"project_input": {"value": "Apollo"}},
            "did": {"did_input": {"value": "Fix bug"}},
            "plan": {"plan_input": {"value": "Ship"}},
            "blockers": {"blockers_input": {"value": ""}},
            "hours": {"hours_input": {"value": "7.5"}},
            "project_1": {"project_input": {"value": "Zeus"}},
            "did_1": {"did_input": {"value": "Design"}},
            "plan_1": {"plan_input": {"value": "Review"}},
            "blockers_1": {"blockers_input": {"value": "Access"}},
            "hours_1": {"hours_input": {"value": "6"}},
        }
    )

    reports = _collect_project_reports(state)

    assert reports == [
        {
            "project": "Apollo",
            "did": "Fix bug",
            "plan": "Ship",
            "blockers": "",
            "hours": "7.5",
        },
        {
            "project": "Zeus",
            "did": "Design",
            "plan": "Review",
            "blockers": "Access",
            "hours": "6",
        },
    ]


def test_build_project_summary_lines_multiline_fields():
    reports = [
        {
            "project": "Apollo",
            "did": "Fix bug\nReview PR",
            "plan": "Ship",
            "blockers": "",
            "hours": "7.5",
        },
        {
            "project": "Zeus",
            "did": "Design",
            "plan": "Review\nPlan",
            "blockers": "Access",
            "hours": "6",
        },
    ]

    today = datetime.date(2024, 10, 18)
    tomorrow = today + datetime.timedelta(days=1)

    lines = _build_project_summary_lines(reports, today, tomorrow)

    assert lines[0] == "Project 1: Apollo"
    assert " - Fix bug" in lines
    assert " - Review PR" in lines
    assert "Project 2: Zeus" in lines
    assert any(line.startswith("d. Working hours: 6") for line in lines)
