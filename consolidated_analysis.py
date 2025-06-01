"""
Consolidated Payment Plan Analysis System
Combines parsing, analysis, calculation, and reporting into a streamlined engine
"""

import pandas as pd
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import os

# Consolidated Models
class PaymentFrequency(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly" 
    BIMONTHLY = "bimonthly"
    UNDEFINED = "undefined"

class CustomerStatus(Enum):
    CURRENT = "current"
    BEHIND = "behind"
    COMPLETED = "completed"

class IssueSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

@dataclass
class PaymentPlan:
    customer_name: str
    plan_id: str
    monthly_amount: float
    frequency: PaymentFrequency
    total_original: float
    total_open: float
    class_field: Optional[str] = None
    earliest_date: Optional[datetime] = None
    issues: List[str] = field(default_factory=list)
    has_issues: bool = False

@dataclass
class CustomerMetrics:
    customer_name: str
    plan_id: str
    monthly_payment: float
    frequency: str
    total_owed: float
    original_amount: float
    percent_paid: float
    months_behind: int
    status: CustomerStatus
    projected_completion: Optional[datetime]
    class_field: Optional[str] = None

class PaymentPlanAnalysisEngine:
    """Consolidated engine that handles all payment plan analysis tasks"""
    
    def __init__(self, output_dir: str = './reports'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Data storage
        self.raw_data = None
        self.payment_plans = []
        self.customer_metrics = []
        self.issues_found = []
        self.quality_report = {}
        self.portfolio_summary = {}
        
        # Processing stats
        self.stats = {
            'total_rows': 0,
            'total_customers': 0,
            'clean_plans': 0,
            'problematic_plans': 0,
            'classes_found': set()
        }

    def analyze_csv_file(self, csv_path: str, class_filter: str = None) -> Dict[str, Any]:
        """Main analysis method - processes entire CSV and returns complete results"""
        
        print(f"🚀 Starting analysis of {csv_path}")
        
        # Step 1: Load and parse data
        self._load_csv(csv_path)
        self._parse_payment_plans()
        
        # Step 2: Quality analysis
        self._analyze_data_quality()
        
        # Step 3: Calculate metrics
        self._calculate_payment_metrics()
        
        # Step 4: Generate projections
        projections = self._calculate_projections(class_filter)
        
        # Step 5: Compile results
        results = self._compile_results(class_filter, projections)
        
        print(f"✅ Analysis complete: {self.stats['total_customers']} customers, {len(self.payment_plans)} plans")
        
        return results

    def _load_csv(self, csv_path: str):
        """Load and standardize CSV data"""
        try:
            self.raw_data = pd.read_csv(csv_path)
            self.stats['total_rows'] = len(self.raw_data)
            
            # Standardize column names
            column_mapping = {
                'Unnamed: 0': '_0', 'Unnamed: 1': '_1', 'Unnamed: 2': '_2'
            }
            self.raw_data.rename(columns=column_mapping, inplace=True)
            
            print(f"📊 Loaded {self.stats['total_rows']} rows")
            
        except Exception as e:
            raise ValueError(f"Failed to load CSV: {str(e)}")

    def _parse_payment_plans(self):
        """Parse CSV data into payment plans - optimized version"""
        
        current_customer = None
        invoice_groups = {}  # Group invoices by customer and payment terms
        
        for idx, row in self.raw_data.iterrows():
            # Skip empty rows
            if row.isna().all():
                continue
            
            # Customer name detection
            if pd.notna(row.get('_1', '')) and row.get('Type') != 'Invoice':
                potential_customer = str(row.get('_1', '')).strip()
                if not potential_customer.lower().startswith('total'):
                    current_customer = potential_customer
                    continue
            
            # Invoice processing
            if row.get('Type') == 'Invoice' and current_customer:
                open_balance = self._parse_amount(row.get('Open Balance', 0))
                
                # Only process invoices with open balance
                if open_balance > 0:
                    payment_terms = str(row.get('FOB', '')).strip() or 'no_terms'
                    class_field = str(row.get('Class', '')).strip() or None
                    
                    # Group key: customer + normalized payment terms
                    group_key = f"{current_customer}_{self._normalize_payment_terms(payment_terms)}"
                    
                    if group_key not in invoice_groups:
                        invoice_groups[group_key] = {
                            'customer_name': current_customer,
                            'payment_terms': payment_terms,
                            'class_field': class_field,
                            'invoices': [],
                            'total_original': 0,
                            'total_open': 0
                        }
                    
                    # Add invoice data
                    original_amount = self._parse_amount(row.get('Amount', 0))
                    invoice_date = self._parse_date(row.get('Date'))
                    
                    invoice_groups[group_key]['invoices'].append({
                        'number': str(row.get('Num', '')),
                        'date': invoice_date,
                        'original': original_amount,
                        'open': open_balance
                    })
                    
                    invoice_groups[group_key]['total_original'] += original_amount
                    invoice_groups[group_key]['total_open'] += open_balance
                    
                    if class_field:
                        self.stats['classes_found'].add(class_field)
        
        # Convert groups to payment plans
        for plan_idx, (group_key, group_data) in enumerate(invoice_groups.items()):
            if group_data['invoices']:  # Only create plans with invoices
                
                # Parse payment terms
                monthly_amount, frequency = self._parse_payment_terms(group_data['payment_terms'])
                
                # Get date range
                dates = [inv['date'] for inv in group_data['invoices'] if inv['date']]
                earliest_date = min(dates) if dates else None
                
                # Create payment plan
                plan = PaymentPlan(
                    customer_name=group_data['customer_name'],
                    plan_id=f"{group_data['customer_name']}_plan_{plan_idx}",
                    monthly_amount=monthly_amount,
                    frequency=frequency,
                    total_original=group_data['total_original'],
                    total_open=group_data['total_open'],
                    class_field=group_data['class_field'],
                    earliest_date=earliest_date
                )
                
                self.payment_plans.append(plan)
        
        # Update stats
        self.stats['total_customers'] = len(set(plan.customer_name for plan in self.payment_plans))
        
        print(f"📋 Created {len(self.payment_plans)} payment plans for {self.stats['total_customers']} customers")

    def _analyze_data_quality(self):
        """Analyze data quality and identify issues"""
        
        for plan in self.payment_plans:
            issues = []
            
            # Check for missing payment terms
            if plan.monthly_amount == 0 or plan.frequency == PaymentFrequency.UNDEFINED:
                issues.append("no_payment_terms")
                plan.has_issues = True
            
            # Check for invalid amounts
            if plan.total_open < 0 or plan.total_original < 0:
                issues.append("invalid_amounts")
                plan.has_issues = True
            
            # Check for impossible balances
            if plan.total_open > plan.total_original:
                issues.append("impossible_balance")
                plan.has_issues = True
            
            # Check for missing class
            if not plan.class_field:
                issues.append("missing_class")
            
            plan.issues = issues
            if issues:
                self.issues_found.extend(issues)
        
        # Update stats
        self.stats['clean_plans'] = len([p for p in self.payment_plans if not p.has_issues])
        self.stats['problematic_plans'] = len([p for p in self.payment_plans if p.has_issues])
        
        print(f"🔍 Quality analysis: {self.stats['clean_plans']} clean, {self.stats['problematic_plans']} problematic")

    def _calculate_payment_metrics(self):
        """Calculate payment metrics for clean plans"""
        
        for plan in self.payment_plans:
            if not plan.has_issues and plan.monthly_amount > 0:
                
                # Calculate months elapsed and behind
                months_elapsed = self._calculate_months_elapsed(plan)
                months_behind = self._calculate_months_behind(plan, months_elapsed)
                
                # Calculate payment percentages
                percent_paid = ((plan.total_original - plan.total_open) / plan.total_original * 100) if plan.total_original > 0 else 0
                
                # Determine status
                if plan.total_open == 0:
                    status = CustomerStatus.COMPLETED
                elif months_behind > 0:
                    status = CustomerStatus.BEHIND
                else:
                    status = CustomerStatus.CURRENT
                
                # Project completion
                projected_completion = self._calculate_completion_date(plan)
                
                # Create metrics
                metrics = CustomerMetrics(
                    customer_name=plan.customer_name,
                    plan_id=plan.plan_id,
                    monthly_payment=plan.monthly_amount,
                    frequency=plan.frequency.value,
                    total_owed=plan.total_open,
                    original_amount=plan.total_original,
                    percent_paid=round(percent_paid, 1),
                    months_behind=months_behind,
                    status=status,
                    projected_completion=projected_completion,
                    class_field=plan.class_field
                )
                
                self.customer_metrics.append(metrics)
        
        print(f"💰 Calculated metrics for {len(self.customer_metrics)} payment plans")

    def _calculate_projections(self, class_filter: str = None, months_ahead: int = 12) -> Dict[str, Any]:
        """Calculate payment projections"""
        
        # Filter metrics if class specified
        metrics_to_project = self.customer_metrics
        if class_filter:
            metrics_to_project = [m for m in self.customer_metrics if m.class_field == class_filter]
        
        # Generate monthly projections
        monthly_projections = []
        total_expected = 0
        
        for month in range(1, months_ahead + 1):
            month_date = datetime.now() + timedelta(days=month * 30)
            month_total = 0
            active_customers = 0
            
            for metrics in metrics_to_project:
                if metrics.status != CustomerStatus.COMPLETED:
                    # Check if this customer has a payment this month
                    if self._is_payment_month(metrics, month):
                        payment_amount = min(metrics.monthly_payment, metrics.total_owed)
                        month_total += payment_amount
                        active_customers += 1
            
            total_expected += month_total
            monthly_projections.append({
                'month': month,
                'date': month_date.isoformat(),
                'expected_payment': round(month_total, 2),
                'active_customers': active_customers,
                'cumulative_total': round(total_expected, 2)
            })
        
        return {
            'monthly_projections': monthly_projections,
            'summary': {
                'total_expected_collection': round(total_expected, 2),
                'average_monthly': round(total_expected / months_ahead, 2),
                'customers_tracked': len(metrics_to_project)
            }
        }

    def _compile_results(self, class_filter: str, projections: Dict) -> Dict[str, Any]:
        """Compile all analysis results into final structure"""
        
        # Calculate portfolio metrics
        behind_customers = [m for m in self.customer_metrics if m.status == CustomerStatus.BEHIND]
        current_customers = [m for m in self.customer_metrics if m.status == CustomerStatus.CURRENT]
        completed_customers = [m for m in self.customer_metrics if m.status == CustomerStatus.COMPLETED]
        
        total_outstanding = sum(m.total_owed for m in self.customer_metrics)
        expected_monthly = sum(self._normalize_to_monthly(m) for m in self.customer_metrics)
        
        # Create comprehensive results
        results = {
            'timestamp': self.timestamp,
            'processing_stats': {
                'total_rows_processed': self.stats['total_rows'],
                'total_customers': self.stats['total_customers'],
                'total_plans': len(self.payment_plans),
                'clean_plans': self.stats['clean_plans'],
                'problematic_plans': self.stats['problematic_plans'],
                'classes_found': sorted(list(self.stats['classes_found']))
            },
            'quality_summary': {
                'data_quality_score': round((self.stats['clean_plans'] / max(len(self.payment_plans), 1)) * 100, 1),
                'total_issues': len(self.issues_found),
                'critical_issues': len([i for i in self.issues_found if i in ['no_payment_terms', 'invalid_amounts']]),
                'issue_types': list(set(self.issues_found))
            },
            'financial_summary': {
                'total_outstanding': round(total_outstanding, 2),
                'expected_monthly': round(expected_monthly, 2),
                'customers_behind': len(behind_customers),
                'customers_current': len(current_customers),
                'customers_completed': len(completed_customers),
                'percentage_behind': round(len(behind_customers) / max(len(self.customer_metrics), 1) * 100, 1)
            },
            'customer_details': self._format_customer_details(),
            'payment_projections': projections,
            'collection_priorities': self._get_collection_priorities()
        }
        
        # Save results to files
        self._save_results(results)
        
        return results

    def _format_customer_details(self) -> List[Dict]:
        """Format customer metrics for API consumption"""
        return [
            {
                'customer_name': m.customer_name,
                'plan_id': m.plan_id,
                'monthly_payment': m.monthly_payment,
                'frequency': m.frequency,
                'total_owed': m.total_owed,
                'original_amount': m.original_amount,
                'percent_paid': m.percent_paid,
                'months_behind': m.months_behind,
                'status': m.status.value,
                'projected_completion': m.projected_completion.isoformat() if m.projected_completion else None,
                'class_field': m.class_field
            }
            for m in self.customer_metrics
        ]

    def _get_collection_priorities(self) -> List[Dict]:
        """Get prioritized collection list"""
        behind_customers = [m for m in self.customer_metrics if m.status == CustomerStatus.BEHIND]
        
        # Sort by months behind (desc) then by amount (desc)
        behind_customers.sort(key=lambda x: (-x.months_behind, -x.total_owed))
        
        return [
            {
                'customer_name': m.customer_name,
                'plan_id': m.plan_id,
                'months_behind': m.months_behind,
                'total_owed': m.total_owed,
                'monthly_payment': m.monthly_payment,
                'class_field': m.class_field,
                'priority_score': m.months_behind * 10 + (m.total_owed / 1000)
            }
            for m in behind_customers[:20]  # Top 20
        ]

    def _save_results(self, results: Dict):
        """Save results to JSON files"""
        
        # Save main results
        with open(self.output_dir / f'analysis_results_{self.timestamp}.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save customer metrics as CSV
        if self.customer_metrics:
            df = pd.DataFrame([
                {
                    'Customer': m.customer_name,
                    'Plan_ID': m.plan_id,
                    'Monthly_Payment': m.monthly_payment,
                    'Frequency': m.frequency,
                    'Total_Owed': m.total_owed,
                    'Percent_Paid': m.percent_paid,
                    'Months_Behind': m.months_behind,
                    'Status': m.status.value,
                    'Class': m.class_field
                }
                for m in self.customer_metrics
            ])
            df.to_csv(self.output_dir / f'customer_metrics_{self.timestamp}.csv', index=False)
        
        print(f"💾 Results saved to {self.output_dir}")

    # Utility methods (consolidated and optimized)
    
    def _parse_amount(self, value) -> float:
        """Parse monetary amount"""
        if pd.isna(value) or value == '':
            return 0.0
        try:
            cleaned = str(value).replace('$', '').replace(',', '').strip()
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

    def _parse_date(self, date_str) -> Optional[datetime]:
        """Parse date string"""
        if pd.isna(date_str):
            return None
        try:
            return pd.to_datetime(date_str)
        except:
            return None

    def _normalize_payment_terms(self, terms: str) -> str:
        """Normalize payment terms for grouping"""
        if not terms or terms == 'no_terms':
            return 'no_terms'
        
        normalized = str(terms).lower().strip()
        # Apply common corrections
        corrections = {
            'quaterly': 'quarterly', 'qtrly': 'quarterly',
            'montly': 'monthly', 'per month': 'monthly'
        }
        
        for wrong, right in corrections.items():
            normalized = normalized.replace(wrong, right)
        
        return normalized

    def _parse_payment_terms(self, terms: str) -> Tuple[float, PaymentFrequency]:
        """Parse payment terms to extract amount and frequency"""
        if not terms or terms == 'no_terms':
            return 0.0, PaymentFrequency.UNDEFINED
        
        terms_lower = str(terms).lower()
        
        # Extract amount
        import re
        amount_match = re.search(r'(\d+(?:\.\d{2})?)', terms_lower)
        amount = float(amount_match.group(1)) if amount_match else 0.0
        
        # Determine frequency
        if any(word in terms_lower for word in ['quarterly', 'qtrly']):
            frequency = PaymentFrequency.QUARTERLY
        elif any(word in terms_lower for word in ['bimonthly', 'bi-monthly']):
            frequency = PaymentFrequency.BIMONTHLY
        elif any(word in terms_lower for word in ['monthly', 'month']):
            frequency = PaymentFrequency.MONTHLY
        else:
            frequency = PaymentFrequency.UNDEFINED
        
        return amount, frequency

    def _calculate_months_elapsed(self, plan: PaymentPlan) -> int:
        """Calculate months elapsed since earliest invoice"""
        if not plan.earliest_date:
            return 0
        
        days_elapsed = (datetime.now() - plan.earliest_date).days
        return math.ceil(days_elapsed / 30.44)  # Always round up to whole months

    def _calculate_months_behind(self, plan: PaymentPlan, months_elapsed: int) -> int:
        """Calculate months behind (always whole numbers)"""
        if months_elapsed <= 0 or plan.monthly_amount <= 0:
            return 0
        
        # Calculate expected payments based on frequency
        if plan.frequency == PaymentFrequency.MONTHLY:
            expected_payments = months_elapsed * plan.monthly_amount
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            expected_payments = (months_elapsed // 3) * plan.monthly_amount
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            expected_payments = (months_elapsed // 2) * plan.monthly_amount
        else:
            expected_payments = months_elapsed * plan.monthly_amount
        
        actual_payments = plan.total_original - plan.total_open
        payment_deficit = expected_payments - actual_payments
        
        if payment_deficit <= 0:
            return 0
        
        # Cap deficit at total owed and convert to months
        capped_deficit = min(payment_deficit, plan.total_open)
        months_behind = capped_deficit / plan.monthly_amount
        
        # Adjust for frequency and return whole months
        if plan.frequency == PaymentFrequency.QUARTERLY:
            months_behind *= 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            months_behind *= 2
        
        return math.ceil(months_behind)

    def _calculate_completion_date(self, plan: PaymentPlan) -> Optional[datetime]:
        """Calculate projected completion date"""
        if plan.monthly_amount <= 0 or plan.total_open <= 0:
            return None
        
        payments_remaining = math.ceil(plan.total_open / plan.monthly_amount)
        
        # Convert to months based on frequency
        if plan.frequency == PaymentFrequency.MONTHLY:
            months_remaining = payments_remaining
        elif plan.frequency == PaymentFrequency.QUARTERLY:
            months_remaining = payments_remaining * 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            months_remaining = payments_remaining * 2
        else:
            months_remaining = payments_remaining
        
        # Project to 15th of target month
        completion_date = datetime.now().replace(day=15)
        for _ in range(months_remaining):
            if completion_date.month == 12:
                completion_date = completion_date.replace(year=completion_date.year + 1, month=1)
            else:
                completion_date = completion_date.replace(month=completion_date.month + 1)
        
        return completion_date

    def _normalize_to_monthly(self, metrics: CustomerMetrics) -> float:
        """Normalize payment to monthly amount"""
        if metrics.frequency == 'monthly':
            return metrics.monthly_payment
        elif metrics.frequency == 'quarterly':
            return metrics.monthly_payment / 3
        elif metrics.frequency == 'bimonthly':
            return metrics.monthly_payment / 2
        return metrics.monthly_payment

    def _is_payment_month(self, metrics: CustomerMetrics, month: int) -> bool:
        """Check if customer has payment in given month based on frequency"""
        if metrics.frequency == 'monthly':
            return True
        elif metrics.frequency == 'quarterly':
            return (month - 1) % 3 == 0
        elif metrics.frequency == 'bimonthly':
            return (month - 1) % 2 == 0
        return True

    # Public API methods for web interface
    
    def get_dashboard_data(self, class_filter: str = None) -> Dict:
        """Get formatted dashboard data"""
        if not hasattr(self, 'results'):
            return {}
        
        # Apply class filter if specified
        metrics = self.customer_metrics
        if class_filter:
            metrics = [m for m in metrics if m.class_field == class_filter]
        
        return {
            'summary_metrics': self.results['financial_summary'],
            'customer_summaries': self._group_by_customer(metrics),
            'payment_plan_details': [m.__dict__ for m in metrics]
        }

    def get_quality_report(self) -> Dict:
        """Get quality analysis report"""
        return {
            'summary': self.results['processing_stats'],
            'quality_metrics': self.results['quality_summary'],
            'issue_breakdown': {issue: self.issues_found.count(issue) for issue in set(self.issues_found)},
            'problematic_customers': [
                {
                    'customer_name': plan.customer_name,
                    'total_open': plan.total_open,
                    'issues': plan.issues
                }
                for plan in self.payment_plans if plan.has_issues
            ]
        }

    def get_collection_priorities(self, class_filter: str = None) -> List[Dict]:
        """Get collection priorities"""
        priorities = self.results['collection_priorities']
        if class_filter:
            priorities = [p for p in priorities if p.get('class_field') == class_filter]
        return priorities

    def _group_by_customer(self, metrics: List[CustomerMetrics]) -> List[Dict]:
        """Group metrics by customer for customer summary view"""
        customer_groups = {}
        
        for metric in metrics:
            if metric.customer_name not in customer_groups:
                customer_groups[metric.customer_name] = {
                    'customer_name': metric.customer_name,
                    'plan_details': [],
                    'total_owed': 0,
                    'total_monthly': 0,
                    'worst_status': CustomerStatus.CURRENT,
                    'worst_months_behind': 0
                }
            
            group = customer_groups[metric.customer_name]
            group['plan_details'].append(metric.__dict__)
            group['total_owed'] += metric.total_owed
            group['total_monthly'] += self._normalize_to_monthly(metric)
            
            # Track worst status
            if metric.status == CustomerStatus.BEHIND:
                group['worst_status'] = CustomerStatus.BEHIND
                group['worst_months_behind'] = max(group['worst_months_behind'], metric.months_behind)
        
        return list(customer_groups.values())

# Example usage
if __name__ == "__main__":
    engine = PaymentPlanAnalysisEngine('./reports')
    results = engine.analyze_csv_file('payment_plans.csv')
    print(f"Analysis complete! Results: {json.dumps(results['financial_summary'], indent=2)}")