from fastapi import APIRouter, Depends, HTTPException, Request

from platform_runtime.api.schemas import (
    CalcPressRequest,
    CalcStateResponse,
    calc_state_response,
)
from platform_runtime.application.calculator import CalculatorSession

router = APIRouter(prefix="/calc", tags=["calculator"])


def get_session(request: Request) -> CalculatorSession:
    return request.app.state.calc_session


@router.get("/state", response_model=CalcStateResponse)
def state(session: CalculatorSession = Depends(get_session)) -> CalcStateResponse:
    return calc_state_response(session.view())


@router.post("/press", response_model=CalcStateResponse)
def press(
    body: CalcPressRequest,
    session: CalculatorSession = Depends(get_session),
) -> CalcStateResponse:
    """Apply one calculator key; return the new view."""
    try:
        view = session.press(body.key)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"unknown calculator key: {body.key!r}")
    return calc_state_response(view)
