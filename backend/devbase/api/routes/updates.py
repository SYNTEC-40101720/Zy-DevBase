from fastapi import APIRouter, Depends, Request

from devbase import __version__
from devbase.api.dependencies import require_local_token
from devbase.api.schemas import UpdateCheckResponse
from devbase.application.update_checker import GitHubReleaseClient

router = APIRouter(
    prefix="/updates",
    tags=["updates"],
    dependencies=[Depends(require_local_token)],
)


@router.get("/check", response_model=UpdateCheckResponse)
def check_update(request: Request) -> UpdateCheckResponse:
    client: GitHubReleaseClient = request.app.state.update_client
    result = client.check(__version__)
    return UpdateCheckResponse(
        current=str(result.current),
        latest=None if result.latest is None else str(result.latest),
        available=result.available,
        release_url=None if result.release is None else result.release.html_url,
        error=result.error,
    )
