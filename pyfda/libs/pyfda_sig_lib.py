# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Library with various signal processing related functions 
"""
import time
import logging
logger = logging.getLogger(__name__)
import numpy as np
from numpy import pi


import scipy.signal as sig


def impz(b, a=1, FS=1, N=0, step = False):
    """
Calculate impulse response of a discrete time filter, specified by
numerator coefficients b and denominator coefficients a of the system
function H(z).

When only b is given, the impulse response of the transversal (FIR)
filter specified by b is calculated.

Parameters
----------
b :  array_like
     Numerator coefficients (transversal part of filter)

a :  array_like (optional, default = 1 for FIR-filter)
     Denominator coefficients (recursive part of filter)

FS : float (optional, default: FS = 1)
     Sampling frequency.

N :  float (optional)
     Number of calculated points.
     Default: N = len(b) for FIR filters, N = 100 for IIR filters

Returns
-------
hn : ndarray with length N (see above)
td : ndarray containing the time steps with same


Examples
--------
>>> b = [1,2,3] # Coefficients of H(z) = 1 + 2 z^2 + 3 z^3
>>> h, n = dsp_lib.impz(b)
"""
    a = np.asarray(a)
    b = np.asarray(b)

    if len(a) == 1:
        if len(b) == 1:
            raise TypeError(
            'No proper filter coefficients: len(a) = len(b) = 1 !')
        else:
            IIR = False
    else:
        if len(b) == 1:
            IIR = True
        # Test whether all elements except first are zero
        elif not np.any(a[1:]) and a[0] != 0:
            #  same as:   elif np.all(a[1:] == 0) and a[0] <> 0:
            IIR = False
        else:
            IIR = True

    if N == 0: # set number of data points automatically
        if IIR:
            N = 100 # TODO: IIR: more intelligent algorithm needed
        else:
            N = min(len(b),  100) # FIR: N = number of coefficients (max. 100)

    impulse = np.zeros(N)
    impulse[0] =1.0 # create dirac impulse as input signal
    hn = np.array(sig.lfilter(b, a, impulse)) # calculate impulse response
    td = np.arange(len(hn)) / FS

    if step: # calculate step response
        hn = np.cumsum(hn)

    return hn, td

#==================================================================
def group_delay(b, a=1, nfft=512, whole=False, analog=False, verbose=True, fs=2.*pi, 
                sos=False, alg="scipy"):
#==================================================================
    """
Calculate group delay of a discrete time filter, specified by
numerator coefficients `b` and denominator coefficients `a` of the system
function `H` ( `z`).

When only `b` is given, the group delay of the transversal (FIR)
filter specified by `b` is calculated.

Parameters
----------
b :  array_like
     Numerator coefficients (transversal part of filter)

a :  array_like (optional, default = 1 for FIR-filter)
     Denominator coefficients (recursive part of filter)

whole : boolean (optional, default : False)
     Only when True calculate group delay around
     the complete unit circle (0 ... 2 pi)

verbose : boolean (optional, default : True)
    Print warnings about frequency points with undefined group delay (amplitude = 0)
    and the time used for calculating the group delay

nfft :  integer (optional, default: 512)
     Number of FFT-points

fs : float (optional, default: fs = 2*pi)
     Sampling frequency.
     
alg : str (default: "scipy")
      The algorithm for calculating the group delay:
          - "scipy" The algorithm used by scipy's grpdelay, 
          - "jos": The original J.O.Smith algorithm; same as in "scipy" except that
            the frequency response is calculated with the FFT instead of polyval
          - "diff": Group delay is calculated by differentiating the phase
          - "Shpakh": Group delay is calculated from second-order sections

Returns
-------
tau_g : ndarray
        group delay

w : ndarray
    angular frequency points where group delay was computed

Notes
=======

Definition and direct calculation
````````````````````````````````````
The following explanation follows [JOS]_.

The group delay :math:`\\tau_g(\\omega)` of discrete time (DT) and continuous time
(CT) systems is the rate of change of phase with respect to angular frequency. 
In the following, derivative is always meant w.r.t. :math:`\\omega`:

.. math::

    \\tau_g(\\omega) 
        = -\\frac{\\partial }{\\partial \\omega}\\angle H( \\omega)
        = -\\frac{\\partial \\phi(\\omega)}{\\partial \\omega}
        = -  \\phi'(\\omega)

With numpy / scipy, the group delay can be calculated directly with

.. code-block:: python

    w, H = sig.freqz(b, a, worN=nfft, whole=whole)
    tau_g = -np.diff(np.unwrap(np.angle(H)))/np.diff(w)
    
The derivative can create numerical problems for e.g. phase jumps at zeros of 
frequency response or when the complex frequency response becomes very small e.g.
in the stop band.

This can be avoided by calculating the group delay from the derivative of the 
*logarithmic* frequency response in polar form (amplitude response and phase):

.. math::
    
    \\ln ( H( \\omega))
      = \\ln \\left({H_A( \\omega)} e^{j \\phi(\\omega)} \\right)
      = \\ln \\left({H_A( \\omega)} \\right) + j \\phi(\\omega)

      \\Rightarrow \\; \\frac{\\partial }{\\partial \\omega} \\ln ( H( \\omega))
      = \\frac{H_A'( \\omega)}{H_A( \\omega)} +  j \\phi'(\\omega)

where :math:`H_A(\\omega)` is the amplitude response. :math:`H_A(\\omega)` and
its derivative :math:`H_A'(\\omega)` are real-valued, therefore, the group
delay can be calculated by separating real and imginary components (and discarding 
the real part):

.. math::
    
    \\begin{align}
    \\Re \\left\\{\\frac{\\partial }{\\partial \\omega} \\ln ( H( \\omega))\\right\\} &= \\frac{H_A'( \\omega)}{H_A( \\omega)} \\\                                                                      
    \\Im \\left\\{\\frac{\\partial }{\\partial \\omega} \\ln ( H( \\omega))\\right\\} &= \\phi'(\\omega)
    \\end{align}                                                                    

and hence

.. math::

      \\tau_g(\\omega) = -\\phi'(\\omega) =
      -\\Im \\left\\{ \\frac{\\partial }{\\partial \\omega}
      \\ln ( H( \\omega)) \\right\\}
      =-\\Im \\left\\{ \\frac{H'(\\omega)}{H(\\omega)} \\right\\}

Note: The last term contains the complex response :math:`H(\omega)`, not the 
amplitude response :math:`H_A(\omega)`!

In the following, it will be shown that the derivative of birational functions 
(like DT and CT filters) can be calculated very efficiently and from this the group
delay.


J.O. Smith's algorithm for FIR filters
````````````````````````````````````````

An efficient form of calculating the group delay of FIR filters based on the derivative of the logarithmic frequency response has been described in [JOS]_ and [Lyons]_ for
discrete time systems. 

A FIR filter is defined via its polyome :math:`H(z) = \\sum_k b_k z^{-k}` and has
the following derivative:
    
.. math::

    \\frac{\\partial }{\\partial \\omega} H(z = e^{j \\omega T})
    = \\frac{\\partial }{\\partial \\omega} \\sum_{k = 0}^N b_k e^{-j k \\omega T}
    =  -jT \\sum_{k = 0}^{N} k b_{k} e^{-j k \\omega T}
    =  -jT H_R(e^{j \\omega T})

where :math:`H_R` is the "ramped" polynome, i.e. polynome :math:`H` multiplied 
with a ramp :math:`k`, yielding

.. math::

    \\tau_g(e^{j \\omega T}) = -\\Im \\left\\{ \\frac{H'(e^{j \\omega T})}
                    {H(e^{j \\omega T})} \\right\\}
                    = -\\Im \\left\\{ -j T \\frac{H_R(e^{j \\omega T})}
                    {H(e^{j \\omega T})} \\right\\}
                    = T \\, \\Re \\left\\{\\frac{H_R(e^{j \\omega T})}
                    {H(e^{j \\omega T})} \\right\\}     

scipy's grpdelay directly calculates the complex frequency response 
:math:`H(e^{j\\omega T})` and its ramped function at the frequency points using 
the polyval function. However, it is faster (probably numerically more robust) 
to use the FFT for calculating the frequency response at the NFFT points. 

When zeros of the frequency response are on or near the data points of the DFT, this 
algorithm runs into numerical problems. Hence, it is neccessary to check whether
the magnitude of the denominator is larger than e.g. 10 times the machine eps. 
In this case, :math:`\\tau_g` can be set to zero or nan. 

J.O. Smith's algorithm for IIR filters (direct calculation)
`````````````````````````````````````````````````````````````

IIR filters are defined by

.. math::
    
        H(z) = \\frac {B(z)}{A(z)} = \\frac {\\sum b_k z^k}{\\sum a_k z^k},
        
their group delay can be calculated numerically via the logarithmic frequency
response as well.
   
The derivative  of :math:`H(z)` w.r.t. :math:`\\omega` is calculated using the
quotient rule and by replacing the derivatives of numerator and denominator 
polynomes with their ramp functions: 
    
.. math::
    
    \\begin{align}
    \\frac{H'(e^{j \\omega T})}{H(e^{j \\omega T})} 
    &= \\frac{\\left(B(e^{j \\omega T})/A(e^{j \\omega T})\\right)'}{B(e^{j \\omega T})/A(e^{j \\omega T})}
    = \\frac{B'(e^{j \\omega T}) A(e^{j \\omega T}) - A'(e^{j \\omega T})B(e^{j \\omega T})}
    { A(e^{j \\omega T}) B(e^{j \\omega T})}  \\\\
    &= \\frac {B'(e^{j \\omega T})} { B(e^{j \\omega T})}  
      - \\frac { A'(e^{j \\omega T})} { A(e^{j \\omega T})}
    = -j T \\left(\\frac { B_R(e^{j \\omega T})} {B(e^{j \\omega T})} - \\frac { A_R(e^{j \\omega T})} {A(e^{j \\omega T})}\\right)
    \\end{align}
                               
This result is substituted once more into the log. derivative from above:

.. math::
    
    \\begin{align}
    \\tau_g(e^{j \\omega T}) 
    =-\\Im \\left\\{ \\frac{H'(e^{j \\omega T})}{H(e^{j \\omega T})} \\right\\}
    &=-\\Im \\left\\{
        -j T \\left(\\frac { B_R(e^{j \\omega T})} {B(e^{j \\omega T})}
                    - \\frac { A_R(e^{j \\omega T})} {A(e^{j \\omega T})}\\right)
                     \\right\\} \\\\
        &= T \\Re \\left\\{\\frac { B_R(e^{j \\omega T})} {B(e^{j \\omega T})}
                    - \\frac { A_R(e^{j \\omega T})} {A(e^{j \\omega T})}
         \\right\\}
    \\end{align}
                  

If the denominator of the computation becomes too small, the group delay
is set to zero.  (The group delay approaches infinity when
there are poles or zeros very close to the unit circle in the z plane.)

J.O. Smith's algorithm for IIR filters (with conversion to FIR case) 
``````````````````````````````````````````````````````````````````````

As a further optimization, the group delay of an IIR filter :math:`H(z) = B(z)/A(z)`
can be calculated from an equivalent FIR filter :math:`C(z)` with the same phase 
response (and hence group delay) as the original filter. This filter is obtained 
by the following steps:
    
* The zeros of :math:`A(z)` are the poles of :math:`1/A(z)`, its phase response is
  :math:`\\angle A(z) = - \\angle 1/A(z)`. 

* Transforming :math:`z \\rightarrow 1/z` mirrors the zeros at the unit circle, 
  correcting the negative phase response. This can be performed numerically by "flipping"
  the order of the coefficients and multiplying by :math:`z^{-N}` where :math:`N`
  is the order of :math:`A(z)`. This operation also conjugates the coefficients (?)
  which mirrors the zeros at the real axis. This effect has to be compensated,
  yielding the polynome :math:`\\tilde{A}(z)`. It is the "flip-conjugate" or 
  "Hermitian conjugate" of :math:`A(z)`.
  
  Frequently (e.g. in the scipy and until recently in the Matlab implementation)
  the conjugate operation is omitted which gives wrong results for complex
  coefficients.
  
* Finally, :math:`C(z) = B(z) \\tilde{A}(z)`. The coefficients of :math:`C(z)`
  are calculated efficiently by convolving the coefficients of :math:`B(z)` and 
  :math:`\\tilde{A}(z)`.

.. math::
    
    C(z) = B(z)\\left[ z^{-N}{A}^{*}(1/z)\\right] = B(z)\\tilde{A}(z)
    
where 

.. math::
    
    \\begin{align}
    \\tilde{A}(z) &=  z^{-N}{A}^{*}(1/z) = {a}^{*}_N + {a}^{*}_{N-1}z^{-1} + \ldots + {a}^{*}_1 z^{-(N-1)}+z^{-N}\\\\
    \Rightarrow \\tilde{A}(e^{j\omega T}) &=  e^{-jN \omega T}{A}^{*}(e^{-j\omega T}) \\\\
    \\Rightarrow \\angle\\tilde{A}(e^{j\omega T}) &= -\\angle A(e^{j\omega T}) - N\omega T
    \\end{align}    


or, in Python:

.. code-block:: python

    c = np.convolve(b, np.conj(a[::-1]))

where :math:`b` and :math:`a` are the coefficient vectors of the original 
numerator and denominator polynomes.

The actual group delay is calculated from the equivalent polynome as in the FIR
case.

The algorithm described above is numerically efficient but not robust for
narrowband IIR filters as pointed out in scipy issues [SC9310]_ and [SC1175]_. 
In the issues, it is recommended to calculate the group delay of IIR filters 
from the definition or using the Shpak algorithm (see below).

Code is available at [ENDO5828333]_ (GPL licensed) or at [SPA]_ (MIT licensed).

J.O. Smith's algorithm for CT filters
``````````````````````````````````````

The derivative of a CT polynome :math:`P(s)` w.r.t. :math:`\\omega` is calculated by:

.. math::

    \\frac{\\partial }{\\partial \\omega} P(s = j \\omega)
    = \\frac{\\partial }{\\partial \\omega} \\sum_{k = 0}^N c_k (j \\omega)^k
    =  j \\sum_{k = 0}^{N-1} (k+1) c_{k+1} (j \\omega)^{k}
    =  j P_R(s = j \\omega)

where :math:`P_R` is the "ramped" polynome, i.e. its `k` th coefficient is
multiplied by the ramp `k` + 1, yielding

.. math::

    \\tau_g(\\omega) = -\\Im \\left\\{ \\frac{H'(\\omega)}{H(\\omega)} \\right\\}
                     = -\\Im \\left\\{j \\frac{H_R(\\omega)}{H(\\omega)} \\right\\}
                     = -\\Re \\left\\{\\frac{H_R(\\omega)}{H(\\omega)} \\right\\}

References
```````````

.. [JOS] https://ccrma.stanford.edu/%7Ejos/fp/Numerical_Computation_Group_Delay.html or

         https://www.dsprelated.com/freebooks/filters/Numerical_Computation_Group_Delay.html

.. [Lyons] https://www.dsprelated.com/showarticle/69.php

.. [SC1175] https://github.com/scipy/scipy/issues/1175

.. [SC9310] https://github.com/scipy/scipy/issues/9310

.. [SPA] https://github.com/spatialaudio/group-delay-of-filters

.. [ENDO5828333] https://gist.github.com/endolith/5828333

.. [OCTAVE] https://sourceforge.net/p/octave/mailman/message/9298101/

Examples
--------
>>> b = [1,2,3] # Coefficients of H(z) = 1 + 2 z^2 + 3 z^3
>>> tau_g, td = pyfda_lib.grpdelay(b)
"""
    # if use_scipy:
    #     w, gd = sig.group_delay((b,a),w=nfft,whole=whole)
    #     return w, gd
    #alg = 'diff' # 'scipy', 'scipy_mod' 'shpak'

    if not whole:
        nfft = 2*nfft
#
    w = fs * np.arange(0, nfft)/nfft # create frequency vector
    minmag = 10. * np.spacing(1) # equivalent to matlab "eps"
    
    tau_g = np.zeros_like(w) # initialize tau_g

    if sos and alg != "shpak":
        b,a = sig.sos2tf(b)
        
    time_0 = time.perf_counter_ns()
    if alg.lower() == 'diff':
        #logger.info("Diff!")
        w, H = sig.freqz(b, a, worN=nfft, whole=whole)
        singular = np.absolute(H) < 10 * minmag
        H[singular] = 0
        tau_g = -np.diff(np.unwrap(np.angle(H)))/np.diff(w)

    elif alg.lower() == 'jos':
        #logger.info("Octave / JOS!")
        try: len(a)
        except TypeError:
            a = 1; oa = 0 # a is a scalar or empty -> order of a = 0
            c = b
            try: len(b)
            except TypeError:
               logger.error('No proper filter coefficients: len(a) = len(b) = 1 !')
        else:
            oa = len(a)-1               # order of denom. a(z) resp. a(s)
            c = np.convolve(b, a[::-1])  # equivalent FIR polynome
                                        # c(z) = b(z) * a(1/z)*z^(-oa)
        try: len(b)
        except TypeError: b=1; ob=0     # b is a scalar or empty -> order of b = 0
        else:
            ob = len(b)-1               # order of numerator b(z)

        if analog:
            a_b = np.convolve(a,b)
            if ob > 1:
                br_a = np.convolve(b[1:] * np.arange(1,ob), a)
            else:
                br_a = 0
            ar_b = np.convolve(a[1:] * np.arange(1,oa), b)

            num = np.fft.fft(ar_b - br_a, nfft)
            den = np.fft.fft(a_b,nfft)
        else:
            oc = oa + ob                  # order of c(z)
            cr = c * np.arange(c.size) # multiply with ramp -> derivative of c wrt 1/z

            num = np.fft.fft(cr,nfft) #
            den = np.fft.fft(c,nfft)  #
    #
        polebins = np.where(abs(den) < minmag)[0] # find zeros of denominator

        if np.size(polebins) > 0 and verbose:  # check whether polebins array is empty
            logger.warning('*** grpdelay warning: group delay singular -> setting to 0 at:')
            for i in polebins:
                logger.warning('f = {0} '.format((fs*i/nfft)))
                num[i] = 0
                den[i] = 1

        if analog: # this doesn't work yet
            tau_g = np.real(num / den)
        else:
            tau_g = np.real(num / den) - oa
    #
        if not whole:
            nfft = nfft/2
            tau_g = tau_g[0:nfft]
            w = w[0:nfft]

    elif alg.lower() == "scipy":
        #logger.info("Scipy!")

###############################################################################
#
# group_delay implementation copied and adapted from scipy.signal (0.16)
#
###############################################################################

        # if w is None:
        #     w = 512
    
        # if isinstance(w, int):
        #     if whole:
        #         w = np.linspace(0, 2 * pi, w, endpoint=False)
        #     else:
        #         w = np.linspace(0, pi, w, endpoint=False)
    
        w = np.atleast_1d(w)
        b, a = map(np.atleast_1d, (b, a))
        c = np.convolve(b, a[::-1])   # coefficients of equivalent FIR polynome
        cr = c * np.arange(c.size)    #  and of the ramped polynome
        z = np.exp(-1j * w) # complex frequency points around the unit circle
        den = np.polyval(c[::-1], z)  # evaluate polynome 
        num = np.polyval(cr[::-1], z) # and ramped polynome 

        singular = np.absolute(den) < 10 * minmag
        if np.any(singular) and verbose:
            singularity_list = ", ".join("{0:.3f}".format(ws/(2*pi)) for ws in w[singular])
            logger.warning("pyfda_lib.py:grpdelay:\n"
                "The group delay is singular at F = [{0:s}], setting to 0".format(singularity_list)
            )
    
        tau_g[~singular] = np.real(num[~singular] / den[~singular]) - a.size + 1

    elif alg.lower() == "shpak":
        #logger.info("Using Shpak's algorithm")
        if sos:
            w, tau_g = sos_group_delayz(b, w, fs=fs)
        else:
            w, tau_g = group_delayz(b,a, w, fs=fs)
            
    else:
        logger.error('Unknown algorithm "{0}"!'.format(alg))
        tau_g = np.zeros_like(w)
    
    time_1 = time.perf_counter_ns()
    delta_t = time_1 - time_0
    if verbose:
        logger.info("grpdelay calculation ({0}): {1:.3g} ms".format(alg, delta_t/1.e6))
    return w, tau_g
    
# ----------------------------------------------------------------------
    
def group_delayz(b, a, w, plot=None, fs=2*np.pi):
    """
    Compute the group delay of digital filter.

    Parameters
    ----------
    b : array_like
        Numerator of a linear filter.
    a : array_like
        Denominator of a linear filter.
    w : array_like
        Frequencies in the same units as `fs`.
    plot : callable
        A callable that takes two arguments. If given, the return parameters
        `w` and `gd` are passed to plot.
    fs : float, optional
        The angular sampling frequency of the digital system.

    Returns
    -------
    w : ndarray
        The frequencies at which `gd` was computed, in the same units as `fs`.
    gd : ndarray
        The group delay in seconds.
    """
    b, a = map(np.atleast_1d, (b, a))
    if len(a) == 1:
        # scipy.signal.group_delay returns gd in samples thus scaled by 1/fs
        gd = sig.group_delay((b, a), w=w, fs=fs)[1] # / fs
    else:
        sos = sig.tf2sos(b, a)
        gd = sos_group_delayz(sos, w, plot, fs)[1]
    if plot is not None:
        plot(w, gd)
    return w, gd

#==============================================================================
#
# The *_group_delayz routines and subroutines have been copied from 
#
# https://github.com/spatialaudio/group-delay-of-filters
#
# committed by Nara Hahn under MIT license
#
#==============================================================================
def sos_group_delayz(sos, w, plot=None, fs=2*np.pi):
    """
    Compute group delay of digital filter in SOS format.

    Parameters
    ----------
    sos : array_like
        Array of second-order filter coefficients, must have shape
        ``(n_sections, 6)``. Each row corresponds to a second-order
        section, with the first three columns providing the numerator
        coefficients and the last three providing the denominator
        coefficients.
    w : array_like
        Frequencies in the same units as `fs`.
    plot : callable, optional
        A callable that takes two arguments. If given, the return parameters
        `w` and `gd` are passed to plot.
    fs : float, optional
        The sampling frequency of the digital system.

    Returns
    -------
    w : ndarray
        The frequencies at which `gd` was computed.
    gd : ndarray
        The group delay in seconds.
    """
    sos, n_sections = sig.filter_design._validate_sos(sos)
    if n_sections == 0:
        raise ValueError('Cannot compute group delay with no sections')
    gd = 0
    for biquad in sos:
        gd += quadfilt_group_delayz(biquad[:3], w, fs)[1]
        gd -= quadfilt_group_delayz(biquad[3:], w, fs)[1]
    if plot is not None:
        plot(w, gd)
    return w, gd


def quadfilt_group_delayz(b, w, fs=2*np.pi):
    """
    Compute group delay of 2nd-order digital filter.

    Parameters
    ----------
    b : array_like
        Coefficients of a 2nd-order digital filter.
    w : array_like
        Frequencies in the same units as `fs`.
    fs : float, optional
        The sampling frequency of the digital system.

    Returns
    -------
    w : ndarray
        The frequencies at which `gd` was computed.
    gd : ndarray
        The group delay in seconds.
    """
    W = 2 * pi * w / fs
    c1 = np.cos(W)
    c2 = np.cos(2*W)
    u0, u1, u2 = b**2  # b[0]**2, b[1]**2, b[2]**2
    v0, v1, v2 = b * np.roll(b, -1)  # b[0]*b[1], b[1]*b[2], b[2]*b[0]
    num = (u1+2*u2) + (v0+3*v1)*c1 + 2*v2*c2
    den = (u0+u1+u2) + 2*(v0+v1)*c1 + 2*v2*c2
    return w, 2 * pi / fs * num / den


def zpk_group_delay(z, p, k, w, plot=None, fs=2*np.pi):
    """
    Compute group delay of digital filter in zpk format.

    Parameters
    ----------
    z : array_like
        Zeroes of a linear filter
    p : array_like
        Poles of a linear filter
    k : scalar
        Gain of a linear filter
    w : array_like
        Frequencies in the same units as `fs`.
    plot : callable, optional
        A callable that takes two arguments. If given, the return parameters
        `w` and `gd` are passed to plot.
    fs : float, optional
        The sampling frequency of the digital system.

    Returns
    -------
    w : ndarray
        The frequencies at which `gd` was computed.
    gd : ndarray
        The group delay in seconds.
    """
    gd = 0
    for z_i in z:
        gd += zorp_group_delayz(z_i, w)[1]
    for p_i in p:
        gd -= zorp_group_delayz(p_i, w)[1]
    if plot is not None:
        plot(w, gd)
    return w, gd


def zorp_group_delayz(zorp, w, fs=1):
    """
    Compute group delay of digital filter with a single zero/pole.

    Parameters
    ----------
    zorp : complex
        Zero or pole of a 1st-order linear filter
    w : array_like
        Frequencies in the same units as `fs`.
    fs : float, optional
        The sampling frequency of the digital system.

    Returns
    -------
    w : ndarray
        The frequencies at which `gd` was computed.
    gd : ndarray
        The group delay in seconds.
    """
    W = 2 * pi * w / fs
    r, phi = np.abs(zorp), np.angle(zorp)
    r2 = r**2
    cos = np.cos(W - phi)
    return w, 2 * pi * (r2 - r*cos) / (r2 + 1 - 2*r*cos)
