from enum import Enum

from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator

__all__ = (
    "Powerup",
    "PowerupType",
    "PowerupConfig",
    "PowerupConfig_Pydantic",
    "Powerup_Pydantic",
    "TeamPowerupPoints",
)


class PowerupType(str, Enum):
    AIRSTRIKE = "airstrike"
    SHIELD = "shield"
    SABOTAGE = "sabotage"


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


class TeamPowerupPoints(models.Model):
    team = fields.ForeignKeyField("models.Team", related_name="team_powerup_points")
    type = fields.CharEnumField(PowerupType)
    used_at = fields.DatetimeField(null=True)
    points = fields.IntField(default=0)


PowerupConfig_Pydantic = pydantic_model_creator(PowerupConfig)
Powerup_Pydantic = pydantic_model_creator(Powerup)
