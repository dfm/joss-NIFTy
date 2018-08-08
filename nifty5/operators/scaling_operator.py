# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright(C) 2013-2018 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik
# and financially supported by the Studienstiftung des deutschen Volkes.

from __future__ import absolute_import, division, print_function

import numpy as np

from ..compat import *
from ..domain_tuple import DomainTuple
from ..field import Field
from ..multi_field import MultiField
from ..sugar import full
from .endomorphic_operator import EndomorphicOperator


class ScalingOperator(EndomorphicOperator):
    """Operator which multiplies a Field with a scalar.

    The NIFTy ScalingOperator class is a subclass derived from the
    EndomorphicOperator. It multiplies an input field with a given factor.

    Parameters
    ----------
    factor : scalar
        The multiplication factor
    domain : Domain or tuple of Domain or DomainTuple
        The domain on which the Operator's input Field lives.

    Notes
    -----
    Formally, this operator always supports all operation modes (times,
    adjoint_times, inverse_times and inverse_adjoint_times), even if `factor`
    is 0 or infinity. It is the user's responsibility to apply the operator
    only in appropriate ways (e.g. call inverse_times only if `factor` is
    nonzero).

    This shortcoming will hopefully be fixed in the future.
    """

    def __init__(self, factor, domain):
        from ..sugar import makeDomain

        if not np.isscalar(factor):
            raise TypeError("Scalar required")
        self._factor = factor
        self._domain = makeDomain(domain)
        self._capability = self._all_ops

    def apply(self, x, mode):
        self._check_input(x, mode)
        fct = self._factor
        if fct == 1.:
            return x
        if fct == 0.:
            return full(self.domain, 0.)
        if (mode & 10) != 0:
            fct = np.conj(fct)
        if (mode & 12) != 0:
            fct = 1./fct
        return x*fct

    def _flip_modes(self, trafo):
        fct = self._factor
        if trafo & self.ADJOINT_BIT:
            fct = np.conj(fct)
        if trafo & self.INVERSE_BIT:
            fct = 1./fct
        return ScalingOperator(fct, self._domain)

    def draw_sample(self, from_inverse=False, dtype=np.float64):
        fct = self._factor
        if fct.imag != 0. or fct.real < 0.:
            raise ValueError("operator not positive definite")
        if fct.real == 0. and from_inverse:
            raise ValueError("operator not positive definite")
        fct = 1./np.sqrt(fct) if from_inverse else np.sqrt(fct)
        cls = Field if isinstance(self._domain, DomainTuple) else MultiField
        return cls.from_random(
            random_type="normal", domain=self._domain, std=fct, dtype=dtype)
