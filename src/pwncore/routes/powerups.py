from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from tortoise.expressions import F, Subquery
from tortoise.functions import Coalesce, Count
from tortoise.transactions import in_transaction

from pwncore.models import Powerup, PowerupConfig, PowerupType, Team
from pwncore.models.powerups import TeamPowerupPoints
from pwncore.models.user import Team_Pydantic
from pwncore.routes.auth import RequireJwt

metadata = {"name": "powerups", "description": "Powerups for teams"}
router = APIRouter(prefix="/powerups", tags=["team"])


@router.get("/view")
async def view_powerups(jwt: RequireJwt):
    results = [
        await view_powerup_type(jwt, powerup_type) for powerup_type in PowerupType
    ]
    return results


@router.get("/active-shields")
async def get_active_shields(jwt: RequireJwt):
    results = await Team_Pydantic.from_queryset(
        Team.all()
        .prefetch_related("powerups")
        .filter(
            powerups__type=PowerupType.SHIELD, powerups__expires_at__gt=datetime.now()
        )
    )

    return results


@router.get("/vulnerable-teams")
async def get_vulnerable_teams():
    results = await Team_Pydantic.from_queryset(
        Team.all()
        .prefetch_related("powerups")
        .filter(
            id__not_in=Subquery(
                Team.filter(
                    id=Subquery(Team.filter(id=F("id")).values("id")),
                    powerups__type=PowerupType.SHIELD,
                    powerups__expires_at__gt=datetime.now(),
                ).values("id")
            )
        )
    )
    return results


async def use_powerup(powerup_type: PowerupType, jwt: RequireJwt):
    team_id = jwt["team_id"]
    team = await Team.get(id=team_id)
    powerup_config = await PowerupConfig.get_or_none(type=powerup_type, is_active=True)
    if not powerup_config:
        raise HTTPException(status_code=400, detail="Powerup not activated yet")
    uses_left = (
        await PowerupConfig.filter(is_active=True)
        .annotate(
            uses_left=F("max_uses")
            - Subquery(
                Powerup.filter(team=team_id, type=powerup_type)
                .annotate(count=Coalesce(Count("id"), 0))
                .values("count")
            )
        )
        .first()
        .values("uses_left")
    )
    if uses_left["uses_left"] <= 0:
        raise HTTPException(status_code=400, detail="Max uses reached")

    powerup = await Powerup.create(
        team=team,
        type=powerup_type,
        used_at=datetime.now(),
    )
    return powerup


@router.get("/view/{powerup_type}")
async def view_powerup_type(jwt: RequireJwt, powerup_type: PowerupType):
    team_id = jwt["team_id"]
    powerup_configs = (
        await PowerupConfig.filter(is_active=True, type=powerup_type)
        .annotate(
            uses_left=F("max_uses")
            - Subquery(
                Powerup.filter(team=team_id, type=powerup_type)
                .annotate(count=Coalesce(Count("type"), 0))
                .values("count")
            )
        )
        .first()
        .values("type", "max_uses", "cost", "description", "uses_left")
    )
    return powerup_configs


@router.post("/use/sabotage")
async def sabotage(team_name: str, jwt: RequireJwt):
    target_team = await Team.get_or_none(name=team_name)
    if not target_team:
        raise HTTPException(status_code=404, detail="Target team not found")

    async with in_transaction():
        powerup = await use_powerup(PowerupType.SABOTAGE, jwt)
        powerup.target_team = target_team
        powerup.expires_at = datetime.now() + timedelta(minutes=10)
        await powerup.save()
        await TeamPowerupPoints.create(
            team=target_team,
            type=PowerupType.SABOTAGE,
            used_at=datetime.now(),
            points=-500,
        )
        await TeamPowerupPoints.create(
            team=powerup.team,
            type=PowerupType.SABOTAGE,
            used_at=datetime.now(),
            points=500,
        )

    return f"Team {target_team.name} has been sabotaged for 10 minutes"


@router.post("/use/airstrike")
async def airstrike(target: str, jwt: RequireJwt):
    team_id = jwt["team_id"]
    target_team = await Team.get_or_none(name=target)
    if not target_team:
        raise HTTPException(status_code=404, detail="Target team not found")

    async with in_transaction():
        powerup = await use_powerup(PowerupType.AIRSTRIKE, jwt)
        powerup.target_team = target_team
        await powerup.save()
        shield_is_active = await Powerup.get_or_none(
            team=team_id, type=PowerupType.SHIELD, expires_at__gt=datetime.now()
        )
        if shield_is_active:
            raise HTTPException(status_code=400, detail="Team protected by Shield")
        await TeamPowerupPoints.create(
            team=target_team,
            type=PowerupType.AIRSTRIKE,
            used_at=datetime.now(),
            points=-300,
        )
    return f"Airstrike launched against team {target_team.name}"


@router.post("/use/shield")
async def shield(jwt: RequireJwt):
    team_id = jwt["team_id"]
    shield_is_active = await Powerup.get_or_none(
        team=team_id, type=PowerupType.SHIELD, expires_at__gt=datetime.now()
    )

    if shield_is_active:
        raise HTTPException(status_code=400, detail="Shield currently active")

    powerup = await use_powerup(PowerupType.SHIELD, jwt)
    powerup.expires_at = datetime.now() + timedelta(minutes=15)
    await powerup.save()
    return "Shield activated for 15 minutes"
