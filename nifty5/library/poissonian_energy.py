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

from numpy import inf, isnan

from ..compat import *
from ..operators.operator import EnergyOperator
from ..operators.sandwich_operator import SandwichOperator
from ..sugar import makeOp
from ..linearization import Linearization


class PoissonianEnergy(EnergyOperator):
    def __init__(self, op, d):
        self._op, self._d = op, d

    @property
    def domain(self):
        return self._op.domain

    def apply(self, x):
        x = self._op(x)
        res = x.sum() - x.log().vdot(self._d)
        if not isinstance(x, Linearization):
            return res
        metric = SandwichOperator.make(x.jac, makeOp(1./x.val))
        return res.add_metric(metric)
