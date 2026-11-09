_MAX_TASKS = 200
_MIN_PK = 1
_MAX_PK = 9007199254740991
_MIN_TITLE_LENGTH = 1
_MAX_TITLE_LENGTH = 180


def _is_leap_year(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    if year % 4 == 0:
        return True
    return False


def _days_in_month(year, month):
    if month == 1:
        return 31
    if month == 2:
        if _is_leap_year(year):
            return 29
        return 28
    if month == 3:
        return 31
    if month == 4:
        return 30
    if month == 5:
        return 31
    if month == 6:
        return 30
    if month == 7:
        return 31
    if month == 8:
        return 31
    if month == 9:
        return 30
    if month == 10:
        return 31
    if month == 11:
        return 30
    if month == 12:
        return 31
    return 0


def _is_valid_date_string(value):
    if type(value) is not str:
        return False
    if len(value) != 10:
        return False
    if value[4] != "-":
        return False
    if value[7] != "-":
        return False
    if value[0] not in "0123456789":
        return False
    if value[1] not in "0123456789":
        return False
    if value[2] not in "0123456789":
        return False
    if value[3] not in "0123456789":
        return False
    if value[5] not in "0123456789":
        return False
    if value[6] not in "0123456789":
        return False
    if value[8] not in "0123456789":
        return False
    if value[9] not in "0123456789":
        return False
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    if month < 1:
        return False
    if month > 12:
        return False
    limit = _days_in_month(year, month)
    if day < 1:
        return False
    if day > limit:
        return False
    return True


def run_feature(payload):
    if type(payload) is not dict:
        raise ValueError("payload must be dict")
    if "today" not in payload:
        raise ValueError("today is required")
    today = payload["today"]
    if type(today) is not str:
        raise ValueError("today must be str")
    if _is_valid_date_string(today) is False:
        raise ValueError("today must be YYYY-MM-DD")
    if "tasks" not in payload:
        tasks = []
    else:
        tasks = payload["tasks"]
        if tasks is None:
            raise ValueError("tasks must be list")
        if type(tasks) is not list:
            raise ValueError("tasks must be list")
    if len(tasks) > _MAX_TASKS:
        raise ValueError("too many tasks")
    seen = {}
    overdue_pairs = []
    today_pairs = []
    upcoming_pairs = []
    completed_pairs = []
    for index in range(len(tasks)):
        task = tasks[index]
        if type(task) is not dict:
            raise ValueError("task must be dict")
        if "pk" not in task:
            raise ValueError("pk is required")
        if "title" not in task:
            raise ValueError("title is required")
        if "due_date" not in task:
            raise ValueError("due_date is required")
        if "completed" not in task:
            raise ValueError("completed is required")
        pk_value = task["pk"]
        title_value = task["title"]
        due_value = task["due_date"]
        completed_value = task["completed"]
        if type(pk_value) is not int:
            raise ValueError("pk must be int")
        if pk_value < _MIN_PK:
            raise ValueError("pk out of range")
        if pk_value > _MAX_PK:
            raise ValueError("pk out of range")
        if pk_value in seen:
            raise ValueError("duplicate pk")
        seen[pk_value] = True
        if type(title_value) is not str:
            raise ValueError("title must be str")
        if len(title_value) < _MIN_TITLE_LENGTH:
            raise ValueError("title out of range")
        if len(title_value) > _MAX_TITLE_LENGTH:
            raise ValueError("title out of range")
        if type(due_value) is not str:
            raise ValueError("due_date must be str")
        if _is_valid_date_string(due_value) is False:
            raise ValueError("due_date must be YYYY-MM-DD")
        if type(completed_value) is not bool:
            raise ValueError("completed must be bool")
        if completed_value is True:
            completed_pairs.append([due_value, pk_value])
        else:
            if due_value < today:
                overdue_pairs.append([due_value, pk_value])
            else:
                if due_value == today:
                    today_pairs.append([due_value, pk_value])
                else:
                    upcoming_pairs.append([due_value, pk_value])
    sorted_overdue = sorted(overdue_pairs)
    sorted_today = sorted(today_pairs)
    sorted_upcoming = sorted(upcoming_pairs)
    sorted_completed = sorted(completed_pairs)
    overdue_pks = []
    for index in range(len(sorted_overdue)):
        pair = sorted_overdue[index]
        overdue_pks.append(pair[1])
    today_pks = []
    for index in range(len(sorted_today)):
        pair = sorted_today[index]
        today_pks.append(pair[1])
    upcoming_pks = []
    for index in range(len(sorted_upcoming)):
        pair = sorted_upcoming[index]
        upcoming_pks.append(pair[1])
    completed_pks = []
    for index in range(len(sorted_completed)):
        pair = sorted_completed[index]
        completed_pks.append(pair[1])
    overdue_count = len(overdue_pks)
    today_count = len(today_pks)
    upcoming_count = len(upcoming_pks)
    completed_count = len(completed_pks)
    task_count = len(tasks)
    open_count = overdue_count + today_count + upcoming_count
    return {"today": today, "task_count": task_count, "open_count": open_count, "overdue_count": overdue_count, "today_count": today_count, "upcoming_count": upcoming_count, "completed_count": completed_count, "overdue_pks": overdue_pks, "today_pks": today_pks, "upcoming_pks": upcoming_pks, "completed_pks": completed_pks}
