from __future__ import absolute_import, division, print_function

import numpy as np

from .compat import *
from .field import Field
from .multi.multi_field import MultiField
from .sugar import makeOp


class Linearization(object):
    def __init__(self, val, jac, metric=None):
        self._val = val
        self._jac = jac
        self._metric = metric

    @property
    def domain(self):
        return self._jac.domain

    @property
    def target(self):
        return self._jac.target

    @property
    def val(self):
        return self._val

    @property
    def jac(self):
        return self._jac

    @property
    def gradient(self):
        """Only available if target is a scalar"""
        return self._jac.adjoint_times(Field(self._jac.target, 1.))

    @property
    def metric(self):
        """Only available if target is a scalar"""
        return self._metric

    def __getitem__(self, name):
        from .operators.field_adapter import FieldAdapter
        return Linearization(self._val[name], FieldAdapter(self.domain, name))

    def __neg__(self):
        return Linearization(
            -self._val, self._jac.chain(-1),
            None if self._metric is None else self._metric.chain(-1))

    def __add__(self, other):
        if isinstance(other, Linearization):
            from .operators.relaxed_sum_operator import RelaxedSumOperator
            met = None
            if self._metric is not None and other._metric is not None:
                met = RelaxedSumOperator((self._metric, other._metric))
            return Linearization(
                self._val.unite(other._val),
                RelaxedSumOperator((self._jac, other._jac)), met)
        if isinstance(other, (int, float, complex, Field, MultiField)):
            return Linearization(self._val+other, self._jac, self._metric)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        return self.__add__(-other)

    def __rsub__(self, other):
        return (-self).__add__(other)

    def __mul__(self, other):
        from .sugar import makeOp
        if isinstance(other, Linearization):
            d1 = makeOp(self._val)
            d2 = makeOp(other._val)
            return Linearization(
                self._val*other._val,
                d2.chain(self._jac) + d1.chain(other._jac))
        if isinstance(other, (int, float, complex)):
            # if other == 0:
            #     return ...
            met = None if self._metric is None else self._metric.chain(other)
            return Linearization(self._val*other, self._jac.chain(other), met)
        if isinstance(other, (Field, MultiField)):
            d2 = makeOp(other)
            return Linearization(self._val*other, d2.chain(self._jac))
        raise TypeError

    def __rmul__(self, other):
        from .sugar import makeOp
        if isinstance(other, (int, float, complex)):
            return Linearization(self._val*other, self._jac.chain(other))
        if isinstance(other, (Field, MultiField)):
            d1 = makeOp(other)
            return Linearization(self._val*other, d1.chain(self._jac))

    def vdot(self, other):
        from .domain_tuple import DomainTuple
        from .operators.vdot_operator import VdotOperator
        if isinstance(other, (Field, MultiField)):
            return Linearization(
                Field(DomainTuple.scalar_domain(),self._val.vdot(other)),
                VdotOperator(other).chain(self._jac))
        return Linearization(
            Field(DomainTuple.scalar_domain(),self._val.vdot(other._val)),
            VdotOperator(self._val).chain(other._jac) +
            VdotOperator(other._val).chain(self._jac))

    def sum(self):
        from .domain_tuple import DomainTuple
        from .operators.vdot_operator import SumReductionOperator
        from .sugar import full
        return Linearization(
            Field(DomainTuple.scalar_domain(), self._val.sum()),
            SumReductionOperator(self._jac.target).chain(self._jac))

    def exp(self):
        tmp = self._val.exp()
        return Linearization(tmp, makeOp(tmp).chain(self._jac))

    def log(self):
        tmp = self._val.log()
        return Linearization(tmp, makeOp(1./self._val).chain(self._jac))

    def tanh(self):
        tmp = self._val.tanh()
        return Linearization(tmp, makeOp(1.-tmp**2).chain(self._jac))

    def positive_tanh(self):
        tmp = self._val.tanh()
        tmp2 = 0.5*(1.+tmp)
        return Linearization(tmp2, makeOp(0.5*(1.-tmp**2)).chain(self._jac))

    def add_metric(self, metric):
        return Linearization(self._val, self._jac, metric)

    @staticmethod
    def make_var(field):
        from .operators.scaling_operator import ScalingOperator
        return Linearization(field, ScalingOperator(1., field.domain))

    @staticmethod
    def make_const(field):
        from .operators.null_operator import NullOperator
        return Linearization(field, NullOperator({}, field.domain))
