"""
CONSOLIDATED Payment Metrics Calculation and Projections
Combines payment metrics calculation and future projections in one module
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
import math

from models import (
    Customer, PaymentPlan, PaymentMetrics, CustomerStatus, 
    PaymentFrequency, PaymentRoadmapEntry
)
from utils import (
    whole_months, cap_deficit_at_balance, get_payment_date_for_month,
    normalize_frequency_to_months, calculate_expected_payments_by_frequency,
    calculate_portfolio_totals, calculate_completion_timeline
)


@dataclass
class CustomerProjection:
    """Customer projection data structure"""
    customer_name: str
    total_monthly_payment: float
    total_owed: float
    completion_month: int
    plan_count: int
    timeline: List[Dict]
    status: str
    months_behind: int
    renegotiation_needed: bool


class EnhancedPaymentCalculator:
    """Consolidated calculator for payment metrics and projections"""
    
    def __init__(self):
        self.payment_day = 15  # Always use 15th of month for payments
        
    def calculate_customer_metrics(self, customer: Customer) -> List[PaymentMetrics]:
        """Calculate metrics for all payment plans for a customer"""
        all_metrics = []
        
        for plan in customer.payment_plans:
            if not plan.has_issues and plan.monthly_amount > 0:
                metrics = self.calculate_plan_metrics(plan)
                if metrics:
                    all_metrics.append(metrics)
        
        return all_metrics
    
    def calculate_plan_metrics(self, plan: PaymentPlan) -> Optional[PaymentMetrics]:
        """Calculate payment metrics for a single payment plan"""
        if plan.has_issues or plan.monthly_amount == 0:
            return None
        
        # Calculate months elapsed (always whole numbers)
        if plan.earliest_date:
            days_elapsed = (datetime.now() - plan.earliest_date).days
            months_elapsed_decimal = days_elapsed / 30.44
            months_elapsed = whole_months(months_elapsed_decimal)
            
            # Calculate expected vs actual payments
            expected_payments = calculate_expected_payments_by_frequency(
                plan.monthly_amount, months_elapsed, plan.frequency.value
            )
            actual_payments = plan.total_original - plan.total_open
            payment_difference = actual_payments - expected_payments
            
            # Calculate months behind (always whole numbers)
            months_behind = self._calculate_months_behind(plan, payment_difference)
            
            # Calculate percentage paid
            percent_paid = ((plan.total_original - plan.total_open) / plan.total_original * 100) if plan.total_original > 0 else 0
            
            # Determine status
            if plan.total_open == 0:
                status = CustomerStatus.COMPLETED
            elif months_behind > 0:
                status = CustomerStatus.BEHIND
            else:
                status = CustomerStatus.CURRENT
            
            # Project completion
            months_remaining, projected_completion = self._calculate_completion(plan)
            
            # Generate payment roadmap
            roadmap = self._generate_payment_roadmap(plan, months_remaining)
            
            return PaymentMetrics(
                customer_name=plan.customer_name,
                plan_id=plan.plan_id,
                monthly_payment=plan.monthly_amount,
                frequency=plan.frequency.value,
                total_owed=plan.total_open,
                original_amount=plan.total_original,
                percent_paid=round(percent_paid, 1),
                months_elapsed=months_elapsed,
                expected_payments=round(expected_payments, 2),
                actual_payments=round(actual_payments, 2),
                payment_difference=round(payment_difference, 2),
                months_behind=months_behind,
                status=status,
                projected_completion=projected_completion,
                months_remaining=months_remaining,
                class_field=plan.class_filter,
                payment_roadmap=roadmap
            )
        
        return None
    
    def _calculate_months_behind(self, plan: PaymentPlan, payment_difference: float) -> int:
        """Calculate months behind - always returns whole numbers"""
        if payment_difference >= 0:
            return 0
        
        # Cap deficit at total owed
        deficit = cap_deficit_at_balance(payment_difference, plan.total_open)
        
        if plan.monthly_amount <= 0:
            return 0
        
        months_behind_decimal = deficit / plan.monthly_amount
        
        # Adjust for frequency
        if plan.frequency == PaymentFrequency.QUARTERLY:
            months_behind_decimal *= 3
        elif plan.frequency == PaymentFrequency.BIMONTHLY:
            months_behind_decimal *= 2
        
        return whole_months(months_behind_decimal)
    
    def _calculate_completion(self, plan: PaymentPlan) -> Tuple[int, Optional[datetime]]:
        """Calculate completion timeline"""
        months_remaining = calculate_completion_timeline(
            plan.total_open, plan.monthly_amount, plan.frequency.value
        )
        
        if months_remaining > 0:
            projected_completion = get_payment_date_for_month(months_remaining, self.payment_day)
        else:
            projected_completion = None
        
        return months_remaining, projected_completion
    
    def _generate_payment_roadmap(self, plan: PaymentPlan, months_remaining: int) -> List[Dict]:
        """Generate payment roadmap"""
        roadmap = []
        
        if plan.monthly_amount <= 0 or months_remaining <= 0:
            return roadmap
        
        current_balance = plan.total_open
        frequency_months = normalize_frequency_to_months(plan.frequency.value)
        payment_number = 1
        max_payments = 60  # Limit to 5 years
        
        for month in range(1, months_remaining + 1, frequency_months):
            if current_balance <= 0 or payment_number > max_payments:
                break
            
            payment_amount = min(plan.monthly_amount, current_balance)
            payment_date = get_payment_date_for_month(month, self.payment_day)
            
            roadmap_entry = {
                'payment_number': payment_number,
                'date': payment_date.strftime('%Y-%m-%d'),
                'expected_payment': round(payment_amount, 2),
                'remaining_balance': round(current_balance - payment_amount, 2),
                'is_overdue': payment_date < datetime.now(),
                'description': f'Payment {payment_number} - {plan.frequency.value}'
            }
            
            roadmap.append(roadmap_entry)
            current_balance -= payment_amount
            payment_number += 1
        
        return roadmap
    
    def calculate_portfolio_metrics(self, all_metrics: List[PaymentMetrics]) -> Dict:
        """Calculate aggregate portfolio metrics"""
        if not all_metrics:
            return self._empty_portfolio_metrics()
        
        # Convert metrics to dict format for utility function
        metrics_dicts = [self._metrics_to_dict(m) for m in all_metrics]
        return calculate_portfolio_totals(metrics_dicts)
    
    def _metrics_to_dict(self, metrics: PaymentMetrics) -> Dict:
        """Convert metrics to dictionary"""
        return {
            'customer_name': metrics.customer_name,
            'total_owed': metrics.total_owed,
            'monthly_payment': metrics.monthly_payment,
            'frequency': metrics.frequency,
            'status': metrics.status.value,
            'months_behind': metrics.months_behind
        }
    
    def _empty_portfolio_metrics(self) -> Dict:
        """Return empty portfolio metrics"""
        return {
            'total_customers': 0,
            'total_plans': 0,
            'total_outstanding': 0,
            'expected_monthly': 0,
            'customers_current': 0,
            'customers_behind': 0,
            'customers_completed': 0
        }
    
    def prioritize_collections(self, all_metrics: List[PaymentMetrics]) -> List[PaymentMetrics]:
        """Prioritize customers for collections"""
        behind_customers = [m for m in all_metrics if m.status == CustomerStatus.BEHIND]
        
        def sort_key(metric):
            capped_difference = cap_deficit_at_balance(metric.payment_difference, metric.total_owed)
            return (-metric.months_behind, -metric.total_owed, -capped_difference)
        
        return sorted(behind_customers, key=sort_key)

    # =============================================
    # PROJECTION FUNCTIONALITY (formerly payment_projections.py)
    # =============================================
    
    def calculate_customer_projections(self, customers_data: Dict, months_ahead: int = 12, scenario: str = 'current') -> List[CustomerProjection]:
        """Calculate payment projections for customers"""
        projections = []
        
        # Extract customer data
        if 'all_customers' in customers_data:
            customers = customers_data['all_customers']
        else:
            customers = customers_data
            
        for customer_name, customer in customers.items():
            projection = self._calculate_single_customer_projection(customer, months_ahead, scenario)
            if projection:
                projections.append(projection)
        
        # Sort by priority: behind customers first, then by monthly payment
        projections.sort(key=lambda x: (
            0 if x.renegotiation_needed else 1,
            -x.total_monthly_payment
        ))
        
        return projections
    
    def _calculate_single_customer_projection(self, customer, months_ahead: int, scenario: str) -> Optional[CustomerProjection]:
        """Calculate projection for a single customer"""
        valid_plans = []
        behind_plans = []
        
        for plan in customer.payment_plans:
            if plan.monthly_amount > 0 and plan.total_open > 0:
                months_behind = self._calculate_months_behind_for_plan(plan)
                
                if months_behind > 0:
                    behind_plans.append((plan, months_behind))
                else:
                    valid_plans.append(plan)
        
        total_months_behind = sum(months for _, months in behind_plans)
        all_plans = valid_plans + [plan for plan, _ in behind_plans]
        
        if not all_plans:
            return None
        
        # Determine projection approach based on scenario
        if total_months_behind > 0:
            if scenario == 'current':
                return self._project_behind_customer_current(customer, all_plans, behind_plans, months_ahead)
            elif scenario == 'restart':
                return self._project_customer_restart(customer, all_plans, months_ahead)
        else:
            return self._project_current_customer(customer, valid_plans, months_ahead)
    
    def _calculate_months_behind_for_plan(self, plan) -> int:
        """Calculate how many months behind a plan is"""
        if not plan.earliest_date:
            return 0
        
        days_elapsed = (datetime.now() - plan.earliest_date).days
        months_elapsed = whole_months(days_elapsed / 30.44)
        
        expected_payments = calculate_expected_payments_by_frequency(
            plan.monthly_amount, months_elapsed, plan.frequency.value
        )
        actual_payments = plan.total_original - plan.total_open
        payment_deficit = expected_payments - actual_payments
        
        if payment_deficit <= 0:
            return 0
        
        capped_deficit = cap_deficit_at_balance(payment_deficit, plan.total_open)
        
        if plan.monthly_amount > 0:
            months_behind_decimal = capped_deficit / plan.monthly_amount
            
            # Adjust for frequency
            if plan.frequency.value == 'quarterly':
                months_behind_decimal *= 3
            elif plan.frequency.value == 'bimonthly':
                months_behind_decimal *= 2
            
            return whole_months(months_behind_decimal)
        
        return 0
    
    def _project_behind_customer_current(self, customer, all_plans, behind_plans, months_ahead) -> CustomerProjection:
        """Project what happens if behind customer continues current behavior"""
        total_months_behind = sum(months for _, months in behind_plans)
        total_monthly = sum(plan.monthly_amount for plan in all_plans)
        total_owed = sum(plan.total_open for plan in all_plans)
        
        timeline = []
        
        for month in range(1, months_ahead + 1):
            month_date = get_payment_date_for_month(month, self.payment_day)
            
            # Behind customers likely won't make regular payments
            monthly_payment = 0
            active_plans = 0
            plan_details = []
            
            # Only include plans that aren't behind
            current_plans = [plan for plan in all_plans if (plan, 0) not in behind_plans]
            
            for plan in current_plans:
                payment_info = self._calculate_plan_payment_for_month(plan, month, 'current')
                if payment_info and payment_info['payment_amount'] > 0:
                    monthly_payment += payment_info['payment_amount']
                    active_plans += 1
                    plan_details.append(payment_info)
            
            timeline.append({
                'month': month,
                'date': month_date.isoformat(),
                'monthly_payment': round(monthly_payment, 2),
                'active_plans': active_plans,
                'plan_details': plan_details,
                'note': 'Behind customer - contact needed' if total_months_behind > 0 else ''
            })
        
        return CustomerProjection(
            customer_name=customer.customer_name,
            total_monthly_payment=total_monthly,
            total_owed=total_owed,
            completion_month=0,
            plan_count=len(all_plans),
            timeline=timeline,
            status='behind' if total_months_behind > 0 else 'current',
            months_behind=total_months_behind,
            renegotiation_needed=total_months_behind > 0
        )
    
    def _project_customer_restart(self, customer, all_plans, months_ahead) -> CustomerProjection:
        """Project what happens if customer restarts payment plan today"""
        total_monthly = sum(plan.monthly_amount for plan in all_plans)
        total_owed = sum(plan.total_open for plan in all_plans)
        
        # Calculate completion assuming they start fresh today
        max_completion_month = 0
        for plan in all_plans:
            plan_completion = calculate_completion_timeline(
                plan.total_open, plan.monthly_amount, plan.frequency.value
            )
            max_completion_month = max(max_completion_month, plan_completion)
        
        completion_month = min(max_completion_month, months_ahead)
        
        # Generate timeline
        timeline = []
        for month in range(1, months_ahead + 1):
            month_date = get_payment_date_for_month(month, self.payment_day)
            
            monthly_payment = 0
            active_plans = 0
            plan_details = []
            
            for plan in all_plans:
                payment_info = self._calculate_plan_payment_for_month(plan, month, 'restart')
                if payment_info and payment_info['payment_amount'] > 0:
                    monthly_payment += payment_info['payment_amount']
                    active_plans += 1
                    plan_details.append(payment_info)
            
            timeline.append({
                'month': month,
                'date': month_date.isoformat(),
                'monthly_payment': round(monthly_payment, 2),
                'active_plans': active_plans,
                'plan_details': plan_details,
                'note': 'Restart scenario' if month == 1 else ''
            })
        
        return CustomerProjection(
            customer_name=customer.customer_name,
            total_monthly_payment=total_monthly,
            total_owed=total_owed,
            completion_month=completion_month,
            plan_count=len(all_plans),
            timeline=timeline,
            status='restart',
            months_behind=0,
            renegotiation_needed=False
        )
    
    def _project_current_customer(self, customer, valid_plans, months_ahead) -> CustomerProjection:
        """Project current customer - normal handling"""
        total_monthly = sum(plan.monthly_amount for plan in valid_plans)
        total_owed = sum(plan.total_open for plan in valid_plans)
        
        # Calculate completion
        max_completion_month = 0
        for plan in valid_plans:
            plan_completion = calculate_completion_timeline(
                plan.total_open, plan.monthly_amount, plan.frequency.value
            )
            max_completion_month = max(max_completion_month, plan_completion)
        
        timeline = []
        for month in range(1, months_ahead + 1):
            month_date = get_payment_date_for_month(month, self.payment_day)
            
            monthly_payment = 0
            active_plans = 0
            plan_details = []
            
            for plan in valid_plans:
                payment_info = self._calculate_plan_payment_for_month(plan, month, 'current')
                if payment_info and payment_info['payment_amount'] > 0:
                    monthly_payment += payment_info['payment_amount']
                    active_plans += 1
                    plan_details.append(payment_info)
            
            timeline.append({
                'month': month,
                'date': month_date.isoformat(),
                'monthly_payment': round(monthly_payment, 2),
                'active_plans': active_plans,
                'plan_details': plan_details
            })
        
        return CustomerProjection(
            customer_name=customer.customer_name,
            total_monthly_payment=total_monthly,
            total_owed=total_owed,
            completion_month=min(max_completion_month, months_ahead),
            plan_count=len(valid_plans),
            timeline=timeline,
            status='current',
            months_behind=0,
            renegotiation_needed=False
        )
    
    def _calculate_plan_payment_for_month(self, plan, month: int, scenario: str) -> Optional[Dict]:
        """Calculate payment for specific plan and month"""
        frequency_months = normalize_frequency_to_months(plan.frequency.value)
        
        # Check if this month is a payment month
        is_payment_month = ((month - 1) % frequency_months) == 0
        
        if not is_payment_month:
            return None
        
        # Calculate payment details
        payment_number = ((month - 1) // frequency_months) + 1
        total_payments_needed = math.ceil(plan.total_open / plan.monthly_amount)
        
        if payment_number > total_payments_needed:
            return None
        
        payment_amount = plan.monthly_amount
        is_final_payment = (payment_number == total_payments_needed)
        
        if is_final_payment:
            # Final payment - pay exact remaining balance
            previous_payments = (payment_number - 1) * plan.monthly_amount
            remaining = max(0, plan.total_open - previous_payments)
            payment_amount = min(payment_amount, remaining)
        
        # Calculate remaining balance
        total_paid_after = payment_number * plan.monthly_amount
        remaining_balance = max(0, plan.total_open - total_paid_after)
        
        if is_final_payment:
            remaining_balance = 0
        
        return {
            'plan_id': plan.plan_id,
            'payment_amount': round(payment_amount, 2),
            'payment_number': payment_number,
            'total_payments': total_payments_needed,
            'frequency': plan.frequency.value,
            'class_field': getattr(plan, 'class_filter', None),
            'is_final_payment': is_final_payment,
            'remaining_balance': round(remaining_balance, 2)
        }
    
    def generate_portfolio_summary(self, projections: List[CustomerProjection], months_ahead: int = 12) -> Dict:
        """Generate portfolio summary with projection data"""
        if not projections:
            return self._empty_portfolio_summary()
        
        monthly_summaries = []
        total_expected = 0
        
        # Categorize customers
        current_customers = [p for p in projections if p.status == 'current']
        behind_customers = [p for p in projections if p.status == 'behind']
        restart_customers = [p for p in projections if p.status == 'restart']
        
        for month in range(1, months_ahead + 1):
            month_total = 0
            active_customers = 0
            completing_customers = 0
            behind_count = 0
            
            for projection in projections:
                if month <= len(projection.timeline):
                    month_data = projection.timeline[month - 1]
                    month_total += month_data['monthly_payment']
                    
                    if month_data['monthly_payment'] > 0:
                        active_customers += 1
                    
                    if projection.status == 'behind':
                        behind_count += 1
                    
                    # Check if any plan completes this month
                    for detail in month_data.get('plan_details', []):
                        if detail.get('is_final_payment', False):
                            completing_customers += 1
            
            total_expected += month_total
            month_date = datetime.now() + relativedelta(months=month)
            
            monthly_summaries.append({
                'month': month,
                'date': month_date.isoformat(),
                'expected_payment': round(month_total, 2),
                'active_customers': active_customers,
                'completing_customers': completing_customers,
                'behind_customers': behind_count,
                'cumulative_total': round(total_expected, 2)
            })
        
        return {
            'monthly_projections': monthly_summaries,
            'summary': {
                'total_customers': len(projections),
                'current_customers': len(current_customers),
                'behind_customers': len(behind_customers),
                'customers_needing_renegotiation': len([p for p in projections if p.renegotiation_needed]),
                'total_expected_collection': round(total_expected, 2),
                'average_monthly': round(total_expected / months_ahead, 2) if months_ahead > 0 else 0,
                'customers_with_payments': len([p for p in projections if any(m['monthly_payment'] > 0 for m in p.timeline)]),
                'total_months_behind': sum(p.months_behind for p in behind_customers),
                'potential_recovery_amount': sum(p.total_owed for p in behind_customers)
            },
            'customer_categories': {
                'current': len(current_customers),
                'behind': len(behind_customers),
                'restart_scenario': len(restart_customers),
                'renegotiation_needed': len([p for p in projections if p.renegotiation_needed])
            }
        }
    
    def _empty_portfolio_summary(self) -> Dict:
        """Return empty portfolio summary"""
        return {
            'monthly_projections': [],
            'summary': {
                'total_customers': 0,
                'total_expected_collection': 0,
                'average_monthly': 0,
                'customers_with_payments': 0
            }
        }
    
    def get_renegotiation_candidates(self, projections: List[CustomerProjection]) -> List[Dict]:
        """Get list of customers who need renegotiation"""
        candidates = []
        
        for projection in projections:
            if projection.renegotiation_needed:
                candidates.append({
                    'customer_name': projection.customer_name,
                    'months_behind': projection.months_behind,
                    'total_owed': projection.total_owed,
                    'current_monthly': projection.total_monthly_payment,
                    'suggested_monthly': projection.total_owed / 30,  # 30-month plan
                    'priority': 'high' if projection.months_behind > 6 else 
                              'medium' if projection.months_behind > 3 else 'low'
                })
        
        # Sort by months behind (most behind first)
        candidates.sort(key=lambda x: -x['months_behind'])
        return candidates