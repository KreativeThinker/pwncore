import random
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException
from tortoise.expressions import F, Subquery

from pwncore.models import (
    Powerup,
    PowerupConfig,
    PowerupConfig_Pydantic,
    PowerupType,
    Team,
    TeamPowerup,
)
from pwncore.routes.auth import RequireJwt

metadata = {"name": "powerups", "description": "Powerups for teams"}
router = APIRouter(prefix="/powerups", tags=["team"])


@router.get("/view", response_model=List[PowerupConfig_Pydantic])
async def view_powerups(jwt: RequireJwt):
    team_id = jwt["team_id"]
    powerup_views = await PowerupConfig_Pydantic.from_queryset(
        PowerupConfig.filter(is_active=True).annotate(
            uses_left=Subquery(
                TeamPowerup.filter(team_id=team_id, powerup_type=F("type")).values_list(
                    "uses_left"
                )
            )
        )
    )
    return powerup_views


@router.post("/use/{powerup_type}")
async def use_powerup(powerup_type: PowerupType, jwt: RequireJwt):
    team_id = jwt["team_id"]
    team = await Team.get(id=team_id)
    powerup_config = await PowerupConfig.get(type=powerup_type)

    if not powerup_config.is_active:
        raise HTTPException(status_code=400, detail="This powerup is not active")

    team_powerup, _ = await TeamPowerup.get_or_create(
        team_id=team_id,
        powerup_type=powerup_type,
        defaults={"uses_left": powerup_config.max_uses},
    )

    if team_powerup.uses_left <= 0:
        raise HTTPException(
            status_code=400, detail="No more uses left for this powerup"
        )

    # team.points -= powerup_config.cost
    # await team.save()

    team_powerup.uses_left -= 1
    await team_powerup.save()

    result = None
    if powerup_type == PowerupType.LUCKY_DRAW:
        result = await lucky_draw(team)
    elif powerup_type == PowerupType.SABOTAGE:
        result = await sabotage(team)
    elif powerup_type == PowerupType.GAMBLE:
        result = await gamble(team)
    elif powerup_type == PowerupType.SIPHON:
        result = await siphon(team)

    return {"message": f"Powerup {powerup_type} used successfully", "result": result}


@router.get("/about/{powerup_type}")
async def get_about_powerups(powerup_type: PowerupType):
    powerup_info = await PowerupConfig_Pydantic.from_queryset_single(
        PowerupConfig.get(type=powerup_type)
    )
    return powerup_info


async def lucky_draw(team: Team):
    other_powerups = [pt for pt in PowerupType if pt != PowerupType.LUCKY_DRAW]
    if random.random() < 0.2:
        chosen_powerup = random.choice(other_powerups)
        powerup_config = await PowerupConfig.get(type=chosen_powerup)
        team_powerup, _ = await TeamPowerup.get_or_create(
            team_id=team.id,
            powerup_type=chosen_powerup,
            defaults={"uses_left": powerup_config.max_uses},
        )
        team_powerup.uses_left += 1
        await team_powerup.save()
        return f"You won an extra use of {chosen_powerup}!"
    return "Better luck next time!"


async def sabotage(team: Team):
    # In a real implementation, you'd choose a target team and apply the effect
    target_team = await Team.exclude(id=team.id).order_by("?").first()
    if not target_team:
        return "No team available to sabotage"

    await Powerup.create(
        team=target_team,
        type=PowerupType.SABOTAGE,
        used_at=datetime.now(),
        target_team=team,
        expires_at=datetime.now() + timedelta(minutes=10),
    )
    return f"Team {target_team.name} has been sabotaged for 10 minutes"


async def gamble(team: Team):
    # This would be implemented in conjunction with the CTF solving logic
    return "Your next CTF will be worth double points!"


async def siphon(team: Team):
    # In a real implementation, you'd choose a target team and apply the effect
    target_team = await Team.exclude(id=team.id).order_by("?").first()
    if not target_team:
        return "No team available to siphon points from"

    siphon_amount = min(50, target_team.points // 10)  # Siphon 10% of points, max 50
    target_team.points -= siphon_amount
    team.points += siphon_amount
    await target_team.save()
    await team.save()

    await Powerup.create(
        team=target_team,
        type=PowerupType.SIPHON,
        used_at=datetime.now(),
        target_team=team,
        expires_at=datetime.now() + timedelta(minutes=5),
    )
    return f"Siphoned {siphon_amount} points from team {target_team.name}"
