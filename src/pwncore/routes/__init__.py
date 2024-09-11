from fastapi import APIRouter

from pwncore.routes import admin, auth, ctf, leaderboard, powerups, round2, team

# from pwncore.config import config

# Main router (all routes go under /api)
router = APIRouter(prefix="/api")

# Include all the subroutes
router.include_router(auth.router)
router.include_router(ctf.router)
router.include_router(team.router)
router.include_router(leaderboard.router)
router.include_router(round2.router)
router.include_router(admin.router)
router.include_router(powerups.router)
# if config.development:
# router.include_router(admin.router)
