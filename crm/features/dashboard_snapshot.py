# Dashboard snapshot core pure deterministic snapshot.
MAX_PK = 9007199254740991
MAX_CENTS = 99999999999999
MAX_ITEMS = 2000
OPEN_STAGES = ('new', 'qualified', 'proposal')
ALL_STAGES = ('new', 'qualified', 'proposal', 'won', 'lost')

def _is_leap_year(year):
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    if year % 400 != 0:
        return False
    return True

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
    return 31

def _is_valid_date(value):
    if type(value) is not str:
        return False
    if len(value) != 10:
        return False
    if value[4] != '-':
        return False
    if value[7] != '-':
        return False
    for c in value[0:4]:
        if c < '0':
            return False
        if c > '9':
            return False
    for c in value[5:7]:
        if c < '0':
            return False
        if c > '9':
            return False
    for c in value[8:10]:
        if c < '0':
            return False
        if c > '9':
            return False
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    if month < 1:
        return False
    if month > 12:
        return False
    dim = _days_in_month(year, month)
    if day < 1:
        return False
    if day > dim:
        return False
    return True

def _parse_cents(value):
    if type(value) is not str:
        raise ValueError('invalid value')
    if len(value) == 0:
        raise ValueError('invalid value')
    dot_count = 0
    for c in value:
        if c == '.':
            dot_count = dot_count + 1
    if dot_count > 1:
        raise ValueError('invalid value')
    int_part = ''
    frac_part = ''
    seen_dot = False
    for c in value:
        if c == '.':
            seen_dot = True
        else:
            if seen_dot:
                frac_part = frac_part + c
            else:
                int_part = int_part + c
    if len(int_part) == 0:
        raise ValueError('invalid value')
    if dot_count == 0:
        if len(frac_part) != 0:
            raise ValueError('invalid value')
    else:
        if len(frac_part) < 1:
            raise ValueError('invalid value')
        if len(frac_part) > 2:
            raise ValueError('invalid value')
    for c in int_part:
        if c < '0':
            raise ValueError('invalid value')
        if c > '9':
            raise ValueError('invalid value')
    if len(int_part) > 1:
        if int_part[0] == '0':
            raise ValueError('invalid value')
    for c in frac_part:
        if c < '0':
            raise ValueError('invalid value')
        if c > '9':
            raise ValueError('invalid value')
    int_value = int(int_part)
    cents = int_value * 100
    if dot_count == 1:
        if len(frac_part) == 1:
            cents = cents + int(frac_part) * 10
        else:
            cents = cents + int(frac_part)
    if cents > MAX_CENTS:
        raise ValueError('invalid value')
    return cents

def run_feature(payload):
    if type(payload) is not dict:
        raise ValueError('invalid payload')
    if 'today' not in payload:
        raise ValueError('invalid today')
    today = payload['today']
    if type(today) is not str:
        raise ValueError('invalid today')
    if not _is_valid_date(today):
        raise ValueError('invalid today')
    if 'deals' in payload:
        deals = payload['deals']
    else:
        deals = []
    if 'tasks' in payload:
        tasks = payload['tasks']
    else:
        tasks = []
    if type(deals) is not list:
        raise ValueError('invalid deals')
    if type(tasks) is not list:
        raise ValueError('invalid tasks')
    if len(deals) > MAX_ITEMS:
        raise ValueError('invalid deals')
    if len(tasks) > MAX_ITEMS:
        raise ValueError('invalid tasks')
    deals_open_count = 0
    deals_closed_count = 0
    deals_open_total_cents = 0
    tasks_open_count = 0
    tasks_completed_count = 0
    tasks_overdue_count = 0
    tasks_due_today_count = 0
    tasks_upcoming_count = 0
    for entry in deals:
        if type(entry) is not dict:
            raise ValueError('invalid deal')
        if 'pk' not in entry:
            raise ValueError('invalid deal')
        if 'stage' not in entry:
            raise ValueError('invalid deal')
        if 'value' not in entry:
            raise ValueError('invalid deal')
        pk = entry['pk']
        stage = entry['stage']
        value = entry['value']
        if type(pk) is not int:
            raise ValueError('invalid deal')
        if pk < 1:
            raise ValueError('invalid deal')
        if pk > MAX_PK:
            raise ValueError('invalid deal')
        if type(stage) is not str:
            raise ValueError('invalid deal')
        if stage not in ALL_STAGES:
            raise ValueError('invalid deal')
        cents = _parse_cents(value)
        if stage in OPEN_STAGES:
            deals_open_count = deals_open_count + 1
            deals_open_total_cents = deals_open_total_cents + cents
        else:
            deals_closed_count = deals_closed_count + 1
    for entry in tasks:
        if type(entry) is not dict:
            raise ValueError('invalid task')
        if 'pk' not in entry:
            raise ValueError('invalid task')
        if 'due_date' not in entry:
            raise ValueError('invalid task')
        if 'completed' not in entry:
            raise ValueError('invalid task')
        pk = entry['pk']
        due_date = entry['due_date']
        completed = entry['completed']
        if type(pk) is not int:
            raise ValueError('invalid task')
        if pk < 1:
            raise ValueError('invalid task')
        if pk > MAX_PK:
            raise ValueError('invalid task')
        if type(due_date) is not str:
            raise ValueError('invalid task')
        if not _is_valid_date(due_date):
            raise ValueError('invalid task')
        if type(completed) is not bool:
            raise ValueError('invalid task')
        if completed:
            tasks_completed_count = tasks_completed_count + 1
        else:
            tasks_open_count = tasks_open_count + 1
            if due_date < today:
                tasks_overdue_count = tasks_overdue_count + 1
            else:
                if due_date == today:
                    tasks_due_today_count = tasks_due_today_count + 1
                else:
                    tasks_upcoming_count = tasks_upcoming_count + 1
    whole = deals_open_total_cents // 100
    frac = deals_open_total_cents % 100
    if frac < 10:
        frac_str = '0' + str(frac)
    else:
        frac_str = str(frac)
    csv_total = str(whole) + '.' + frac_str
    display_total = 'R$ ' + str(whole) + ',' + frac_str
    tasks_due_count = tasks_overdue_count + tasks_due_today_count
    result = {}
    result['today'] = today
    result['deals_open_count'] = deals_open_count
    result['deals_closed_count'] = deals_closed_count
    result['deals_open_total_cents'] = deals_open_total_cents
    result['deals_open_total_csv'] = csv_total
    result['deals_open_total_display'] = display_total
    result['tasks_open_count'] = tasks_open_count
    result['tasks_completed_count'] = tasks_completed_count
    result['tasks_overdue_count'] = tasks_overdue_count
    result['tasks_due_today_count'] = tasks_due_today_count
    result['tasks_upcoming_count'] = tasks_upcoming_count
    result['tasks_due_count'] = tasks_due_count
    return result
