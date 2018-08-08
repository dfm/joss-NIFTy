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

from .. import dobj
from ..compat import *
from ..field import Field
from ..logger import logger
from .iteration_controller import IterationController
from .minimizer import Minimizer


def _toArray(fld):
    return fld.to_global_data().reshape(-1)


def _toArray_rw(fld):
    return fld.to_global_data_rw().reshape(-1)


def _toField(arr, dom):
    return Field.from_global_data(dom, arr.reshape(dom.shape).copy())


class _MinHelper(object):
    def __init__(self, energy):
        self._energy = energy
        self._domain = energy.position.domain

    def _update(self, x):
        pos = _toField(x, self._domain)
        if (pos != self._energy.position).any():
            self._energy = self._energy.at(pos)

    def fun(self, x):
        self._update(x)
        return self._energy.value

    def jac(self, x):
        self._update(x)
        return _toArray_rw(self._energy.gradient)

    def hessp(self, x, p):
        self._update(x)
        res = self._energy.metric(_toField(p, self._domain))
        return _toArray_rw(res)


class ScipyMinimizer(Minimizer):
    """Scipy-based minimizer

    Parameters
    ----------
    method     : str
        The selected Scipy minimization method.
    options    : dictionary
        A set of custom options for the selected minimizer.
    """

    def __init__(self, method, options, need_hessp, bounds):
        super(ScipyMinimizer, self).__init__()
        if not dobj.is_numpy():
            raise NotImplementedError
        self._method = method
        self._options = options
        self._need_hessp = need_hessp
        self._bounds = bounds

    def __call__(self, energy):
        import scipy.optimize as opt
        hlp = _MinHelper(energy)
        energy = None  # drop handle, since we don't need it any more
        bounds = None
        if self._bounds is not None:
            if len(self._bounds) == 2:
                lo = self._bounds[0]
                hi = self._bounds[1]
                bounds = [(lo, hi)]*hlp._energy.position.size
            else:
                raise ValueError("unrecognized bounds")

        x = _toArray_rw(hlp._energy.position)
        hessp = hlp.hessp if self._need_hessp else None
        r = opt.minimize(hlp.fun, x, method=self._method, jac=hlp.jac,
                         hessp=hessp, options=self._options, bounds=bounds)
        if not r.success:
            logger.error("Problem in Scipy minimization: {}".format(r.message))
            return hlp._energy, IterationController.ERROR
        return hlp._energy, IterationController.CONVERGED


def NewtonCG(xtol, maxiter, disp=False):
    """Returns a ScipyMinimizer object carrying out the Newton-CG algorithm.

    See Also
    --------
    ScipyMinimizer
    """
    options = {"xtol": xtol, "maxiter": maxiter, "disp": disp}
    return ScipyMinimizer("Newton-CG", options, True, None)


def L_BFGS_B(ftol, gtol, maxiter, maxcor=10, disp=False, bounds=None):
    """Returns a ScipyMinimizer object carrying out the L-BFGS-B algorithm.

    See Also
    --------
    ScipyMinimizer
    """
    options = {"ftol": ftol, "gtol": gtol, "maxiter": maxiter,
               "maxcor": maxcor, "disp": disp}
    return ScipyMinimizer("L-BFGS-B", options, False, bounds)


class ScipyCG(Minimizer):
    def __init__(self, tol, maxiter):
        super(ScipyCG, self).__init__()
        if not dobj.is_numpy():
            raise NotImplementedError
        self._tol = tol
        self._maxiter = maxiter

    def __call__(self, energy, preconditioner=None):
        from scipy.sparse.linalg import LinearOperator as scipy_linop, cg
        from .quadratic_energy import QuadraticEnergy
        if not isinstance(energy, QuadraticEnergy):
            raise ValueError("need a quadratic energy for CG")

        class mymatvec(object):
            def __init__(self, op):
                self._op = op

            def __call__(self, inp):
                return _toArray(self._op(_toField(inp, self._op.domain)))

        op = energy._A
        b = _toArray(energy._b)
        sx = _toArray(energy.position)
        sci_op = scipy_linop(shape=(op.domain.size, op.target.size),
                             matvec=mymatvec(op))
        prec_op = None
        if preconditioner is not None:
            prec_op = scipy_linop(shape=(op.domain.size, op.target.size),
                                  matvec=mymatvec(preconditioner))
        res, stat = cg(sci_op, b, x0=sx, tol=self._tol, M=prec_op,
                       maxiter=self._maxiter)
        stat = (IterationController.CONVERGED if stat >= 0 else
                IterationController.ERROR)
        return energy.at(_toField(res, op.domain)), stat
