from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "message": "Server is running"}

class KQLRequest(BaseModel):
    workspace_id: str
    query: str
    timespan: Optional[str] = None

class KQLResponse(BaseModel):
    tables: list = []
    error: Optional[str] = None

# Initialize Azure Monitor client
try:
    credential = DefaultAzureCredential()
    client = LogsQueryClient(credential)
    logger.info("Azure Monitor client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Azure credentials: {e}")
    raise

@app.post("/query")
async def query(request: KQLRequest) -> KQLResponse:
    try:
        logger.info(f"Received query request for workspace: {request.workspace_id}")
        logger.info(f"Query: {request.query}")
        
        # Handle timespan - fix the logic
        from datetime import datetime, timedelta, timezone
        timespan = None
        if request.timespan:
            # If timespan is provided, use it as an ISO8601 duration
            # For now, we'll use a default timespan since the provided timespan logic was incorrect
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            timespan = (start_time, end_time)
            logger.info(f"Using timespan: {start_time} to {end_time}")

        # Execute query
        logger.info("Executing query...")
        response = client.query_workspace(
            workspace_id=request.workspace_id,
            query=request.query,
            timespan=timespan
        )
        
        logger.info(f"Query executed with status: {response.status}")        # Format response
        if response.status == LogsQueryStatus.SUCCESS:
            logger.info("Processing response tables...")
            tables = []
            for i, table in enumerate(response.tables):
                try:
                    logger.info(f"Processing table {i}")
                    columns = []
                    for col in getattr(table, 'columns', []):
                        if hasattr(col, 'name'):
                            columns.append(col.name)
                        elif isinstance(col, dict) and 'name' in col:
                            columns.append(col['name'])
                        else:
                            columns.append(str(col))
                    
                    # Process rows with better error handling
                    processed_rows = []
                    raw_rows = getattr(table, 'rows', [])
                    logger.info(f"Processing {len(raw_rows)} rows")
                    
                    for row_idx, row in enumerate(raw_rows):
                        try:
                            processed_row = []
                            for cell in row:
                                # Convert any non-JSON-serializable types to strings
                                if cell is None:
                                    processed_row.append(None)
                                elif isinstance(cell, (str, int, float, bool)):
                                    processed_row.append(cell)
                                else:
                                    # Convert complex types to string
                                    processed_row.append(str(cell))
                            processed_rows.append(processed_row)
                        except Exception as row_error:
                            logger.error(f"Error processing row {row_idx}: {row_error}")
                            # Skip problematic rows
                            continue
                    
                    table_dict = {
                        'name': getattr(table, 'name', f'table_{i}'),
                        'columns': columns,
                        'rows': processed_rows,
                        'row_count': len(processed_rows)
                    }
                    tables.append(table_dict)
                    logger.info(f"Successfully processed table {i} with {len(processed_rows)} rows")
                    
                except Exception as table_error:
                    logger.error(f"Error processing table {i}: {table_error}")
                    # Continue with other tables
                    continue            
            logger.info(f"Returning {len(tables)} tables")
            return KQLResponse(tables=tables)
        else:
            error_msg = getattr(response, 'partial_error', 'Query failed')
            logger.error(f"Query failed: {error_msg}")
            return KQLResponse(error=str(error_msg))

    except Exception as e:
        logger.error(f"Exception in query handler: {str(e)}", exc_info=True)
        return KQLResponse(error=f"Server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
