from enum import Enum
from dataclasses import dataclass

class Orientation(Enum):
  HORIZONTAL = "horizontal"
  VERTICAL = "vertical"

@dataclass
class Dimension:
  w: int
  l: int

@dataclass
class Vehicle:
  id: str
  dimensions: Dimension
  shipping_fee: float
  weight: float
  eta: int

@dataclass
class Ship:
  dimensions: Dimension
  max_capacity: int

@dataclass(frozen=True)
class Position:
  x: int
  y: int
  orientation: Orientation