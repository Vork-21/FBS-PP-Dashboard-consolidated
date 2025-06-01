"""
Common utility functions for the Payment Plan Analysis System
Consolidates frequently used functions across modules
"""

import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
from dateutil.relativedelta import relativedelta


def format_currency(amount: float, include_cents: bool = False) -> str:
    """Format currency consistently across the application"""
    if include_cents:
        return f"${amount:,.2f}"
    else:
        return f"${amount:,.0f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format percentage consistently"""
    return f"{value:.{decimals}f}%"


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def whole_months(decimal_months: float) -> int:
    """Always return whole months (rounded up)"""
    return math.ceil(decimal_months)


def cap_deficit_at_balance(deficit: float, total_balance: float) -> float:
    """Cap payment deficit at total balance owed"""
    return min(abs(deficit), total_balance)


def get_payment_date_for_month(month_number: int, payment_day: int = 15) -> datetime:
    """Get payment date for a given month (always 15th by default)"""
    current_date = datetime.now()
    target_date = current_date + relativedelta(months=month_number)
    return target_date.replace(day=payment_day)


def normalize_frequency_to_months(frequency: str) -> int:
    """Convert payment frequency to month intervals"""
    frequency_map = {
        'monthly': 1,
        'quarterly': 3,
        'bimonthly': 2,
        'undefined': 1
    }
    return frequency_map.get(frequency.lower(), 1)


def calculate_expected_payments_by_frequency(monthly_amount: float, months_elapsed: int, frequency: str) -> float:
    """Calculate expected payments based on frequency and time elapsed"""
    if frequency == 'monthly':
        return months_elapsed * monthly_amount
    elif frequency == 'quarterly':
        quarterly_periods = months_elapsed // 3
        return quarterly_periods * monthly_amount
    elif frequency == 'bimonthly':
        bimonthly_periods = months_elapsed // 2
        return bimonthly_periods * monthly_amount
    else:
        return months_elapsed * monthly_amount


def sort_customers_by_priority(customers: List[Dict], sort_key: str = 'months_behind') -> List[Dict]:
    """Sort customers by collection priority"""
    def priority_key(customer):
        months_behind = customer.get('months_behind', 0)
        total_owed = customer.get('total_owed', 0)
        
        if sort_key == 'months_behind':
            return (-months_behind, -total_owed)
        elif sort_key == 'balance':
            return (-total_owed, -months_behind)
        else:
            return customer.get('customer_name', '').lower()
    
    return sorted(customers, key=priority_key)


def group_by_class(items: List[Dict], class_field: str = 'class_field') -> Dict[str, List[Dict]]:
    """Group items by class field"""
    grouped = {}
    for item in items:
        class_name = item.get(class_field) or 'Unknown'
        if class_name not in grouped:
            grouped[class_name] = []
        grouped[class_name].append(item)
    return grouped


def calculate_portfolio_totals(metrics: List[Dict]) -> Dict:
    """Calculate portfolio-wide totals from metrics"""
    if not metrics:
        return {
            'total_customers': 0,
            'total_plans': 0,
            'total_outstanding': 0,
            'expected_monthly': 0,
            'customers_behind': 0,
            'customers_current': 0,
            'customers_completed': 0
        }
    
    # Group by customer to avoid double counting
    customers_by_status = {}
    total_outstanding = sum(m.get('total_owed', 0) for m in metrics)
    expected_monthly = 0
    
    for metric in metrics:
        customer_name = metric.get('customer_name')
        status = metric.get('status', 'unknown')
        
        # Calculate expected monthly (normalize all to monthly)
        frequency = metric.get('frequency', 'monthly')
        monthly_payment = metric.get('monthly_payment', 0)
        
        if frequency == 'monthly':
            expected_monthly += monthly_payment
        elif frequency == 'quarterly':
            expected_monthly += monthly_payment / 3
        elif frequency == 'bimonthly':
            expected_monthly += monthly_payment / 2
        
        # Track customer status (use worst status per customer)
        current_status = customers_by_status.get(customer_name, 'current')
        
        if status == 'behind' or current_status == 'behind':
            customers_by_status[customer_name] = 'behind'
        elif status == 'completed' and current_status == 'current':
            customers_by_status[customer_name] = 'completed'
        elif current_status == 'current':
            customers_by_status[customer_name] = status
    
    # Count customers by status
    status_counts = {'current': 0, 'behind': 0, 'completed': 0}
    for status in customers_by_status.values():
        if status in status_counts:
            status_counts[status] += 1
    
    return {
        'total_customers': len(customers_by_status),
        'total_plans': len(metrics),
        'total_outstanding': total_outstanding,
        'expected_monthly': expected_monthly,
        'customers_current': status_counts['current'],
        'customers_behind': status_counts['behind'],
        'customers_completed': status_counts['completed']
    }


def filter_metrics(metrics: List[Dict], filters: Dict) -> List[Dict]:
    """Apply filters to metrics list"""
    filtered = metrics.copy()
    
    # Class filter
    if filters.get('class_filter') and filters['class_filter'] != 'all':
        filtered = [m for m in filtered if m.get('class_field') == filters['class_filter']]
    
    # Status filter
    if filters.get('status_filter') and filters['status_filter'] != 'all':
        filtered = [m for m in filtered if m.get('status') == filters['status_filter']]
    
    # Frequency filter
    if filters.get('frequency_filter') and filters['frequency_filter'] != 'all':
        filtered = [m for m in filtered if m.get('frequency') == filters['frequency_filter']]
    
    # Behind customers only
    if filters.get('behind_only', False):
        filtered = [m for m in filtered if m.get('months_behind', 0) > 0]
    
    return filtered


def search_metrics(metrics: List[Dict], search_term: str) -> List[Dict]:
    """Search metrics by customer name"""
    if not search_term:
        return metrics
    
    search_lower = search_term.lower()
    return [m for m in metrics if search_lower in m.get('customer_name', '').lower()]


def paginate_data(data: List, page: int = 1, items_per_page: int = 25) -> Dict:
    """Paginate data and return page info"""
    total_items = len(data)
    total_pages = math.ceil(total_items / items_per_page) if items_per_page > 0 else 1
    
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    
    return {
        'data': data[start_index:end_index],
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_items,
            'items_per_page': items_per_page,
            'start_index': start_index + 1,
            'end_index': min(end_index, total_items),
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    }


def merge_dicts_deeply(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts_deeply(result[key], value)
        else:
            result[key] = value
    return result


def validate_csv_structure(df) -> List[str]:
    """Validate CSV has required structure"""
    issues = []
    required_columns = ['Type', 'Date', 'Num', 'FOB', 'Open Balance', 'Amount']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        issues.append(f"Missing required columns: {', '.join(missing_columns)}")
    
    if len(df) == 0:
        issues.append("CSV file is empty")
    
    # Check for invoice rows
    if 'Type' in df.columns:
        invoice_rows = df[df['Type'] == 'Invoice']
        if len(invoice_rows) == 0:
            issues.append("No invoice rows found (Type = 'Invoice')")
    
    return issues


def clean_string(value: str) -> str:
    """Clean and normalize string values"""
    if not value:
        return ""
    return str(value).strip()


def is_valid_date(date_string: str) -> bool:
    """Check if string is a valid date"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def get_status_display_info(status: str, months_behind: int = 0) -> Dict:
    """Get display information for status"""
    if months_behind > 0:
        if months_behind >= 6:
            return {'display': 'Critical', 'class': 'danger', 'icon': 'exclamation-triangle'}
        elif months_behind >= 3:
            return {'display': 'Severe', 'class': 'warning', 'icon': 'exclamation-circle'}
        else:
            return {'display': 'Behind', 'class': 'warning', 'icon': 'clock'}
    
    status_map = {
        'current': {'display': 'Current', 'class': 'success', 'icon': 'check-circle'},
        'completed': {'display': 'Completed', 'class': 'info', 'icon': 'check'},
        'behind': {'display': 'Behind', 'class': 'danger', 'icon': 'exclamation-triangle'}
    }
    
    return status_map.get(status, {'display': 'Unknown', 'class': 'secondary', 'icon': 'question'})


def calculate_completion_timeline(total_owed: float, monthly_payment: float, frequency: str) -> int:
    """Calculate months to completion"""
    if monthly_payment <= 0 or total_owed <= 0:
        return 0
    
    payments_needed = math.ceil(total_owed / monthly_payment)
    frequency_months = normalize_frequency_to_months(frequency)
    
    return ((payments_needed - 1) * frequency_months) + 1


def export_to_csv_string(data: List[Dict], columns: List[str] = None) -> str:
    """Convert data to CSV string"""
    if not data:
        return ""
    
    if not columns:
        columns = list(data[0].keys())
    
    # Header
    csv_lines = [','.join(columns)]
    
    # Data rows
    for row in data:
        csv_row = []
        for col in columns:
            value = row.get(col, '')
            # Escape commas in values
            if isinstance(value, str) and ',' in value:
                value = f'"{value}"'
            csv_row.append(str(value))
        csv_lines.append(','.join(csv_row))
    
    return '\n'.join(csv_lines)