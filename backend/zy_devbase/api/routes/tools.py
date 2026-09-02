from fastapi import APIRouter, Depends

from zy_devbase.api.dependencies import get_runtime
from zy_devbase.api.schemas import (
    ToolDescriptorResponse,
    ToolListResponse,
    tool_descriptor_response,
)
from zy_devbase.application.job_runtime import JobRuntime

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
def list_tools(runtime: JobRuntime = Depends(get_runtime)) -> ToolListResponse:
    """Return all registered tool descriptors for the frontend nav layer."""
    return ToolListResponse(
        tools=[tool_descriptor_response(d) for d in runtime.registry().descriptors()]
    )
