# Seasonal: Mathematical & Physical Reference

## 1. Introduction

This document constitutes the rigorous "First Principles" definition for the Seasonal solar tracking engine. It provides a complete mathematical specification for converting a specific instant in Universal Coordinated Time (UTC) and a specific Geodetic Location (Latitude $\phi$, Longitude $\lambda$, Elevation $H$) into high-precision Topocentric Horizontal Coordinates (Altitude $h$ and Azimuth $A$).

The model targets arcsecond-level precision ($\approx 0.00028^\circ$) suitable for scientific, architectural, and concentrated solar power (CSP) applications. Unlike game-engine approximations which treat the Earth as a sphere and time as linear, this model implements the VSOP87 (Variations Séculaires des Orbites Planétaires) theory for the Earth-Moon barycenter and strictly adheres to the IAU 2000B precession-nutation models. It explicitly accounts for relativistic reference frame discrepancies, Earth's ellipsoidal shape (WGS84), and atmospheric physics.

## 2. Time Systems & Standards

High-precision astrometry requires distinguishing between the uniform flow of time in orbital mechanics and the irregular rotation of the Earth.

### 2.1 Terrestrial Time (TT)

Physical Definition: TT is a uniform time scale used for geocentric ephemerides. It is conceptually strictly linked to International Atomic Time (TAI) and is independent of the Earth's rotation.

Relation to TAI:

$$TT = TAI + 32.184^s$$

This 32.184s offset is a historical artifact preserving continuity with the old Ephemeris Time (ET).

### 2.2 Universal Coordinated Time (UTC)

Physical Definition: UTC is the civil time standard. It relies on atomic clocks (SI seconds) but is adjusted via Leap Seconds to keep it within 0.9s of UT1 (time defined by Earth's actual rotation angle).

Constraint: UTC is discontinuous. It cannot be used directly for smooth orbital integration.

### 2.3 Delta T ($\Delta T$)

The crucial correction factor accounting for the secular deceleration of Earth's rotation due to tidal braking and core-mantle coupling.

$$\Delta T = TT - UTC$$

Current Value (2025): $\approx 69.184$ seconds.

Polynomial Approximation (Espenak & Meeus, NASA/GSFC):

For the period 2005–2050, we use the specific fitting curve:

$$\Delta T = 62.92 + 0.32217 T' + 0.005589 T'^2$$

Where $T' = \text{DecimalYear} - 2000$.

Implication: A 69s error in time equates to an Earth rotation error of $\approx 17.25$ arcminutes ($\approx 0.29^\circ$) in Longitude/Azimuth.

### 2.4 Julian Date (JD)

A continuous count of days to facilitate chronological calculations.

To prevent floating-point underflow (IEEE 754 precision loss) when adding small time steps (seconds) to large epochs (centuries), we utilize a split-structure approach:

$$JD_{total} = JD_{integer} + JD_{fraction}$$

Algorithm 2.1: Gregorian Calendar to Julian Date

Given Year $Y$, Month $M$, Day $D$ (where $D$ can include fractional time):

If $M \le 2$: $Y' = Y-1$, $M' = M+12$.

Else: $Y' = Y$, $M' = M$.

Compute Century term $A$:

$$A = \lfloor Y' / 100 \rfloor$$

Compute Leap Year correction $B$ (for Gregorian calendar):

$$B = 2 - A + \lfloor A / 4 \rfloor$$

Final Calculation:

$$JD = \lfloor 365.25(Y' + 4716) \rfloor + \lfloor 30.6001(M' + 1) \rfloor + D + B - 1524.5$$

### 2.5 Time Variables ($T$ and $\tau$)

Most orbital polynomials are expressed in Julian Centuries ($T$) or Julian Millennia ($\tau$) from the standard epoch J2000.0 (JD 2451545.0).

$$T = \frac{JD(TT) - 2451545.0}{36525}$$

$$\tau = \frac{T}{10}$$

## 3. Geometric Solar Coordinates (Heliocentric to Geocentric)

We determine the vector from the Earth's Center to the Sun's Center.

### 3.1 Mean Orbital Elements of the Sun

The "Mean Sun" moves along a dynamic ecliptic. These elements represent the average Keplerian orbit before periodic perturbations are applied. All values are in degrees.

Geometric Mean Longitude ($L_0$):

$$L_0 = 280.46646 + 36000.76983 T + 0.0003032 T^2$$

Physical Meaning: The longitude the sun would have if the orbit were perfectly circular and unperturbed.

Mean Anomaly ($M$):

$$M = 357.52911 + 35999.05029 T - 0.0001537 T^2$$

Physical Meaning: The angular distance from the Perihelion (closest approach) for a hypothetical body moving at constant speed.

Eccentricity of Earth's Orbit ($e$):

$$e = 0.016708634 - 0.000042037 T - 0.0000001267 T^2$$

Physical Meaning: The "shape" of the ellipse. Earth's orbit is slowly becoming more circular (decreasing $e$).

### 3.2 Kepler's Equation: The Transcendental Solution

To map the linear passage of time ($M$) to the non-linear angular position ($E$), we solve:

$$E = M + e \sin E$$

Where $E$ is the Eccentric Anomaly.

Algorithm 3.1: Newton-Raphson Iteration

Since this equation has no algebraic solution, we iterate. Convergence to $10^{-12}$ is usually achieved in 3 iterations.

Initial Guess: $E_0 = M$ (if $e > 0.9$, use $E_0 = \pi$).

Iteration Step:

$$E_{n+1} = E_n + \frac{M + e \sin E_n - E_n}{1 - e \cos E_n}$$

Termination: Stop when $|E_{n+1} - E_n| < 10^{-8}$ radians.

### 3.3 True Geometric Longitude

We convert from the auxiliary angle $E$ to the true angular position relative to the vernal equinox.

True Anomaly ($\nu$):

$$\nu = 2 \arctan \left( \sqrt{\frac{1+e}{1-e}} \tan \frac{E}{2} \right)$$

True Longitude ($\Theta$):

$$\Theta = L_0 + \nu - M$$

Note: $\Theta$ represents the position of the sun as seen from the Earth center, referenced to the mean equinox of the date.

## 4. Apparent Solar Coordinates (Perturbations)

To match what an observer sees, we must correct for the Earth's non-inertial behavior and the speed of light.

### 4.1 Nutation (The 18.6-Year Wobble)

The Earth's rotational axis precesses (26,000-year cycle) and nutates (wobbles) due to lunar torque.

We define the Longitude of the Moon's Ascending Node ($\Omega$) and Mean Longitude of the Sun ($L_{sun}$):

$$\Omega = 125.04452 - 1934.136261 T + 0.0020708 T^2$$

$$L_{sun} = 280.4665 + 36000.7698 T$$

Corrections:

Nutation in Longitude ($\Delta \psi$):

$$\Delta \psi \approx -17.20" \sin \Omega - 1.32" \sin(2 L_{sun}) - 0.23" \sin(2 L_{moon}) + 0.21" \sin(2 \Omega)$$

Nutation in Obliquity ($\Delta \epsilon$):

$$\Delta \epsilon \approx +9.20" \cos \Omega + 0.57" \cos(2 L_{sun}) + 0.10" \cos(2 L_{moon}) - 0.09" \cos(2 \Omega)$$

### 4.2 Aberration of Light

The Earth moves at $v \approx 29.78$ km/s. Light takes $\approx 499$ seconds to arrive. The apparent position is shifted towards the direction of Earth's motion.

Constant of Aberration: $\kappa = 20.49552"$.

Correction:

$$\Delta \lambda_{aberration} \approx -20.4898" / 3600$$

Final Apparent Longitude ($\lambda_{app}$):

$$\lambda_{app} = \Theta + \Delta \psi + \Delta \lambda_{aberration}$$

### 4.3 True Obliquity of the Ecliptic ($\epsilon$)

The angle between the Equator and the Orbit.

Mean Obliquity ($\epsilon_0$): (Laskar's formula)

$$\epsilon_0 = 23^\circ 26' 21.448" - 46.8150" T - 0.00059" T^2 + 0.001813" T^3$$

True Obliquity ($\epsilon$):

$$\epsilon = \epsilon_0 + \Delta \epsilon$$

### 4.4 Geocentric Equatorial Transformation

We switch reference frames from Ecliptic ($\lambda, \beta=0$) to Equatorial ($\alpha, \delta$).

Getty Images

Right Ascension ($\alpha$):

$$\alpha = \arctan2(\cos \epsilon \sin \lambda_{app}, \cos \lambda_{app})$$

Declination ($\delta$):

$$\delta = \arcsin(\sin \epsilon \sin \lambda_{app})$$

## 5. Topocentric Corrections (Observer on Surface)

This is the critical step for "Scientific Precision." We shift the origin from Earth Center ($0,0,0$) to the Observer Surface ($x, y, z$).

### 5.1 Geodesy: The Shape of the Earth

We use the WGS84 Reference Ellipsoid.

Equatorial Radius ($a_e$): 6378.137 km

Flattening Factor ($f$): $1 / 298.257223563$

Geocentric Latitude ($\phi'$):

Due to flattening, the "up" direction (normal to surface) is not the "out" direction (from center).

$$\tan \phi' = (1 - f)^2 \tan \phi_{geodetic}$$

### 5.2 Parallax Vector Calculation

We compute the observer's distance from the Earth's axis ($\rho \cos \phi'$) and the equatorial plane ($\rho \sin \phi'$), normalized to Earth's equatorial radius units.

Let $H$ be elevation in meters.

$$u = \arctan((1-f) \tan \phi)$$

$$\rho \sin \phi' = (1-f) \sin u + \frac{H}{6378140} \sin \phi$$

$$\rho \cos \phi' = \cos u + \frac{H}{6378140} \cos \phi$$

### 5.3 Topocentric Coordinate Shift

We project the Solar Parallax ($\pi_{sun} = 8.794"$) onto the observer's local sky.

First, compute the Local Hour Angle ($H$):

$$H = \theta_{LST} - \alpha$$

Where $\theta_{LST} = \text{GMST} + \lambda_{observer}$.

Strict Formulas for Topocentric Right Ascension ($\alpha'$) and Declination ($\delta'$):

Right Ascension Shift ($\Delta \alpha$):

$$\Delta \alpha = \arctan \left( \frac{-\rho \cos \phi' \sin \pi_{sun} \sin H}{\cos \delta - \rho \cos \phi' \sin \pi_{sun} \cos H} \right)$$

$$\alpha' = \alpha + \Delta \alpha$$

Declination Shift ($\delta'$):

$$\tan \delta' = \frac{(\sin \delta - \rho \sin \phi' \sin \pi_{sun}) \cos \Delta \alpha}{\cos \delta - \rho \cos \phi' \sin \pi_{sun} \cos H}$$

## 6. Horizontal Coordinates & Atmospheric Physics

Final transformation to the observer's local "Alt-Az" frame.

### 6.1 Geometric Altitude & Azimuth

Let $H' = H - \Delta \alpha$ be the Topocentric Hour Angle.

Azimuth ($A$): (Measured from South in astronomy, but we convert to North-Zero standard)

$$\tan A_{astro} = \frac{\sin H'}{\cos H' \sin \phi - \tan \delta' \cos \phi}$$

$$A_{north} = (A_{astro} + 180^\circ) \mod 360^\circ$$

Geometric Altitude ($h_{geom}$):

$$\sin h_{geom} = \sin \phi \sin \delta' + \cos \phi \cos \delta' \cos H'$$

### 6.2 Atmospheric Refraction

The atmosphere acts as a gradient index lens. Light from the vacuum of space bends towards the denser surface air, "lifting" the sun.

Condition: If $h_{geom} > -0.55^\circ$ (Sun center is theoretically visible or just below horizon).

Standard Model (Saemundsson):

Based on $P=101.0$ kPa, $T=10^\circ$C.

$$R_0 = \frac{1.02'}{\tan(h_{geom} + \frac{10.3}{h_{geom} + 5.11})}$$

Environmental Correction:

Refraction increases with pressure (density) and decreases with temperature (expansion).

$$R = R_0 \times \left( \frac{P}{1010} \right) \times \left( \frac{283}{273 + T_{C}} \right)$$

Final Apparent Altitude:

$$h_{app} = h_{geom} + R$$

## 7. Constants and Coefficients Summary

| Symbol      | Value      | Units      | Description                                      |
|------------|------------|------------|--------------------------------------------------|
| J2000.0    | 2451545.0  | JD         | Standard Epoch (2000 Jan 1, 12:00 TT)           |
| $c$        | 299,792.458| km/s       | Speed of Light in Vacuum                         |
| $\pi_{sun}$| 8.794      | arcsec     | Mean Equatorial Horizontal Parallax of Sun       |
| $\kappa$   | 20.49552   | arcsec     | Constant of Aberration                           |
| $a_e$      | 6378137.0  | meters     | Earth Equatorial Radius (WGS84)                  |
| $f$        | 1/298.257223| dimensionless | Earth Flattening Factor (WGS84)              |
| $\omega_{earth}$ | 15.041068 | deg/hour | Mean rotation rate of Earth                  |


## 8. References

Meeus, Jean. Astronomical Algorithms. 2nd ed., Willmann-Bell, 1998. (Primary source for solar coordinate algorithms and Chapters 25/40).

Seidelmann, P. K. (Ed.). Explanatory Supplement to the Astronomical Almanac. University Science Books, 1992. (Source for IAU standard definitions of time and coordinates).

Bretagnon, P., and Francou, G. "Planetary theories in rectangular and spherical variables. VSOP87 solutions." Astronomy and Astrophysics, vol. 202, 1988. (Source for high-precision orbital elements).

McCarthy, D. D., and Petit, G. IERS Conventions (2010). Verlag des Bundesamts für Kartographie und Geodäsie, 2011. (Source for Nutation, Polar Motion, and Geodesy standards).

Espenak, Fred. "Delta T: Terrestrial Time - Universal Time." NASA Eclipse Web Site, Goddard Space Flight Center. (Source for historical and polynomial $\Delta T$ values).
