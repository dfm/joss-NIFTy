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
# Copyright(C) 2021 Max-Planck-Society
# Author: Philipp Arras

import numpy as np
from .operator import Operator
from .energy_operators import EnergyOperator, LikelihoodEnergyOperator
from .linear_operator import LinearOperator
from .endomorphic_operator import EndomorphicOperator


try:
    import jax
    jax.config.update("jax_enable_x64", True)
    __all__ = ["JaxOperator", "JaxLikelihoodEnergyOperator"]
except ImportError:
    __all__ = []

def _jax2np(obj):
    if isinstance(obj, dict):
        return {kk: np.array(vv) for kk, vv in obj.items()}
    return np.array(obj)


class JaxOperator(Operator):
    """Wrap a jax function as nifty operator.

    Parameters
    ----------
    domain : DomainTuple or MultiDomain
        Domain of the operator.

    target : DomainTuple or MultiDomain
        Target of the operator.

    func : callable
        The jax function that is evaluated by the operator. It has to be
        implemented in terms of `jax.numpy` calls. If `domain` is a
        `DomainTuple`, `func` takes a `dict` as argument and like-wise for the
        target.
    """
    def __init__(self, domain, target, func):
        from ..sugar import makeDomain
        self._domain = makeDomain(domain)
        self._target = makeDomain(target)
        self._func = jax.jit(func)
        self._vjp = jax.jit(lambda x: jax.vjp(func, x))
        self._fwd = jax.jit(lambda x, y: jax.jvp(self._func, (x,), (y,))[1])

    def apply(self, x):
        from ..sugar import is_linearization, makeField
        self._check_input(x)
        if is_linearization(x):
            res, bwd = self._vjp(x.val.val)
            fwd = lambda y: self._fwd(x.val.val, y)
            jac = _JaxJacobian(self._domain, self._target, fwd, bwd)
            return x.new(makeField(self._target, _jax2np(res)), jac)
        return makeField(self._target, _jax2np(self._func(x.val)))

    def _simplify_for_constant_input_nontrivial(self, c_inp):
        func2 = lambda x: self._func({**x, **c_inp.val})
        dom = {kk: vv for kk, vv in self._domain.items()
                if kk not in c_inp.keys()}
        return None, JaxOperator(dom, self._target, func2)


class JaxLikelihoodEnergyOperator(LikelihoodEnergyOperator):
    """Wrap a jax function as nifty likelihood energy operator.

    Parameters
    ----------
    domain : DomainTuple or MultiDomain
        Domain of the operator.

    func : callable
        The jax function that is evaluated by the operator. It has to be
        implemented in terms of `jax.numpy` calls. If `domain` is a
        `DomainTuple`, `func` takes a `dict` as argument and like-wise for the
        target. It needs to map to a scalar.

    transformation : Operator, optional
        Coordinate transformation to Euclidean space.

    sampling_dtype : dtype, optional
        The dtype that shall be used for drawing samples from the metric of the
        likelihood.
    """
    def __init__(self, domain, func, transformation=None, sampling_dtype=None):
        from ..sugar import makeDomain
        self._domain = makeDomain(domain)
        self._func = jax.jit(func)
        self._grad = jax.jit(jax.grad(func))
        self._dt = sampling_dtype
        self._trafo = transformation

    def get_transformation(self):
        if self._trafo is None:
            s = self.__name__ + " was instantiated without `transformation`"
            raise RuntimeError(s)
        return self._dt, self._trafo

    def apply(self, x):
        from ..sugar import is_linearization, makeField
        from .simple_linear_operators import VdotOperator
        from ..linearization import Linearization
        self._check_input(x)
        lin = is_linearization(x)
        val = x.val.val if lin else x.val
        res = makeField(self._target, _jax2np(self._func(val)))
        if not lin:
            return res
        jac = VdotOperator(makeField(self._domain, _jax2np(self._grad(val))))
        res = x.new(res, jac)
        if not x.want_metric:
            return res
        return res.add_metric(self.get_metric_at(x.val))

    def _simplify_for_constant_input_nontrivial(self, c_inp):
        func2 = lambda x: self._func({**x, **c_inp.val})
        dom = {kk: vv for kk, vv in self._domain.items()
                if kk not in c_inp.keys()}
        _, trafo = self._trafo.simplify_for_constant_input(c_inp)
        if isinstance(self._dt, dict):
            dt = {kk: self._dt[kk] for kk in dom.keys()}
        else:
            dt = self._dt
        return None, JaxLikelihoodEnergyOperator(dom, func2, trafo, dt)


class _JaxJacobian(LinearOperator):
    def __init__(self, domain, target, func, adjfunc):
        from ..sugar import makeDomain
        self._domain = makeDomain(domain)
        self._target = makeDomain(target)
        self._func = func
        self._adjfunc = adjfunc
        self._capability = self.TIMES | self.ADJOINT_TIMES

    def apply(self, x, mode):
        from ..sugar import makeField
        self._check_input(x, mode)
        if mode == self.TIMES:
            fx = self._func(x.val)
        else:
            fx = self._adjfunc(x.val)[0]
        return makeField(self._tgt(mode), _jax2np(fx))
