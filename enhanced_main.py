"""
Streamlined main orchestration for payment plan analysis
Simplified and consolidated for better maintainability
"""

from typing import Dict, List, Optional
import sys
import pandas as pd
from datetime import datetime

# Import modules (keeping working parsers and analyzers unchanged)
from enhanced_parsers import EnhancedPaymentPlanParser
from enhanced_analyzers import EnhancedIssueAnalyzer
from enhanced_calculators import EnhancedPaymentCalculator  # Now consolidated
from enhanced_reporters import EnhancedReportGenerator
from utils import format_currency, validate_csv_structure


class PaymentPlanAnalysisSystem:
    """Streamlined payment plan analysis system"""
    
    def __init__(self, output_dir: str = './reports'):
        self.parser = EnhancedPaymentPlanParser()
        self.analyzer = EnhancedIssueAnalyzer()
        self.calculator = EnhancedPaymentCalculator()  # Now handles both metrics and projections
        self.reporter = EnhancedReportGenerator(output_dir)
        self.results = None
        
    def analyze_file(self, csv_path: str, class_filter: str = None) -> Dict:
        """Run complete analysis on a CSV file"""
        print("\n" + "="*80)
        print("PAYMENT PLAN ANALYSIS SYSTEM")
        print("="*80 + "\n")
        
        try:
            # Step 1: Load and validate data
            print("📂 Loading and validating CSV file...")
            self._load_and_validate_csv(csv_path)
            
            # Step 2: Parse customer data
            print("\n📊 Parsing customer data...")
            customers = self._parse_customer_data()
            
            # Step 3: Analyze data quality
            print("\n🔍 Analyzing data quality...")
            clean_customers, problematic_customers = self._analyze_data_quality(customers)
            
            # Step 4: Calculate payment metrics
            print("\n💰 Calculating payment metrics...")
            all_metrics = self._calculate_payment_metrics(clean_customers, class_filter)
            
            # Step 5: Generate reports
            print("\n📝 Generating reports...")
            reports = self._generate_reports(customers, clean_customers, problematic_customers, all_metrics)
            
            # Step 6: Display summary
            self._display_summary(reports)
            
            # Store results
            self.results = {
                'quality_report': reports['quality_report'],
                'dashboard_data': reports['dashboard_data'],
                'portfolio_metrics': reports['portfolio_metrics'],
                'timestamp': self.reporter.timestamp,
                'all_customers': customers,
                'all_metrics': all_metrics,
                'data_quality_report': self.parser.data_quality_report
            }
            
            return self.results
            
        except Exception as e:
            print(f"❌ Analysis failed: {str(e)}")
            return None
    
    def _load_and_validate_csv(self, csv_path: str):
        """Load and validate CSV file"""
        try:
            # Load the file
            self.parser.load_csv(csv_path)
            print("✅ File loaded successfully")
            
            # Basic validation
            issues = validate_csv_structure(self.parser.raw_data)
            if issues:
                print("⚠️  CSV structure issues found:")
                for issue in issues:
                    print(f"   - {issue}")
                if "Missing required columns" in str(issues):
                    raise ValueError("CSV file missing required columns")
            else:
                print("✅ CSV structure validated")
                
        except Exception as e:
            raise ValueError(f"Failed to load CSV: {str(e)}")
    
    def _parse_customer_data(self):
        """Parse customer data from CSV"""
        customers = self.parser.parse_customers()
        total_plans = sum(len(c.payment_plans) for c in customers.values())
        customers_with_multiple_plans = sum(1 for c in customers.values() if c.has_multiple_plans)
        
        print(f"✅ Found {len(customers)} customers with {total_plans} payment plans")
        print(f"   📋 {customers_with_multiple_plans} customers have multiple payment plans")
        
        # Show data quality summary
        if self.parser.data_quality_report:
            report = self.parser.data_quality_report
            print(f"   📊 Processed {report.total_invoices_processed} invoices")
            print(f"   💰 {report.total_invoices_with_open_balance} with open balances")
            print(f"   ✅ {report.total_invoices_ignored} paid invoices ignored")
            if report.classes_found:
                print(f"   🏷️  Classes found: {', '.join(report.classes_found)}")
        
        return customers
    
    def _analyze_data_quality(self, customers):
        """Analyze data quality and categorize customers"""
        categorized = self.analyzer.analyze_all_customers(customers)
        clean_customers = categorized['clean']
        problematic_customers = categorized['problematic']
        
        print(f"✅ Clean customers: {len(clean_customers)}")
        print(f"⚠️  Problematic customers: {len(problematic_customers)}")
        print(f"📋 Total issues found: {len(self.analyzer.issues)}")
        
        # Show issue breakdown
        issue_summary = self.analyzer.get_issue_summary()
        if issue_summary:
            print("\n  Issue types found:")
            for issue_type, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"    - {issue_type.replace('_', ' ').title()}: {count}")
        
        return clean_customers, problematic_customers
    
    def _calculate_payment_metrics(self, clean_customers, class_filter):
        """Calculate payment metrics for clean customers"""
        all_metrics = []
        for customer in clean_customers:
            customer_metrics = self.calculator.calculate_customer_metrics(customer)
            all_metrics.extend(customer_metrics)
        
        print(f"✅ Calculated metrics for {len(all_metrics)} payment plans")
        print(f"   👥 Covering {len(set(m.customer_name for m in all_metrics))} customers")
        
        # Apply class filter if specified
        if class_filter:
            filtered_metrics = [m for m in all_metrics if m.class_field == class_filter]
            print(f"🏷️  Filtered to {len(filtered_metrics)} plans in class '{class_filter}'")
            all_metrics = filtered_metrics
        
        # Calculate portfolio metrics
        portfolio_metrics = self.calculator.calculate_portfolio_metrics(all_metrics)
        self._display_portfolio_summary(portfolio_metrics)
        
        return all_metrics
    
    def _display_portfolio_summary(self, portfolio_metrics):
        """Display portfolio summary"""
        print(f"\n  Portfolio summary:")
        print(f"    - Total customers tracked: {portfolio_metrics['total_customers']}")
        print(f"    - Total plans tracked: {portfolio_metrics['total_plans']}")
        print(f"    - Total tracked balance: {format_currency(portfolio_metrics['total_outstanding'])}")
        print(f"    - Expected monthly: {format_currency(portfolio_metrics['expected_monthly'])}")
        print(f"    - Customers behind: {portfolio_metrics['customers_behind']}")
        
        # Show class breakdown if available
        if portfolio_metrics.get('plans_by_class'):
            print(f"\n  Breakdown by class:")
            for class_name, data in sorted(portfolio_metrics['plans_by_class'].items(), 
                                         key=lambda x: x[1]['total_owed'], reverse=True):
                print(f"    - {class_name}: {data['count']} plans, {format_currency(data['total_owed'])}")
    
    def _generate_reports(self, customers, clean_customers, problematic_customers, all_metrics):
        """Generate all reports"""
        quality_report = self.reporter.generate_comprehensive_quality_report(
            customers, 
            clean_customers,
            problematic_customers,
            self.analyzer.issues,
            self.parser.data_quality_report
        )
        
        dashboard_data = self.reporter.generate_enhanced_dashboard_data(
            customers,
            clean_customers,
            problematic_customers,
            all_metrics
        )
        
        # Calculate portfolio metrics for dashboard
        portfolio_metrics = self.calculator.calculate_portfolio_metrics(all_metrics)
        
        # Save all reports
        timestamp = self.reporter.save_all_reports(
            quality_report,
            dashboard_data,
            self.analyzer.issues,
            all_metrics,
            customers
        )
        
        return {
            'quality_report': quality_report,
            'dashboard_data': dashboard_data,
            'portfolio_metrics': portfolio_metrics,
            'timestamp': timestamp
        }
    
    def _display_summary(self, reports):
        """Display final analysis summary"""
        quality_report = reports['quality_report']
        dashboard_data = reports['dashboard_data']
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        
        print(f"\n📊 OVERVIEW:")
        print(f"  Total Customers: {quality_report['summary']['total_customers']}")
        print(f"  - Clean: {quality_report['summary']['clean_customers']} ({quality_report['summary']['data_quality_score']:.1f}%)")
        print(f"  - Problematic: {quality_report['summary']['problematic_customers']} ({quality_report['summary']['percentage_with_issues']:.1f}%)")
        print(f"  Total Payment Plans: {quality_report['summary']['total_payment_plans']}")
        print(f"  Total Outstanding: {format_currency(quality_report['summary']['total_outstanding'])}")
        
        print(f"\n💵 FINANCIAL TRACKING:")
        print(f"  Tracked: {format_currency(dashboard_data['summary_metrics']['total_outstanding_tracked'])}")
        print(f"  Untracked: {format_currency(dashboard_data['summary_metrics']['total_outstanding_untracked'])}")
        print(f"  Expected Monthly: {format_currency(dashboard_data['summary_metrics']['expected_monthly_collection'])}")
        
        # Show critical issues
        critical_issues = quality_report.get('critical_issues_requiring_immediate_attention', [])
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in critical_issues[:3]:
                print(f"  - {issue['issue_type']}: {issue['customers_affected']} customers affected")
        else:
            print(f"\n🎉 No critical issues found!")
        
        print(f"\n✅ Reports saved with timestamp: {self.reporter.timestamp}")
        print(f"📁 Location: {self.reporter.output_dir}/")
    
    # =====================================
    # CUSTOMER AND PROJECTION METHODS
    # =====================================
    
    def get_customer_details(self, customer_name: str) -> Optional[Dict]:
        """Get detailed information for a specific customer"""
        if not self.results:
            return None
        
        customers = self.results['all_customers']
        customer = customers.get(customer_name)
        
        if not customer:
            return None
        
        # Get metrics for this customer
        customer_metrics = [m for m in self.results['all_metrics'] if m.customer_name == customer_name]
        
        return {
            'customer_info': {
                'name': customer.customer_name,
                'total_plans': len(customer.payment_plans),
                'total_open_balance': customer.total_open_balance,
                'all_classes': customer.all_classes,
                'has_multiple_plans': customer.has_multiple_plans
            },
            'payment_plans': [{
                'plan_id': plan.plan_id,
                'monthly_amount': plan.monthly_amount,
                'frequency': plan.frequency.value,
                'total_open': plan.total_open,
                'class_filter': plan.class_filter,
                'has_issues': plan.has_issues,
                'issues': [issue.to_dict() for issue in plan.issues]
            } for plan in customer.payment_plans],
            'metrics': [self.calculator._metrics_to_dict(m) for m in customer_metrics],
            'payment_roadmaps': [m.payment_roadmap for m in customer_metrics]
        }
    
    def get_payment_projections(self, months_ahead: int = 12, scenario: str = 'current', class_filter: str = None) -> Optional[Dict]:
        """Get payment projections using consolidated calculator"""
        if not self.results:
            return None
        
        try:
            # Get customer data
            customers_data = self.results['all_customers']
            
            # Apply class filter if specified
            if class_filter:
                filtered_customers = {}
                for name, customer in customers_data.items():
                    if class_filter in customer.all_classes:
                        filtered_customers[name] = customer
                customers_data = filtered_customers
            
            # Calculate projections using consolidated calculator
            projections = self.calculator.calculate_customer_projections(
                customers_data, months_ahead, scenario
            )
            
            # Generate portfolio summary
            portfolio_summary = self.calculator.generate_portfolio_summary(projections, months_ahead)
            
            return {
                'customer_projections': [
                    {
                        'customer_name': proj.customer_name,
                        'total_monthly_payment': proj.total_monthly_payment,
                        'total_owed': proj.total_owed,
                        'completion_month': proj.completion_month,
                        'plan_count': proj.plan_count,
                        'timeline': proj.timeline,
                        'status': proj.status,
                        'months_behind': proj.months_behind,
                        'renegotiation_needed': proj.renegotiation_needed
                    } for proj in projections
                ],
                'portfolio_summary': portfolio_summary,
                'parameters': {
                    'months_ahead': months_ahead,
                    'scenario': scenario,
                    'class_filter': class_filter,
                    'total_customers': len(projections)
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculating projections: {str(e)}")
            return None
    
    def get_collection_priorities(self, class_filter: str = None) -> List[Dict]:
        """Get prioritized list for collections"""
        if not self.results:
            return []
        
        metrics = self.results['all_metrics']
        if class_filter:
            metrics = [m for m in metrics if m.class_field == class_filter]
        
        prioritized = self.calculator.prioritize_collections(metrics)
        
        return [{
            'customer_name': m.customer_name,
            'plan_id': m.plan_id,
            'months_behind': m.months_behind,
            'total_owed': m.total_owed,
            'payment_difference': m.payment_difference,
            'class_field': m.class_field,
            'monthly_payment': m.monthly_payment,
            'status': m.status.value
        } for m in prioritized[:20]]  # Top 20
    
    def get_customers_by_class(self, class_name: str) -> List[Dict]:
        """Get all customers in a specific class"""
        if not self.results:
            return []
        
        customers = self.results['all_customers']
        class_customers = []
        
        for customer in customers.values():
            if class_name in customer.all_classes:
                class_customers.append({
                    'customer_name': customer.customer_name,
                    'total_open_balance': customer.total_open_balance,
                    'total_plans': len(customer.payment_plans),
                    'has_issues': any(plan.has_issues for plan in customer.payment_plans)
                })
        
        return sorted(class_customers, key=lambda x: x['total_open_balance'], reverse=True)
    
    def export_for_excel(self, output_path: str = None, include_roadmaps: bool = True):
        """Export analysis results to Excel"""
        if not self.results:
            print("⚠️  No analysis results available. Run analyze_file first.")
            return
        
        if not output_path:
            output_path = f"payment_analysis_{self.results['timestamp']}.xlsx"
        
        try:
            # Use existing reporter functionality
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                self._export_summary_sheet(writer)
                self._export_customer_sheets(writer)
                self._export_metrics_sheets(writer)
            
            print(f"\n📊 Excel report saved: {output_path}")
            
        except Exception as e:
            print(f"❌ Error exporting to Excel: {str(e)}")
    
    def _export_summary_sheet(self, writer):
        """Export summary sheet to Excel"""
        summary_data = {
            'Metric': [
                'Total Customers', 'Clean Customers', 'Problematic Customers',
                'Total Outstanding', 'Expected Monthly', 'Data Quality Score'
            ],
            'Value': [
                self.results['quality_report']['summary']['total_customers'],
                self.results['quality_report']['summary']['clean_customers'],
                self.results['quality_report']['summary']['problematic_customers'],
                format_currency(self.results['quality_report']['summary']['total_outstanding']),
                format_currency(self.results['dashboard_data']['summary_metrics']['expected_monthly_collection']),
                f"{self.results['quality_report']['summary']['data_quality_score']:.1f}%"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
    
    def _export_customer_sheets(self, writer):
        """Export customer data sheets"""
        if self.results['dashboard_data']['customer_summaries']:
            customer_df = pd.DataFrame(self.results['dashboard_data']['customer_summaries'])
            customer_df = customer_df.drop('plan_details', axis=1, errors='ignore')
            customer_df.to_excel(writer, sheet_name='Customers', index=False)
    
    def _export_metrics_sheets(self, writer):
        """Export metrics sheets"""
        if self.results['dashboard_data']['payment_plan_details']:
            plans_df = pd.DataFrame(self.results['dashboard_data']['payment_plan_details'])
            plans_df.to_excel(writer, sheet_name='Payment Plans', index=False)


# Command line interface
def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_main.py <csv_file_path> [output_directory] [class_filter]")
        print("Example: python enhanced_main.py 'payment_plans.csv' './reports' 'BR'")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else './reports'
    class_filter = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Create and run analysis
    system = PaymentPlanAnalysisSystem(output_dir)
    results = system.analyze_file(csv_path, class_filter)
    
    if results:
        # Optionally export to Excel
        response = input("\n📊 Export to Excel? (y/n): ")
        if response.lower() == 'y':
            system.export_for_excel()
        
        # Show collection priorities
        response = input("\n📋 Show collection priorities? (y/n): ")
        if response.lower() == 'y':
            priorities = system.get_collection_priorities(class_filter)
            if priorities:
                print(f"\n🎯 TOP COLLECTION PRIORITIES:")
                for i, priority in enumerate(priorities[:10], 1):
                    print(f"  {i}. {priority['customer_name']} ({priority['plan_id']})")
                    print(f"     {priority['months_behind']} months behind, {format_currency(priority['total_owed'])}")


if __name__ == "__main__":
    main()