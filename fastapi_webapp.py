"""
Consolidated FastAPI Web Application for Payment Plan Analysis
Streamlined with unified customer/projections functionality
"""

from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
import tempfile
import shutil
import io
import csv
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

# Import consolidated analysis system
from enhanced_main import PaymentPlanAnalysisSystem
from utils import format_currency, export_to_csv_string

# Initialize FastAPI app
app = FastAPI(
    title="Payment Plan Analysis System",
    description="Consolidated payment plan analysis with unified customer and projections view",
    version="3.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"

# Create directories if they don't exist
for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, REPORTS_DIR]:
    directory.mkdir(exist_ok=True)

# Setup templates and static files
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global analysis system instance
analysis_system = None
current_results = None

def has_analysis_results() -> bool:
    """Check if we have analysis results"""
    return current_results is not None

# =====================================
# CORE PAGE ROUTES
# =====================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Payment Plan Analysis Dashboard",
        "has_results": has_analysis_results()
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page alias"""
    return await dashboard(request)

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, class_filter: Optional[str] = Query(None)):
    """Unified customers and projections page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("customers_unified.html", {
        "request": request,
        "title": "Customer Payment Tracking & Projections",
        "has_results": True,
        "class_filter": class_filter
    })

@app.get("/quality", response_class=HTMLResponse)
async def quality_page(request: Request):
    """Data quality analysis page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("quality.html", {
        "request": request,
        "title": "Data Quality Report",
        "has_results": True
    })

@app.get("/collections", response_class=HTMLResponse)
async def collections_page(request: Request):
    """Collections priority page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("collections.html", {
        "request": request,
        "title": "Collection Priorities",
        "has_results": True
    })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Reports and downloads page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "title": "Reports & Downloads",
        "has_results": True
    })

# =====================================
# CORE API ROUTES
# =====================================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file upload and analysis"""
    global analysis_system, current_results
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Save uploaded file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"upload_{timestamp}_{file.filename}"
    file_path = UPLOADS_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Initialize analysis system
        analysis_system = PaymentPlanAnalysisSystem(str(REPORTS_DIR))
        
        # Run analysis
        results = analysis_system.analyze_file(str(file_path))
        
        if results:
            current_results = results
            return JSONResponse({
                "success": True,
                "message": "File uploaded and analyzed successfully",
                "filename": filename,
                "summary": {
                    "total_customers": results['quality_report']['summary']['total_customers'],
                    "clean_customers": results['quality_report']['summary']['clean_customers'],
                    "problematic_customers": results['quality_report']['summary']['problematic_customers'],
                    "total_outstanding": results['quality_report']['summary']['total_outstanding'],
                    "data_quality_score": results['quality_report']['summary']['data_quality_score']
                }
            })
        else:
            raise HTTPException(status_code=500, detail="Analysis failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()

@app.post("/api/clear")
async def clear_results():
    """Clear current analysis results"""
    global analysis_system, current_results
    
    analysis_system = None
    current_results = None
    
    return JSONResponse({"success": True, "message": "Results cleared"})

# =====================================
# DATA API ROUTES
# =====================================

@app.get("/api/results/summary")
async def get_results_summary():
    """Get analysis results summary"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    return JSONResponse(current_results['quality_report']['summary'])

@app.get("/api/results/dashboard")
async def get_dashboard_data(class_filter: Optional[str] = Query(None)):
    """Get consolidated dashboard data"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    dashboard_data = current_results['dashboard_data']
    
    # Apply class filter if specified
    if class_filter:
        filtered_customers = []
        for customer in dashboard_data['customer_summaries']:
            customer_plans = [plan for plan in customer['plan_details'] 
                            if plan.get('class_field') == class_filter]
            if customer_plans:
                filtered_customer = customer.copy()
                filtered_customer['plan_details'] = customer_plans
                filtered_customers.append(filtered_customer)
        
        dashboard_data = dashboard_data.copy()
        dashboard_data['customer_summaries'] = filtered_customers
        dashboard_data['payment_plan_details'] = [
            plan for plan in dashboard_data['payment_plan_details']
            if plan.get('class_field') == class_filter
        ]
    
    return JSONResponse(dashboard_data)

@app.get("/api/results/quality")
async def get_quality_report():
    """Get detailed quality report"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    return JSONResponse(current_results['quality_report'])

# =====================================
# UNIFIED CUSTOMER & PROJECTIONS API
# =====================================

@app.get("/api/customers/data")
async def get_customers_data(
    class_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("months_behind_desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100)
):
    """Get unified customer data with metrics and basic projections"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        # Get base data
        dashboard_data = current_results['dashboard_data']
        plans = dashboard_data.get('payment_plan_details', [])
        
        # Apply filters
        filtered_plans = plans
        
        if class_filter and class_filter != 'all':
            filtered_plans = [p for p in filtered_plans if p.get('class_field') == class_filter]
        
        if status_filter and status_filter != 'all':
            filtered_plans = [p for p in filtered_plans if p.get('status') == status_filter]
        
        if search:
            search_lower = search.lower()
            filtered_plans = [p for p in filtered_plans if search_lower in p.get('customer_name', '').lower()]
        
        # Sort data
        sort_field, sort_direction = sort_by.split('_') if '_' in sort_by else (sort_by, 'desc')
        reverse = sort_direction == 'desc'
        
        if sort_field == 'months':
            filtered_plans.sort(key=lambda x: x.get('months_behind', 0), reverse=reverse)
        elif sort_field == 'total':
            filtered_plans.sort(key=lambda x: x.get('total_owed', 0), reverse=reverse)
        elif sort_field == 'customer':
            filtered_plans.sort(key=lambda x: x.get('customer_name', ''), reverse=reverse)
        elif sort_field == 'monthly':
            filtered_plans.sort(key=lambda x: x.get('monthly_payment', 0), reverse=reverse)
        
        # Paginate
        total_items = len(filtered_plans)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_data = filtered_plans[start_idx:end_idx]
        
        return JSONResponse({
            "data": page_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total_items,
                "total_pages": (total_items + per_page - 1) // per_page,
                "has_next": end_idx < total_items,
                "has_prev": page > 1
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting customer data: {str(e)}")

@app.get("/api/customers/{customer_name}")
async def get_customer_details(customer_name: str):
    """Get detailed information for a specific customer"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    details = analysis_system.get_customer_details(customer_name)
    if not details:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_name}' not found")
    
    return JSONResponse(details)

@app.get("/api/projections/customers")
async def get_customer_projections(
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$'),
    class_filter: Optional[str] = Query(None)
):
    """Get payment projections for customers"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    try:
        projections = analysis_system.get_payment_projections(months, scenario, class_filter)
        if not projections:
            raise HTTPException(status_code=500, detail="Failed to calculate projections")
        
        return JSONResponse(projections['customer_projections'])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating projections: {str(e)}")

@app.get("/api/projections/portfolio")
async def get_portfolio_projections(
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$'),
    class_filter: Optional[str] = Query(None)
):
    """Get portfolio-wide payment projections"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    try:
        projections = analysis_system.get_payment_projections(months, scenario, class_filter)
        if not projections:
            raise HTTPException(status_code=500, detail="Failed to calculate projections")
        
        return JSONResponse(projections['portfolio_summary'])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating portfolio projections: {str(e)}")

# =====================================
# COLLECTIONS API
# =====================================

@app.get("/api/collections/priorities")
async def get_collection_priorities(class_filter: Optional[str] = Query(None)):
    """Get prioritized collection list"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    priorities = analysis_system.get_collection_priorities(class_filter)
    return JSONResponse(priorities)

# =====================================
# UTILITY API ROUTES
# =====================================

@app.get("/api/classes")
async def get_available_classes():
    """Get list of available classes for filtering"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    classes = current_results['quality_report']['data_processing']['classes_found']
    return JSONResponse({"classes": classes})

@app.get("/api/customers/by-class/{class_name}")
async def get_customers_by_class(class_name: str):
    """Get customers filtered by class"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    customers = analysis_system.get_customers_by_class(class_name)
    return JSONResponse(customers)

# =====================================
# DOWNLOAD ROUTES
# =====================================

@app.get("/api/download/excel")
async def download_excel():
    """Download comprehensive Excel report"""
    if not analysis_system or not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        timestamp = current_results['timestamp']
        excel_filename = f"payment_analysis_{timestamp}.xlsx"
        excel_path = REPORTS_DIR / excel_filename
        
        analysis_system.export_for_excel(str(excel_path))
        
        if excel_path.exists():
            return FileResponse(
                path=str(excel_path),
                filename=excel_filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to generate Excel file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel: {str(e)}")

@app.get("/api/download/collections-csv")
async def download_collections_csv():
    """Download collections list as CSV"""
    if not current_results:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    try:
        # Get behind customers data
        dashboard_data = current_results['dashboard_data']
        plans = dashboard_data.get('payment_plan_details', [])
        behind_plans = [p for p in plans if p.get('months_behind', 0) > 0]
        
        # Prepare CSV data
        csv_data = []
        headers = ['Customer', 'Plan ID', 'Class', 'Months Behind', 'Balance Owed', 'Monthly Payment', 'Status']
        csv_data.append(headers)
        
        for plan in behind_plans:
            csv_data.append([
                plan.get('customer_name', ''),
                plan.get('plan_id', ''),
                plan.get('class_field', ''),
                plan.get('months_behind', 0),
                plan.get('total_owed', 0),
                plan.get('monthly_payment', 0),
                plan.get('status', 'behind')
            ])
        
        # Convert to CSV string
        csv_string = export_to_csv_string([dict(zip(headers, row)) for row in csv_data[1:]], headers)
        
        filename = f"collections_list_{current_results['timestamp']}.csv"
        
        return Response(
            content=csv_string,
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating CSV: {str(e)}")

@app.get("/api/download/customer-projection/{customer_name}")
async def download_customer_projection_csv(
    customer_name: str,
    months: int = Query(12, ge=1, le=60),
    scenario: str = Query('current', regex='^(current|restart)$')
):
    """Download specific customer projection as CSV"""
    if not analysis_system:
        raise HTTPException(status_code=404, detail="No analysis system available")
    
    try:
        # Get customer projections
        projections = analysis_system.get_payment_projections(months, scenario)
        if not projections:
            raise HTTPException(status_code=404, detail="No projections available")
        
        # Find specific customer
        customer_projection = None
        for proj in projections['customer_projections']:
            if proj['customer_name'] == customer_name:
                customer_projection = proj
                break
        
        if not customer_projection:
            raise HTTPException(status_code=404, detail=f"Customer '{customer_name}' not found in projections")
        
        # Prepare CSV data
        csv_data = []
        headers = ['Month', 'Date', 'Payment Amount', 'Active Plans', 'Plan Details']
        csv_data.append(headers)
        
        for month_data in customer_projection['timeline']:
            plan_details = []
            for detail in month_data.get('plan_details', []):
                plan_detail_str = f"{detail['plan_id']}: ${detail['payment_amount']} (Payment {detail['payment_number']}/{detail['total_payments']})"
                plan_details.append(plan_detail_str)
            
            csv_data.append([
                f"Month {month_data['month']}",
                month_data['date'][:10],  # Just date part
                month_data['monthly_payment'],
                month_data['active_plans'],
                '; '.join(plan_details)
            ])
        
        # Convert to CSV string
        csv_string = export_to_csv_string([dict(zip(headers, row)) for row in csv_data[1:]], headers)
        
        filename = f"{customer_name.replace(' ', '_')}_projection_{scenario}.csv"
        
        return Response(
            content=csv_string,
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting customer projection: {str(e)}")

# =====================================
# ERROR HANDLERS
# =====================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {
        "request": request,
        "title": "Page Not Found"
    }, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse("500.html", {
        "request": request,
        "title": "Server Error",
        "error": str(exc)
    }, status_code=500)

# =====================================
# HEALTH & STARTUP
# =====================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("🚀 Consolidated Payment Plan Analysis System Starting...")
    print(f"📁 Reports directory: {REPORTS_DIR}")
    print(f"📁 Uploads directory: {UPLOADS_DIR}")
    print("✅ FastAPI application ready!")

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_webapp:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )