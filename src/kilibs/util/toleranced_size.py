from __future__ import annotations

import math
import re
from typing import Any

from kilibs.geom.operations import round_to_grid_nearest


class TolerancedSize:

    @staticmethod
    def to_metric(value: float, unit: str | None = None) -> float:
        if unit == "inch":
            factor = 25.4
        elif unit == "mil":
            factor = 25.4 / 1000
        else:
            factor = 1
        return value * factor

    def __init__(
        self,
        minimum: float | None = None,
        nominal: float | None = None,
        maximum: float | None = None,
        tolerance: float | list[float] | None = None,
        unit: str | None = None,
    ) -> None:

        # Instance attributes:
        self.minimum: float
        """Minimum dimension."""
        self.nominal: float
        """Nominal dimension."""
        self.maximum: float
        """Maximum dimension."""
        self.ipc_tol: float
        """Total tolerance (difference between maximum and minimum tolerance)."""
        self.ipc_tol_RMS: float
        """Total RMS tolerance."""
        self.maximum_RMS: float
        """RMS of the maximum tolerance."""
        self.minimum_RMS: float
        """RMS of the minimum tolerance."""

        if nominal is not None:
            self.nominal = nominal
        else:
            if minimum is None:
                if maximum is None:
                    raise KeyError("Either nominal or minimum or maximum must be given")
                else:
                    self.nominal = maximum
            else:
                if maximum is None:
                    self.nominal = minimum
                else:
                    self.nominal = (minimum + maximum) / 2

        if minimum is not None and maximum is not None:
            self.minimum = minimum
            self.maximum = maximum
        elif tolerance is not None:
            if isinstance(tolerance, int | float):
                self.minimum = self.nominal - tolerance
                self.maximum = self.nominal + tolerance
            elif len(tolerance) == 2:
                if tolerance[0] < 0:
                    self.minimum = self.nominal + tolerance[0]
                    self.maximum = self.nominal + tolerance[1]
                elif tolerance[1] < 0:
                    self.minimum = self.nominal + tolerance[1]
                    self.maximum = self.nominal + tolerance[0]
                else:
                    self.minimum = self.nominal - tolerance[0]
                    self.maximum = self.nominal + tolerance[1]
        else:
            self.minimum = self.nominal
            self.maximum = self.nominal

        if self.maximum < self.minimum:
            raise ValueError(
                "Maximum is smaller than minimum. Tolerance ranges given wrong or parameters confused."
            )

        self.minimum = TolerancedSize.to_metric(self.minimum, unit)
        self.nominal = TolerancedSize.to_metric(self.nominal, unit)
        self.maximum = TolerancedSize.to_metric(self.maximum, unit)

        self.ipc_tol = self.maximum - self.minimum
        self.ipc_tol_RMS = self.ipc_tol
        self.maximum_RMS = self.maximum
        self.minimum_RMS = self.minimum

    def update_rms(self, tolerances: list[float]) -> None:
        ipc_tol_RMS = 0.0
        for t in tolerances:
            ipc_tol_RMS += t**2

        self.ipc_tol_RMS = math.sqrt(ipc_tol_RMS)
        if self.ipc_tol_RMS > self.ipc_tol:
            if round_to_grid_nearest(self.ipc_tol_RMS, 1e-6) > round_to_grid_nearest(
                self.ipc_tol, 1e-6
            ):
                raise ValueError(
                    "RMS tolerance larger than normal tolerance. Did you give the wrong tolerances?\ntol(RMS): {} tol: {}".format(
                        self.ipc_tol_RMS, self.ipc_tol
                    )
                )
            # the discrepancy most likely comes from floating point errors. Ignore it.
            self.ipc_tol_RMS = self.ipc_tol

        self.maximum_RMS = self.maximum - (self.ipc_tol - self.ipc_tol_RMS) / 2
        self.minimum_RMS = self.minimum + (self.ipc_tol - self.ipc_tol_RMS) / 2

    def __add__(self, other: int | float | TolerancedSize) -> TolerancedSize:
        if isinstance(other, int | float):
            result = TolerancedSize(
                minimum=self.minimum + other, maximum=self.maximum + other
            )
            return result

        result = TolerancedSize(
            minimum=self.minimum + other.minimum, maximum=self.maximum + other.maximum
        )
        result.update_rms([self.ipc_tol_RMS, other.ipc_tol_RMS])
        return result

    def __sub__(self, other: int | float | TolerancedSize) -> TolerancedSize:
        if isinstance(other, int | float):
            result = TolerancedSize(
                minimum=self.minimum - other, maximum=self.maximum - other
            )
            return result

        result = TolerancedSize(
            minimum=self.minimum - other.maximum, maximum=self.maximum - other.minimum
        )
        result.update_rms([self.ipc_tol_RMS, other.ipc_tol_RMS])
        return result

    def __mul__(self, other: int | float) -> TolerancedSize:
        if type(other) not in [int, float]:
            raise NotImplementedError(
                "Only multiplication with int and float is implemented right now."
            )
        result = TolerancedSize(
            minimum=self.minimum * other, maximum=self.maximum * other
        )
        result.update_rms([self.ipc_tol_RMS * math.sqrt(other)])
        return result

    def __div__(self, other: int | float) -> TolerancedSize:
        return self.__truediv__(other)

    def __truediv__(self, other: int | float) -> TolerancedSize:
        if type(other) not in [int, float]:
            raise NotImplementedError(
                "Only multiplication with int and float is implemented right now."
            )
        result = TolerancedSize(
            minimum=self.minimum / other, maximum=self.maximum / other
        )
        result.update_rms([self.ipc_tol_RMS / math.sqrt(other)])
        return result

    def __floordiv__(self, other: int | float) -> TolerancedSize:
        if type(other) not in [int, float]:
            raise NotImplementedError(
                "Only multiplication with int and float is implemented right now."
            )
        result = TolerancedSize(
            minimum=self.minimum // other, maximum=self.maximum // other
        )
        result.update_rms([self.ipc_tol_RMS // math.sqrt(other)])
        return result

    @staticmethod
    def from_string(
        input: str | int | float, unit: str | None = None
    ) -> TolerancedSize:
        minimum = None
        nominal = None
        maximum = None
        tolerance: float | list[float] | None = None

        s = re.sub(r"\s+", "", str(input))
        if isinstance(input, int | float):
            nominal = input
        elif "+/-" in s:
            tokens = s.split("+/-")
            nominal = float(tokens[0])
            tolerance = float(tokens[1])
        elif "+" in s and "-" in s:
            if s.count("+") > 1 or s.count("-") > 1:
                raise ValueError(
                    "Illegal dimension specifier: {}\n\tToo many tolerance specifiers. Expected nom+tolp-toln".format(
                        input
                    )
                )
            idxp = s.find("+")
            idxn = s.find("-")

            nominal = float(s[0 : min(idxp, idxn)])
            tolerance = [
                float(s[idxn : idxp if idxn < idxp else None]),
                float(s[idxp : idxn if idxn > idxp else None]),
            ]
        elif "..." in s or ".." in s:
            s = s.replace("...", "..")
            tokens = s.split("..")
            if len(tokens) > 3:
                raise ValueError(
                    "Illegal dimension specifier: {}\n\tToo many tokens separated by '...' (Valid options are min...max or min...nom...max)".format(
                        input
                    )
                )
            minimum = float(tokens[0])
            maximum = float(tokens[-1])
            if len(tokens) == 3:
                nominal = float(tokens[1])
        else:
            try:
                nominal = float(s)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                raise ValueError(
                    "Dimension specifier not recognised: {}\n\t Valid options are nom, nom+/-tol, nom+tolp-toln, min...max or min...nom...max".format(
                        input
                    )
                ) from e

        return TolerancedSize(
            minimum=minimum,
            nominal=nominal,
            maximum=maximum,
            tolerance=tolerance,
            unit=unit,
        )

    @staticmethod
    def from_yaml(
        yaml: dict[str, Any] | str,
        base_name: str | None = None,
        unit: str | None = None,
    ) -> TolerancedSize:
        if base_name is not None and isinstance(yaml, dict):
            if (
                base_name + "_min" in yaml
                or base_name + "_max" in yaml
                or base_name + "_tol" in yaml
            ):
                return TolerancedSize(
                    minimum=yaml.get(base_name + "_min"),
                    nominal=yaml.get(base_name),
                    maximum=yaml.get(base_name + "_max"),
                    tolerance=yaml.get(base_name + "_tol"),
                )
            elif (yaml_base := yaml.get(base_name)) is not None:
                return TolerancedSize.from_yaml(yaml_base, unit=unit)
            else:
                raise ValueError(f"Could not find {base_name} in the YAML file.")

        elif isinstance(yaml, dict):
            return TolerancedSize(
                minimum=yaml.get("minimum"),
                nominal=yaml.get("nominal"),
                maximum=yaml.get("maximum"),
                tolerance=yaml.get("tolerance"),
                unit=unit,
            )
        else:
            return TolerancedSize.from_string(yaml, unit)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return "nom: {}, min: {}, max: {}  | min_rms: {}, max_rms: {}".format(
            self.nominal, self.minimum, self.maximum, self.minimum_RMS, self.maximum_RMS
        )


class TolerancedSizeHandler:
    def __init__(self, dictionary: dict[str, Any], unit: str | None = None) -> None:
        """Create an instance of TolerancedSizeHandler.

        Args:
            dictionary: The dictionary from which the data shall be extracted and
                converted to instances of `TolerancedSize` when `get()` is called.
            unit: The unit that shall be used when converting data to `TolerancedSize`.
        """
        # Instance attributes
        self.dictionary = dictionary
        """The dictionary that is used whenever `get()` is called."""
        self.unit = unit
        """The unit that is used whenever `get()` is called."""

    def get(
        self, base_name: str | list[str], default: float | None = None
    ) -> TolerancedSize:
        """Return the toleranced size of the value corresponding to the given key.

        Args:
            base_name: The base name (without postfix `_min` or `_max`) of the key that
                of the toleranced size that is stored in the `dictionary`.
                If a list is given instead of a string, the first entry of the list
                that has a matching key in the dictionary is used.
            default: The optional default value that shall be used in case no key equal
                to `base_name` was found. If `default` is `None` and no key equal to
                `base_name` was found a KeyError is raised.

        Returns:
            The toleranced size of the value corresponding to the given key.
        """
        if isinstance(base_name, str):
            try:
                return TolerancedSize.from_yaml(
                    yaml=self.dictionary, base_name=base_name, unit=self.unit
                )
            except ValueError:
                pass
        else:
            for name in base_name:
                try:
                    return TolerancedSize.from_yaml(
                        yaml=self.dictionary, base_name=name, unit=self.unit
                    )
                except ValueError:
                    pass
        if default is None:
            raise KeyError(f"Could not find key '{base_name}' in the dictionary!")
        else:
            return TolerancedSize(nominal=default)

    def get_or_none(self, base_name: str | list[str]) -> TolerancedSize | None:
        """Same as `get()`, however, if the none of the given base_names has a matching
        key in the dictionary, instead of raising an exception, the value `None` is
        returned."""
        try:
            return self.get(base_name=base_name)
        except KeyError:
            return None
