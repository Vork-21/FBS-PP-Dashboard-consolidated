"""
FINAL Streamlined FastAPI Web Application for Payment Plan Analysis
All errors fixed - ready to run
"""

from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Query, Form
from fastapi import Path as FastAPIPath  # Avoid conflict with pathlib.Path
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
import tempfile
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import math

# Import our consolidated analysis engine
try:
    from consolidated_analysis import PaymentPlanAnalysisEngine
except ImportError:
    print("❌ Error: consolidated_analysis.py not found!")
    print("📝 Make sure consolidated_analysis.py is in the same directory as streamlined_webapp.py")
    exit(1)

# Initialize FastAPI app
app = FastAPI(
    title="Payment Plan Analysis System",
    description="Streamlined payment plan analysis with consolidated backend",
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

# Create directories
for directory in [TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, REPORTS_DIR]:
    directory.mkdir(exist_ok=True)

# Setup templates and static files
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global analysis engine instance
analysis_engine = None

def has_analysis_results() -> bool:
    """Check if we have analysis results"""
    return analysis_engine is not None and hasattr(analysis_engine, 'results')

# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Payment Plan Analysis Dashboard",
        "has_results": has_analysis_results()
    })

# ============================================================================
# CONSOLIDATED API ENDPOINTS
# ============================================================================

@app.post("/api/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    class_filter: Optional[str] = Form(None)
):
    """Single endpoint for file upload and complete analysis"""
    global analysis_engine
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Save uploaded file temporarily
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_path = UPLOADS_DIR / f"upload_{timestamp}_{file.filename}"
    
    try:
        # Save file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Initialize and run analysis
        analysis_engine = PaymentPlanAnalysisEngine(str(REPORTS_DIR))
        results = analysis_engine.analyze_csv_file(str(temp_path), class_filter)
        
        # Store results in engine for later API calls
        analysis_engine.results = results
        
        return JSONResponse({
            "success": True,
            "message": "Analysis completed successfully",
            "summary": results['financial_summary'],
            "quality_score": results['quality_summary']['data_quality_score'],
            "timestamp": results['timestamp']
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()

@app.get("/api/data")
async def get_data(
    view: str = Query("dashboard", description="Data view type"),
    class_filter: Optional[str] = Query(None),
    months_ahead: int = Query(12, ge=1, le=60)
):
    """Unified data endpoint - returns different views of the analysis results"""
    
    if not analysis_engine or not hasattr(analysis_engine, 'results'):
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    # Validate view parameter
    valid_views = ["dashboard", "quality", "collections", "projections"]
    if view not in valid_views:
        raise HTTPException(status_code=400, detail=f"Invalid view. Must be one of: {valid_views}")
    
    try:
        if view == "dashboard":
            return analysis_engine.get_dashboard_data(class_filter)
            
        elif view == "quality":
            return analysis_engine.get_quality_report()
            
        elif view == "collections":
            return {
                "priorities": analysis_engine.get_collection_priorities(class_filter),
                "summary": analysis_engine.results['financial_summary']
            }
            
        elif view == "projections":
            # Recalculate projections with current parameters
            projections = analysis_engine._calculate_projections(class_filter, months_ahead)
            
            # Add customer-level projections
            customer_projections = analysis_engine._generate_customer_projections(
                class_filter, months_ahead
            )
            
            return {
                "portfolio": projections,
                "customers": customer_projections,
                "parameters": {
                    "months_ahead": months_ahead,
                    "class_filter": class_filter
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving {view} data: {str(e)}")

@app.get("/api/customer/{customer_name}")
async def get_customer_details(customer_name: str):
    """Get detailed information for a specific customer"""
    
    if not analysis_engine:
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    # Find customer in results
    customer_data = None
    dashboard_data = analysis_engine.get_dashboard_data()
    
    for customer in dashboard_data.get('customer_summaries', []):
        if customer['customer_name'] == customer_name:
            customer_data = customer
            break
    
    if not customer_data:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_name}' not found")
    
    return customer_data

@app.get("/api/export/{format_type}")
async def export_data(
    format_type: str = FastAPIPath(..., description="Export format type"),
    view: str = Query("complete", description="Data view to export"),
    class_filter: Optional[str] = Query(None)
):
    """Unified export endpoint for different formats and views"""
    
    if not analysis_engine or not hasattr(analysis_engine, 'results'):
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    # Validate parameters
    valid_formats = ["excel", "csv", "json"]
    valid_views = ["complete", "dashboard", "collections", "quality"]
    
    if format_type not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid format. Must be one of: {valid_formats}")
    
    if view not in valid_views:
        raise HTTPException(status_code=400, detail=f"Invalid view. Must be one of: {valid_views}")
    
    try:
        timestamp = analysis_engine.results['timestamp']
        
        if format_type == "json":
            # Export JSON data
            if view == "complete":
                data = analysis_engine.results
            else:
                data = await get_data(view=view, class_filter=class_filter)
            
            filename = f"{view}_data_{timestamp}.json"
            json_path = REPORTS_DIR / filename
            
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            return FileResponse(
                path=str(json_path),
                filename=filename,
                media_type='application/json'
            )
            
        elif format_type == "csv":
            # Export CSV data
            import pandas as pd
            
            if view == "collections":
                # Export collections data
                priorities = analysis_engine.get_collection_priorities(class_filter)
                df = pd.DataFrame(priorities)
                filename = f"collections_{timestamp}.csv"
            else:
                # Export customer metrics
                dashboard_data = analysis_engine.get_dashboard_data(class_filter)
                df = pd.DataFrame(dashboard_data.get('payment_plan_details', []))
                filename = f"{view}_data_{timestamp}.csv"
            
            csv_path = REPORTS_DIR / filename
            df.to_csv(csv_path, index=False)
            
            return FileResponse(
                path=str(csv_path),
                filename=filename,
                media_type='text/csv'
            )
            
        elif format_type == "excel":
            # Export Excel file with multiple sheets
            filename = f"payment_analysis_{timestamp}.xlsx"
            excel_path = REPORTS_DIR / filename
            
            # Create comprehensive Excel export
            analysis_engine._create_excel_export(str(excel_path), class_filter)
            
            return FileResponse(
                path=str(excel_path),
                filename=filename,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/classes")
async def get_available_classes():
    """Get list of available classes for filtering"""
    if not analysis_engine or not hasattr(analysis_engine, 'results'):
        raise HTTPException(status_code=404, detail="No analysis results available")
    
    classes = analysis_engine.results['processing_stats']['classes_found']
    return {"classes": classes}

@app.post("/api/clear")
async def clear_results():
    """Clear current analysis results"""
    global analysis_engine
    analysis_engine = None
    return JSONResponse({"success": True, "message": "Results cleared"})

# ============================================================================
# PAGE ROUTES
# ============================================================================

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
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Data Quality Report",
        "has_results": True
    })

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, class_filter: Optional[str] = Query(None)):
    """Customer details page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Customer Payment Tracking",
        "has_results": True,
        "class_filter": class_filter
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
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Collection Priorities",
        "has_results": True
    })

@app.get("/projections", response_class=HTMLResponse)
async def projections_page(request: Request):
    """Payment projections page"""
    if not has_analysis_results():
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Upload File - Payment Plan Analysis",
            "has_results": False,
            "error": "No analysis results available. Please upload a file first."
        })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Payment Projections",
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
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Reports & Downloads",
        "has_results": True
    })

# ============================================================================
# ENHANCED ANALYSIS ENGINE METHODS
# ============================================================================

def _generate_customer_projections(self, class_filter: str = None, months_ahead: int = 12) -> list[Dict]:
    """Generate customer-level projections"""
    metrics = self.customer_metrics
    if class_filter:
        metrics = [m for m in metrics if m.class_field == class_filter]
    
    customer_projections = []
    
    # Group by customer
    customer_groups = {}
    for metric in metrics:
        if metric.customer_name not in customer_groups:
            customer_groups[metric.customer_name] = []
        customer_groups[metric.customer_name].append(metric)
    
    for customer_name, customer_metrics_list in customer_groups.items():
        total_monthly = sum(self._normalize_to_monthly(m) for m in customer_metrics_list)
        total_owed = sum(m.total_owed for m in customer_metrics_list)
        worst_status = max((m.status for m in customer_metrics_list), key=lambda s: ['current', 'completed', 'behind'].index(s.value))
        
        # Calculate completion
        if total_monthly > 0 and total_owed > 0:
            completion_months = math.ceil(total_owed / total_monthly)
            completion_month = min(completion_months, months_ahead)
        else:
            completion_month = 0
        
        # Generate timeline
        timeline = []
        remaining_balance = total_owed
        
        for month in range(1, months_ahead + 1):
            monthly_payment = 0
            active_plans = 0
            
            if remaining_balance > 0:
                for metric in customer_metrics_list:
                    if self._is_payment_month(metric, month):
                        payment = min(metric.monthly_payment, metric.total_owed)
                        monthly_payment += payment
                        active_plans += 1
                
                remaining_balance = max(0, remaining_balance - monthly_payment)
            
            timeline.append({
                'month': month,
                'monthly_payment': round(monthly_payment, 2),
                'active_plans': active_plans,
                'remaining_balance': round(remaining_balance, 2)
            })
        
        customer_projections.append({
            'customer_name': customer_name,
            'total_monthly_payment': round(total_monthly, 2),
            'total_owed': round(total_owed, 2),
            'completion_month': completion_month,
            'plan_count': len(customer_metrics_list),
            'status': worst_status.value,
            'timeline': timeline
        })
    
    return customer_projections

def _create_excel_export(self, excel_path: str, class_filter: str = None):
    """Create comprehensive Excel export"""
    import pandas as pd
    from openpyxl import Workbook
    
    # Get data
    dashboard_data = self.get_dashboard_data(class_filter)
    quality_data = self.get_quality_report()
    collections_data = self.get_collection_priorities(class_filter)
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        
        # Sheet 1: Summary
        summary_data = {
            'Metric': [
                'Total Customers',
                'Total Plans',
                'Data Quality Score',
                'Total Outstanding',
                'Expected Monthly',
                'Customers Behind',
                'Clean Plans',
                'Problematic Plans'
            ],
            'Value': [
                self.results['processing_stats']['total_customers'],
                self.results['processing_stats']['total_plans'],
                f"{self.results['quality_summary']['data_quality_score']}%",
                f"${self.results['financial_summary']['total_outstanding']:,.2f}",
                f"${self.results['financial_summary']['expected_monthly']:,.2f}",
                self.results['financial_summary']['customers_behind'],
                self.results['processing_stats']['clean_plans'],
                self.results['processing_stats']['problematic_plans']
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        # Sheet 2: Customer Details
        if dashboard_data.get('payment_plan_details'):
            plans_df = pd.DataFrame(dashboard_data['payment_plan_details'])
            plans_df.to_excel(writer, sheet_name='Payment Plans', index=False)
        
        # Sheet 3: Collections
        if collections_data:
            collections_df = pd.DataFrame(collections_data)
            collections_df.to_excel(writer, sheet_name='Collections', index=False)
        
        # Sheet 4: Quality Issues
        if quality_data.get('problematic_customers'):
            quality_df = pd.DataFrame(quality_data['problematic_customers'])
            quality_df.to_excel(writer, sheet_name='Quality Issues', index=False)

# Add methods to engine class
PaymentPlanAnalysisEngine._generate_customer_projections = _generate_customer_projections
PaymentPlanAnalysisEngine._create_excel_export = _create_excel_export

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Page Not Found",
        "has_results": has_analysis_results(),
        "error": "Page not found"
    }, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Server Error",
        "has_results": has_analysis_results(),
        "error": f"Server error: {str(exc)}"
    }, status_code=500)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "has_results": has_analysis_results()
    }

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("🚀 Streamlined Payment Plan Analysis System Starting...")
    print(f"📁 Reports directory: {REPORTS_DIR}")
    print(f"📁 Uploads directory: {UPLOADS_DIR}")
    print("✅ FastAPI application ready!")

if __name__ == "__main__":
    uvicorn.run(
        "streamlined_webapp:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )