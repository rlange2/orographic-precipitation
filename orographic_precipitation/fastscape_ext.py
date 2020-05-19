import numpy as np
import xsimlab as xs

from fastscape.models import basic_model
from fastscape.processes import FlowAccumulator, SurfaceTopography, UniformRectilinearGrid2D
from .orographic_precipitation import compute_orographic_precip


@xs.process
class OrographicPrecipitation:
    """Computes orographic precipitation following Smith & Barstad (2004)
    """
    # --- initial conditions
    lapse_rate = xs.variable(description="adiabatic lapse rate")
    lapse_rate_m = xs.variable(description="moist adiabatic lapse rate")
    ref_density = xs.variable(description="reference saturation water vapor density",
                              attrs={"units": "kg/m^3"})

    # --- input variables
    latitude = xs.variable(description="latitude",
                           attrs={"units": "degrees"})
    precip_base = xs.variable(description="background, non-orographic precipitation rate",
                              attrs={"units": "mm/h"})
    wind_speed = xs.variable(description="wind speed",
                             attrs={"units": "m/s"})
    wind_dir = xs.variable(description="wind direction (azimuth)",
                           attrs={"units": "degrees"})
    conv_time = xs.variable(description="conversion time",
                           attrs={"units": "s"})
    fall_time = xs.variable(description="fallout time",
                           attrs={"units": "s"})
    nm = xs.variable(description="moist stability frequency",
                           attrs={"units": "1/s"})
    hw = xs.variable(description="water vapor scale height",
                           attrs={"units": "m"})
    cw = xs.variable(description="uplift sensitivity", intent="out",
                           attrs={"units": "kg/m^3"})

    # --- variables needed for computation
    dx = xs.foreign(UniformRectilinearGrid2D, "dx")
    dy = xs.foreign(UniformRectilinearGrid2D, "dy")
    shape = xs.foreign(UniformRectilinearGrid2D, "shape")
    elevation = xs.foreign(SurfaceTopography, "elevation")

    # --- output variable
    precip_rate = xs.variable(
        dims=("y", "x"), description="precipitation rate", intent="out", attrs={"units": "mm/h"}
    )

    def _get_params(self):
        self.cw = self.ref_density * self.lapse_rate_m / self.lapse_rate

        return {
            "latitude" : self.latitude,
            "precip_base" : self.precip_base,
            "wind_speed" : self.wind_speed,
            "wind_dir" : self.wind_dir,
            "conv_time" : self.conv_time,
            "fall_time" : self.fall_time,
            "nm" : self.nm,
            "hw" : self.hw,
            "cw" : self.cw}

    def initialize(self):
        self._params = self._get_params()
        self.precip_rate = np.zeros(self.shape)

    def run_step(self):
        self._params.update(self._get_params())
        self.precip_rate = compute_orographic_precip(self.elevation,
                                                self.dx,
                                                self.dy,
                                                **self._params)


@xs.process
class OrographicDrainageDischarge(FlowAccumulator):
    """Accumulate orographic precipitation from upstream to downstream.

    For use in the context of landscape evolution modeling, ``flowacc`` values
    are converted from mm^3 h^-1 to m^3 yr^-1. For convenience, the ``discharge``
    on demand variable still returns the values in mm^3 h^-1.  
    """
    runoff = xs.foreign(OrographicPrecipitation, 'precip_rate')
    discharge = xs.on_demand(
        dims=('y','x'), description='discharge from orographic precipitation', attrs={"units": "mm^3/h"}
    )

    def run_step(self):
        super().run_step()

        # scale mm^3/h to m^3/yr
        self.flowacc *= 8.76e-6

    @discharge.compute
    def _discharge(self):
        return self.flowacc / 8.76e-6


precip_model = basic_model.update_processes({
    'orographic': OrographicPrecipitation,
    'drainage': OrographicDrainageDischarge
})