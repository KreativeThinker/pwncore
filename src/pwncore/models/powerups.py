from enum import Enum

from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

__all__ = (
    "Powerup",
    "PowerupType",
    "PowerupConfig",
    "PowerupConfig_Pydantic",
    "TeamPowerup",
    "Powerup_Pydantic",
    "TeamPowerup_Pydantic",
)


class PowerupType(str, Enum):
    LUCKY_DRAW = "lucky_draw"
    SABOTAGE = "sabotage"
    GAMBLE = "gamble"
    SIPHON = "siphon"


class PowerupConfig(models.Model):
    type = fields.CharEnumField(PowerupType, unique=True, null=False)
    cost = fields.IntField()
    max_uses = fields.IntField()
    is_active = fields.BooleanField(default=False)
    description = fields.CharField(max_length=255)


class Powerup(models.Model):
    team = fields.ForeignKeyField("models.Team", related_name="powerups")
    type = fields.CharEnumField(PowerupType)
    used_at = fields.DatetimeField(null=True)
    target_team = fields.ForeignKeyField(
        "models.Team", null=True, related_name="targeted_powerups"
    )
    expires_at = fields.DatetimeField(null=True)
    profit = fields.FloatField(default=0)


class TeamPowerup(models.Model):
    team = fields.ForeignKeyField("models.Team", related_name="team_powerups")
    powerup_type = fields.CharEnumField(PowerupType)
    uses_left = fields.IntField()


PowerupConfig_Pydantic = pydantic_model_creator(PowerupConfig)
Powerup_Pydantic = pydantic_model_creator(Powerup)
TeamPowerup_Pydantic = pydantic_model_creator(TeamPowerup)
