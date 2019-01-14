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
# Copyright(C) 2013-2019 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik.

from .. import utilities
from ..domain_tuple import DomainTuple
from ..field import Field
from ..linearization import Linearization
from ..sugar import makeOp, makeDomain
from .operator import Operator
from .sampling_enabler import SamplingEnabler
from .sandwich_operator import SandwichOperator
from .simple_linear_operators import VdotOperator


class EnergyOperator(Operator):
    """ Basis class EnergyOperator.

    Operator which has a scalar domain as target domain.
    
    An EnergyOperator returns a scalar for a field, and a linearized 

    Typical usage in IFT: 
    as an information Hamiltonian ( = negative log probability) 
    or as a Gibbs free energy ( = averaged Hamiltonian), aka Kullbach-Leibler 
    divergence. 
    
    An EnergyOperator can also provide its gradient as an EndomorphicOperator 
    that converts a field into a field, the gradient of the Hamiltonian at the 
    field location. 
    """
    _target = DomainTuple.scalar_domain()


class SquaredNormOperator(EnergyOperator):
    """ NIFTy class for a squared norm energy.

    The  NIFTy SquaredNormOperator class derives from the EnergyOperator class.

    A SquaredNormOperator represents a field energy E that is the L2 norm of a 
    field f: E = f^dagger f
    """   
    def __init__(self, domain):
        self._domain = domain

    def apply(self, x):
        self._check_input(x)
        if isinstance(x, Linearization):
            val = Field.scalar(x.val.vdot(x.val))
            jac = VdotOperator(2*x.val)(x.jac)
            return x.new(val, jac)
        return Field.scalar(x.vdot(x))


class QuadraticFormOperator(EnergyOperator):
    """ NIFTy class for quadratic field energies.

    The  NIFTy QuadraticFormOperator derives from the EnergyOperator class.

    It represents a field energy E that is a quadratic form of a field f with 
    kernel op: E = f^dagger op f /2 
    """      
    def __init__(self, op):
        from .endomorphic_operator import EndomorphicOperator
        if not isinstance(op, EndomorphicOperator):
            raise TypeError("op must be an EndomorphicOperator")
        self._op = op
        self._domain = op.domain

    def apply(self, x):
        self._check_input(x)
        if isinstance(x, Linearization):
            t1 = self._op(x.val)
            jac = VdotOperator(t1)(x.jac)
            val = Field.scalar(0.5*x.val.vdot(t1))
            return x.new(val, jac)
        return Field.scalar(0.5*x.vdot(self._op(x)))


class GaussianEnergy(EnergyOperator):
    def __init__(self, mean=None, covariance=None, domain=None):
        self._domain = None
        if mean is not None:
            self._checkEquivalence(mean.domain)
        if covariance is not None:
            self._checkEquivalence(covariance.domain)
        if domain is not None:
            self._checkEquivalence(domain)
        if self._domain is None:
            raise ValueError("no domain given")
        self._mean = mean
        if covariance is None:
            self._op = SquaredNormOperator(self._domain).scale(0.5)
        else:
            self._op = QuadraticFormOperator(covariance.inverse)
        self._icov = None if covariance is None else covariance.inverse

    def _checkEquivalence(self, newdom):
        newdom = makeDomain(newdom)
        if self._domain is None:
            self._domain = newdom
        else:
            if self._domain != newdom:
                raise ValueError("domain mismatch")

    def apply(self, x):
        self._check_input(x)
        residual = x if self._mean is None else x-self._mean
        res = self._op(residual).real
        if not isinstance(x, Linearization) or not x.want_metric:
            return res
        metric = SandwichOperator.make(x.jac, self._icov)
        return res.add_metric(metric)


class PoissonianEnergy(EnergyOperator):
    def __init__(self, d):
        self._d = d
        self._domain = DomainTuple.make(d.domain)

    def apply(self, x):
        self._check_input(x)
        res = x.sum() - x.log().vdot(self._d)
        if not isinstance(x, Linearization):
            return Field.scalar(res)
        if not x.want_metric:
            return res
        metric = SandwichOperator.make(x.jac, makeOp(1./x.val))
        return res.add_metric(metric)


class InverseGammaLikelihood(EnergyOperator):
    def __init__(self, d):
        self._d = d
        self._domain = DomainTuple.make(d.domain)

    def apply(self, x):
        self._check_input(x)
        res = 0.5*(x.log().sum() + (1./x).vdot(self._d))
        if not isinstance(x, Linearization):
            return Field.scalar(res)
        if not x.want_metric:
            return res
        metric = SandwichOperator.make(x.jac, makeOp(0.5/(x.val**2)))
        return res.add_metric(metric)


class BernoulliEnergy(EnergyOperator):
    def __init__(self, d):
        self._d = d
        self._domain = DomainTuple.make(d.domain)

    def apply(self, x):
        self._check_input(x)
        v = x.log().vdot(-self._d) - (1.-x).log().vdot(1.-self._d)
        if not isinstance(x, Linearization):
            return Field.scalar(v)
        if not x.want_metric:
            return v
        met = makeOp(1./(x.val*(1.-x.val)))
        met = SandwichOperator.make(x.jac, met)
        return v.add_metric(met)


class Hamiltonian(EnergyOperator):
    def __init__(self, lh, ic_samp=None):
        self._lh = lh
        self._prior = GaussianEnergy(domain=lh.domain)
        self._ic_samp = ic_samp
        self._domain = lh.domain

    def apply(self, x):
        self._check_input(x)
        if (self._ic_samp is None or not isinstance(x, Linearization) or
                not x.want_metric):
            return self._lh(x)+self._prior(x)
        else:
            lhx, prx = self._lh(x), self._prior(x)
            mtr = SamplingEnabler(lhx.metric, prx.metric.inverse,
                                  self._ic_samp, prx.metric.inverse)
            return (lhx+prx).add_metric(mtr)

    def __repr__(self):
        subs = 'Likelihood:\n{}'.format(utilities.indent(self._lh.__repr__()))
        subs += '\nPrior: Quadratic{}'.format(self._lh.domain.keys())
        return 'Hamiltonian:\n' + utilities.indent(subs)


class SampledKullbachLeiblerDivergence(EnergyOperator):
    def __init__(self, h, res_samples):
        """
        # MR FIXME: does h have to be a Hamiltonian? Couldn't it be any energy?
        h: Hamiltonian
        N: Number of samples to be used
        """
        self._h = h
        self._domain = h.domain
        self._res_samples = tuple(res_samples)

    def apply(self, x):
        self._check_input(x)
        mymap = map(lambda v: self._h(x+v), self._res_samples)
        return utilities.my_sum(mymap) * (1./len(self._res_samples))
